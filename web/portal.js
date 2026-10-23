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
  try { matters = await request("/my-matters"); } catch(e){ matters=[]; if (el("matterDetail")) el("matterDetail").textContent = "Could not load matters: " + e.message; showToast("Backend unavailable"); }
  renderMatterSelects();
  await loadPlanningRequest();
  await loadWorkflowAppointments();
  loadDocs();
  if (currentUser && currentUser.role !== "client") loadReport();
}
async function loadPlanningRequest() {
  const box = el("planningRequest");
  if (!box) return;
  try {
    const workflow = await request("/my-workflow");
    if (Array.isArray(workflow)) throw new Error("Unexpected workflow response");
    if (!workflow) {
      const matter = matters[0];
      box.innerHTML = matter ? `<h3>${esc(matter.client_name)}’s matter</h3><p><strong>Matter:</strong> ${esc(matter.id)}</p><p><strong>Status:</strong> ${esc(matter.stage)}</p><p><a href="intake.html">Start a planning request</a></p>` : `No planning request yet. <a href="intake.html">Start an intake</a>`;
      return;
    }
    const docs = (workflow.documents_requested || []).join(", ") || "Not selected yet";
    const consultation = workflow.appointments?.consultation?.scheduled_at || workflow.appointments?.consultation?.requested_at || "Not requested";
    const signing = workflow.appointments?.signing?.scheduled_at || workflow.appointments?.signing?.requested_at || "Not requested";
    const cancel = ["consultation", "signing"].filter(kind => workflow.appointments?.[kind] && !["cancelled", "Cancelled"].includes(workflow.appointments[kind].status)).map(kind => `<button class="btn secondary" data-cancel-appointment="${kind}">Cancel ${kind}</button>`).join(" ");
    box.innerHTML = `<h3>${esc(workflow.client_name)}’s estate plan</h3><p><strong>Matter:</strong> ${esc(workflow.matter_id || "Pending")}</p><p><strong>Status:</strong> ${esc(workflow.stage.replaceAll("_", " "))}</p><p><strong>Documents:</strong> ${esc(docs)}</p><p><strong>Consultation:</strong> ${esc(consultation)}</p><p><strong>Signing:</strong> ${esc(signing)}</p>${cancel}<p><button class="btn" id="editPlanningRequest">Modify planning request</button></p>`;
    box.querySelectorAll("[data-cancel-appointment]").forEach(button => button.onclick = async () => {
      try { await request(`/workflows/${workflow.id}/cancel-appointment`, "POST", {decision:"cancel",note:button.dataset.cancelAppointment}); await loadPlanningRequest(); }
      catch (error) { showToast("Could not cancel appointment: " + error.message); }
    });
    el("editPlanningRequest").onclick = async () => {
      try { await request(`/workflows/${workflow.id}/edit`, "POST", {}); location.href = "intake.html"; }
      catch (error) { showToast("Could not edit request: " + error.message); }
    };
  } catch (error) { box.textContent = "Could not load your planning request: " + error.message; }
}

async function loadWorkflowAppointments() {
  const box = el("workflowAppointments");
  if (!box) return;
  try {
    const items = await request("/appointments");
    const pending = items.filter(item => item.workflow_id && item.status === "Requested");
    box.innerHTML = pending.length ? pending.map(item => `<p><strong>${esc(item.kind)}:</strong> ${esc(item.scheduled_at)} <span class="badge">Pending approval</span> <button class="btn secondary" data-cancel-appt="${esc(item.id)}">Cancel request</button></p>`).join("") : "No pending appointment requests.";
    box.querySelectorAll("[data-cancel-appt]").forEach(button => button.onclick = async () => {
      try { await request(`/appointments/${button.dataset.cancelAppt}?status=Cancelled`, "PATCH"); await loadWorkflowAppointments(); await loadPlanningRequest(); }
      catch (error) { showToast("Could not cancel appointment: " + error.message); }
    });
  } catch (error) { box.textContent = "Could not load appointment requests: " + error.message; }
}

function renderMatterSelects() {
  for (const id of ["crMatter", "apptMatter"]) {
    const input = el(id);
    if (input && matters.length === 1 && !input.value) input.value = matters[0].id;
  }
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
  el("changeForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (el("changeType").value === "New will") {
      try {
        const workflow = await request("/workflows", "POST", {related_names:[], demo_mode:false});
        el("crMatter").value = workflow.matter_id;
        el("crMatter").disabled = true;
        el("crOut").innerHTML = `New matter <strong>${esc(workflow.matter_id)}</strong> created. <a href="intake.html">Continue the new planning request →</a>`;
      } catch (error) { el("crOut").textContent = error.message; }
      return;
    }
    const body = {
      matter_id: el("crMatter").value,
      requested_by: "client",
      change_type: el("changeType").value,
      affected_documents: el("docs").value,
      impact: el("crImpact").value,
      status: "Open"
    };
    try {
      const result = await request("/change-requests","POST",body);
      el("crOut").textContent = "Submitted: " + result.id;
    } catch (error) { el("crOut").textContent = error.message; }
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
