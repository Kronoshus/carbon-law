"""Staff alerts by phone (ntfy). The topic is the firm's private staff topic; without one, alerts are only logged.
An alert never carries client names or content: only what happened and a link to the journey in the dashboard."""
import logging
import os

import httpx

log = logging.getLogger("aprende.notify")


def notify_staff(title, message):
    topic = os.environ.get("APRENDE_STAFF_NTFY_TOPIC")
    if not topic:
        log.warning("staff alert (no ntfy topic set): %s: %s", title, message)
        return
    try:
        httpx.post(f"https://ntfy.sh/{topic}", content=message.encode(), headers={"Title": title}, timeout=10)
    except httpx.HTTPError:
        log.exception("staff alert failed: %s", title)
