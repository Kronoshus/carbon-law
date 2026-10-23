function esc(value) { return String(value ?? "").replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch])); }

function renderReportSummary(report, targetId="report") {
  const el = document.getElementById(targetId);
  if (!el || !report) return;
  const stages = Object.entries(report.by_stage||{}).map(([k,v])=>`<span>${esc(k)}: ${v}</span>`).join(" | ");
  el.innerHTML = `<div class="card"><strong>Total:</strong> ${report.total||0} &nbsp; <strong>High Risk:</strong> ${(report.high_risk||[]).length} &nbsp; <strong>Urgent:</strong> ${(report.urgent||[]).length} &nbsp; <strong>Review Queue:</strong> ${(report.attorney_review_queue||[]).length}</div><p>${stages}</p>`;
}

const DASHBOARD_API = "https://carbon-law.onrender.com";
async function request(path, method="GET", body=null) {
  const opts = { method, headers: {"Content-Type":"application/json", ...(getToken() ? {Authorization:"Bearer "+getToken()} : {})} };
  if (body) opts.body = JSON.stringify(body);
  let res;
  try { res = await fetch(DASHBOARD_API + path, opts); }
  catch (_) { throw new Error("Could not reach the Carbon backend. Check your connection and try again."); }
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    if (res.status === 401) throw new Error("Your session has expired. Sign in again to continue.");
    if (res.status === 403) throw new Error("Your account does not have staff access to this report.");
    throw new Error(data.detail || `Backend request failed (${res.status}).`);
  }
  return res.json();
}

let matters = [], staffVerified=false;
async function load() {
  try {
    const user=await CarbonAuth.requireServerAuth(["paralegal","attorney","admin"]);
    if(!user)return;
    staffVerified=true;
    document.querySelector(".main-content").hidden=false;
    const box=document.getElementById("userBox"),name=document.createElement("p"),role=document.createElement("p"),link=document.createElement("a");name.textContent=user.name;role.textContent=user.role;link.href="#";link.textContent="Logout";link.onclick=()=>{logout();return false};box.replaceChildren(name,role,link);
    matters = await request("/matters");
    document.getElementById("backendError")?.remove();
  } catch (e) {
    matters = [];
    let error = document.getElementById("backendError");
    if (!error) { error = document.createElement("p"); error.id = "backendError"; error.className = "intake-error"; document.querySelector(".main-content").prepend(error); }
    document.querySelector(".main-content").hidden=false; error.textContent = e.message;
  }
  if(!staffVerified)return;
  populateFilters();
  render();
  await loadReport();
}
function populateFilters() {
  const stages = [...new Set(matters.map(m=>m.stage))].sort();
  const owners = [...new Set(matters.map(m=>m.owner))].sort();
  const sf = document.getElementById("stageFilter");
  const of = document.getElementById("ownerFilter");
  if (sf) { sf.innerHTML = '<option value="">All stages</option>' + stages.map(s=>`<option>${esc(s)}</option>`).join(""); }
  if (of) { of.innerHTML = '<option value="">All owners</option>' + owners.map(o=>`<option>${esc(o)}</option>`).join(""); }
}
function filtered() {
  const q = (document.getElementById("search")?.value || "").toLowerCase();
  const stage = document.getElementById("stageFilter")?.value || "";
  const risk = document.getElementById("riskFilter")?.value || "";
  const owner = document.getElementById("ownerFilter")?.value || "";
  return matters.filter(m =>
    (!q || (m.id+" "+m.client_name).toLowerCase().includes(q)) &&
    (!stage || m.stage === stage) &&
    (!risk || m.risk_level === risk) &&
    (!owner || m.owner === owner)
  );
}
function render() {
  const rows = document.getElementById("rows");
  if (!rows) return;
  const data = filtered();
  rows.innerHTML = "";
  if (data.length === 0) { document.getElementById("emptyState").style.display = "block"; return; }
  document.getElementById("emptyState").style.display = "none";
  data.forEach(m => {
    const tr = document.createElement("tr");
    const riskCls = "badge-" + (m.risk_level||"Low").toLowerCase();
    const prioCls = m.priority === "Urgent" ? "badge-urgent" : "badge-normal";
    tr.innerHTML = `<td><strong>${esc(m.id)}</strong></td><td>${esc(m.client_name)}</td><td>${esc(m.stage)}</td><td>${esc(m.owner)}</td><td>${esc(m.due_date||"—")}</td><td><span class="badge ${riskCls}">${esc(m.risk_level)}</span></td><td><span class="badge ${prioCls}">${esc(m.priority)}</span></td><td>${esc(m.next_action||"")}</td>`;
    rows.appendChild(tr);
  });
  document.getElementById("total").textContent = matters.length;
  document.getElementById("highRisk").textContent = matters.filter(m=>m.risk_level==="High").length;
  document.getElementById("review").textContent = matters.filter(m=>String(m.stage).includes("Review")).length;
  document.getElementById("urgent").textContent = matters.filter(m=>m.priority==="Urgent").length;
  const today = new Date().toISOString().slice(0,10);
  document.getElementById("overdue").textContent = matters.filter(m=>m.due_date && m.due_date < today && m.stage !== "10 Closed").length;
}
async function loadReport() {
  try {
    const report = await request("/reports/friday");
    renderReportSummary(report);
  } catch (e) {
    document.getElementById("report").textContent = e.message;
  }
}
document.addEventListener("DOMContentLoaded", () => {
  load();
  ["search","stageFilter","riskFilter","ownerFilter"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener("input", render);
    if (el) el.addEventListener("change", render);
  });
  document.getElementById("refreshBtn")?.addEventListener("click", load);
});

document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("genReport");
  if (btn) btn.addEventListener("click", async () => {
    btn.disabled = true;
    try {
      const report = await request("/reports/friday");
      renderReportSummary(report);
    } catch (e) {
      document.getElementById("report").textContent = e.message;
    } finally { btn.disabled = false; }
  });
});
