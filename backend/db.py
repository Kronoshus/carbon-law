import os, json, sqlite3, threading

DATABASE_URL = os.environ.get("DATABASE_URL")
POSTGRES = bool(DATABASE_URL and DATABASE_URL.startswith("postgres"))
PLACEHOLDER = "%s" if POSTGRES else "?"

if POSTGRES:
    import psycopg
    # Hosted Postgres (Neon, Supabase) closes idle connections; reconnect once when that happens.
    RECONNECT_ERRORS = (psycopg.OperationalError, psycopg.InterfaceError)
else:
    RECONNECT_ERRORS = ()

# The request lock in app.py already serializes callers; this keeps db.py safe on its own.
_lock = threading.Lock()
_conn = None
_last_saved = {}

def _connect():
    if POSTGRES:
        # prepare_threshold=None: transaction-mode poolers (e.g. Supabase port 6543) reject prepared statements.
        return psycopg.connect(DATABASE_URL, autocommit=True, prepare_threshold=None, connect_timeout=10)
    path = os.environ.get("CARBON_DB_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "carbon.db"))
    return sqlite3.connect(path, isolation_level=None, check_same_thread=False)

def _run(sql, params):
    global _conn
    if _conn is None:
        _conn = _connect()
    cur = _conn.cursor()
    cur.execute(sql, params)
    return cur.fetchone() if cur.description else None

def _execute(sql, params=()):
    global _conn
    try:
        return _run(sql, params)
    except RECONNECT_ERRORS:
        _conn = None
        return _run(sql, params)

def init_db():
    with _lock:
        _execute("CREATE TABLE IF NOT EXISTS collections (name TEXT PRIMARY KEY, data TEXT NOT NULL)")

def load_collection(name, default):
    with _lock:
        row = _execute(f"SELECT data FROM collections WHERE name={PLACEHOLDER}", (name,))
        if not row:
            return default
        try:
            data = json.loads(row[0])
        except Exception:
            return default
        _last_saved[name] = row[0]
        return data

def save_collection(name, data):
    with _lock:
        payload = json.dumps(data)
        if _last_saved.get(name) == payload:
            return
        _execute(f"INSERT INTO collections (name,data) VALUES ({PLACEHOLDER},{PLACEHOLDER}) ON CONFLICT(name) DO UPDATE SET data=excluded.data", (name, payload))
        _last_saved[name] = payload

init_db()
