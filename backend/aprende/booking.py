"""Availability, slots, booking, cancel, reschedule (T6-07)."""
import datetime
import json
import os
import uuid
from zoneinfo import ZoneInfo

import app as backend_app
from aprende import firm
import db
from aprende import auth, clock, journey
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

LA = ZoneInfo("America/Los_Angeles")
UTC = datetime.timezone.utc
DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
DAY_NAMES = {0: "mon", 1: "tue", 2: "wed", 3: "thu", 4: "fri", 5: "sat", 6: "sun"}

router = APIRouter()


def now():
    return clock.now()


def notify_staff(title, message):
    from aprende.notify import notify_staff as _ns
    _ns(title, message)


def send_confirmation(to, subject, body):
    return backend_app.send_email(to, subject, body)


WEEKDAYS = {"es": ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"],
            "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]}
MONTHS = {"es": ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"],
          "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]}
with open(os.path.join(os.path.dirname(__file__), "..", "..", "aprende", "src", "core", "office.json"), encoding="utf-8") as _f:
    OFFICE = json.load(_f)       # the app reads the same file
OFFICE_MAP = "https://maps.google.com/?q=" + "+".join(f"{OFFICE['street']} {OFFICE['city']}".replace(",", "").split())
PLACE = {"es": "La firma es en la oficina: {name}, {street}, {city}".format(**OFFICE),
         "en": "The signing is at the office: {name}, {street}, {city}".format(**OFFICE)}
KIND = {"signing": ("la firma de sus documentos", "your document signing"), "consultation": ("su consulta con el abogado Raval", "your consultation with attorney Raval")}


def when(start_utc, lang):
    """The Los Angeles date and time phrase for an appointment, in `lang`."""
    t = start_utc.astimezone(LA)
    hm = f"{t.hour % 12 or 12}:{t.minute:02d}"
    if lang == "es":
        return f"{WEEKDAYS['es'][t.weekday()]} {t.day} de {MONTHS['es'][t.month - 1]} de {t.year}, a las {hm} {'a. m.' if t.hour < 12 else 'p. m.'}"
    return f"{WEEKDAYS['en'][t.weekday()]}, {MONTHS['en'][t.month - 1]} {t.day}, {t.year}, at {hm} {'a.m.' if t.hour < 12 else 'p.m.'}"


def confirmation(kind, start_utc):
    """The confirmation email, in Spanish then English, with the Los Angeles date and time (and the place, for a signing)."""
    es = f"Su cita para {KIND[kind][0]}: {when(start_utc, 'es')} (hora de California)."
    en = f"Your appointment for {KIND[kind][1]}: {when(start_utc, 'en')} (California time)."
    if kind == "signing":
        es += f"\n{PLACE['es']}\n{OFFICE_MAP}"
        en += f"\n{PLACE['en']}\n{OFFICE_MAP}"
    return es + "\nPuede cambiarla o cancelarla en la aplicación hasta 24 horas antes.\n\n" + en + "\nYou can change or cancel it in the app up to 24 hours before.\n\nCarbon Law Group"


def _now_iso():
    return now().astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


_load_availability = firm._load_availability


_save_setting = firm._save_setting


_load_holidays = lambda: set(firm._load_holidays())


def _parse_dt(s):
    t = str(s).strip()
    if t.endswith("Z"):
        t = t[:-1] + "+00:00"
    dt = datetime.datetime.fromisoformat(t)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _validate_availability(hours, slot_minutes):
    if not isinstance(hours, dict):
        raise HTTPException(422, "hours required")
    if not isinstance(slot_minutes, dict):
        raise HTTPException(422, "slot_minutes required")
    for day, ranges in hours.items():
        if day not in DAYS:
            raise HTTPException(422, "unknown day")
        if not isinstance(ranges, list):
            raise HTTPException(422, "ranges must be list")
        for r in ranges:
            if not (isinstance(r, (list, tuple)) and len(r) == 2):
                raise HTTPException(422, "range must be [start,end]")
            a, b = r[0], r[1]
            try:
                ta = datetime.time.fromisoformat(a)
                tb = datetime.time.fromisoformat(b)
            except ValueError:
                raise HTTPException(422, "bad time")
            if (ta.hour * 60 + ta.minute) >= (tb.hour * 60 + tb.minute):
                raise HTTPException(422, "range ends before it starts")
    for k, v in slot_minutes.items():
        if not isinstance(v, int) or v <= 0 or (v % 30) != 0:
            raise HTTPException(422, "minutes must be multiple of 30")
    return hours, slot_minutes


def _is_real_local(dt_local):
    utc = dt_local.astimezone(UTC)
    back = utc.astimezone(LA)
    return back.replace(tzinfo=None) == dt_local.replace(tzinfo=None)


def _offered_slots(kind, date_str, ignore_booked=False):
    settings = _load_availability()
    if not settings:
        return []
    hours = settings.get("hours") or {}
    slot_minutes = (settings.get("slot_minutes") or {}).get(kind)
    if not slot_minutes:
        return []
    holidays = _load_holidays()
    if date_str in holidays:
        return []
    try:
        d = datetime.date.fromisoformat(date_str)
    except ValueError:
        return []
    day_key = DAY_NAMES[d.weekday()]
    day_ranges = hours.get(day_key) or []
    blocks_needed = slot_minutes // 30

    if ignore_booked:
        booked_blocks = set()
    else:
        booked_blocks = set(r[0] for r in db.query("SELECT block_start_utc FROM booking_blocks"))

    nowt = now()
    offered = []
    for rng in day_ranges:
        start_t = datetime.time.fromisoformat(rng[0])
        end_t = datetime.time.fromisoformat(rng[1])
        cur = datetime.datetime.combine(d, start_t, tzinfo=LA)
        end_dt = datetime.datetime.combine(d, end_t, tzinfo=LA)
        while cur + datetime.timedelta(minutes=slot_minutes) <= end_dt:
            ok = True
            block_starts = []
            for i in range(blocks_needed):
                bt = cur + datetime.timedelta(minutes=30 * i)
                if not _is_real_local(bt):
                    ok = False
                    break
                block_starts.append(bt)
            if ok:
                slot_start_utc = cur.astimezone(UTC)
                if slot_start_utc > nowt:
                    all_free = True
                    for bt in block_starts:
                        if bt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ") in booked_blocks:
                            all_free = False
                            break
                    if all_free:
                        offered.append({
                            "start": slot_start_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                            "local": cur.strftime("%Y-%m-%dT%H:%M:%S"),
                        })
            cur = cur + datetime.timedelta(minutes=30)
    seen = set()
    out = []
    for s in offered:
        if s["start"] in seen:
            continue
        seen.add(s["start"])
        out.append(s)
    out.sort(key=lambda x: x["start"])
    return out


def _is_offered(kind, start_utc_str):
    dt = _parse_dt(start_utc_str)
    local_date = dt.astimezone(LA).date().isoformat()
    slots = _offered_slots(kind, local_date)
    return any(s["start"] == start_utc_str for s in slots)


def _is_valid_slot(kind, start_utc_str):
    dt = _parse_dt(start_utc_str)
    local_date = dt.astimezone(LA).date().isoformat()
    slots = _offered_slots(kind, local_date, ignore_booked=True)
    return any(s["start"] == start_utc_str for s in slots)


def _gate_missing(j, kind):
    if kind == "signing":
        if not j["gates"].get("may_book_signing"):
            return ["may_book_signing"]
        return []
    if j["conflict"] == "hold":                          # no meeting with a possibly adverse party (brief s.6)
        return ["may_collect_details"]
    facts = j["facts"]
    needed = [f"lesson_completed:{d}" for d in ("will", "trust", "ahcd", "poa")]
    if all(f in facts for f in needed):
        return []
    return ["core_lessons"]


def _user_email(user_id):
    for u in backend_app.users.values():
        if u.get("id") == user_id:
            return u.get("email")
    return None


def _user_name(user_id):
    for u in backend_app.users.values():
        if u.get("id") == user_id:
            return u.get("name")
    return None


class AvailabilityBody(BaseModel):
    hours: dict
    slot_minutes: dict


class HolidaysBody(BaseModel):
    dates: list


class BookingBody(BaseModel):
    kind: str
    start: str


class PatchBody(BaseModel):
    start: str


@router.put("/staff/availability")
def put_availability(body: AvailabilityBody, u: dict = Depends(auth.staff())):
    hours, slot_minutes = _validate_availability(body.hours, body.slot_minutes)
    _save_setting("availability", {"hours": hours, "slot_minutes": slot_minutes}, u["email"])   # existing bookings are kept
    backend_app.log_audit(u["email"], "firm_settings", "settings", "availability", json.dumps({"hours": hours, "slot_minutes": slot_minutes}))
    return {"availability": {"hours": hours, "slot_minutes": slot_minutes}}


@router.put("/staff/holidays")
def put_holidays(body: HolidaysBody, u: dict = Depends(auth.staff())):
    dates = [str(d) for d in body.dates]
    _save_setting("holidays", dates, u["email"])
    backend_app.log_audit(u["email"], "firm_settings", "settings", "holidays", json.dumps(dates))
    return {"holidays": dates}


@router.get("/booking/slots")
def get_slots(kind: str, from_: str = Query(..., alias="from"), days: int = 1, user: dict = Depends(auth.client_user), j: dict = Depends(auth.client_journey)):
    pass
    missing = _gate_missing(j, kind)
    if missing:
        return JSONResponse(status_code=409, content={"error": "gate", "missing": missing})
    start_date = datetime.date.fromisoformat(from_)
    all_slots = []
    for i in range(days):
        d = start_date + datetime.timedelta(days=i)
        all_slots.extend(_offered_slots(kind, d.isoformat()))
    return {"slots": all_slots}


@router.post("/booking")
def post_booking(body: BookingBody, user: dict = Depends(auth.client_user), j: dict = Depends(auth.client_journey)):

    missing = _gate_missing(j, body.kind)
    if missing:
        return JSONResponse(status_code=409, content={"error": "gate", "missing": missing})
    if not _is_valid_slot(body.kind, body.start):
        raise HTTPException(422, "not an offered slot")
    settings = _load_availability() or {}
    slot_minutes = (settings.get("slot_minutes") or {}).get(body.kind)
    if not slot_minutes:
        raise HTTPException(422, "no slot length")
    start_utc = _parse_dt(body.start)
    end_utc = start_utc + datetime.timedelta(minutes=slot_minutes)
    blocks_needed = slot_minutes // 30
    block_starts = [start_utc + datetime.timedelta(minutes=30 * i) for i in range(blocks_needed)]
    booking_id = str(uuid.uuid4())
    try:
        with db.transaction() as conn:
            conn.execute(
                "INSERT INTO bookings (id, journey_id, kind, start_utc, end_utc, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (booking_id, j["id"], body.kind, start_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                 end_utc.strftime("%Y-%m-%dT%H:%M:%SZ"), "active", _now_iso()))
            for bs in block_starts:
                conn.execute("INSERT INTO booking_blocks (block_start_utc, booking_id) VALUES (?, ?)",
                             (bs.strftime("%Y-%m-%dT%H:%M:%SZ"), booking_id))
            conn.commit()
    except Exception as e:
        msg = str(e).lower()
        if "unique" in msg or "duplicate" in msg or "constraint" in msg:
            return JSONResponse(status_code=409, content={"error": "taken"})
        raise
    if body.kind == "signing":
        journey.apply(j["id"], "signing_booked", {}, actor="system")
    email = _user_email(user["id"])
    if email:
        send_confirmation(email, "Confirmación de su cita / Appointment confirmation", confirmation(body.kind, start_utc))
    notify_staff("New booking", "A {} booking was made. Journey: {}".format(body.kind, j["id"]))
    from aprende import reminders                      # cycle: reminders uses booking.when
    reminders.schedule_appointment(booking_id, start_utc)
    return {"id": booking_id, "kind": body.kind, "start": start_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "local": start_utc.astimezone(LA).strftime("%Y-%m-%dT%H:%M:%S")}


@router.get("/booking")
def get_booking(user: dict = Depends(auth.client_user), j: dict = Depends(auth.client_journey)):

    rows = db.query("SELECT id, kind, start_utc, end_utc, status FROM bookings WHERE journey_id = ? AND status = 'active'", (j["id"],))
    out = []
    for r in rows:
        out.append({"id": r[0], "kind": r[1], "start": r[2], "end": r[3], "status": r[4]})
    return out


@router.delete("/booking/{booking_id}")
def delete_booking(booking_id: str, user: dict = Depends(auth.client_user), j: dict = Depends(auth.client_journey)):

    rows = db.query("SELECT id, journey_id, start_utc FROM bookings WHERE id = ?", (booking_id,))
    if not rows or rows[0][1] != j["id"]:
        raise HTTPException(404, "not found")
    start_utc = _parse_dt(rows[0][2])
    if (start_utc - now()).total_seconds() < 24 * 3600:
        raise HTTPException(409, "within 24 hours")
    with db.transaction() as conn:
        conn.execute("DELETE FROM booking_blocks WHERE booking_id = ?", (booking_id,))
        conn.execute("UPDATE bookings SET status = 'cancelled', cancelled_at = ? WHERE id = ?", (_now_iso(), booking_id))
        conn.commit()
    return {"ok": True}


@router.patch("/booking/{booking_id}")
def patch_booking(booking_id: str, body: PatchBody, user: dict = Depends(auth.client_user), j: dict = Depends(auth.client_journey)):

    rows = db.query("SELECT id, journey_id, kind, start_utc FROM bookings WHERE id = ?", (booking_id,))
    if not rows or rows[0][1] != j["id"]:
        raise HTTPException(404, "not found")
    kind = rows[0][2]
    old_start = _parse_dt(rows[0][3])
    if (old_start - now()).total_seconds() < 24 * 3600:
        raise HTTPException(409, "within 24 hours")
    if not _is_valid_slot(kind, body.start):
        raise HTTPException(422, "not an offered slot")
    settings = _load_availability() or {}
    slot_minutes = (settings.get("slot_minutes") or {}).get(kind)
    new_start = _parse_dt(body.start)
    new_end = new_start + datetime.timedelta(minutes=slot_minutes)
    blocks_needed = slot_minutes // 30
    new_blocks = [new_start + datetime.timedelta(minutes=30 * i) for i in range(blocks_needed)]
    try:
        with db.transaction() as conn:
            conn.execute("DELETE FROM booking_blocks WHERE booking_id = ?", (booking_id,))
            for bs in new_blocks:
                conn.execute("INSERT INTO booking_blocks (block_start_utc, booking_id) VALUES (?, ?)",
                             (bs.strftime("%Y-%m-%dT%H:%M:%SZ"), booking_id))
            conn.execute("UPDATE bookings SET start_utc = ?, end_utc = ? WHERE id = ?",
                         (new_start.strftime("%Y-%m-%dT%H:%M:%SZ"), new_end.strftime("%Y-%m-%dT%H:%M:%SZ"), booking_id))
            conn.commit()
    except Exception as e:
        msg = str(e).lower()
        if "unique" in msg or "duplicate" in msg or "constraint" in msg:
            return JSONResponse(status_code=409, content={"error": "taken"})
        raise
    from aprende import reminders
    reminders.schedule_appointment(booking_id, new_start)
    return {"id": booking_id, "kind": kind, "start": new_start.strftime("%Y-%m-%dT%H:%M:%SZ")}


@router.get("/staff/bookings")
def staff_bookings(from_: str = Query(..., alias="from"), days: int = 1, user: dict = Depends(auth.staff())):

    start_date = datetime.date.fromisoformat(from_)
    end_date = start_date + datetime.timedelta(days=days)
    start_utc = datetime.datetime.combine(start_date, datetime.time.min, tzinfo=LA).astimezone(UTC)
    end_utc = datetime.datetime.combine(end_date, datetime.time.min, tzinfo=LA).astimezone(UTC)
    rows = db.query(
        "SELECT b.id, b.journey_id, b.kind, b.start_utc FROM bookings b WHERE b.status = 'active' AND b.start_utc >= ? AND b.start_utc < ?",
        (start_utc.strftime("%Y-%m-%dT%H:%M:%SZ"), end_utc.strftime("%Y-%m-%dT%H:%M:%SZ")))
    out = []
    for r in rows:
        jid = r[1]
        j = journey.get_journey(jid)
        name = None
        if j:
            name = _user_name(j["user_id"])
        out.append({"id": r[0], "journey_id": jid, "kind": r[2], "start": r[3], "client_name": name or ""})
    return out
