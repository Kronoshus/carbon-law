
function renderReportSummary(report, targetId="report") {
  const el = document.getElementById(targetId);
  if (!el || !report) return;
  const stages = Object.entries(report.by_stage||{}).map(([k,v])=>`<span>${k}: ${v}</span>`).join(" | ");
  el.innerHTML = `<div class="card"><strong>Total:</strong> ${report.total||0} &nbsp; <strong>High Risk:</strong> ${(report.high_risk||[]).length} &nbsp; <strong>Urgent:</strong> ${(report.urgent||[]).length} &nbsp; <strong>Review Queue:</strong> ${(report.attorney_review_queue||[]).length}</div><p>${stages}</p>`;
}

const API = localStorage.getItem("carbon_api") || "https://carbon-law.onrender.com";
const el = (id) => document.getElementById(id);
async function request(path, method="GET", body=null) {
  const opts = { method, headers: {"Content-Type":"application/json"} };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(API + path, opts);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

let matters = [];
async function load() {
  try { await request("/seed","POST").catch(()=>null); matters = await request("/matters"); } catch(e){ matters=[]; }
  renderMatterSelects();
  renderDetail();
  loadDocs();
  loadReport();
}
function matterOptions(selectId) {
  const sel = el(selectId);
  if (!sel) return;
  sel.innerHTML = matters.map(m=>`<option value="${m.id}">${m.id} - ${m.client_name}</option>`).join("");
}
function renderMatterSelects() {
  matterOptions("matterSelect");
  matterOptions("crMatter");
  matterOptions("apptMatter");
  matterOptions("docMatter");
}
function renderDetail() {
  const id = el("matterSelect")?.value;
  const m = matters.find(x=>x.id===id);
  const box = el("matterDetail");
  if (!box) return;
  if (!m) { box.innerHTML = "No matter selected."; return; }
  box.innerHTML = `<div class="card"><h3>${m.id} — ${m.client_name}</h3>
  <p><strong>Stage:</strong> ${m.stage}</p>
  <p><strong>Owner:</strong> ${m.owner}</p>
  <p><strong>Attorney Reviewer:</strong> ${m.attorney_reviewer||"Unassigned"}</p>
  <p><strong>Due Date:</strong> ${m.due_date||"TBD"}</p>
  <p><strong>Risk:</strong> ${m.risk_level} | <strong>Priority:</strong> ${m.priority}</p>
  <p><strong>Document Status:</strong> ${m.document_status}</p>
  <p><strong>Title Status:</strong> ${m.title_status}</p>
  <p><strong>Funding Status:</strong> ${m.funding_status}</p>
  <p><strong>Appointment Status:</strong> ${m.appointment_status}</p>
  <p><strong>Next Action:</strong> ${m.next_action||""}</p>
  <p><strong>Blocker:</strong> ${m.blocker||"None"}</p></div>`;
}
async function loadDocs() {
  try {
    const docs = await request("/documents");
    const rows = el("docRows");
    if (!rows) return;
    rows.innerHTML = "";
    docs.forEach(d => {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td>${d.matter_id}</td><td>${d.name}</td><td>${d.version}</td><td>${d.status}</td>`;
      rows.appendChild(tr);
    });
  } catch(e){}
}
async function loadReport() {
  try {
    const report = await request("/reports/friday");
    renderReportSummary(report);
  } catch(e){ if (el("report")) el("report").textContent = "Backend unavailable."; }
}
document.addEventListener("DOMContentLoaded", () => {
  load();
  el("matterSelect")?.addEventListener("change", renderDetail);
  el("changeForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const body = {
      matter_id: el("crMatter").value,
      requested_by: "client",
      change_type: el("changeType").value,
      affected_documents: el("docs").value,
      impact: el("crImpact").value,
      status: "Open"
    };
    const result = await request("/change-requests","POST",body);
    el("crOut").textContent = "Submitted: " + result.id;
  });
  el("bookAppt")?.addEventListener("click", async () => {
    const body = {
      matter_id: el("apptMatter").value,
      kind: "Signing",
      scheduled_at: el("apptTime").value || new Date().toISOString(),
      status: "Rescheduled",
      note: "Client requested reschedule"
    };
    const result = await request("/appointments","POST",body);
    el("apptOut").textContent = "Appointment request submitted: " + result.id;
  });
  el("cancelAppt")?.addEventListener("click", async () => {
    const body = {
      matter_id: el("apptMatter").value,
      kind: "Signing",
      scheduled_at: new Date().toISOString(),
      status: "Cancelled",
      note: "Client requested cancellation"
    };
    const result = await request("/appointments","POST",body);
    el("apptOut").textContent = "Cancellation request submitted: " + result.id;
  });
  el("addDoc")?.addEventListener("click", async () => {
    const body = {
      matter_id: el("docMatter").value,
      name: el("docName").value,
      status: el("docStatus").value
    };
    await request("/documents","POST",body);
    await loadDocs();
  });
});

document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("genReport");
  if (btn) btn.addEventListener("click", async () => {
    try {
      const report = await request("/reports/friday");
      renderReportSummary(report);
    } catch (e) { }
  });
});
