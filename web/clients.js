const CONFLICT_LABELS = { pending: "Pendiente", clear: "Sin conflicto", hold: "En revisión" };

async function loadClients() {
  const rows = document.getElementById("clientesRows");
  if (!rows) return;
  const token = getToken();
  let me = null;
  try { me = await fetch(CARBON_API_BASE + "/auth/me", { headers: { Authorization: "Bearer " + token } }).then(r => r.json()); } catch (_) {}
  let list = [];
  try { list = await fetch(CARBON_API_BASE + "/staff/journeys", { headers: { Authorization: "Bearer " + token } }).then(r => r.json()); } catch (_) { list = []; }
  rows.replaceChildren();
  for (const r of list) {
    const tr = document.createElement("tr");
    const tdName = document.createElement("td");
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = r.client_name;
    btn.addEventListener("click", () => openClient(r.journey_id, me));
    tdName.appendChild(btn);
    tr.appendChild(tdName);

    const tdDay = document.createElement("td");
    tdDay.textContent = String(r.day);
    tr.appendChild(tdDay);

    const tdLate = document.createElement("td");
    tdLate.textContent = (r.late || []).join(", ");
    tr.appendChild(tdLate);

    const tdConf = document.createElement("td");
    tdConf.textContent = CONFLICT_LABELS[r.conflict] || r.conflict;
    tr.appendChild(tdConf);

    const tdDatos = document.createElement("td");
    tdDatos.textContent = r.datos.done + " de " + r.datos.total;
    tr.appendChild(tdDatos);

    const tdPay = document.createElement("td");
    tdPay.textContent = r.payment.paid ? "Pagado" : "Sin pagar";
    tr.appendChild(tdPay);

    const tdDrafts = document.createElement("td");
    tdDrafts.textContent = String(r.drafts_waiting);
    tr.appendChild(tdDrafts);

    const tdAppts = document.createElement("td");
    tdAppts.textContent = (r.appointments || []).map(a => a.kind + " " + a.start_utc).join(", ");
    tr.appendChild(tdAppts);

    const tdQs = document.createElement("td");
    tdQs.textContent = r.questions.open + " / " + r.questions.answered;
    tr.appendChild(tdQs);

    rows.appendChild(tr);
  }
}

async function openClient(jid, me) {
  const token = getToken();
  const detail = await fetch(CARBON_API_BASE + "/staff/journeys/" + jid, { headers: { Authorization: "Bearer " + token } }).then(r => r.json());
  const container = document.getElementById("clienteDetail");
  if (!container) return;
  container.hidden = false;
  container.replaceChildren();

  const heading = document.createElement("h3");
  heading.textContent = detail.client_name;
  container.appendChild(heading);

  const list = document.createElement("ul");
  for (const q of (detail.questions || [])) {
    const li = document.createElement("li");
    const pq = document.createElement("p");
    pq.textContent = q.question;
    li.appendChild(pq);
    if (q.answer) {
      const pa = document.createElement("p");
      const strong = document.createElement("strong");
      strong.textContent = "Respuesta del abogado";
      pa.appendChild(strong);
      pa.appendChild(document.createTextNode(" " + q.answer));
      li.appendChild(pa);
    }
    list.appendChild(li);
  }
  container.appendChild(list);

  if (me && me.role === "attorney") {
    const label = document.createElement("label");
    label.textContent = "Respuesta del abogado";
    label.setAttribute("for", "respuesta-" + jid);
    container.appendChild(label);
    const textarea = document.createElement("textarea");
    textarea.id = "respuesta-" + jid;
    container.appendChild(textarea);
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = "Enviar respuesta";
    btn.addEventListener("click", async () => {
      const qid = (detail.questions && detail.questions[0]) ? detail.questions[0].id : null;
      if (!qid) return;
      await fetch(CARBON_API_BASE + "/staff/attorney-questions/" + qid + "/answer", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: "Bearer " + getToken() },
        body: JSON.stringify({ answer: textarea.value }),
      });
    });
    container.appendChild(btn);
  } else {
    const p = document.createElement("p");
    p.textContent = "Solo el abogado responde las preguntas.";
    container.appendChild(p);
  }
}

if (document.getElementById("clientes")) {
  loadClients();
}
