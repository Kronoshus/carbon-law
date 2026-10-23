function esc(value) { return String(value ?? "").replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch])); }

const WORKFLOW_LABELS={conflict_review:"Conflict review",conflict_hold:"Conflict hold",document_selection:"Document selection",intake:"Client information",draft_ready:"Draft ready",client_review:"Client review",attorney_review:"Attorney review",consultation:"Consultation",signing:"Signing",complete:"Complete"};
function workflowLabel(value){return WORKFLOW_LABELS[value]||value||"—"}
function formatAppointmentTime(value) { if (!value) return ""; const timestamp=typeof value==="string"&&!/[zZ]|[+-]\d{2}:?\d{2}$/.test(value)?value+"Z":value; const date = new Date(timestamp); return Number.isNaN(date.getTime()) ? value : date.toLocaleString(undefined, {dateStyle:"long",timeStyle:"short"}); }
function localDateTime(value) { if (!value) return ""; const date=new Date(value); return Number.isNaN(date.getTime())?"":new Date(date.getTime()-date.getTimezoneOffset()*60000).toISOString().slice(0,16); }
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
  let res;
  try { res = await fetch(ADMIN_API + path, opts); }
  catch (_) { throw new Error("Could not reach the Carbon backend. Check your connection and try again."); }
  if (!res.ok) { const data=await res.json().catch(()=>({})); if(res.status===401)throw new Error("Your session expired. Sign in again.");if(res.status===403)throw new Error("Your account does not have permission to do this.");throw new Error(data.detail||`Request failed (${res.status}).`); }
  return res.json();
}

