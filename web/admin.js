function esc(value) { return String(value ?? "").replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch])); }

const STAGES = ["1 Intake","2 Attorney Scope","3 Client Data Collection","4 Drafting","5 Review Queue","6 Client Review","7 Signing Preparation","8 Execution","9 Funding Follow-Up","10 Closed"];
function formatAppointmentTime(value) { if (!value) return ""; const date = new Date(value); return Number.isNaN(date.getTime()) ? value : date.toLocaleString(undefined, {dateStyle:"long",timeStyle:"short"}); }
function renderReportSummary(report, targetId="report") {
  const el = document.getElementById(targetId);
  if (!el || !report) return;
  const stages = Object.entries(report.by_stage||{}).map(([k,v])=>`<span>${esc(k)}: ${v}</span>`).join(" | ");
  el.innerHTML = `<div class="card"><strong>Total:</strong> ${report.total||0} &nbsp; <strong>High Risk:</strong> ${(report.high_risk||[]).length} &nbsp; <strong>Urgent:</strong> ${(report.urgent||[]).length} &nbsp; <strong>Attorney Review:</strong> ${(report.attorney_review_queue||[]).length} &nbsp; <strong>Overdue:</strong> ${report.overdue_count||0} &nbsp; <strong>Open tasks:</strong> ${report.open_tasks||0} &nbsp; <strong>Open change requests:</strong> ${report.open_change_requests||0} &nbsp; <strong>Pending appointments:</strong> ${report.appointments_pending||0}</div><p>${stages}</p>`;
}

