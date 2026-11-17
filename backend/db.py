import os, json, sqlite3, threading, contextlib

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
# RLock so transaction() and execute()/query() can nest within one thread.
_lock = threading.RLock()
_conn = None
_last_saved = {}


def _connect():
    if POSTGRES:
        import psycopg
        # prepare_threshold=None: transaction-mode poolers (e.g. Supabase port 6543) reject prepared statements.
        return psycopg.connect(DATABASE_URL, autocommit=True, prepare_threshold=None, connect_timeout=10)
    path = os.environ.get("CARBON_DB_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "carbon.db"))
    return sqlite3.connect(path, isolation_level=None, check_same_thread=False)


def _ensure_conn():
    global _conn
    if _conn is None:
        _conn = _connect()
    return _conn


def _run(sql, params=()):
    global _conn
    try:
        conn = _ensure_conn()
        cur = conn.cursor()
        cur.execute(sql, params)
        return cur.fetchone() if cur.description else None
    except RECONNECT_ERRORS:
        _conn = None
        conn = _ensure_conn()
        cur = conn.cursor()
        cur.execute(sql, params)
        return cur.fetchone() if cur.description else None


def _execute(sql, params=()):
    global _conn
    try:
        conn = _ensure_conn()
        cur = conn.cursor()
        cur.execute(sql, params)
        return cur.fetchone() if cur.description else None
    except RECONNECT_ERRORS:
        _conn = None
        conn = _ensure_conn()
        cur = conn.cursor()
        cur.execute(sql, params)
        return cur.fetchone() if cur.description else None


def execute(sql, params=()):
    """Execute a statement with `?` placeholders (translated for Postgres). Returns rowcount."""
    translated = sql.replace("?", "%s") if POSTGRES else sql
    with _lock:
        global _conn
        try:
            conn = _ensure_conn()
            cur = conn.cursor()
            cur.execute(translated, params)
            return cur.rowcount
        except RECONNECT_ERRORS:
            _conn = None
            conn = _ensure_conn()
            cur = conn.cursor()
            cur.execute(translated, params)
            return cur.rowcount


def query(sql, params=()):
    """Run a SELECT with `?` placeholders; return list of rows."""
    translated = sql.replace("?", "%s") if POSTGRES else sql
    with _lock:
        global _conn
        try:
            conn = _ensure_conn()
            cur = conn.cursor()
            cur.execute(translated, params)
            return cur.fetchall() if cur.description else []
        except RECONNECT_ERRORS:
            _conn = None
            conn = _ensure_conn()
            cur = conn.cursor()
            cur.execute(translated, params)
            return cur.fetchall() if cur.description else []


class _TxConn:
    """Wrapper around a connection whose execute() translates `?` placeholders."""

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=()):
        translated = sql.replace("?", "%s") if POSTGRES else sql
        cur = self._conn.cursor()
        cur.execute(translated, params)
        return cur

    def cursor(self):
        return self._conn.cursor()

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def __getattr__(self, name):
        return getattr(self._conn, name)


@contextlib.contextmanager
def transaction():
    conn = _ensure_conn()
    with _lock:
        if POSTGRES:
            prev_autocommit = getattr(conn, "autocommit", True)
            conn.autocommit = False
        else:
            conn.execute("BEGIN")
        try:
            yield _TxConn(conn)
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            raise
        finally:
            if POSTGRES:
                try:
                    conn.autocommit = prev_autocommit
                except Exception:
                    pass


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
