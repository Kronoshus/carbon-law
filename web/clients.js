const CONFLICT_LABELS = { pending: "Pending", clear: "Clear", hold: "On hold" };
const STEP_LABELS = {
  lesson_will: "Will lesson", lesson_trust: "Trust lesson", lesson_ahcd: "Health care directive lesson",
  lesson_poa: "Power of attorney lesson", pay: "Agreement and payment", attorney_review: "Attorney review",
  client_review: "Client review", changes: "Changes", signing: "Signing", final_lesson: "Final lesson",
};
const KIND_LABELS = { consultation: "Consultation", signing: "Signing" };
const LA_TIME = new Intl.DateTimeFormat("en-US", { timeZone: "America/Los_Angeles", dateStyle: "medium", timeStyle: "short" });

function el(tag, props, ...children) {
  const node = Object.assign(document.createElement(tag), props || {});
  node.append(...children.filter((c) => c !== null && c !== undefined));
  return node;
}

function staffFetch(path, options) {
  const headers = { Authorization: "Bearer " + getToken() };
  if (options && options.body) headers["Content-Type"] = "application/json";
  return fetch(CARBON_API_BASE + path, Object.assign({ headers }, options || {}));
}

function say(text) {
  const msg = document.getElementById("clientesMessage");
  if (msg) msg.textContent = text;
}

async function loadClients() {
  const rows = document.getElementById("clientesRows");
  if (!rows) return;
  let me = null;
  let list = [];
  try {
    me = await staffFetch("/auth/me").then((r) => r.json());
    const res = await staffFetch("/staff/journeys");
    if (!res.ok) throw new Error(String(res.status));
    list = await res.json();
  } catch (_) {
    say("Could not load the client list. Try again later.");
    return;
  }
  if (!list.length) {
    rows.replaceChildren(el("tr", { className: "empty-row" }, el("td", { colSpan: 9, textContent: "No clients yet." })));
    return;
  }
  rows.replaceChildren(...list.map((r) => {
    const open = el("button", { type: "button", className: "btn secondary sm", textContent: r.client_name });
    open.addEventListener("click", () => openClient(r.journey_id, me));
    const late = (r.late || []).map((s) => STEP_LABELS[s] || s).join(", ");
    const cells = [
      el("td", null, open),
      el("td", { textContent: String(r.day) }),
      el("td", { textContent: late, className: late ? "late" : "" }),
      el("td", { textContent: CONFLICT_LABELS[r.conflict] || r.conflict }),
      el("td", { textContent: r.datos.done + " of " + r.datos.total }),
      el("td", { textContent: r.payment.paid ? "Paid" : "Not paid" }),
      el("td", { textContent: String(r.drafts_waiting) }),
      el("td", null, ...(r.appointments || []).map((a) => el("div", { textContent: (KIND_LABELS[a.kind] || a.kind) + ": " + LA_TIME.format(new Date(a.start_utc)) }))),
      el("td", { textContent: r.questions.open + " open, " + r.questions.answered + " answered" }),
    ];
    return el("tr", null, ...cells);
  }));
}

function questionItem(q, canAnswer) {
  const item = el("li", { className: "client-question" }, el("p", { textContent: q.question }));
  if (!canAnswer) {
    if (q.answer) item.append(el("p", null, el("strong", { textContent: "Attorney's answer: " }), q.answer));
    return item;
  }
  const box = el("textarea", { id: "respuesta-" + q.id, value: q.answer || "" });
  const send = el("button", { type: "button", className: "btn sm", textContent: q.answer ? "Change answer" : "Send answer" });
  send.addEventListener("click", async () => {
    const r = await staffFetch("/staff/attorney-questions/" + q.id + "/answer", { method: "POST", body: JSON.stringify({ answer: box.value }) });
    say(r.ok ? "Answer sent. The client sees it under Preguntas in the app." : "Could not send the answer.");
  });
  item.append(el("label", { htmlFor: box.id, textContent: "Attorney's answer" }), box, send);
  return item;
}

async function openClient(jid, me) {
  const container = document.getElementById("clienteDetail");
  if (!container) return;
  const r = await staffFetch("/staff/journeys/" + jid);
  if (!r.ok) { say("Could not open this client's file."); return; }
  const detail = await r.json();
  const canAnswer = Boolean(me && me.role === "attorney");
  const questions = detail.questions || [];
  container.replaceChildren(
    el("h3", { textContent: detail.client_name }),
    questions.length ? el("ul", { className: "client-questions" }, ...questions.map((q) => questionItem(q, canAnswer)))
                     : el("p", { textContent: "No questions for the attorney." }),
  );
  if (!canAnswer) container.append(el("p", { textContent: "Only the attorney answers questions." }));
  container.hidden = false;
}

if (document.getElementById("clientes")) {
  loadClients();
}
