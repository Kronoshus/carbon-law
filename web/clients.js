const CONFLICT_LABELS = { pending: "Pendiente", clear: "Sin conflicto", hold: "En revisión" };
const STEP_LABELS = {
  lesson_will: "Lección: testamento", lesson_trust: "Lección: fideicomiso", lesson_ahcd: "Lección: directiva médica",
  lesson_poa: "Lección: poder notarial", pay: "Acuerdo y pago", attorney_review: "Revisión del abogado",
  client_review: "Revisión de la clienta", changes: "Cambios", signing: "Firma", final_lesson: "Lección final",
};
const KIND_LABELS = { consultation: "Consulta", signing: "Firma" };
const LA_TIME = new Intl.DateTimeFormat("es-US", { timeZone: "America/Los_Angeles", dateStyle: "medium", timeStyle: "short" });

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
    list = await staffFetch("/staff/journeys").then((r) => (r.ok ? r.json() : []));
  } catch (_) {
    say("No se pudo cargar la lista de clientes.");
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
      el("td", { textContent: r.datos.done + " de " + r.datos.total }),
      el("td", { textContent: r.payment.paid ? "Pagado" : "Sin pagar" }),
      el("td", { textContent: String(r.drafts_waiting) }),
      el("td", { textContent: (r.appointments || []).map((a) => (KIND_LABELS[a.kind] || a.kind) + ", " + LA_TIME.format(new Date(a.start_utc))).join("; ") }),
      el("td", { textContent: r.questions.open + " sin responder, " + r.questions.answered + " respondidas" }),
    ];
    return el("tr", null, ...cells);
  }));
}

function questionItem(q, canAnswer) {
  const item = el("li", { className: "client-question" }, el("p", { textContent: q.question }));
  if (q.answer) {
    item.append(el("p", null, el("strong", { textContent: "Respuesta del abogado: " }), q.answer));
  }
  if (!canAnswer) return item;
  const box = el("textarea", { id: "respuesta-" + q.id, value: q.answer || "" });
  const send = el("button", { type: "button", className: "btn sm", textContent: q.answer ? "Cambiar respuesta" : "Enviar respuesta" });
  send.addEventListener("click", async () => {
    const r = await staffFetch("/staff/attorney-questions/" + q.id + "/answer", { method: "POST", body: JSON.stringify({ answer: box.value }) });
    say(r.ok ? "Respuesta enviada. La clienta la ve en Preguntas." : "No se pudo enviar la respuesta.");
  });
  item.append(el("label", { htmlFor: box.id, textContent: "Respuesta del abogado" }), box, send);
  return item;
}

async function openClient(jid, me) {
  const container = document.getElementById("clienteDetail");
  if (!container) return;
  const r = await staffFetch("/staff/journeys/" + jid);
  if (!r.ok) { say("No se pudo abrir el expediente."); return; }
  const detail = await r.json();
  const canAnswer = Boolean(me && me.role === "attorney");
  const questions = detail.questions || [];
  container.replaceChildren(
    el("h3", { textContent: detail.client_name }),
    questions.length ? el("ul", { className: "client-questions" }, ...questions.map((q) => questionItem(q, canAnswer)))
                     : el("p", { textContent: "No hay preguntas para el abogado." }),
  );
  if (!canAnswer) container.append(el("p", { textContent: "Solo el abogado responde las preguntas." }));
  container.hidden = false;
}

if (document.getElementById("clientes")) {
  loadClients();
}
