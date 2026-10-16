const API = window.location.origin.includes("localhost") ? "http://localhost:8000" : (localStorage.getItem("carbon_api") || "http://localhost:8000");
const el = (id) => document.getElementById(id);

async function request(path, method="GET", body=null) {
  const opts = { method, headers: {"Content-Type":"application/json"} };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(API + path, opts);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

let matters = [];
async function loadMatters() {
  try {
    matters = await request("/matters");
  } catch (e) {
    matters = [{id:"CL-0001", client_name:"Sample Client", stage:"6 Client Review", owner:"Paralegal A", appointment_status:"Booked", risk_level:"Low"}];
  }
  renderMatters();
  loadReport();
}

function renderMatters() {
  const body = el("matterRows");
  if (!body) return;
  body.innerHTML = "";
  matters.forEach(m => {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${m.id}</td><td>${m.client_name}</td><td>${m.stage}</td><td>${m.owner}</td><td>${m.risk_level}</td><td>${m.next_action || ""}</td>`;
    body.appendChild(tr);
  });
  if (el("matterCount")) el("matterCount").textContent = matters.length;
}

async function loadReport() {
  try {
    const report = await request("/reports/friday");
    if (el("report")) el("report").textContent = JSON.stringify(report, null, 2);
  } catch (e) {
    if (el("report")) el("report").textContent = "Backend unavailable. Showing sample mode.";
  }
}

async function submitChangeRequest(event) {
  event.preventDefault();
  const body = {
    matter_id: el("matter").value,
    requested_by: "client",
    change_type: el("changeType").value,
    affected_documents: el("docs").value,
    status: "Open"
  };
  try {
    const result = await request("/change-requests", "POST", body);
    el("out").textContent = "Change request submitted: " + result.id;
  } catch (e) {
    el("out").textContent = "Change request recorded locally: " + JSON.stringify(body, null, 2);
  }
}

async function requestAppointment(action) {
  const matterId = el("matter").value || (matters.length ? matters[0].id : "");
  const body = {
    matter_id: matterId,
    kind: "Signing",
    scheduled_at: new Date(Date.now() + 86400000).toISOString(),
    status: action === "cancel" ? "Cancelled" : "Rescheduled",
    note: action === "cancel" ? "Client requested cancellation" : "Client requested reschedule"
  };
  try {
    const result = await request("/appointments", "POST", body);
    el("out").textContent = action + " request submitted: " + result.id;
  } catch (e) {
    el("out").textContent = action + " request recorded locally.";
  }
}

document.addEventListener("DOMContentLoaded", () => {
  loadMatters();
  const form = el("changeForm");
  if (form) form.addEventListener("submit", submitChangeRequest);
  const cancel = el("cancel");
  if (cancel) cancel.addEventListener("click", () => requestAppointment("cancel"));
  const resched = el("reschedule");
  if (resched) resched.addEventListener("click", () => requestAppointment("reschedule"));
});
