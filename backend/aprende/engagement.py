"""Engagement letter templates, rendering, signing, and PDF export (T6-01)."""
import datetime
import hashlib
import io
import json
import os
import re
import uuid

import db

import app as backend_app

DOC_NAMES = {
    "will": {"es": "Testamento", "en": "Will"},
    "trust": {"es": "Fideicomiso en vida", "en": "Living trust"},
    "poa": {"es": "Poder legal para finanzas (poder notarial)", "en": "Financial power of attorney"},
    "ahcd": {"es": "Directiva de atención médica", "en": "Advance health care directive"},
}

MONTHS_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
             "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
MONTHS_EN = ["January", "February", "March", "April", "May", "June", "July",
             "August", "September", "October", "November", "December"]


def _now_iso():
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat()


def _la_today(lang):
    try:
        from zoneinfo import ZoneInfo
        now = datetime.datetime.now(ZoneInfo("America/Los_Angeles"))
    except Exception:
        now = datetime.datetime.now(datetime.timezone.utc)
    if lang == "en":
        return f"{MONTHS_EN[now.month - 1]} {now.day}, {now.year}"
    return f"{now.day} de {MONTHS_ES[now.month - 1]} de {now.year}"


def _user_by_id(user_id):
    for u in backend_app.users.values():
        if u.get("id") == user_id:
            return u
    return None