async function openWorkflowReview(workflow) {
  if (!workflow) return;
  const dialog=q("reviewDialog");
  q("reviewTitle").textContent=`Review drafts · ${workflow.client_name}`;
  q("reviewStatus").textContent=workflow.staff_review_note ? `Previous reviewer note: ${workflow.staff_review_note}` : "Illustrative working drafts; not signing-ready.";
  const drafts=workflow.drafts||workflow.attorney_demo_drafts||{};
  q("reviewDocuments").innerHTML=Object.entries(drafts).map(([name,d])=>`<article class="review-document"><h3>${esc(name)} · v${esc(d.version)}</h3><pre class="document-content">${esc(d.content)}</pre></article>`).join("");
  dialog.dataset.workflow=workflow.id;
  q("reviewNote").value="";
  q("approveDrafts").disabled=Object.values(drafts).some(d=>String(d.content||"").includes("[ATTORNEY TO COMPLETE"));
  q("reviewStatus").textContent += q("approveDrafts").disabled ? " Complete every [ATTORNEY TO COMPLETE…] placeholder before approval." : "";
  dialog.showModal();
}
async function submitWorkflowReview(decision) {
  const dialog=q("reviewDialog"), note=q("reviewNote").value.trim();
  if (decision === "attorney_changes" && !note) { q("reviewStatus").textContent="Enter a note describing the required changes."; q("reviewNote").focus(); return; }
  if (decision === "attorney_approved" && !confirm("Approve these drafts?")) return;
  if (decision === "attorney_changes" && !confirm("Send these drafts back to the paralegal with your notes?")) return;
  const buttons=[q("approveDrafts"),q("requestChanges")]; buttons.forEach(button=>button.disabled=true);
  try { await request(`/workflows/${dialog.dataset.workflow}/staff-review`,"PATCH",{decision,note}); dialog.close();showMessage("workflowMessage",decision==="attorney_approved"?"Drafts approved.":"Drafts returned with reviewer notes.");await Promise.all([loadWorkflows(),loadMatters(),loadDocuments()]); }
  catch(error) { showError(error,"workflowMessage"); }
  finally { buttons.forEach(button=>button.disabled=false); }
}
async function loadWorkflows() {
  const rows = document.getElementById("workflowRows"); if (!rows) return;
  try {
  const workflows = await request("/my-workflow");
  if (!Array.isArray(workflows)) throw new Error("Staff workflow data is unavailable for this account.");
  rows.innerHTML = workflows.map(w => {
    const assignedAttorney = adminMatters.find(m => m.id === w.matter_id)?.attorney_reviewer;
    const canReview = staffUser?.role === "admin" || (staffUser?.role === "attorney" && assignedAttorney === staffUser.id);
    const hasDraft = Object.keys(w.drafts||{}).length > 0 || Object.keys(w.attorney_demo_drafts||{}).length > 0;
    const review = w.stage === "attorney_review" && canReview && hasDraft ? `<button class="btn sm" data-review="${esc(w.id)}">Review drafts</button>` : "";
    const appointment = w.appointments||{};
    const intakeAction = w.stage === "conflict_review" ? `<button class="btn sm" data-workflow="${esc(w.id)}" data-decision="conflict_cleared">Clear</button> <button class="btn secondary sm" data-workflow="${esc(w.id)}" data-decision="conflict_flagged">Flag</button>` : w.stage === "consultation" && appointment.consultation?.status === "requested" ? `<input type="datetime-local" data-time="${esc(w.id)}-consultation" value="${esc(localDateTime(appointment.consultation.requested_at))}"><button class="btn sm" data-schedule="${esc(w.id)}" data-kind="consultation">Approve consultation</button>` : w.stage === "signing" && appointment.signing?.status === "requested" ? `<input type="datetime-local" data-time="${esc(w.id)}-signing" value="${esc(localDateTime(appointment.signing.requested_at))}"><button class="btn sm" data-schedule="${esc(w.id)}" data-kind="signing">Approve signing</button>` : w.stage === "consultation" && appointment.consultation?.status === "scheduled" ? `<button class="btn secondary sm" data-workflow="${esc(w.id)}" data-decision="consultation_completed">Mark consultation complete</button>` : w.stage === "draft_ready" && (staffUser?.role==="attorney"||staffUser?.role==="admin") ? `<button class="btn sm" data-generate-demo="${esc(w.id)}">Generate demo drafts</button>` : "—";
    const draftLabel = w.attorney_demo_drafts && Object.keys(w.attorney_demo_drafts).length ? "Illustrative demo drafts — not signing-ready" : "Drafts";
    return `<tr><td>${esc(w.client_name)}<br><small>${esc((w.related_names||[]).join(", "))}</small></td><td>${esc(workflowLabel(w.stage))}</td><td>${esc((w.documents_requested||[]).join(", ")||"Conflict review")} ${hasDraft?`<p>${esc(draftLabel)} · ${Object.keys(w.drafts||w.attorney_demo_drafts||{}).length} document(s)</p>`:""}${w.staff_review_note?`<p><strong>Reviewer notes:</strong> ${esc(w.staff_review_note)}</p>`:""}</td><td>${review} ${intakeAction}</td></tr>`;
  }).join("");
  rows.querySelectorAll("button[data-review]").forEach(button=>button.onclick=()=>openWorkflowReview(workflows.find(w=>w.id===button.dataset.review)));

  rows.querySelectorAll("button[data-schedule]").forEach(button => button.addEventListener("click", async () => { const input=rows.querySelector(`[data-time="${button.dataset.workflow}-${button.dataset.kind}"]`); if (!input?.value) {showError("Choose a date and time.","workflowMessage");return;} if(!confirm(`Approve this ${button.dataset.kind} appointment request?`))return; try {button.disabled=true;await request(`/workflows/${button.dataset.workflow}/appointment`,"PATCH",{kind:button.dataset.kind,scheduled_at:new Date(input.value).toISOString()});showMessage("workflowMessage","Appointment request approved.");await Promise.all([loadWorkflows(),loadAppointments()]);}catch(error){showError(error,"workflowMessage");button.disabled=false;} }));
  rows.querySelectorAll("button[data-generate-demo]").forEach(button => button.addEventListener("click", async () => {
    if (!confirm("Generate attorney-review demo drafts? These are not legally approved or signing-ready.")) return;
    try { button.disabled=true; await request(`/workflows/${button.dataset.generateDemo}/attorney-demo-drafts`, "POST"); showMessage("workflowMessage","Demo drafts generated for attorney review only."); await loadWorkflows(); }
    catch(error) { showError(error,"workflowMessage"); button.disabled=false; }
  }));
  rows.querySelectorAll("button[data-workflow]").forEach(button => button.addEventListener("click", async () => {
    const decision=button.dataset.decision;
    if (!confirm(`Confirm ${decision.replaceAll("_", " ")}?`)) return;
    try { button.disabled=true; await request(`/workflows/${button.dataset.workflow}/staff-review`, "PATCH", {decision}); showMessage("workflowMessage","Intake review updated."); await Promise.all([loadWorkflows(),loadMatters()]); }
    catch(error) { showError(error,"workflowMessage"); button.disabled=false; }
  }));
  } catch(error) { showError(error,"workflowMessage"); }
}

