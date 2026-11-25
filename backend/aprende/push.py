"""Push subscriptions and delivery (T8-03)."""
import json
import os

import db
from aprende import clock, motivation


def public_key():
    return os.environ.get("APRENDE_VAPID_PUBLIC_KEY") or None


def _now_iso():
    return clock.now_iso()


def subscribe(journey_id, endpoint, p256dh, auth, lang):
    db.execute(
        "INSERT INTO push_subscriptions (endpoint, journey_id, p256dh, auth, lang, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?) "
        "ON CONFLICT (endpoint) DO UPDATE SET journey_id = excluded.journey_id, "
        "p256dh = excluded.p256dh, auth = excluded.auth, lang = excluded.lang",
        (endpoint, journey_id, p256dh, auth, lang, _now_iso()),
    )


def unsubscribe(journey_id):
    cur = db.query("SELECT COUNT(*) FROM push_subscriptions WHERE journey_id = ?", (journey_id,))
    n = cur[0][0] if cur else 0
    db.execute("DELETE FROM push_subscriptions WHERE journey_id = ?", (journey_id,))
    return n


def _deliver(sub, data):
    # pywebpush imported here so the module loads without it
    try:
        from pywebpush import webpush, WebPushException
    except Exception:
        import logging
        logging.getLogger("aprende.push").warning("pywebpush unavailable; no push sent")
        return 0
    private_key = os.environ.get("APRENDE_VAPID_PRIVATE_KEY")
    if not private_key:
        import logging
        logging.getLogger("aprende.push").warning("push not configured: no VAPID private key")
        return 0
    info = {
        "endpoint": sub["endpoint"],
        "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]},
    }
    try:
        webpush(
            subscription_info=info,
            data=data,
            vapid_private_key=private_key,
            vapid_claims={"sub": "mailto:kevin@carbonlg.com"},
        )
        return 201
    except WebPushException as exc:
        status = getattr(exc.response, "status_code", None)
        if status is None:
            try:
                status = int(str(exc).split()[0])
            except (ValueError, IndexError):
                status = 0
        return status or 0
    except Exception:
        return 0


def send(journey_id, texts, url):
    if not motivation.get_reminder(journey_id).get("enabled"):
        return 0
    rows = db.query("SELECT endpoint, p256dh, auth, lang FROM push_subscriptions WHERE journey_id = ?", (journey_id,))
    deliveries = 0
    for endpoint, p256dh, auth, lang in rows:
        sub = {"endpoint": endpoint, "p256dh": p256dh, "auth": auth, "lang": lang}
        t = (texts.get(lang) or texts.get("es") or {})
        payload = json.dumps({"title": t.get("title"), "body": t.get("body"), "url": url})
        status = _deliver(sub, payload)
        if status in (404, 410):                                   # the browser dropped it
            db.execute("DELETE FROM push_subscriptions WHERE endpoint = ?", (endpoint,))
        elif 200 <= status < 300:
            deliveries += 1
    return deliveries
