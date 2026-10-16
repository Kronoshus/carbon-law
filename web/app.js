
function renderReportSummary(report, targetId="report") {
  const el = document.getElementById(targetId);
  if (!el || !report) return;
  const stages = Object.entries(report.by_stage||{}).map(([k,v])=>`<span>${k}: ${v}</span>`).join(" | ");
  el.innerHTML = `<div class="card"><strong>Total:</strong> ${report.total||0} &nbsp; <strong>High Risk:</strong> ${(report.high_risk||[]).length} &nbsp; <strong>Urgent:</strong> ${(report.urgent||[]).length} &nbsp; <strong>Review Queue:</strong> ${(report.attorney_review_queue||[]).length}</div><p>${stages}</p>`;
}

const API = localStorage.getItem("carbon_api") || "https://carbon-law.onrender.com";
async function request(path, method="GET", body=null) {
  const opts = { method, headers: {"Content-Type":"application/json"} };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(API + path, opts);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

let matters = [];
async function load() {
  try {
    await request("/seed", "POST").catch(()=>null);
    matters = await request("/matters");
  } catch (e) {
    matters = [];
  }
  populateFilters();
  render();
  loadReport();
}
function populateFilters() {
  const stages = [...new Set(matters.map(m=>m.stage))].sort();
  const owners = [...new Set(matters.map(m=>m.owner))].sort();
  const sf = document.getElementById("stageFilter");
  const of = document.getElementById("ownerFilter");
  if (sf) { sf.innerHTML = '<option value="">All stages</option>' + stages.map(s=>`<option>${s}</option>`).join(""); }
  if (of) { of.innerHTML = '<option value="">All owners</option>' + owners.map(o=>`<option>${o}</option>`).join(""); }
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
  rows.innerHTML = "";
  filtered().forEach(m => {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${m.id}</td><td>${m.client_name}</td><td>${m.stage}</td><td>${m.owner}</td><td>${m.due_date||""}</td><td>${m.risk_level}</td><td>${m.priority}</td><td>${m.next_action||""}</td>`;
    rows.appendChild(tr);
  });
  document.getElementById("total").textContent = matters.length;
  document.getElementById("highRisk").textContent = matters.filter(m=>m.risk_level==="High").length;
  document.getElementById("review").textContent = matters.filter(m=>String(m.stage).includes("Review")).length;
  document.getElementById("urgent").textContent = matters.filter(m=>m.priority==="Urgent").length;
}
async function loadReport() {
  try {
    const report = await request("/reports/friday");
    renderReportSummary(report);
  } catch (e) {
    document.getElementById("report").textContent = "Backend unavailable.";
  }
}
document.addEventListener("DOMContentLoaded", () => {
  load();
  ["search","stageFilter","riskFilter","ownerFilter"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener("input", render);
    if (el) el.addEventListener("change", render);
  });
  const seed = document.getElementById("seedBtn");
  if (seed) seed.addEventListener("click", async () => { await request("/seed","POST"); await load(); });
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
