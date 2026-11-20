"""Reminders: daily nudge, appointment reminder, yearly review (T8-03)."""
import datetime
import json

import app as backend_app
import db
from aprende import booking, jobs, journey, motivation, notify, push

# Wording needs attorney approval (#50).
TEXT = {
    "daily": {
        "es": {"title": "La Calavera", "body": "Su lección de hoy le espera. Son unos 15 minutos."},
        "en": {"title": "La Calavera", "body": "Today's lesson is waiting for you. About 15 minutes."},
    },
    "appointment": {
        "es": {"title": "Carbon Law Group", "body": "Le recordamos su cita para {kind}: {when} (hora de California). Si necesita cambiarla, llame a la oficina."},
        "en": {"title": "Carbon Law Group", "body": "A reminder of your appointment for {kind}: {when} (California time). If you need to change it, please call the office."},
    },
    "annual": {
        "es": {"title": "Carbon Law Group", "body": "Hace un año que completó su plan. Es un buen momento para revisarlo: un cambio en su familia, sus bienes o su domicilio puede requerir una actualización. Puede reservar una consulta en la aplicación."},
        "en": {"title": "Carbon Law Group", "body": "It has been a year since you completed your plan. This is a good time to review it: a change in your family, your property or your address may call for an update. You can book a consultation in the app."},
    },
}


def now():
    return datetime.datetime.now(datetime.timezone.utc)


def _user_email(journey_id):
    j = journey.get_journey(journey_id)
    if not j:
        return None
    for u in backend_app.users.values():
        if u.get("id") == j["user_id"]:
            return u.get("email")
    return None


def daily_tick(at):
    for jid in motivation.reminders_due(at):
        push.send(jid, TEXT["daily"], "#/aprender")
        motivation.mark_reminded(jid, at)


def schedule_daily(at):
    if at.minute % 15 == 0:
        slot = at + datetime.timedelta(minutes=15)
    else:
        slot = at + datetime.timedelta(minutes=15 - (at.minute % 15))
    if slot <= at:
        slot = at + datetime.timedelta(minutes=15)
    jobs.enqueue("daily_reminders", f"daily_reminders:{slot:%Y-%m-%dT%H:%M}", run_after=slot)


def _daily_handler(job):
    daily_tick(now())
    base = now()
    try:
        rows = db.query("SELECT run_after FROM jobs WHERE id = ?", (job["id"],))
        if rows and rows[0][0]:
            ra = rows[0][0]
            base = datetime.datetime.fromisoformat(str(ra).replace("Z", "+00:00"))
            if getattr(base, "tzinfo", None) is None:
                base = base.replace(tzinfo=datetime.timezone.utc)
    except Exception:
        base = now()
    schedule_daily(base)


jobs.register("daily_reminders", _daily_handler)


def schedule_appointment(booking_id, start_utc):
    if isinstance(start_utc, str):
        start_utc = datetime.datetime.fromisoformat(start_utc.replace("Z", "+00:00"))
    if start_utc.tzinfo is None:
        start_utc = start_utc.replace(tzinfo=datetime.timezone.utc)
    nowt = now()
    if (start_utc - nowt).total_seconds() > 30 * 3600:
        jobs.enqueue(
            "appointment_reminder",
            f"appointment_reminder:{booking_id}:{start_utc:%Y%m%dT%H%MZ}",
            payload={"booking_id": booking_id, "start": start_utc.strftime("%Y-%m-%dT%H:%M:%SZ")},
            run_after=start_utc - datetime.timedelta(hours=24),
        )


def _appointment_handler(job):
    payload = job.get("payload") or {}
    booking_id = payload.get("booking_id")
    start_payload = payload.get("start")
    # booking still active AND its start matches
    rows = db.query("SELECT journey_id, kind, start_utc, status FROM bookings WHERE id = ?", (booking_id,))
    if not rows:
        return
    bid_jid, kind, start_db, status = rows[0]
    if status != "active":
        return
    if start_db != start_payload:
        return
    start_utc = datetime.datetime.fromisoformat(start_db.replace("Z", "+00:00"))
    if start_utc.tzinfo is None:
        start_utc = start_utc.replace(tzinfo=datetime.timezone.utc)
    if start_db != start_payload:
        return
    j = journey.get_journey(bid_jid)
    if j is None:
        return
    jid = bid_jid
    when_es = booking.when(start_utc, "es")
    when_en = booking.when(start_utc, "en")
    kind_es = booking.KIND[kind][0]
    kind_en = booking.KIND[kind][1]
    body_es = TEXT["appointment"]["es"]["body"].format(kind=kind_es, when=when_es)
    body_en = TEXT["appointment"]["en"]["body"].format(kind=kind_en, when=when_en)
    email_body = body_es + "\n\n" + body_en + "\nCarbon Law Group"
    # Actually spec: es text, blank line, en text, then "Carbon Law Group"
    email_body = body_es + "\n\n" + body_en + "\nCarbon Law Group"
    email = _user_email(jid)
    if email:
        send_email(email, "Recordatorio de su cita / Appointment reminder", email_body)
    push_texts = {
        "es": {"title": TEXT["appointment"]["es"]["title"], "body": body_es},
        "en": {"title": TEXT["appointment"]["en"]["title"], "body": body_en},
    }
    # push uses one language per subscription; push.send formats? We already formatted body. But push.send expects texts with body. Good.
    # However push.send uses texts[lang]["body"]. We provide formatted. Good.
    push.send(jid, push_texts, "#/cita")


jobs.register("appointment_reminder", _appointment_handler)


def schedule_annual_review(journey_id, after, year=1):
    if isinstance(after, str):
        after = datetime.datetime.fromisoformat(after.replace("Z", "+00:00"))
    if after.tzinfo is None:
        after = after.replace(tzinfo=datetime.timezone.utc)
    run_after = after + datetime.timedelta(days=365)
    jobs.enqueue(
        "annual_review",
        f"annual_review:{journey_id}:{year}",
        payload={"journey_id": journey_id, "year": year},
        run_after=run_after,
    )


def _annual_handler(job):
    payload = job.get("payload") or {}
    jid = payload.get("journey_id")
    year = payload.get("year", 1)
    if not jid:
        return
    j = journey.get_journey(jid)
    if j is None:
        return
    send_email(_user_email(jid) or "", "Revisión anual de su plan / Yearly review of your plan",
               TEXT["annual"]["es"]["body"] + "\n\n" + TEXT["annual"]["en"]["body"] + "\nCarbon Law Group")
    push.send(jid, TEXT["annual"], "#/plan")
    notify_staff("Revisión anual", f"Expediente {jid}: toca la revisión anual del plan.")
    # schedule next
    # this job's run_after
    rows = db.query("SELECT run_after FROM jobs WHERE id = ?", (job["id"],))
    run_after_str = rows[0][0] if rows else None
    if run_after_str:
        after = datetime.datetime.fromisoformat(run_after_str)
        if after.tzinfo is None:
            after = after.replace(tzinfo=datetime.timezone.utc)
    else:
        after = now()
    schedule_annual_review(jid, after, year + 1)


jobs.register("annual_review", _annual_handler)


def send_email(to, subject, body):
    return backend_app.send_email(to, subject, body)


def notify_staff(title, message):
    notify.notify_staff(title, message)
