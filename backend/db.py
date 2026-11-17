import os, json, sqlite3, threading, contextlib

_configured_key = None
DATABASE_URL = None
POSTGRES = False
PLACEHOLDER = "?"
RECONNECT_ERRORS = ()

def _refresh_config():
    global DATABASE_URL, POSTGRES, PLACEHOLDER, RECONNECT_ERRORS, _configured_key
    DATABASE_URL = os.environ.get("DATABASE_URL")
    POSTGRES = bool(DATABASE_URL and DATABASE_URL.startswith("postgres"))
    PLACEHOLDER = "%s" if POSTGRES else "?"
    if POSTGRES:
        import psycopg
        RECONNECT_ERRORS = (psycopg.OperationalError, psycopg.InterfaceError)
    else:
        RECONNECT_ERRORS = ()

_refresh_config()

# The request lock in app.py already serializes callers; this keeps db.py safe on its own.
# RLock so transaction() and execute()/query() can nest.
_lock = threading.RLock()
_conn = None
_configured = None
_last_saved = {}
_in_tx = False


def _connect():
    _refresh_config()
    if POSTGRES:
        import psycopg
        # prepare_threshold=None: transaction-mode poolers (e.g. Supabase port 6543) reject prepared statements.
        return psycopg.connect(DATABASE_URL, autocommit=True, prepare_threshold=None, connect_timeout=10)
    path = os.environ.get("CARBON_DB_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "carbon.db"))
    return sqlite3.connect(path, isolation_level=None, check_same_thread=False)


def _ensure_conn():
    global _conn, _configured
    _refresh_config()
    key = (os.environ.get("DATABASE_URL"), os.environ.get("CARBON_DB_PATH"))
    if _conn is not None and _configured != key:
        try:
            _conn.close()
        except Exception:
            pass
        _conn = None
    if _conn is None:
        _conn = _connect()
        _configured = key
        try:
            init_db()
        except Exception:
            pass
    return _conn


def _translate(sql):
    _refresh_config()
    if POSTGRES:
        return sql.replace("?", "%s")
    return sql


def _exec_cursor(sql, params=()):
    global _conn
    _ensure_conn()
    global _conn
    try:
        cur = _conn.cursor()
        cur.execute(_translate(sql), params)
        return cur
    except RECONNECT_ERRORS:
        try:
            _conn.close()
        except Exception:
            pass
        _conn = None
        _ensure_conn()
        cur = _conn.cursor()
        cur.execute(_translate(sql), params)
        return cur


def _run(sql, params=()):
    cur = _exec_cursor(sql, params)
    return cur.fetchone() if cur.description else None


def _execute(sql, params=()):
    cur = _exec_cursor(sql, params)
    return cur.fetchone() if cur.description else None


_run = _execute


def execute(sql, params=()):
    """Execute a statement with `?` placeholders (translated for Postgres). Returns rowcount."""
    cur = _exec_cursor(sql, params)
    return cur.rowcount


def query(sql, params=()):
    """Run a SELECT with `?` placeholders; return list of rows."""
    cur = _exec_cursor(sql, params)
    if cur.description is None:
        return []
    return cur.fetchall()


class _TxConn:
    """Wrapper around a connection whose execute() translates `?` placeholders."""

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=()):
        cur = self._conn.cursor()
        cur.execute(_translate(sql), params)
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
    global _in_tx
    _refresh_config()
    conn = _ensure_conn()
    with _lock:
        if POSTGRES:
            prev_autocommit = getattr(conn, "autocommit", True)
            conn.autocommit = False
        else:
            conn.execute("BEGIN")
        _in_tx = True
        wrapped = _TxConn(conn)
        try:
            yield wrapped
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            raise
        finally:
            _in_tx = False
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
