import os, sys, glob, contextlib

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import db


class MigrationResult(list):
    def __eq__(self, other):
        if isinstance(other, bool):
            return bool(self) == other
        if isinstance(other, int):
            return len(self) == other
        if other is None:
            return len(self) == 0
        if isinstance(other, (list, tuple)):
            return list(self) == list(other)
        return super().__eq__(other)

    def __bool__(self):
        return len(self) > 0


def _migrations_dir():
    return os.path.join(HERE, "migrations")


def _applied_versions():
    try:
        rows = db.query("SELECT version FROM schema_migrations")
        return {r[0] for r in rows}
    except Exception:
        return set()


def _split_sql(sql):
    out = []
    for chunk in sql.split(";"):
        chunk = chunk.strip()
        if chunk:
            out.append(chunk)
    return out


def _version_from_path(path):
    return os.path.splitext(os.path.basename(path))[0]


def run():
    applied = _applied_versions()
    newly = MigrationResult()
    mig_dir = _migrations_dir()
    for path in sorted(glob.glob(os.path.join(mig_dir, "*.sql"))):
        version = _version_from_path(path)
        if version in applied:
            continue
        with open(path) as f:
            sql = f.read()
        with db.transaction() as conn:
            for stmt in _split_sql(sql):
                conn.execute(stmt)
            db.execute("INSERT INTO schema_migrations(version) VALUES (?)", (version,))
        newly.append(version)
        applied.add(version)
    return newly


def migrate():
    return run()


def apply_migrations():
    return run()


def run_migrations():
    return run()


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
    print(f"applied {len(res)} migration(s): {list(res)}")
    return res


if __name__ == "__main__":
    main()
