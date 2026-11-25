function esc(value) { return String(value ?? "").replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch])); }
function formatAppointmentTime(value) { if (!value) return ""; const date = new Date(value); return Number.isNaN(date.getTime()) ? value : date.toLocaleString(undefined, {dateStyle:"long",timeStyle:"short"}); }

function renderReportSummary(report, targetId="report") {
  const el = document.getElementById(targetId);
  if (!el || !report) return;
  el.innerHTML = reportCard([["Total",report.total||0],["High risk",(report.high_risk||[]).length],["Urgent",(report.urgent||[]).length],["Attorney review",(report.attorney_review_queue||[]).length]], report.by_stage);
}

function reportCard(figures, byStage) {
  const stages = Object.entries(byStage||{});
  return `<div class="card"><dl class="report-figures">${figures.map(([label,value])=>`<div><dt>${esc(label)}</dt><dd>${esc(value)}</dd></div>`).join("")}</dl>${stages.length?`<table class="report-stages"><caption>Matters by stage</caption><tbody>${stages.map(([stage,count])=>`<tr><td>${esc(stage)}</td><td>${esc(count)}</td></tr>`).join("")}</tbody></table>`:""}</div>`;
}

const PORTAL_API = "https://carbon-law.onrender.com";
const el = (id) => document.getElementById(id);
function authHeaders() { const t = getToken(); const h = {"Content-Type":"application/json"}; if (t) h.Authorization = "Bearer "+t; return h; }
async function request(path, method="GET", body=null) {
  const opts = { method, headers: authHeaders() };
  if (body) opts.body = JSON.stringify(body);
  let res;
  try { res = await fetch(PORTAL_API + path, opts); }
  catch (_) { throw new Error("We can’t reach the service right now."); }
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    if (res.status < 500 && typeof data.detail === "string") throw new Error(data.detail);
    throw new Error("The service had a problem.");
  }
  return res.json();
}
const TRY_LATER = "Please try again later, or call Carbon Law Group at (323) 543-4453.";
function isPast(value) { const date = new Date(value); return !Number.isNaN(date.getTime()) && date < new Date(); }
function formatAppointmentTime(value) {
  if (!value || value === "Not requested") return value || "Not requested";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString(undefined, {dateStyle:"long", timeStyle:"short"});
}
function showToast(msg) {
  const t = document.createElement("div"); t.className="toast"; t.textContent=msg;
  document.body.appendChild(t); setTimeout(()=>t.remove(),3000);
}

let matters = [];
let pendingNewWill = null;
const currentUser = getUser();
async function load() {
  const token = getToken();
  if (!token) { window.location.href = "login.html"; return; }
  try { matters = await request("/my-matters"); } catch(e){ matters=[]; }
  renderMatterSelects();
  await loadPlanningRequest();
  await loadWorkflowAppointments();
  await loadChangeRequests();
  loadDocs();
  if (currentUser && currentUser.role !== "client") loadReport();
}
async function loadPlanningRequest() {
  const box = el("planningRequest");
  if (!box) return;
  try {
    const workflows = await request("/my-workflows");
    if (!workflows.length) {
      const matter = matters[0];
      box.innerHTML = matter ? `<h3>${esc(matter.client_name)}’s matter</h3><p><strong>Matter:</strong> ${esc(matter.id)}</p><p><strong>Status:</strong> ${esc(matter.stage)}</p><p><a href="intake.html">Start a planning request</a></p>` : `No planning request yet. <a href="intake.html">Start an intake</a>`;
      return;
    }
    box.innerHTML = workflows.map(workflow => {
      const docs = (workflow.documents_requested || []).join(", ") || "Not selected yet";
      const appointmentLine = kind => {
        const appointment = workflow.appointments?.[kind];
        const value = appointment?.scheduled_at || appointment?.requested_at;
        const status = appointment?.status === "requested" ? " <span class=\"badge\">Pending approval</span>" : appointment?.status === "scheduled" ? " <span class=\"badge\">Approved</span>" : appointment?.status === "cancelled" ? " <span class=\"badge\">Cancelled</span>" : "";
        return `<p><strong>${kind === "consultation" ? "Consultation" : "Signing"}:</strong> ${esc(formatAppointmentTime(value))}${status}</p>`;
      };
      // a past appointment cannot be cancelled any more
      const cancel = ["consultation", "signing"].filter(kind => { const a = workflow.appointments?.[kind]; return a && !["cancelled", "Cancelled"].includes(a.status) && !isPast(a.scheduled_at || a.requested_at); }).map(kind => `<button class="btn secondary sm" data-cancel-appointment="${esc(workflow.id)}:${kind}">Cancel ${kind}</button>`).join(" ");
      return `<article class="planning-request"><h3>${esc(workflow.client_name)}’s estate plan</h3><p><strong>Matter:</strong> ${esc(workflow.matter_id || "Pending")}</p><p><strong>Status:</strong> ${esc(workflow.stage.replaceAll("_", " "))}</p><p><strong>Documents:</strong> ${esc(docs)}</p>${appointmentLine("consultation")}${appointmentLine("signing")}<p class="planning-actions"><button class="btn" data-edit-workflow="${esc(workflow.id)}">Modify planning request</button> ${cancel}</p></article>`;
    }).join('<hr>');
    box.querySelectorAll("[data-cancel-appointment]").forEach(button => button.onclick = async () => {
      const [workflowId, kind] = button.dataset.cancelAppointment.split(":");
      try { await request(`/workflows/${workflowId}/cancel-appointment`, "POST", {decision:"cancel",note:kind}); await loadPlanningRequest(); }
      catch (error) { showToast("Could not cancel appointment: " + error.message); }
    });
    box.querySelectorAll("[data-edit-workflow]").forEach(button => button.onclick = async () => {
      try { await request(`/workflows/${button.dataset.editWorkflow}/reopen-section`, "POST", {part:2}); location.href = `intake.html?workflow=${encodeURIComponent(button.dataset.editWorkflow)}&part=2`; }
      catch (error) { showToast("Could not edit request: " + error.message); }
    });
  } catch (error) { box.textContent = `Your planning request did not load. ${error.message} ${TRY_LATER}`; }
}

