#!/usr/bin/env python
"""Dev-only, for the Playwright backend (T8-06): a fake model and a fake Stripe on one local port (E2E_FAKE_PORT).

- POST /v1/chat/completions  the model, OpenAI shape. Intake: asks the current question; once the client has answered,
                             thanks her and ends with [DONE: <question id>]. Drafting: full-length articles with only
                             verified sections. Every call is logged.
- GET  /calls                the call log: [{"kind": "intake"|"learn"|"draft", "at": ...}]
- POST /v1/checkout/sessions Stripe Checkout (form body), answers {id, url}; the url is the test page below.
- GET  /pay/<id>             a test checkout page with one button; POST /pay/<id> sends Stripe's signed
                             checkout.session.completed webhook to the backend, then goes to the session's success_url.
- POST /webhook              sends that signed webhook for {journey_id, amount_total, session_id} (a test calling it early).
Nothing here reaches the network."""
import hashlib
import hmac
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from carbon_intake import DOCS, WORDS  # noqa: E402

PORT = int(os.environ.get("E2E_FAKE_PORT", "8291"))
BACKEND = f"http://127.0.0.1:{os.environ.get('E2E_API_PORT', '8011')}"
SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "whsec_e2e")
CALLS, SESSIONS = [], {}


def draft(system):
    kind = next(k for k, d in DOCS.items() if f"drafting a complete {d['name']} " in system)
    doc, n = DOCS[kind], len(DOCS[kind]["articles"])
    m = re.search(r"You write ONLY Articles (\w+) to (\w+)", system)
    first, last = (WORDS.index(m.group(1)) + 1, WORDS.index(m.group(2)) + 1) if m else (1, n)
    cite = sorted(doc["cites"])[0]
    per = doc["min"] // n + 60                                    # words per article, so the whole instrument is full length
    arts = []
    for a in range(first, last + 1):
        w = WORDS[a - 1]
        body = " ".join(f"Clause {w.lower()}-{i} records the stated wish number {i} of the client in plain terms."
                        for i in range(per // 13 + 1))
        arts.append(f"## ARTICLE {w}: PROVISIONS OF ARTICLE {w}\n\n**{a}.1 Terms.** {body} "
                    f"Probate Code section {cite} applies to article {w.lower()}. "
                    f"[ATTORNEY TO CONFIRM - standard term in article {w.lower()}]")
    title = re.sub(r"\[ATTORNEY TO COMPLETE - [^\]]*\]", "TORRES FAMILY", doc["title"])     # the attorney fills it in
    head = (f"## Attorney review notes\n### Information to complete\n- None.\n\n# {title}\n\n" if first == 1 else "")
    return head + "\n\n".join(arts) + "\n"


def intake(system, messages):
    qid = re.search(r"\[DONE: ([a-z_]+)\]", system).group(1)
    question = re.search(r'The current question is:\n"([^"]*)"', system).group(1)
    if messages and messages[-1]["role"] == "user":
        return f"Gracias, lo anoté. [DONE: {qid}]"
    return question


def signed_webhook(obj):
    raw = json.dumps({"type": "checkout.session.completed", "data": {"object": obj}}).encode()
    t = str(int(time.time()))                       # Stripe signs with the real time: the backend's tolerance is real time too
    sig = hmac.new(SECRET.encode(), (t + ".").encode() + raw, hashlib.sha256).hexdigest()
    req = urllib.request.Request(f"{BACKEND}/payments/webhook", data=raw, method="POST",
                                 headers={"Content-Type": "application/json", "Stripe-Signature": f"t={t},v1={sig}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, status, body=b"", ctype="application/json", headers=()):
        if not isinstance(body, bytes):
            body = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in headers:
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        return self.rfile.read(int(self.headers.get("Content-Length") or 0))

    def do_GET(self):
        if self.path == "/health":
            return self._send(200, {"ok": True})
        if self.path == "/calls":
            return self._send(200, CALLS)
        m = re.fullmatch(r"/pay/([\w-]+)", self.path)
        if m and m.group(1) in SESSIONS:
            s = SESSIONS[m.group(1)]
            page = (f"<!doctype html><html lang=es><title>Stripe (prueba)</title><main><h1>Stripe: pago de prueba</h1>"
                    f"<p>Total: ${s['amount_total'] // 100:,}</p><form method=post><button>Pagar (prueba)</button></form></main>")
            return self._send(200, page.encode(), "text/html; charset=utf-8")
        self._send(404, {"error": "not found"})

    def do_POST(self):
        raw = self._body()
        if self.path == "/v1/chat/completions":
            req = json.loads(raw)
            msgs = req["messages"]
            system = msgs[0]["content"] if msgs and msgs[0]["role"] == "system" else ""
            rest = [m for m in msgs if m["role"] != "system"]
            if "drafting a complete" in system:
                kind, text = "draft", draft(system)
            elif "[DONE:" in system:
                kind, text = "intake", intake(system, rest)
            else:
                kind, text = "learn", "Es información general. Para su caso, pregúntele al abogado Raval."
            CALLS.append({"kind": kind, "at": time.time()})
            return self._send(200, {"choices": [{"message": {"role": "assistant", "content": text}}],
                                    "usage": {"prompt_tokens": 0, "completion_tokens": 0}})
        if self.path == "/v1/checkout/sessions":
            form = dict(urllib.parse.parse_qsl(raw.decode()))
            sid = f"cs_test_e2e_{len(SESSIONS) + 1}"
            SESSIONS[sid] = {"id": sid, "amount_total": int(form["line_items[0][price_data][unit_amount]"]),
                             "journey_id": form["metadata[journey_id]"], "success_url": form["success_url"]}
            return self._send(200, {"id": sid, "url": f"http://127.0.0.1:{PORT}/pay/{sid}"})
        m = re.fullmatch(r"/pay/([\w-]+)", self.path)
        if m and m.group(1) in SESSIONS:
            s = SESSIONS[m.group(1)]
            signed_webhook({"id": s["id"], "payment_status": "paid", "amount_total": s["amount_total"],
                            "metadata": {"journey_id": s["journey_id"]}})
            return self._send(303, headers=[("Location", s["success_url"].replace("{CHECKOUT_SESSION_ID}", s["id"]))])
        if self.path == "/webhook":
            b = json.loads(raw)
            status = signed_webhook({"id": b["session_id"], "payment_status": "paid", "amount_total": b["amount_total"],
                                     "metadata": {"journey_id": b["journey_id"]}})
            return self._send(200, {"status": status})
        self._send(404, {"error": "not found"})


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
