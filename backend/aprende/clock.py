"""The one server clock for journey time: the real UTC time. In the Playwright backend only (APRENDE_E2E_CLOCK=1), tests
can move it forward through /e2e/clock; time keeps running from the moved point."""
import datetime
import os

ENABLED = os.environ.get("APRENDE_E2E_CLOCK") == "1"
if ENABLED and (os.environ.get("RENDER") or os.environ.get("STRIPE_MODE", "test").lower() == "live"):
    raise RuntimeError("APRENDE_E2E_CLOCK is for the test backend only")
_offset = datetime.timedelta(0)


def now():
    return datetime.datetime.now(datetime.timezone.utc) + _offset


def now_iso():
    """Naive UTC ISO, the format journey events and jobs store."""
    return now().replace(tzinfo=None).isoformat()


def set_now(target):
    """Test backend only, and forward only: events are ordered by their time."""
    global _offset
    if not ENABLED:
        raise RuntimeError("the clock can only be moved in the test backend")
    if target < now():
        raise ValueError("the clock only moves forward")
    _offset = target - datetime.datetime.now(datetime.timezone.utc)
