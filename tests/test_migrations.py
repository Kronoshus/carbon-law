import os, sys, tempfile, pytest

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.join(os.path.dirname(HERE), "backend")
sys.path.insert(0, BACKEND)

# SQLite environment set before import
os.environ.setdefault("DATABASE_URL", "")
os.environ["CARBON_DB_PATH"] = tempfile.mktemp(suffix=".db")

import db
import migrate

TABLES = {"schema_migrations", "settings", "journeys", "journey_events",
          "jobs", "ai_calls", "events", "collections"}


def test_migrate_from_empty_sqlite():
    migrate.run()
    rows = db.query("SELECT name FROM sqlite_master WHERE type='table'")
    names = {r[0] for r in rows}
    for t in {"schema_migrations", "settings", "journeys", "journey_events",
              "jobs", "ai_calls", "events"}:
        assert t in names, t
    assert db.query("SELECT COUNT(*) FROM schema_migrations")[0][0] == 1


def test_migrate_is_idempotent():
    migrate.run()
    before = db.query("SELECT COUNT(*) FROM schema_migrations")[0][0]
    second = migrate.run()
    after = db.query("SELECT COUNT(*) FROM schema_migrations")[0][0]
    assert before == after
    assert not second


def test_journey_event_dedupe():
    migrate.run()
    db.execute("INSERT INTO journeys (id,user_id,tz,started_at) VALUES (?,?,?,?)",
               ("j1", "u1", "UTC", "2026-01-01"))
    db.execute("INSERT INTO journey_events (id,journey_id,type,payload_json,actor,created_at,dedupe_key) VALUES (?,?,?,?,?,?,?)",
               ("e1", "j1", "doc", "{}", "user", "2026-01-01", "k1"))
    try:
        db.execute("INSERT INTO journey_events (id,journey_id,type,payload_json,actor,created_at,dedupe_key) VALUES (?,?,?,?,?,?,?)",
                   ("e2", "j1", "doc", "{}", "user", "2026-01-01", "k1"))
    except Exception:
        pass
    rows = db.query("SELECT COUNT(*) FROM journey_events WHERE journey_id=? AND type=? AND dedupe_key=?",
                    ("j1", "doc", "k1"))
    assert rows[0][0] == 1


def test_legacy_collections_untouched():
    migrate.run()
    before = db.query("SELECT COUNT(*) FROM collections")[0][0]
    db.execute("INSERT INTO collections (name,data) VALUES (?,?)", ("legacy", "{}"))
    db.execute("INSERT INTO collections (name,data) VALUES (?,?) ON CONFLICT(name) DO NOTHING",
               ("legacy2", "{}"))
    # re-run migration must not drop collections
    migrate.run()
    after = db.query("SELECT COUNT(*) FROM collections")[0][0]
    assert after >= before + 1


pg_url = os.environ.get("APRENDE_TEST_PG_URL")


@pytest.mark.skipif(not pg_url, reason="APRENDE_TEST_PG_URL not set")
def test_migrate_from_empty_postgres():
    os.environ["DATABASE_URL"] = pg_url
    os.environ.pop("CARBON_DB_PATH", None)
    import importlib
    importlib.reload(db)
    importlib.reload(migrate)
    migrate.run()
    rows = db.query("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
    names = {r[0] for r in rows}
    for t in {"schema_migrations", "settings", "journeys", "journey_events",
              "jobs", "ai_calls", "events", "collections"}:
        assert t in names, t
    assert db.query("SELECT COUNT(*) FROM schema_migrations")[0][0] == 1
