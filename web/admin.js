function esc(value) { return String(value ?? "").replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch])); }

const STAGES = ["1 Intake","2 Attorney Scope","3 Client Data Collection","4 Drafting","5 Review Queue","6 Client Review","7 Signing Preparation","8 Execution","9 Funding Follow-Up","10 Closed"];
function renderReportSummary(report, targetId="report") {
  const el = document.getElementById(targetId);
  if (!el || !report) return;
  const stages = Object.entries(report.by_stage||{}).map(([k,v])=>`<span>${esc(k)}: ${v}</span>`).join(" | ");
  el.innerHTML = `<div class="card"><strong>Total:</strong> ${report.total||0} &nbsp; <strong>High Risk:</strong> ${(report.high_risk||[]).length} &nbsp; <strong>Urgent:</strong> ${(report.urgent||[]).length} &nbsp; <strong>Review Queue:</strong> ${(report.attorney_review_queue||[]).length}</div><p>${stages}</p>`;
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

async function load() {
  const token = getToken();
  if (!token) { window.location.href = "login.html"; return; }
  await loadMatters();
  await loadChangeRequests();
  await loadAppointments();
  await loadDocuments();
  await loadReport();
}
async function loadMatters() {
  try {
    const matters = await request("/matters");
    const rows = document.getElementById("adminMatterRows");
    if (rows) {
      rows.innerHTML = "";
      matters.forEach(m => {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td>${esc(m.id)}</td><td>${esc(m.client_name)}</td><td>${esc(m.stage)}</td><td>${esc(m.owner)}</td><td>${esc(m.risk_level)}</td><td>${esc(m.priority)}</td><td>${esc(m.due_date||"")}</td>
        <td><select data-id="${esc(m.id)}" class="stageSelect">
        ${STAGES.map(s=>`<option ${s===m.stage?"selected":""}>${esc(s)}</option>`).join("")}
        </select></td>`;
        rows.appendChild(tr);
      });
      document.querySelectorAll(".stageSelect").forEach(sel => {
        sel.addEventListener("change", async (e) => {
          const id = e.target.getAttribute("data-id");
          await request(`/matters/${id}`, "PATCH", {stage: e.target.value});
          await loadMatters();
        });
      });
    }
  } catch (e) { document.getElementById("adminOut").textContent = "Backend unavailable."; }
}
async function loadChangeRequests() {
  try {
    const items = await request("/change-requests");
    const rows = document.getElementById("crRows");
    if (rows) {
      rows.innerHTML = "";
      items.forEach(c => {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td>${c.id.slice(0,8)}</td><td>${esc(c.matter_id)}</td><td>${esc(c.change_type)}</td><td>${esc(c.requested_by)}</td><td>${esc(c.status)}</td><td>${esc(c.impact||"")}</td>`;
        rows.appendChild(tr);
      });
    }
  } catch(e){}
}
async function loadAppointments() {
  try {
    const items = await request("/appointments");
    const rows = document.getElementById("apptRows");
    if (rows) {
      rows.innerHTML = "";
      items.forEach(a => {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td>${a.id.slice(0,8)}</td><td>${esc(a.matter_id)}</td><td>${esc(a.kind)}</td><td>${esc(a.scheduled_at)}</td><td>${esc(a.status)}</td><td>${esc(a.note||"")}</td>`;
        rows.appendChild(tr);
      });
    }
  } catch(e){}
}
async function loadDocuments() {
  try {
    const items = await request("/documents");
    const rows = document.getElementById("docRows");
    if (rows) {
      rows.innerHTML = "";
      items.forEach(d => {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td>${esc(d.matter_id)}</td><td>${esc(d.name)}</td><td>${d.version}</td><td>${esc(d.status)}</td>`;
        rows.appendChild(tr);
      });
    }
  } catch(e){}
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