const ADMIN_API = "https://carbon-law.onrender.com";
function authHeaders() { const t = getToken(); const h = {"Content-Type":"application/json"}; if (t) h.Authorization = "Bearer "+t; return h; }
async function request(path, method="GET", body=null) {
  const opts = { method, headers: authHeaders() };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(ADMIN_API + path, opts);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

async function loadWorkflows() {
  const rows = document.getElementById("workflowRows"); if (!rows) return;
  const workflows = await request("/my-workflow");
  rows.innerHTML = workflows.map(w => `<tr><td>${esc(w.client_name)}<br><small>${esc((w.related_names||[]).join(", "))}</small></td><td>${esc(w.stage)}</td><td>${esc((w.documents_requested||[]).join(", ")||"Conflict review")}${w.drafts&&Object.keys(w.drafts).length?`<details><summary>Review drafts</summary>${Object.entries(w.drafts).map(([name,d])=>`<h4>${esc(name)}</h4><pre>${esc(d.content)}</pre>`).join("")}</details>`:""}</td><td>${w.stage==="conflict_review"?`<button class="btn sm" data-workflow="${esc(w.id)}" data-decision="conflict_cleared">Clear</button> <button class="btn secondary sm" data-workflow="${esc(w.id)}" data-decision="conflict_flagged">Flag</button>`:w.stage==="attorney_review"?`<button class="btn sm" data-workflow="${esc(w.id)}" data-decision="attorney_approved">Attorney approve</button> <button class="btn secondary sm" data-workflow="${esc(w.id)}" data-decision="attorney_changes">Request changes</button>`:["consultation","signing"].includes(w.stage)?`${(w.appointments||{}).consultation?.status==="requested"?`<input type="datetime-local" data-time="${esc(w.id)}-consultation" value="${esc((w.appointments||{}).consultation.requested_at)}"><button class="btn sm" data-schedule="${esc(w.id)}" data-kind="consultation">Approve consultation</button>`:""} ${(w.appointments||{}).signing?.status==="requested"?`<input type="datetime-local" data-time="${esc(w.id)}-signing" value="${esc((w.appointments||{}).signing.requested_at)}"><button class="btn sm" data-schedule="${esc(w.id)}" data-kind="signing">Approve signing</button>`:""} ${(w.appointments||{}).consultation?.status==="scheduled"?`<button class="btn secondary sm" data-workflow="${esc(w.id)}" data-decision="consultation_completed">Mark consultation complete</button>`:""}`:"—"}</td></tr>`).join("");
  rows.querySelectorAll("button[data-schedule]").forEach(button => button.addEventListener("click", async () => { const input=rows.querySelector(`[data-time="${button.dataset.workflow}-${button.dataset.kind}"]`); if (!input?.value) return; await request(`/workflows/${button.dataset.workflow}/appointment`,"PATCH",{kind:button.dataset.kind,scheduled_at:input.value}); await loadWorkflows(); await loadAppointments(); }));
  rows.querySelectorAll("button[data-workflow]").forEach(button => button.addEventListener("click", async () => { await request(`/workflows/${button.dataset.workflow}/staff-review`, "PATCH", {decision:button.dataset.decision}); await loadWorkflows(); }));
}

async function load() {
  const token = getToken();
  if (!token) { window.location.href = "login.html"; return; }
  await loadMatters();
  await loadWorkflows();
  await loadChangeRequests();
  await loadAppointments();
  await loadDocuments();
  await loadReport();
  await Promise.all([loadContacts(),loadOperationsReports(),loadAudit(),loadPracticeFiles("prompts"),loadPracticeFiles("templates")]);
}
async function loadMatters() {
  try {
    adminMatters = await request("/matters");
    const matters = adminMatters;
    setupMatterSelectors();
    const rows = document.getElementById("adminMatterRows");
    if (rows) {
      rows.innerHTML = "";
      matters.forEach(m => {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td><button class="btn secondary sm" data-history="${esc(m.id)}">${esc(m.id)}</button></td><td>${esc(m.client_name)}</td><td>${esc(m.stage)}</td><td>${esc(m.owner)}</td><td>${esc(m.risk_level)}</td><td>${esc(m.priority)}</td><td>${esc(m.due_date||"")}</td>
        <td><select data-id="${esc(m.id)}" class="stageSelect">
        ${STAGES.map(s=>`<option ${s===m.stage?"selected":""}>${esc(s)}</option>`).join("")}
        </select></td>`;
        rows.appendChild(tr);
      });
      rows.querySelectorAll("[data-history]").forEach(button=>button.onclick=()=>loadMatterHistory(button.dataset.history));
      document.querySelectorAll(".stageSelect").forEach(sel => {
        sel.addEventListener("change", async (e) => {
          const id = e.target.getAttribute("data-id");
          try { await request(`/matters/${id}`, "PATCH", {stage: e.target.value}); await Promise.all([loadMatters(),loadWorkflows(),loadAudit()]); }
          catch(error) { showError(error); }
        });
      });
    }
  } catch (e) { showError(e); }
}
async function loadChangeRequests() {
  try {
    const items = await request("/change-requests");
    const rows = document.getElementById("crRows");
    if (rows) {
      rows.innerHTML = "";
      items.forEach(c => {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td>${c.id.slice(0,8)}</td><td>${esc(c.matter_id)}</td><td>${esc(c.change_type)}</td><td>${esc(c.requested_by)}</td><td><select data-cr-status="${esc(c.id)}">${["Open","In Review","Resolved","Rejected"].map(status=>`<option ${c.status===status?"selected":""}>${status}</option>`).join("")}</select></td><td>${esc(c.impact||"")}<br><input data-cr-resolution="${esc(c.id)}" placeholder="Resolution / client-facing update" value="${esc(c.resolution||"")}"><button class="btn secondary sm" data-save-cr="${esc(c.id)}">Save</button></td>`;
        rows.appendChild(tr);
      });
      rows.querySelectorAll("[data-save-cr]").forEach(button=>button.onclick=async()=>{const id=button.dataset.saveCr;try{await request(`/change-requests/${id}`,"PATCH",{status:rows.querySelector(`[data-cr-status="${CSS.escape(id)}"]`).value,resolution:rows.querySelector(`[data-cr-resolution="${CSS.escape(id)}"]`).value});await loadChangeRequests();await loadTasks();await loadAudit()}catch(e){showError(e)}});
    }
  } catch(e){showError(e)}
}
async function loadAppointments() {
  try {
    const items = await request("/appointments");
    const rows = document.getElementById("apptRows");
    if (rows) {
      rows.innerHTML = "";
      items.forEach(a => {
        const tr = document.createElement("tr");
        const dt = a.scheduled_at ? new Date(a.scheduled_at) : null; const local = dt && !Number.isNaN(dt.getTime()) ? new Date(dt.getTime()-dt.getTimezoneOffset()*60000).toISOString().slice(0,16) : "";
        tr.innerHTML = `<td>${a.id.slice(0,8)}</td><td>${esc(a.matter_id)}</td><td>${esc(a.kind)}</td><td><input data-appt="time" type="datetime-local" value="${esc(local)}"></td><td><select data-appt="status">${["Requested","Scheduled","Cancelled","Completed"].map(status=>`<option ${a.status===status?"selected":""}>${status}</option>`).join("")}</select></td><td><input data-appt="note" value="${esc(a.note||"")}"><button class="btn secondary sm" data-save-appointment="${esc(a.id)}">Save</button></td>`;
        rows.appendChild(tr);
      });
      rows.querySelectorAll("[data-save-appointment]").forEach(button=>button.onclick=()=>saveAppointment(button));
    }
  } catch(e){showError(e)}
}
async function loadDocuments() {
  try {
    const items = await request("/documents");
    const rows = document.getElementById("docRows");
    if (rows) {
      rows.innerHTML = "";
      items.forEach(d => {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td>${esc(d.matter_id)}</td><td>${esc(d.name)}</td><td>${d.version}</td><td><select data-doc-status="${esc(d.id)}">${["Draft","Attorney Review","Client Review","Signed","Archived"].map(status=>`<option ${d.status===status?"selected":""}>${status}</option>`).join("")}</select> <button class="btn secondary sm" data-save-document="${esc(d.id)}">Save</button></td>`;
        rows.appendChild(tr);
      });
      rows.querySelectorAll("[data-save-document]").forEach(button=>button.onclick=async()=>{const id=button.dataset.saveDocument;try{await request(`/documents/${id}?status=${encodeURIComponent(rows.querySelector(`[data-doc-status="${CSS.escape(id)}"]`).value)}`,"PATCH");await loadDocuments();await loadAudit()}catch(e){showError(e)}});
    }
  } catch(e){showError(e)}
}
async function loadReport() {
  try {
    const report = await request("/reports/friday");
    renderReportSummary(report);
  } catch(e){}
}

document.addEventListener("DOMContentLoaded", () => {
  load();
  const form = document.getElementById("matterForm");
  if (form) form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const body = {
      id: document.getElementById("newId").value,
      client_name: document.getElementById("newClient").value,
      stage: "1 Intake",
      owner: document.getElementById("newOwner").value || "Unassigned",
      attorney_reviewer: document.getElementById("newAttorney").value || null,
      risk_level: document.getElementById("newRisk").value,
      priority: document.getElementById("newPriority").value,
      due_date: document.getElementById("newDue").value || null,
      next_action: "Complete intake"
    };
    const result = await request("/matters","POST",body);
    document.getElementById("adminOut").textContent = "Matter created: " + result.id;
    await loadMatters();
  await loadWorkflows();
  });
});

document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("genReport");
  if (btn) btn.addEventListener("click", async () => {
    try {
      const report = await request("/reports/friday");
      renderReportSummary(report);
    } catch (e) { showError(e,"report"); }
  });
});


let adminMatters = [];
const q = id => document.getElementById(id);
const query = values => new URLSearchParams(values).toString();
function showMessage(id, text) { const node=q(id); if(node) node.textContent=text; }
function showError(error, target="adminOut") { showMessage(target,error?.message||String(error)); }
function optionList(items, value, label=value) { return items.map(item=>`<option value="${esc(item[value]||"")}">${esc(item[label]||"")}</option>`).join(""); }
function setupMatterSelectors() {
  const data=q("matterOptions"); if(data) data.innerHTML=adminMatters.map(m=>`<option value="${esc(m.id)}">${esc(m.client_name)}</option>`).join("");
  for(const id of ["commMatter","taskFilter"]) { const select=q(id); if(!select) continue; const previous=select.value; select.innerHTML=`<option value="">${id==="taskFilter"?"All matters":"Select a matter"}</option>`+adminMatters.map(m=>`<option value="${esc(m.id)}">${esc(m.id)} — ${esc(m.client_name)}</option>`).join(""); if(previous) select.value=previous; }
}
async function loadTasks() {
  try {
    const id=q("taskFilter")?.value; const items=await request("/tasks"+(id?`?matter_id=${encodeURIComponent(id)}`:""));
    q("taskRows").innerHTML=items.map(t=>`<tr><td>${esc(t.matter_id)}</td><td>${esc(t.title)}</td><td><input data-field="owner" value="${esc(t.owner)}" aria-label="Task owner"></td><td><input data-field="due_date" type="date" value="${esc(t.due_date||"")}" aria-label="Task due date"></td><td><select data-field="status"><option ${t.status==="Open"?"selected":""}>Open</option><option ${t.status==="In Progress"?"selected":""}>In Progress</option><option ${t.status==="Done"?"selected":""}>Done</option><option ${t.status==="Blocked"?"selected":""}>Blocked</option></select></td><td><input data-field="blocker" value="${esc(t.blocker||"None")}" aria-label="Blocker"></td><td><button class="btn secondary sm" data-save-task="${esc(t.id)}">Save</button></td></tr>`).join("");
    q("taskRows").querySelectorAll("[data-save-task]").forEach(button=>button.onclick=async()=>{const row=button.closest("tr"),payload={};row.querySelectorAll("[data-field]").forEach(el=>payload[el.dataset.field]=el.value);try{await request(`/tasks/${button.dataset.saveTask}`,"PATCH",payload);showMessage("taskMessage","Task updated.");await loadTasks();await loadAudit()}catch(e){showError(e,"taskMessage")}});
  } catch(e){showError(e,"taskMessage")}
}
async function loadContacts() {
  try { const items=await request("/contacts"); q("contactRows").innerHTML=items.map(c=>`<tr><td>${esc(c.created_at||"")}</td><td>${esc(c.name)}</td><td>${esc(c.email)}</td><td>${esc(c.phone)}</td><td>${esc(c.service||"")}<br>${esc(c.message||"")}</td><td><select data-contact-status="${esc(c.id)}">${["New","Contacted","Consultation Scheduled","Converted","Closed"].map(s=>`<option ${c.status===s?"selected":""}>${s}</option>`).join("")}</select></td><td><input data-contact-note="${esc(c.id)}" value="${esc(c.note||"")}" maxlength="500"></td><td><button class="btn secondary sm" data-save-contact="${esc(c.id)}">Save</button></td></tr>`).join("");
    q("contactRows").querySelectorAll("[data-save-contact]").forEach(button=>button.onclick=async()=>{const id=button.dataset.saveContact;try{await request(`/contacts/${id}`,"PATCH",{status:q("contactRows").querySelector(`[data-contact-status="${CSS.escape(id)}"]`).value,note:q("contactRows").querySelector(`[data-contact-note="${CSS.escape(id)}"]`).value});showMessage("contactMessage","Contact updated.");await loadContacts();await loadAudit()}catch(e){showError(e,"contactMessage")}});
  } catch(e){showError(e,"contactMessage")}
}
async function loadCommunications() {
  const matterId=q("commMatter")?.value; if(!matterId){q("commRows").textContent="Select a matter to view its communication log.";return;}
  try { const items=await request(`/communications?matter_id=${encodeURIComponent(matterId)}`); q("commRows").innerHTML=items.length?items.map(c=>`<p><strong>${esc(c.direction)} · ${esc(c.channel)} · ${esc(c.created_at)}</strong> (${esc(c.visibility||"internal")})<br>${esc(c.summary)}</p>`).join(""):"No communication entries for this matter."; }
  catch(e){showError(e,"commMessage")}
}
async function loadOperationsReports() {
  try {
    const [capacity,bottlenecks]=await Promise.all([request("/reports/capacity"),request("/reports/bottlenecks")]);
    q("capacityReport").innerHTML=`<p>Counts by matter owner, not hours or availability.</p><table><thead><tr><th>Owner</th><th>Matters</th><th>High risk</th><th>Urgent</th><th>Overdue</th></tr></thead><tbody>${Object.entries(capacity.by_owner||{}).map(([owner,v])=>`<tr><td>${esc(owner)}</td><td>${v.matters}</td><td>${v.high_risk}</td><td>${v.urgent}</td><td>${v.overdue}</td></tr>`).join("")}</tbody></table>`;
    q("bottleneckReport").innerHTML=`<p>Waiting on client: <strong>${bottlenecks.waiting_on_client}</strong> · Blocked matters: <strong>${bottlenecks.blocked_matters}</strong> · Open change requests: <strong>${bottlenecks.open_change_requests}</strong></p><ul>${(bottlenecks.top_stages||[]).map(([stage,count])=>`<li>${esc(stage)}: ${count}</li>`).join("")}</ul>`;
  }catch(e){showError(e,"capacityReport")}
}
async function loadAudit() {
  try { const entity=q("auditEntity")?.value.trim(); const items=await request(`/audit?limit=100${entity?`&entity=${encodeURIComponent(entity)}`:""}`); q("auditRows").innerHTML=items.slice().reverse().map(a=>`<tr><td>${esc(a.time)}</td><td>${esc(a.actor)}</td><td>${esc(a.action)}</td><td>${esc(a.entity)} ${esc(a.entity_id)}</td><td>${esc(a.detail)}</td></tr>`).join(""); }
  catch(e){showError(e,"auditRows")}
}
async function loadPracticeFiles(kind) {
  const select=q(kind+"Select"), content=q(kind+"Content");
  try { const files=await request(`/${kind}s`); select.innerHTML='<option value="">Select a '+kind.slice(0,-1)+'</option>'+files.map(f=>`<option value="${esc(f.name)}">${esc(f.name)}</option>`).join(""); select.onchange=async()=>{if(!select.value){content.textContent="";return}try{const data=await request(`/${kind}s/${encodeURIComponent(select.value)}`);content.textContent=data.content}catch(e){content.textContent=e.message}}; }
  catch(e){content.textContent=e.message}
}
async function loadMatterHistory(matterId) {
  try {const h=await request(`/matters/${encodeURIComponent(matterId)}/history`);const entries=[...(h.stages||[]).map(x=>({...x,type:"Stage",detail:x.stage})),...(h.tasks||[]).map(x=>({...x,time:x.updated_at||x.created_at,type:"Task",detail:x.title})),...(h.changes||[]).map(x=>({...x,time:x.updated_at||x.created_at,type:"Change request",detail:x.change_type+" — "+x.status})),...(h.comms||[]).map(x=>({...x,time:x.created_at,type:"Communication",detail:x.summary}))].sort((a,b)=>String(a.time||"").localeCompare(String(b.time||"")));q("historyTitle").textContent=`${matterId} history`;q("historyContent").innerHTML=entries.map(x=>`<p><strong>${esc(x.time||"")} · ${esc(x.type)}</strong> — ${esc(x.detail||"")}</p>`).join("")||"No history recorded.";q("historyDialog").showModal()}catch(e){showError(e)}
}
async function saveAppointment(button) {
  const row=button.closest("tr"),id=button.dataset.saveAppointment,payload={status:row.querySelector('[data-appt="status"]').value,scheduled_at:row.querySelector('[data-appt="time"]').value,note:row.querySelector('[data-appt="note"]').value};
  try {await request(`/appointments/${id}?${query(payload)}`,"PATCH");showMessage("appointmentMessage","Appointment updated and client record synced.");await Promise.all([loadAppointments(),loadWorkflows(),loadAudit()])}catch(e){showError(e,"appointmentMessage")}
}
document.addEventListener("DOMContentLoaded",()=>{
  q("closeHistory")?.addEventListener("click",()=>q("historyDialog").close());
  q("taskFilter")?.addEventListener("change",loadTasks);
  q("commMatter")?.addEventListener("change",loadCommunications);
  q("refreshAudit")?.addEventListener("click",loadAudit);
  q("auditEntity")?.addEventListener("change",loadAudit);
  q("taskForm")?.addEventListener("submit",async event=>{event.preventDefault();const body={matter_id:q("taskMatter").value,title:q("taskTitle").value,owner:q("taskOwner").value,due_date:q("taskDue").value||null,blocker:q("taskBlocker").value||"None"};try{await request("/tasks","POST",body);q("taskForm").reset();q("taskBlocker").value="None";showMessage("taskMessage","Task created.");await Promise.all([loadTasks(),loadAudit(),loadReport()])}catch(e){showError(e,"taskMessage")}});
  q("saveComm")?.addEventListener("click",async()=>{const body={matter_id:q("commMatter").value,channel:q("commChannel").value,direction:q("commDirection").value,summary:q("commSummary").value,visibility:q("commVisibility").value};try{await request("/communications","POST",body);q("commSummary").value="";showMessage("commMessage","Communication saved to staff record.");await Promise.all([loadCommunications(),loadAudit()])}catch(e){showError(e,"commMessage")}});
  q("exportMatters")?.addEventListener("click",async event=>{event.preventDefault();try{const res=await fetch(`${ADMIN_API}/export/matters.csv`,{headers:authHeaders()});if(!res.ok)throw new Error((await res.json().catch(()=>({}))).detail||`Export failed (${res.status})`);const blob=await res.blob(),url=URL.createObjectURL(blob),link=document.createElement("a");link.href=url;link.download="matters.csv";link.click();URL.revokeObjectURL(url)}catch(e){showError(e)}});
});
