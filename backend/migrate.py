import os, sys, glob

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import db

# Migration files must not contain ';' inside a statement (naive splitter).


def _migrations_dir():
    return os.path.join(HERE, "migrations")


def _applied_versions():
    try:
        rows = db.query("SELECT version FROM schema_migrations")
        return {r[0] for r in rows}
    except Exception:
        return set()


def _split_sql(sql):
    return [chunk.strip() for chunk in sql.split(";") if chunk.strip()]


def _version_from_path(path):
    return os.path.splitext(os.path.basename(path))[0]


def run():
    applied = _applied_versions()
    newly = []
    for path in sorted(glob.glob(os.path.join(_migrations_dir(), "*.sql"))):
        version = _version_from_path(path)
        if version in applied:
            continue
        with open(path) as f:
            sql = f.read()
        with db.transaction() as conn:
            for stmt in _split_sql(sql):
                conn.execute(stmt)
            conn.execute("INSERT INTO schema_migrations(version) VALUES (?)", (version,))
        newly.append(version)
        applied.add(version)
    return newly


def pending():
    applied = _applied_versions()
    out = []
    for path in sorted(glob.glob(os.path.join(_migrations_dir(), "*.sql"))):
        v = _version_from_path(path)
        if v not in applied:
            out.append(v)
    return out


def main():
    res = run()
    print(f"applied {len(res)} migration(s): {res}")
    return res


if __name__ == "__main__":
    main()