async function loadWorkflowAppointments() {
  const box = el("workflowAppointments");
  if (!box) return;
  try {
    const items = await request("/appointments");
    const pending = items.filter(item => item.workflow_id && item.status === "Requested");
    box.innerHTML = pending.length ? pending.map(item => `<p><strong>${esc(item.kind)}:</strong> ${esc(formatAppointmentTime(item.scheduled_at))} <span class="badge">Pending approval</span> <button class="btn secondary sm" data-cancel-appt="${esc(item.id)}">Cancel request</button></p>`).join("") : "No pending appointment requests.";
    box.querySelectorAll("[data-cancel-appt]").forEach(button => button.onclick = async () => {
      try { await request(`/appointments/${button.dataset.cancelAppt}`, "PATCH", {status:"Cancelled"}); await loadWorkflowAppointments(); await loadPlanningRequest(); }
      catch (error) { showToast("Could not cancel appointment: " + error.message); }
    });
  } catch (error) { box.textContent = `Your appointment requests did not load. ${error.message} ${TRY_LATER}`; }
}

function showNewWillMatter(workflow) {
  el("matterIdGroup").hidden = false;
  el("crMatter").required = false;
  el("crMatter").value = workflow.matter_id;
  el("crMatter").disabled = true;
  el("crOut").innerHTML = `New matter <strong>${esc(workflow.matter_id)}</strong> created. <a href="intake.html">Continue the new planning request →</a>`;
}
function renderMatterSelects() {
  for (const id of ["crMatter", "apptMatter"]) {
    const input = el(id);
    if (input && matters.length === 1 && !input.value) input.value = matters[0].id;
  }
}
async function loadChangeRequests() {
  const box=el("changeRequestStatus"); if(!box)return;
  try {const items=await request("/change-requests");box.innerHTML=items.length?items.map(c=>`<article><p><strong>${esc(c.change_type)}</strong> · ${esc(c.status)}</p><p>Matter: ${esc(c.matter_id)} · Documents: ${esc(c.affected_documents||"Not specified")}</p><p>${esc(c.resolution||c.impact||"The firm will update this request as it is reviewed.")}</p></article>`).join("<hr>"):"No change requests yet."}catch(e){box.textContent=`Your change requests did not load. ${e.message} ${TRY_LATER}`}
}
async function loadDocs() {
  try {
    const docs = await request("/documents");
    const rows = el("docRows");
    if (!rows) return;
    rows.innerHTML = docs.length ? "" : `<tr class="empty-row"><td colspan="4">No documents yet. Drafts appear here when the firm shares them.</td></tr>`;
    docs.forEach(d => {
      const tr = document.createElement("tr");
      const review = d.content ? `<details><summary>View review draft</summary><pre>${esc(d.content)}</pre></details>` : "";
      tr.innerHTML = `<td>${esc(d.matter_id)}</td><td>${esc(d.name)}${review}</td><td>${d.version}</td><td>${esc(d.status)}</td>`;
      rows.appendChild(tr);
    });
  } catch(e){ if (el("docRows")) el("docRows").innerHTML = `<tr class="empty-row"><td colspan="4">Your documents did not load. ${esc(e.message)} ${esc(TRY_LATER)}</td></tr>`; }
}
async function loadReport() {
  try {
    const report = await request("/reports/friday");
    renderReportSummary(report);
  } catch(e){ if (el("report")) el("report").textContent = "The report did not load. " + e.message; }
}
document.addEventListener("DOMContentLoaded", () => {
  load();
  el("changeType")?.addEventListener("change", () => {
    const isNewWill = el("changeType").value === "New will";
    el("matterIdGroup").hidden = isNewWill;
    el("crMatter").required = !isNewWill;
    el("crMatter").disabled = false;
    el("crMatter").value = isNewWill ? "" : (matters[0]?.id || "");
    el("crOut").textContent = "";
    if (isNewWill && !pendingNewWill) el("crOut").textContent = "Submit to create a new matter ID.";
    if (isNewWill && pendingNewWill) showNewWillMatter(pendingNewWill);
  });
  el("changeForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (el("changeType").value === "New will") {
      try {
        const workflow = pendingNewWill || await request("/workflows", "POST", {related_names:[], demo_mode:false});
        pendingNewWill = workflow;
        location.href = "intake.html";
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
      el("crOut").textContent = "Submitted. Current status: " + result.status;
      await loadChangeRequests();
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