def create_template(es, en, created_by):
    rows = db.query("SELECT COALESCE(MAX(version), 0) FROM engagement_templates")
    version = (rows[0][0] if rows else 0) + 1
    tid = str(uuid.uuid4())
    db.execute(
        "INSERT INTO engagement_templates (id, version, es, en, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (tid, version, es, en, created_by, _now_iso()))
    return {"id": tid, "version": version}


def approve_template(tid, approved_by):
    db.execute("UPDATE engagement_templates SET approved_by = ?, approved_at = ? WHERE id = ?",
               (approved_by, _now_iso(), tid))
    return True


def get_approved_template():
    rows = db.query("SELECT id, version, es, en, approved_by, approved_at FROM engagement_templates "
                    "WHERE approved_by IS NOT NULL ORDER BY approved_at DESC, created_at DESC LIMIT 1")
    if not rows:
        return None
    r = rows[0]
    return {"id": r[0], "version": r[1], "es": r[2], "en": r[3], "approved_by": r[4], "approved_at": r[5]}


def set_firm_profile(profile, updated_by):
    import json
    existing = db.query("SELECT key FROM settings WHERE key = ?", ("firm_profile",))
    if existing:
        db.execute("UPDATE settings SET value_json = ?, updated_by = ?, updated_at = ? WHERE key = ?",
                   (json.dumps(profile), updated_by, _now_iso(), "firm_profile"))
    else:
        db.execute("INSERT INTO settings (key, value_json, updated_by, updated_at) VALUES (?, ?, ?, ?)",
                   ("firm_profile", json.dumps(profile), updated_by, _now_iso()))
    return True


def get_firm_profile():
    rows = db.query("SELECT value_json FROM settings WHERE key = ?", ("firm_profile",))
    if not rows:
        return None
    import json
    try:
        return json.loads(rows[0][0])
    except Exception:
        return None


def _earned(jid):
    return {(d, e): c for d, e, c in db.query("SELECT document, event, amount_cents FROM discounts WHERE journey_id = ?", (jid,))}


def _confirmed_docs(j):
    return list(j.get("documents", {}).get("confirmed") or [])


def render(j, lang):
    template = get_approved_template()
    profile = get_firm_profile()
    if template is None or profile is None:
        return None, None
    confirmed = _confirmed_docs(j)
    user = _user_by_id(j["user_id"])
    client_name = (user or {}).get("name", "")
    import aprende.pricing as pricing
    earned = _earned(j["id"])
    pricing_settings = pricing.load_settings("pricing")
    q = pricing.quote(pricing_settings or {}, j["facts"], confirmed, earned=earned)
    total = q["total"]
    items_by_code = {it["code"]: it for it in q["items"]}
    documents_lines = "\n".join(f"- {DOC_NAMES[c][lang]}" for c in confirmed)
    fee_lines = "\n".join(f"- {DOC_NAMES[c][lang]}: ${items_by_code[c]['price'] // 100:,}" for c in confirmed)
    values = {
        "client_name": client_name,
        "date": _la_today(lang),
        "bar_number": profile.get("bar_number", ""),
        "documents": documents_lines,
        "fee_lines": fee_lines,
        "total": f"${total // 100:,}",
        "costs_line": (profile.get("costs_line") or {}).get(lang, ""),
        "refund_policy": (profile.get("refund_policy") or {}).get(lang, ""),
        "data_promise": (profile.get("data_promise") or {}).get(lang, ""),
        "client_signature": "____________________",
        "attorney_signature": "____________________",
    }
    tmpl_text = template["es"] if lang == "es" else template["en"]

    def repl(m):
        key = m.group(1)
        if key in values:
            return str(values[key])
        return m.group(0)

    text = re.sub(r"\{([a-z_]+)\}", repl, tmpl_text)
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return text, sha, template, profile


def render_current(j, lang):
    r = render(j, lang)
    if r is None:
        return None, None
    text, sha, template, profile = r
    return text, sha


def find_lang_for_sha(j, sha):
    for lang in ("es", "en"):
        text, s = render_current(j, lang)
        if s == sha:
            return lang, text
    return None, None


def get_signature(jid):
    rows = db.query("SELECT journey_id, template_id, version, lang, text, sha256, client_name, client_ip, client_signed_at, attorney_name, attorney_signed_at FROM engagement_signatures WHERE journey_id = ?", (jid,))
    if not rows:
        return None
    r = rows[0]
    return {
        "journey_id": r[0], "template_id": r[1], "version": r[2], "lang": r[3],
        "text": r[4], "sha256": r[5], "client_name": r[6], "client_ip": r[7],
        "client_signed_at": r[8], "attorney_name": r[9], "attorney_signed_at": r[10],
    }


def sign(jid, name, accept, sha256, client_ip):
    if not accept or not (name or "").strip():
        raise ValueError("invalid")
    sig = get_signature(jid)
    if sig is not None:
        return "noop"
    import aprende.journey as journey
    j = journey.get_journey(jid)
    if j is None:
        raise ValueError("journey not found")
    # infer lang
    lang, text = find_lang_for_sha(j, sha256)
    if lang is None:
        # text changed
        raise ValueError("text_changed")
    template = get_approved_template()
    profile = get_firm_profile()
    if template is None or profile is None:
        raise ValueError("not_ready")
    # recompute to be safe
    cur_text, cur_sha = render_current(j, lang)
    if cur_sha != sha256:
        raise ValueError("text_changed")
    # insert
    db.execute(
        "INSERT INTO engagement_signatures (journey_id, template_id, version, lang, text, sha256, client_name, client_ip, client_signed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (jid, template["id"], template["version"], lang, text, sha256, name.strip(), client_ip, _now_iso()))
    journey.apply(jid, "engagement_signed", {}, actor=name.strip())
    return "ok"


def countersign(jid, attorney_name):
    sig = get_signature(jid)
    if sig is None:
        raise ValueError("not_signed")
    if sig.get("attorney_signed_at"):
        return "noop"
    db.execute("UPDATE engagement_signatures SET attorney_name = ?, attorney_signed_at = ? WHERE journey_id = ?",
               (attorney_name, _now_iso(), jid))
    import aprende.journey as journey
    journey.apply(jid, "engagement_countersigned", {}, actor=attorney_name)
    return "ok"


def _font_path():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    p = os.path.join(base, "fonts", "DejaVuSans.ttf")
    if os.path.exists(p):
        return p
    # fallback system
    for cand in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",):
        if os.path.exists(cand):
            return cand
    return None


def make_pdf(sig, for_staff=False):
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    fp = _font_path()
    if fp:
        pdf.add_font("DejaVu", "", fp, uni=True)
        pdf.set_font("DejaVu", size=11)
    else:
        pdf.set_font("Helvetica", size=11)
    # letter text
    usable = pdf.w - pdf.l_margin - pdf.r_margin
    for line in sig["text"].split("\n"):
        # break any word that is wider than the usable width so multi_cell never fails
        words = line.split(" ")
        safe = []
        for w in words:
            if pdf.get_string_width(w) > usable:
                chunk = ""
                for ch in w:
                    if pdf.get_string_width(chunk + ch) > usable:
                        safe.append(chunk)
                        chunk = ch
                    else:
                        chunk += ch
                if chunk:
                    safe.append(chunk)
            else:
                safe.append(w)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(0, 6, " ".join(safe))
    pdf.ln(4)
    # signature record
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, 6, "Signature record")
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, 6, f"Client: {sig['client_name']}")
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, 6, f"Client signed at: {sig['client_signed_at']}")
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, 6, f"Client IP: {sig.get('client_ip') or ''}")
    att_name = sig.get("attorney_name") or "pendiente"
    att_time = sig.get("attorney_signed_at") or "pendiente"
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, 6, f"Attorney: {att_name}")
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, 6, f"Attorney signed at: {att_time}")
    pdf.set_font("DejaVu" if fp else "Helvetica", size=5)
    pdf.cell(0, 6, f"SHA-256: {sig['sha256']}", ln=1)
    pdf.set_font("DejaVu" if fp else "Helvetica", size=11)
    out = pdf.output(dest="S")
    if isinstance(out, str):
        out = out.encode("latin-1")
    return bytes(out)
