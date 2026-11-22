"""Reminders: daily nudge, appointment reminder, yearly review (T8-03)."""
import datetime
import json

import app as backend_app
import db
from aprende import booking, clock, jobs, journey, motivation, notify, push

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
    return clock.now()


def _aware(t):
    t = datetime.datetime.fromisoformat(t.replace("Z", "+00:00")) if isinstance(t, str) else t
    return t if t.tzinfo else t.replace(tzinfo=datetime.timezone.utc)


def _user_email(journey_id):
    j = journey.get_journey(journey_id)
    return next((u.get("email") for u in backend_app.users.values() if j and u.get("id") == j["user_id"]), None)


def _run_after(job):
    rows = db.query("SELECT run_after FROM jobs WHERE id = ?", (job["id"],))
    return _aware(rows[0][0]) if rows and rows[0][0] else now()


def daily_tick(at):
    for jid in motivation.reminders_due(at):
        push.send(jid, TEXT["daily"], "#/aprender")
        motivation.mark_reminded(jid, at)


def schedule_daily(at):
    """Queue the next tick on the next quarter hour after `at`."""
    slot = (at + datetime.timedelta(minutes=15 - at.minute % 15)).replace(second=0, microsecond=0)
    jobs.enqueue("daily_reminders", f"daily_reminders:{slot:%Y-%m-%dT%H:%M}", run_after=slot)


def _daily_handler(job):
    daily_tick(now())
    schedule_daily(_run_after(job))


jobs.register("daily_reminders", _daily_handler)


def schedule_appointment(booking_id, start_utc):
    """Remind 24 hours before; a booking made less than about a day ahead has only its confirmation."""
    start_utc = _aware(start_utc)
    if start_utc - now() > datetime.timedelta(hours=30):
        jobs.enqueue("appointment_reminder", f"appointment_reminder:{booking_id}:{start_utc:%Y%m%dT%H%MZ}",
                     payload={"booking_id": booking_id, "start": start_utc.strftime("%Y-%m-%dT%H:%M:%SZ")},
                     run_after=start_utc - datetime.timedelta(hours=24))


def _appointment_handler(job):
    p = job.get("payload") or {}
    rows = db.query("SELECT journey_id, kind, start_utc, status FROM bookings WHERE id = ?", (p.get("booking_id"),))
    if not rows or rows[0][3] != "active" or rows[0][2] != p.get("start"):      # cancelled or moved: the new job reminds
        return
    jid, kind, start, _ = rows[0]
    start = _aware(start)
    body = {lang: TEXT["appointment"][lang]["body"].format(kind=booking.KIND[kind][i], when=booking.when(start, lang))
            for i, lang in enumerate(("es", "en"))}
    email = _user_email(jid)
    if email:
        send_email(email, "Recordatorio de su cita / Appointment reminder", body["es"] + "\n\n" + body["en"] + "\nCarbon Law Group")
    push.send(jid, {lang: {"title": TEXT["appointment"][lang]["title"], "body": body[lang]} for lang in body}, "#/cita")


jobs.register("appointment_reminder", _appointment_handler)


def schedule_annual_review(journey_id, after, year=1):
    jobs.enqueue("annual_review", f"annual_review:{journey_id}:{year}", payload={"journey_id": journey_id, "year": year},
                 run_after=_aware(after) + datetime.timedelta(days=365))


def _annual_handler(job):
    p = job.get("payload") or {}
    jid, year = p.get("journey_id"), p.get("year", 1)
    if not jid or journey.get_journey(jid) is None:
        return
    email = _user_email(jid)
    if email:
        send_email(email, "Revisión anual de su plan / Yearly review of your plan",
                   TEXT["annual"]["es"]["body"] + "\n\n" + TEXT["annual"]["en"]["body"] + "\nCarbon Law Group")
    push.send(jid, TEXT["annual"], "#/plan")
    notify_staff("Revisión anual", f"Expediente {jid}: toca la revisión anual del plan.")
    schedule_annual_review(jid, _run_after(job), year + 1)


jobs.register("annual_review", _annual_handler)


def send_email(to, subject, body):
    return backend_app.send_email(to, subject, body)


def notify_staff(title, message):
    notify.notify_staff(title, message)
