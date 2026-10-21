function esc(value) { return String(value ?? "").replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch])); }

function renderReportSummary(report, targetId="report") {
  const el = document.getElementById(targetId);
  if (!el || !report) return;
  const stages = Object.entries(report.by_stage||{}).map(([k,v])=>`<span>${esc(k)}: ${v}</span>`).join(" | ");
  el.innerHTML = `<div class="card"><strong>Total:</strong> ${report.total||0} &nbsp; <strong>High Risk:</strong> ${(report.high_risk||[]).length} &nbsp; <strong>Urgent:</strong> ${(report.urgent||[]).length} &nbsp; <strong>Review Queue:</strong> ${(report.attorney_review_queue||[]).length}</div><p>${stages}</p>`;
}

const PORTAL_API = "https://carbon-law.onrender.com";
const el = (id) => document.getElementById(id);
function authHeaders() { const t = getToken(); const h = {"Content-Type":"application/json"}; if (t) h.Authorization = "Bearer "+t; return h; }
async function request(path, method="GET", body=null) {
  const opts = { method, headers: authHeaders() };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(PORTAL_API + path, opts);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
function showToast(msg) {
  const t = document.createElement("div"); t.className="toast"; t.textContent=msg;
  document.body.appendChild(t); setTimeout(()=>t.remove(),3000);
}

let matters = [];
const currentUser = getUser();
async function load() {
  const token = getToken();
  if (!token) { window.location.href = "login.html"; return; }
  try { matters = await request("/my-matters"); } catch(e){ matters=[]; showToast("Backend unavailable"); }
  renderMatterSelects();
  renderDetail();
  loadDocs();
  if (currentUser && currentUser.role !== "client") loadReport();
}
function matterOptions(selectId) {
  const sel = el(selectId);
  if (!sel) return;
  sel.innerHTML = matters.map(m=>`<option value="${esc(m.id)}">${esc(m.id)} - ${esc(m.client_name)}</option>`).join("");
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
  box.innerHTML = `<div class="card"><h3>${esc(m.id)} — ${esc(m.client_name)}</h3>
  <p><strong>Stage:</strong> ${esc(m.stage)}</p>
  <p><strong>Owner:</strong> ${esc(m.owner)}</p>
  <p><strong>Attorney Reviewer:</strong> ${esc(m.attorney_reviewer||"Unassigned")}</p>
  <p><strong>Due Date:</strong> ${esc(m.due_date||"TBD")}</p>
  <p><strong>Risk:</strong> ${esc(m.risk_level)} | <strong>Priority:</strong> ${esc(m.priority)}</p>
  <p><strong>Document Status:</strong> ${esc(m.document_status)}</p>
  <p><strong>Title Status:</strong> ${esc(m.title_status)}</p>
  <p><strong>Funding Status:</strong> ${esc(m.funding_status)}</p>
  <p><strong>Appointment Status:</strong> ${esc(m.appointment_status)}</p>
  <p><strong>Next Action:</strong> ${esc(m.next_action||"")}</p>
  <p><strong>Blocker:</strong> ${esc(m.blocker||"None")}</p></div>`;
}
async function loadDocs() {
  try {
    const docs = await request("/documents");
    const rows = el("docRows");
    if (!rows) return;
    rows.innerHTML = "";
    docs.forEach(d => {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td>${esc(d.matter_id)}</td><td>${esc(d.name)}</td><td>${d.version}</td><td>${esc(d.status)}</td>`;
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
