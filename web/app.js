function esc(value) { return String(value ?? "").replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch])); }

function renderReportSummary(report, targetId="report") {
  const el = document.getElementById(targetId);
  if (!el || !report) return;
  el.innerHTML = reportCard([["Total",report.total||0],["High risk",(report.high_risk||[]).length],["Urgent",(report.urgent||[]).length],["Attorney review",(report.attorney_review_queue||[]).length]], report.by_stage);
}

function reportCard(figures, byStage) {
  const stages = Object.entries(byStage||{});
  return `<div class="card"><dl class="report-figures">${figures.map(([label,value])=>`<div><dt>${esc(label)}</dt><dd>${esc(value)}</dd></div>`).join("")}</dl>${stages.length?`<table class="report-stages"><caption>Matters by stage</caption><tbody>${stages.map(([stage,count])=>`<tr><td>${esc(stage)}</td><td>${esc(count)}</td></tr>`).join("")}</tbody></table>`:""}</div>`;
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
    if (res.status >= 500) throw new Error("The server had a problem.");
    throw new Error(typeof data.detail === "string" ? data.detail : `Request failed (${res.status}).`);
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
    const box=document.getElementById("userBox"),name=document.createElement("p"),role=document.createElement("p"),link=document.createElement("a");name.textContent=user.name;role.textContent=user.role;link.href="#";link.textContent="Sign out";link.onclick=()=>{logout();return false};box.replaceChildren(name,role,link);
    matters = await request("/matters");
    document.getElementById("backendError")?.remove();
  } catch (e) {
    // no numbers rather than zeros that look real
    matters = [];
    let error = document.getElementById("backendError");
    if (!error) { error = document.createElement("p"); error.id = "backendError"; error.className = "notice"; document.querySelector(".main-content").prepend(error); }
    const retry = document.createElement("button"); retry.type = "button"; retry.className = "btn secondary sm"; retry.textContent = "Try again"; retry.onclick = load;
    document.querySelector(".main-content").hidden=false; error.replaceChildren(`Matters did not load. ${e.message} `, retry);
    for (const id of ["total","highRisk","review","urgent","overdue"]) document.getElementById(id).textContent = "—";
    document.getElementById("rows").innerHTML = "";
    document.getElementById("emptyState").style.display = "none";
    return;
  }
  if(!staffVerified)return;
  populateFilters();
  render();
  await loadReport();
}
function formatDue(value) { if (!value) return "—"; const date = new Date(`${String(value).slice(0,10)}T00:00:00`); return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString(undefined, {dateStyle:"long"}); }
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
  document.getElementById("emptyState").style.display = data.length ? "none" : "block";
  data.forEach(m => {
    const tr = document.createElement("tr");
    const riskCls = "badge-" + (m.risk_level||"Low").toLowerCase();
    const prioCls = m.priority === "Urgent" ? "badge-urgent" : "badge-normal";
    tr.innerHTML = `<td><strong>${esc(m.id)}</strong></td><td>${esc(m.client_name)}</td><td>${esc(m.stage)}</td><td>${esc(m.owner)}</td><td>${esc(formatDue(m.due_date))}</td><td><span class="badge ${riskCls}">${esc(m.risk_level)}</span></td><td><span class="badge ${prioCls}">${esc(m.priority)}</span></td><td>${esc(m.next_action||"")}</td>`;
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
    document.getElementById("report").textContent = "The report did not load. " + e.message;
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
