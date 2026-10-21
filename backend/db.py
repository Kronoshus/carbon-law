import os, json, sqlite3

DATABASE_URL = os.environ.get("DATABASE_URL")

def _conn():
    if DATABASE_URL and DATABASE_URL.startswith("postgres"):
        import psycopg
        return psycopg.connect(DATABASE_URL)
    path = os.environ.get("CARBON_DB_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "carbon.db"))
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c = _conn()
    cur = c.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS collections (name TEXT PRIMARY KEY, data TEXT NOT NULL)")
    c.commit()
    c.close()

def load_collection(name, default):
    c = _conn()
    cur = c.cursor()
    placeholder = "%s" if DATABASE_URL and DATABASE_URL.startswith("postgres") else "?"
    cur.execute(f"SELECT data FROM collections WHERE name={placeholder}", (name,))
    row = cur.fetchone()
    c.close()
    if row:
        try:
            return json.loads(row[0] if not hasattr(row,'__getitem__') else row[0])
        except Exception:
            return default
    return default

def save_collection(name, data):
    c = _conn()
    cur = c.cursor()
    payload = json.dumps(data)
    # upsert
    placeholder = "%s" if DATABASE_URL and DATABASE_URL.startswith("postgres") else "?"
    try:
        cur.execute(f"INSERT INTO collections (name,data) VALUES ({placeholder},{placeholder}) ON CONFLICT(name) DO UPDATE SET data=excluded.data", (name, payload))
    except Exception:
        cur.execute(f"DELETE FROM collections WHERE name={placeholder}", (name,))
        cur.execute(f"INSERT INTO collections (name,data) VALUES ({placeholder},{placeholder})", (name, payload))
    c.commit()
    c.close()

init_db()