let staffUser=null;
async function load() {
  staffUser=await verifyStaff();
  if (!staffUser) return;
  q("adminMain").hidden=false;
  q("workflowRows").innerHTML='<tr><td colspan="4">Loading…</td></tr>';
  const box=q("userBox"), name=document.createElement("p"),role=document.createElement("p"),link=document.createElement("a");
  name.textContent=staffUser.name; role.textContent=staffUser.role; link.href="#";link.textContent="Logout";link.onclick=()=>{logout();return false};box.replaceChildren(name,role,link);
  try { [stageOptions,staffList]=await Promise.all([request("/stages"),request("/staff")]); } catch(error) { showError(error,"mattersMessage"); }
  setupStaffSelectors();
  await loadSection(loadMatters);
  const sections=[loadWorkflows,loadChangeRequests,loadAppointments,loadDocuments,loadReport,loadTasks,loadContacts,loadOperationsReports,loadAudit,()=>loadPracticeFiles("prompt"),()=>loadPracticeFiles("template")];
  await Promise.allSettled(sections.map(loadSection));
}
async function loadSection(loadFn) { try { await loadFn(); } catch(error) { showError(error,sectionErrorTarget(loadFn)); } }
function sectionErrorTarget(loadFn) { return ({loadMatters:"mattersMessage",loadWorkflows:"workflowMessage",loadChangeRequests:"changeRequestsMessage",loadAppointments:"appointmentMessage",loadDocuments:"documentsMessage",loadReport:"reportMessage",loadTasks:"taskMessage",loadContacts:"contactMessage",loadOperationsReports:"capacityMessage",loadAudit:"auditMessage"})[loadFn.name]||"adminStatus"; }
async function verifyStaff() {
  try { return await CarbonAuth.requireServerAuth(["paralegal","attorney","admin"]); }
  catch(error) { showError(error,"adminStatus"); return null; }
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
        tr.innerHTML = `<td><button class="btn secondary sm" data-history="${esc(m.id)}">${esc(m.id)}</button></td><td>${esc(m.client_name)}</td><td>${esc(m.stage)}</td><td>${esc(m.owner)}</td><td><select class="attorneySelect" data-id="${esc(m.id)}"><option value="">Unassigned</option>${staffList.filter(s=>s.role==="attorney").map(s=>`<option value="${esc(s.id)}" ${m.attorney_reviewer===s.id?"selected":""}>${esc(s.name)}</option>`).join("")}</select></td><td>${esc(m.risk_level)}</td><td>${esc(m.priority)}</td><td>${esc(m.due_date?new Date(`${m.due_date}T00:00:00`).toLocaleDateString():"")}</td>
        <td><select data-id="${esc(m.id)}" class="stageSelect">
        ${[...new Set([m.stage,...stageOptions])].map(s=>`<option value="${esc(s)}" ${s===m.stage?"selected":""} ${stageOptions.includes(s)?"":"disabled"}>${esc(s)}</option>`).join("")}
        </select></td>`;
        rows.appendChild(tr);
      });
      rows.querySelectorAll("[data-history]").forEach(button=>button.onclick=()=>loadMatterHistory(button.dataset.history));
      rows.querySelectorAll(".attorneySelect").forEach(select=>select.addEventListener("change",async()=>{const id=select.dataset.id,attorney_reviewer=select.value||null;if(!confirm("Change the assigned attorney for this matter?")){await loadMatters();return;}try{select.disabled=true;await request(`/matters/${encodeURIComponent(id)}`,"PATCH",{attorney_reviewer});showMessage("mattersMessage","Attorney assignment updated.");await loadMatters();}catch(error){showError(error,"mattersMessage");await loadMatters();}}));
      document.querySelectorAll(".stageSelect").forEach(sel => {
        sel.addEventListener("change", async (e) => {
          const id = e.target.getAttribute("data-id"), stage=e.target.value;
          if(!confirm(`Change ${id} to ${stage}?`)){await loadMatters();return;}
          try { await request(`/matters/${id}`, "PATCH", {stage}); showMessage("mattersMessage","Matter stage updated."); await Promise.all([loadMatters(),loadWorkflows(),loadAudit()]); }
          catch(error) { showError(error,"mattersMessage"); await loadMatters(); }
        });
      });
    }
  } catch (e) { showError(e,"mattersMessage"); }
}
async function loadChangeRequests() {
  try {
    const items = await request("/change-requests");
    const rows = document.getElementById("crRows");
    if (rows) {
      rows.innerHTML = "";
      items.forEach(c => {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td>${esc(c.id.slice(0,8))}</td><td>${esc(c.matter_id)}</td><td>${esc(c.change_type)}</td><td>${esc(c.requested_by)}</td><td><select data-cr-status="${esc(c.id)}">${["Open","In Review","Resolved","Rejected"].map(status=>`<option ${c.status===status?"selected":""}>${status}</option>`).join("")}</select></td><td>${esc(c.impact||"")}<br><input data-cr-resolution="${esc(c.id)}" placeholder="Resolution / client-facing update" value="${esc(c.resolution||"")}"><button class="btn secondary sm" data-save-cr="${esc(c.id)}">Save</button></td>`;
        rows.appendChild(tr);
      });
      rows.querySelectorAll("[data-save-cr]").forEach(button=>button.onclick=async()=>{const id=button.dataset.saveCr;button.disabled=true;try{await request(`/change-requests/${id}`,"PATCH",{status:rows.querySelector(`[data-cr-status="${CSS.escape(id)}"]`).value,resolution:rows.querySelector(`[data-cr-resolution="${CSS.escape(id)}"]`).value});showMessage("changeRequestsMessage","Change request saved.");await Promise.all([loadChangeRequests(),loadTasks(),loadAudit()])}catch(e){showError(e,"changeRequestsMessage")}finally{button.disabled=false}});
    }
  } catch(e){showError(e,"changeRequestsMessage")}
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
        tr.innerHTML = `<td>${esc(a.id.slice(0,8))}</td><td>${esc(a.matter_id)}</td><td>${esc(a.kind)}</td><td><input data-appt="time" type="datetime-local" value="${esc(local)}" data-original="${esc(local)}"></td><td><select data-appt="status">${[...new Set(["Requested","Scheduled","Cancelled","Completed","Booked","Rescheduled",a.status])].map(status=>`<option value="${esc(status)}" ${a.status===status?"selected":""}>${esc(({Booked:"Booked (legacy)",Rescheduled:"Rescheduled (legacy)"})[status]||status)}</option>`).join("")}</select></td><td><input data-appt="note" value="${esc(a.note||"")}"><button class="btn secondary sm" data-save-appointment="${esc(a.id)}">Save</button></td>`;
        rows.appendChild(tr);
      });
      rows.querySelectorAll("[data-save-appointment]").forEach(button=>button.onclick=()=>saveAppointment(button));
    }
  } catch(e){showError(e,"appointmentMessage")}
}
async function loadDocuments() {
  try {
    const items = await request("/documents");
    const rows = document.getElementById("docRows");
    if (rows) {
      rows.innerHTML = "";
      const latestItems=items.filter(d=>!items.some(other=>other.matter_id===d.matter_id&&other.name===d.name&&other.version>d.version));
      latestItems.forEach(d => {
        const tr = document.createElement("tr");
        const content = typeof d.content === "string" ? d.content : "";
        const preview = content ? `<details><summary>Open document</summary><pre class="document-content">${esc(content)}</pre></details>` : `<span class="muted">No draft content is stored for this record.</span>`;
        const state = d.status==="Superseded" ? `Replaced by v${esc(d.replaced_by_version||"?")}` : d.status;
        const history = items.filter(old=>old.matter_id===d.matter_id&&old.name===d.name&&old.version<d.version).map(old=>`<details><summary>Version history</summary><p>v${esc(old.version)} · ${esc(old.status)} · replaced by v${esc(old.replaced_by_version||d.version)}</p><details><summary>Open v${esc(old.version)}</summary><pre class="document-content">${esc(old.content||"")}</pre></details></details>`).join("");
        tr.innerHTML = `<td>${esc(d.matter_id)}</td><td>${esc(d.name)}<br>${d.status==="Superseded"?`<span class="muted">History version</span>`:preview}${history}</td><td>v${esc(d.version)}${d.status==="Superseded"?` · replaced by v${esc(d.replaced_by_version||"?")}`:" · latest"}</td><td>${esc(state)}${d.status==="Superseded"?"":`<select data-doc-status="${esc(d.id)}">${["Draft","Attorney Review","Client Review","Signed","Archived"].map(status=>`<option ${d.status===status?"selected":""}>${status}</option>`).join("")}</select> <button class="btn secondary sm" data-save-document="${esc(d.id)}">Save</button>`}</td>`;
        rows.appendChild(tr);
      });
      rows.querySelectorAll("[data-save-document]").forEach(button=>button.onclick=async()=>{const id=button.dataset.saveDocument;button.disabled=true;try{await request(`/documents/${id}`,"PATCH",{status:rows.querySelector(`[data-doc-status="${CSS.escape(id)}"]`).value});await loadDocuments();await loadAudit();showMessage("documentsMessage","Document status updated.")}catch(e){showError(e,"documentsMessage")}finally{button.disabled=false}});
    }
  } catch(e){showError(e,"documentsMessage")}
}
async function loadReport() {
  const report = await request("/reports/friday");
  renderReportSummary(report);
}

document.addEventListener("DOMContentLoaded", () => {
  load();
  const form = document.getElementById("matterForm");
  if (form) form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const body = {
      client_name: document.getElementById("newClient").value,
      stage: "1 Intake",
      owner: document.getElementById("newOwner").value || "Unassigned",
      attorney_reviewer: document.getElementById("newAttorney").value || null,
      risk_level: document.getElementById("newRisk").value,
      priority: document.getElementById("newPriority").value,
      due_date: document.getElementById("newDue").value || null,
      next_action: "Complete intake"
    };
    const submit=e.submitter, originalLabel=submit.textContent; submit.disabled=true;submit.textContent="Creating…";
    try {
      body.owner = body.owner || "Unassigned";
      const result = await request("/matters","POST",body);
      form.reset(); closeModal("matterModal"); showMessage("mattersMessage",`Matter created: ${result.id}`);
      await Promise.all([loadMatters(),loadWorkflows(),loadTasks(),loadReport(),loadAudit()]);
    } catch(error) { showError(error,"adminOut"); }
    finally { submit.disabled=false;submit.textContent=originalLabel; }
  });
});

document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("genReport");
  if (btn) btn.addEventListener("click", async () => {
    btn.disabled=true;
    try {
      const report = await request("/reports/friday");
      renderReportSummary(report); showMessage("reportMessage","Report refreshed.");
    } catch (e) { showError(e,"reportMessage"); }
    finally { btn.disabled=false; }
  });
});


let adminMatters = [], stageOptions=[], staffList=[];
const q = id => document.getElementById(id);
const query = values => new URLSearchParams(values).toString();
function showMessage(id, text) { const node=q(id); if(node) node.textContent=text; }
function showError(error, target="adminStatus") { const node=q(target);if(node){node.textContent=error?.message||String(error);node.classList.add("error-message");} }
function setupStaffSelectors() {
  q("newOwner").innerHTML=`<option value="">Unassigned</option>`+staffList.filter(s=>["paralegal","attorney","admin"].includes(s.role)).map(s=>`<option value="${esc(s.name)}">${esc(s.name)} · ${esc(s.role)}</option>`).join("");
  q("newAttorney").innerHTML=`<option value="">Unassigned</option>`+staffList.filter(s=>s.role==="attorney").map(s=>`<option value="${esc(s.id)}">${esc(s.name)}</option>`).join("");
}
function setupMatterSelectors() {
  const data=q("matterOptions"); if(data) data.innerHTML=adminMatters.map(m=>`<option value="${esc(m.id)}">${esc(m.client_name)}</option>`).join("");
  for(const id of ["commMatter","taskFilter","taskMatter"]) { const select=q(id); if(!select) continue; const previous=select.value; select.innerHTML=`<option value="">${id==="taskFilter"?"All matters":"Select a matter"}</option>`+adminMatters.map(m=>`<option value="${esc(m.id)}">${esc(m.id)} — ${esc(m.client_name)}</option>`).join(""); if(previous) select.value=previous; }
  const ownerSelect=q("taskOwner"), owner=ownerSelect?.value;
  if(ownerSelect){ownerSelect.innerHTML='<option value="">Select owner</option>'+staffList.filter(s=>["paralegal","attorney","admin"].includes(s.role)).map(s=>`<option value="${esc(s.name)}">${esc(s.name)} · ${esc(s.role)}</option>`).join("");if(staffList.some(s=>s.name===owner))ownerSelect.value=owner;}
}
async function loadTasks() {
  try {
    const id=q("taskFilter")?.value; const items=await request("/tasks"+(id?`?matter_id=${encodeURIComponent(id)}`:""));
    q("taskRows").innerHTML=items.map(t=>`<tr><td>${esc(t.matter_id)}</td><td>${esc(t.title)}</td><td><input data-field="owner" value="${esc(t.owner)}" aria-label="Task owner"></td><td><input data-field="due_date" type="date" value="${esc(t.due_date||"")}" aria-label="Task due date"></td><td><select data-field="status"><option ${t.status==="Open"?"selected":""}>Open</option><option ${t.status==="In Progress"?"selected":""}>In Progress</option><option ${t.status==="Done"?"selected":""}>Done</option><option ${t.status==="Blocked"?"selected":""}>Blocked</option></select></td><td><input data-field="blocker" value="${esc(t.blocker||"None")}" aria-label="Blocker"></td><td><button class="btn secondary sm" data-save-task="${esc(t.id)}">Save</button></td></tr>`).join("");
    q("taskRows").querySelectorAll("[data-save-task]").forEach(button=>button.onclick=async()=>{const row=button.closest("tr"),payload={};row.querySelectorAll("[data-field]").forEach(el=>payload[el.dataset.field]=el.value);button.disabled=true;try{await request(`/tasks/${button.dataset.saveTask}`,"PATCH",payload);showMessage("taskMessage","Task updated.");await loadTasks();await loadAudit()}catch(e){showError(e,"taskMessage")}finally{button.disabled=false}});
  } catch(e){showError(e,"taskMessage")}
}
async function loadContacts() {
  try { const items=await request("/contacts"); q("contactRows").innerHTML=items.map(c=>`<tr><td>${esc(formatAppointmentTime(c.created_at))}</td><td>${esc(c.name)}</td><td>${esc(c.email)}</td><td>${esc(c.phone)}</td><td>${esc(c.service||"")}<br>${esc(c.message||"")}</td><td><select data-contact-status="${esc(c.id)}">${["New","Contacted","Consultation Scheduled","Converted","Closed"].map(s=>`<option ${c.status===s?"selected":""}>${s}</option>`).join("")}</select></td><td><input data-contact-note="${esc(c.id)}" value="${esc(c.note||"")}" maxlength="500"></td><td><button class="btn secondary sm" data-save-contact="${esc(c.id)}">Save</button></td></tr>`).join("");
    q("contactRows").querySelectorAll("[data-save-contact]").forEach(button=>button.onclick=async()=>{const id=button.dataset.saveContact;button.disabled=true;try{await request(`/contacts/${id}`,"PATCH",{status:q("contactRows").querySelector(`[data-contact-status="${CSS.escape(id)}"]`).value,note:q("contactRows").querySelector(`[data-contact-note="${CSS.escape(id)}"]`).value});showMessage("contactMessage","Contact updated.");await loadContacts();await loadAudit()}catch(e){showError(e,"contactMessage")}finally{button.disabled=false}});
  } catch(e){showError(e,"contactMessage")}
}
async function loadCommunications() {
  const matterId=q("commMatter")?.value; if(!matterId){q("commRows").textContent="Select a matter to view its communication log.";return;}
  try { const items=await request(`/communications?matter_id=${encodeURIComponent(matterId)}`); q("commRows").innerHTML=items.length?items.map(c=>`<p><strong>${esc(c.direction)} · ${esc(c.channel)} · ${esc(formatAppointmentTime(c.created_at))}</strong> (${esc(c.visibility||"internal")})<br>${esc(c.summary)}</p>`).join(""):"No communication entries for this matter."; }
  catch(e){showError(e,"commMessage")}
}
async function loadOperationsReports() {
  const [capacityResult,bottleneckResult]=await Promise.allSettled([request("/reports/capacity"),request("/reports/bottlenecks")]);
  if(capacityResult.status==="fulfilled") { const capacity=capacityResult.value; q("capacityReport").innerHTML=`<p>Counts by matter owner, not hours or availability.</p><table><thead><tr><th>Owner</th><th>Matters</th><th>High risk</th><th>Urgent</th><th>Overdue</th></tr></thead><tbody>${Object.entries(capacity.by_owner||{}).map(([owner,v])=>`<tr><td>${esc(owner)}</td><td>${v.matters}</td><td>${v.high_risk}</td><td>${v.urgent}</td><td>${v.overdue}</td></tr>`).join("")}</tbody></table>`; } else showError(capacityResult.reason,"capacityMessage");
  if(bottleneckResult.status==="fulfilled") { const bottlenecks=bottleneckResult.value; q("bottleneckReport").innerHTML=`<p>Waiting on client: <strong>${bottlenecks.waiting_on_client}</strong> · Blocked matters: <strong>${bottlenecks.blocked_matters}</strong> · Open change requests: <strong>${bottlenecks.open_change_requests}</strong></p><ul>${(bottlenecks.top_stages||[]).map(([stage,count])=>`<li>${esc(stage)}: ${count}</li>`).join("")}</ul>`; } else showError(bottleneckResult.reason,"bottleneckMessage");
}
async function loadAudit() {
  try { const entity=q("auditEntity")?.value.trim(); const items=await request(`/audit?limit=100${entity?`&entity=${encodeURIComponent(entity)}`:""}`); q("auditRows").innerHTML=items.slice().reverse().map(a=>`<tr><td>${esc(formatAppointmentTime(a.time))}</td><td>${esc(a.actor)}</td><td>${esc(a.action)}</td><td>${esc(a.entity)} ${esc(a.entity_id)}</td><td>${esc(a.detail)}</td></tr>`).join(""); }
  catch(e){showError(e,"auditMessage")}
}
async function loadPracticeFiles(kind) {
  const select=q(kind+"Select"), content=q(kind+"Content");
  try { const files=await request(`/${kind}s`); select.innerHTML='<option value="">Select a '+kind+'</option>'+files.map(f=>`<option value="${esc(f.name)}">${esc(f.name)}</option>`).join(""); select.onchange=async()=>{if(!select.value){content.textContent="";return}try{const data=await request(`/${kind}s/${encodeURIComponent(select.value)}`);content.textContent=data.content;showMessage(kind+"Message","")}catch(e){showError(e,kind+"Message")}}; }
  catch(e){showError(e,kind==="prompt"?"promptMessage":"templateMessage")}
}
async function loadMatterHistory(matterId) {
  try {const h=await request(`/matters/${encodeURIComponent(matterId)}/history`);const entries=[...(h.stages||[]).map(x=>({...x,type:"Stage",detail:x.stage})),...(h.tasks||[]).map(x=>({...x,time:x.updated_at||x.created_at,type:"Task",detail:x.title})),...(h.changes||[]).map(x=>({...x,time:x.updated_at||x.created_at,type:"Change request",detail:x.change_type+" — "+x.status})),...(h.comms||[]).map(x=>({...x,time:x.created_at,type:"Communication",detail:x.summary}))].sort((a,b)=>String(a.time||"").localeCompare(String(b.time||"")));q("historyTitle").textContent=`${matterId} history`;q("historyContent").innerHTML=entries.map(x=>`<p><strong>${esc(formatAppointmentTime(x.time))} · ${esc(x.type)}</strong> — ${esc(x.detail||"")}</p>`).join("")||"No history recorded.";q("historyDialog").showModal()}catch(e){showError(e)}
}
async function saveAppointment(button) {
  button.disabled=true;
  const row=button.closest("tr"),id=button.dataset.saveAppointment,time=row.querySelector('[data-appt="time"]'),payload={status:row.querySelector('[data-appt="status"]').value,note:row.querySelector('[data-appt="note"]').value};
  if(time.value!==time.dataset.original) payload.scheduled_at=time.value?new Date(time.value).toISOString():"";
  try {await request(`/appointments/${id}`,"PATCH",payload);showMessage("appointmentMessage","Appointment updated and client record synced.");await Promise.all([loadAppointments(),loadWorkflows(),loadAudit()])}catch(e){showError(e,"appointmentMessage")}finally{button.disabled=false}
}
document.addEventListener("DOMContentLoaded",()=>{
  q("matterModal")?.addEventListener("close",()=>{q("matterForm").reset();q("adminOut").textContent="";});
  q("matterModal")?.addEventListener("click",event=>{if(event.target===q("matterModal"))closeModal("matterModal")});
  q("closeHistory")?.addEventListener("click",()=>q("historyDialog").close());
  q("closeReview")?.addEventListener("click",()=>q("reviewDialog").close());
  q("approveDrafts")?.addEventListener("click",()=>submitWorkflowReview("attorney_approved"));
  q("requestChanges")?.addEventListener("click",()=>submitWorkflowReview("attorney_changes"));
  q("taskFilter")?.addEventListener("change",loadTasks);
  q("commMatter")?.addEventListener("change",loadCommunications);
  q("refreshAudit")?.addEventListener("click",loadAudit);
  q("auditEntity")?.addEventListener("change",loadAudit);
  q("taskForm")?.addEventListener("submit",async event=>{event.preventDefault();const body={matter_id:q("taskMatter").value,title:q("taskTitle").value,owner:q("taskOwner").value,due_date:q("taskDue").value||null,blocker:q("taskBlocker").value||"None"},button=event.submitter;const label=button.textContent;button.disabled=true;button.textContent="Saving…";try{await request("/tasks","POST",body);q("taskForm").reset();q("taskBlocker").value="None";showMessage("taskMessage","Task created.");await Promise.all([loadTasks(),loadAudit(),loadReport()])}catch(e){showError(e,"taskMessage")}finally{button.disabled=false;button.textContent=label}});
  q("saveComm")?.addEventListener("click",async()=>{const body={matter_id:q("commMatter").value,channel:q("commChannel").value,direction:q("commDirection").value,summary:q("commSummary").value.trim(),visibility:q("commVisibility").value},button=q("saveComm");if(!body.matter_id){showError("Select a matter first.","commMessage");return;}if(!body.summary){showError("Enter a communication summary.","commMessage");return;}button.disabled=true;try{await request("/communications","POST",body);q("commSummary").value="";showMessage("commMessage","Communication saved to staff record.");await Promise.all([loadCommunications(),loadAudit()])}catch(e){showError(e,"commMessage")}finally{button.disabled=false}});
  q("exportMatters")?.addEventListener("click",async event=>{event.preventDefault();const button=event.currentTarget;button.disabled=true;try{const res=await fetch(`${ADMIN_API}/export/matters.csv`,{headers:authHeaders()});if(!res.ok)throw new Error((await res.json().catch(()=>({}))).detail||`Export failed (${res.status})`);const blob=await res.blob(),url=URL.createObjectURL(blob),link=document.createElement("a");link.href=url;link.download="matters.csv";link.click();URL.revokeObjectURL(url);showMessage("adminStatus","CSV export downloaded.")}catch(e){showError(e)}finally{button.disabled=false}});
});
