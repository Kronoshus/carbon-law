"""The engagement letter and fee agreement (T6-01; Bus. & Prof. Code § 6148): templates the attorney approves, the letter
rendered for one client, the client's signature on the exact text shown, the attorney's countersignature, and the PDF copy."""
import datetime
import hashlib
import json
import os
import re
import uuid
from zoneinfo import ZoneInfo

from fpdf import FPDF

import app as backend_app
import db
from aprende import clock, journey, legacy, pricing

DOC_NAMES = {"will": {"es": "Testamento", "en": "Will"}, "trust": {"es": "Fideicomiso en vida", "en": "Living trust"},
             "poa": {"es": "Poder legal para finanzas (poder notarial)", "en": "Financial power of attorney"},
             "ahcd": {"es": "Directiva de atención médica", "en": "Advance health care directive"}}
MONTHS = {"es": ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"],
          "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]}
PROFILE_KEYS = ("bar_number", "costs_line", "refund_policy", "data_promise")
BLANK = "____________________"
FONT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fonts", "DejaVuSans.ttf")


def _today(lang):
    d = clock.now().astimezone(ZoneInfo("America/Los_Angeles")).date()
    return f"{d.day} de {MONTHS['es'][d.month - 1]} de {d.year}" if lang == "es" else f"{MONTHS['en'][d.month - 1]} {d.day}, {d.year}"


def create_template(es, en, by):
    version = db.query("SELECT COALESCE(MAX(version), 0) FROM engagement_templates")[0][0] + 1
    tid = str(uuid.uuid4())
    db.execute("INSERT INTO engagement_templates (id, version, es, en, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?)",
               (tid, version, es, en, by, journey._now_iso()))
    return {"id": tid, "version": version}


def approve_template(tid, by):
    return db.execute("UPDATE engagement_templates SET approved_by = ?, approved_at = ? WHERE id = ?", (by, journey._now_iso(), tid)) > 0


def approved_template():
    rows = db.query("SELECT id, version, es, en FROM engagement_templates WHERE approved_by IS NOT NULL ORDER BY version DESC LIMIT 1")
    return dict(zip(("id", "version", "es", "en"), rows[0])) if rows else None


def firm_profile():
    rows = db.query("SELECT value_json FROM settings WHERE key = 'firm_profile'")
    return json.loads(rows[0][0]) if rows else None


def set_firm_profile(profile, by):
    db.execute("INSERT INTO settings (key, value_json, updated_by, updated_at) VALUES ('firm_profile', ?, ?, ?) "
               "ON CONFLICT (key) DO UPDATE SET value_json = excluded.value_json, updated_by = excluded.updated_by, "
               "updated_at = excluded.updated_at", (json.dumps(profile), by, journey._now_iso()))


def missing():
    """What the firm must still provide before any client sees a letter."""
    profile = firm_profile() or {}
    return ([] if approved_template() else ["approved_template"]) + \
           ([] if all(profile.get(k) for k in PROFILE_KEYS) else ["firm_profile"])


def render(j, lang):
    """The letter for this client, every placeholder filled in one pass (a "{total}" typed in a name stays literal)."""
    template, profile = approved_template(), firm_profile()
    codes = j["documents"]["confirmed"]
    earned = {(d, e): c for d, e, c in db.query("SELECT document, event, amount_cents FROM discounts WHERE journey_id = ?", (j["id"],))}
    quote = pricing.quote(pricing.load_settings("pricing") or {}, j["facts"], codes, earned=earned)
    price = {it["code"]: it["price"] for it in quote["items"]}
    money = lambda cents: f"${cents // 100:,}"
    values = {"client_name": legacy._user_name(j["user_id"]), "date": _today(lang), "bar_number": profile["bar_number"],
              "documents": "\n".join(f"- {DOC_NAMES[c][lang]}" for c in codes),
              "fee_lines": "\n".join(f"- {DOC_NAMES[c][lang]}: {money(price[c])}" for c in codes),
              "total": money(quote["total"]), "costs_line": profile["costs_line"][lang], "refund_policy": profile["refund_policy"][lang],
              "data_promise": profile["data_promise"][lang], "client_signature": BLANK, "attorney_signature": BLANK}
    text = re.sub(r"\{([a-z_]+)\}", lambda m: values.get(m.group(1), m.group(0)), template[lang])
    return {"template_id": template["id"], "version": template["version"], "lang": lang, "text": text,
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}


def signature(jid):
    rows = db.query("SELECT template_id, version, lang, text, sha256, client_name, client_ip, client_signed_at, attorney_name, "
                    "attorney_signed_at FROM engagement_signatures WHERE journey_id = ?", (jid,))
    return dict(zip(("template_id", "version", "lang", "text", "sha256", "client_name", "client_ip", "client_signed_at",
                     "attorney_name", "attorney_signed_at"), rows[0])) if rows else None


def sign(j, name, sha256, ip):
    """True when this call signed; False when the letter was already signed. Raises LookupError if the text changed."""
    if signature(j["id"]):
        return False
    shown = next((r for r in (render(j, "es"), render(j, "en")) if r["sha256"] == sha256), None)
    if shown is None:
        raise LookupError("text_changed")
    new = db.execute("INSERT INTO engagement_signatures (journey_id, template_id, version, lang, text, sha256, client_name, client_ip, "
                     "client_signed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT (journey_id) DO NOTHING",
                     (j["id"], shown["template_id"], shown["version"], shown["lang"], shown["text"], sha256, name, ip, journey._now_iso()))
    if new:
        journey.apply(j["id"], "engagement_signed", {}, actor=name)
    return bool(new)


def countersign(jid, attorney_name):
    db.execute("UPDATE engagement_signatures SET attorney_name = ?, attorney_signed_at = ? WHERE journey_id = ? AND attorney_signed_at IS NULL",
               (attorney_name, journey._now_iso(), jid))
    journey.apply(jid, "engagement_countersigned", {}, actor=attorney_name)


def pdf(sig):
    """The copy: the letter as signed, then the signature record with the full SHA-256 of the text."""
    doc = FPDF()
    doc.set_auto_page_break(True, margin=18)
    doc.add_page()
    doc.add_font("DejaVu", "", FONT)
    write = lambda text, size=11, gap=1.5: (doc.set_font("DejaVu", size=size), doc.multi_cell(0, size * 0.5, text), doc.ln(gap))
    for line in sig["text"].split("\n"):
        plain = line.replace("**", "")
        if plain.startswith("# "):
            write(plain[2:], 16, 3)
        elif plain.startswith("## "):
            write(plain[3:], 13, 1)
        elif plain.strip():
            write(plain)
    doc.ln(4)
    pending = "pendiente" if sig["lang"] == "es" else "pending"
    for label, value in (("Signature record / Registro de firmas", ""), ("Client", sig["client_name"]),
                         ("Client signed (UTC)", sig["client_signed_at"]), ("Client IP", sig["client_ip"] or ""),
                         ("Attorney", sig["attorney_name"] or pending), ("Attorney signed (UTC)", sig["attorney_signed_at"] or pending),
                         ("SHA-256 of the text", "")):
        write(f"{label}: {value}" if value else label, 10, 0.5)
    write(sig["sha256"], 8, 0)
    return bytes(doc.output())
