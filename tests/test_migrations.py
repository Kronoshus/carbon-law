import os, sys, tempfile, subprocess, pytest, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.join(os.path.dirname(HERE), "backend")
sys.path.insert(0, BACKEND)

_orig_db_url = os.environ.get("DATABASE_URL")
_orig_db_path = os.environ.get("CARBON_DB_PATH")
os.environ["DATABASE_URL"] = ""
os.environ["CARBON_DB_PATH"] = tempfile.mktemp(suffix=".db")

import db
import migrate

# Restore process env so other tests/subprocesses are not polluted.
if _orig_db_url is None:
    os.environ.pop("DATABASE_URL", None)
else:
    os.environ["DATABASE_URL"] = _orig_db_url
if _orig_db_path is None:
    os.environ.pop("CARBON_DB_PATH", None)
else:
    os.environ["CARBON_DB_PATH"] = _orig_db_path

TABLES = {"schema_migrations", "settings", "journeys", "journey_events",
          "jobs", "ai_calls", "events", "characters"}


def test_migrate_from_empty_sqlite():
    migrate.run()
    rows = db.query("SELECT name FROM sqlite_master WHERE type='table'")
    names = {r[0] for r in rows}
    for t in TABLES:
        assert t in names, t
    assert db.query("SELECT COUNT(*) FROM schema_migrations")[0][0] == 2


def test_migrate_is_idempotent():
    migrate.run()
    before = db.query("SELECT COUNT(*) FROM schema_migrations")[0][0]
    second = migrate.run()
    after = db.query("SELECT COUNT(*) FROM schema_migrations")[0][0]
    assert before == after
    assert second == []


def test_journey_event_dedupe():
    migrate.run()
    db.execute("INSERT INTO journeys (id,user_id,tz,started_at) VALUES (?,?,?,?)",
               ("j1", "u1", "UTC", "2026-01-01"))
    db.execute("INSERT INTO journey_events (id,journey_id,type,payload_json,actor,created_at) VALUES (?,?,?,?,?,?)",
               ("e1", "j1", "doc", "{}", "user", "2026-01-01"))
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO journey_events (id,journey_id,type,payload_json,actor,created_at) VALUES (?,?,?,?,?,?)",
                   ("e2", "j1", "doc", "{}", "user", "2026-01-01"))


def test_legacy_collections_untouched():
    migrate.run()
    db.execute("INSERT INTO collections (name,data) VALUES (?,?)", ("legacy", "{}"))
    before = db.query("SELECT COUNT(*) FROM collections")[0][0]
    migrate.run()
    after = db.query("SELECT COUNT(*) FROM collections")[0][0]
    assert after == before


def test_concurrent_writes_do_not_interleave():
    import threading
    migrate.run()
    errors = []

    def failing(idx):
        try:
            with db.transaction() as conn:
                conn.execute("INSERT INTO jobs (id,kind,key,status) VALUES (?,?,?,?)",
                             (f"fail-{idx}", "k", f"key-fail-{idx}", "ok"))
                raise ValueError("boom")
        except ValueError:
            pass
        except Exception as e:
            errors.append(e)

    def plain():
        db.execute("INSERT INTO jobs (id,kind,key,status) VALUES (?,?,?,?)",
                   ("plain", "k", "key-plain", "ok"))

    ts = [threading.Thread(target=failing, args=(i,)) for i in range(2)]
    tp = threading.Thread(target=plain)
    for t in ts + [tp]:
        t.start()
    for t in ts + [tp]:
        t.join()
    assert not errors
    ids = {r[0] for r in db.query("SELECT id FROM jobs WHERE id IN ('fail-0','fail-1','plain')")}
    assert "plain" in ids
    assert "fail-0" not in ids
    assert "fail-1" not in ids


pg_url = os.environ.get("APRENDE_TEST_PG_URL")


@pytest.mark.skipif(not pg_url, reason="APRENDE_TEST_PG_URL not set")
def test_migrate_from_empty_postgres():
    code = """
import os, sys
os.environ['DATABASE_URL'] = {url!r}
sys.path.insert(0, {backend!r})
import psycopg
conn = psycopg.connect({url!r}, autocommit=True)
conn.execute('DROP SCHEMA public CASCADE')
conn.execute('CREATE SCHEMA public')
conn.close()
import db, migrate
applied = migrate.run()
assert applied == ['0001_aprende_core', '0002_characters']
tables = {{r[0] for r in db.query("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")}}
for t in {tables!r}:
    assert t in tables, t
assert db.query("SELECT COUNT(*) FROM schema_migrations")[0][0] == 2
assert migrate.run() == []
assert db.query("SELECT COUNT(*) FROM schema_migrations")[0][0] == 2
print("postgres migration ok")
""".format(url=pg_url, backend=BACKEND, tables=sorted(TABLES))
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    print(r.stdout)
    print(r.stderr)
    assert r.returncode == 0, r.stderr
