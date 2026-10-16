const API = localStorage.getItem("carbon_api") || "https://carbon-law.onrender.com";
async function request(path, method="GET", body=null) {
  const opts = { method, headers: {"Content-Type":"application/json"} };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(API + path, opts);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

async function load() {
  try { await request("/seed","POST").catch(()=>null); } catch(e){}
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
        tr.innerHTML = `<td>${m.id}</td><td>${m.client_name}</td><td>${m.stage}</td><td>${m.owner}</td><td>${m.risk_level}</td><td>${m.priority}</td><td>${m.due_date||""}</td>
        <td><select data-id="${m.id}" class="stageSelect">
        ${["1 Intake","2 Attorney Scope","3 Client Follow-up","4 Drafting","5 Internal Review","6 Client Review","7 Revisions","8 Final Review","9 Funding","10 Signing","11 Complete"].map(s=>`<option ${s===m.stage?"selected":""}>${s}</option>`).join("")}
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
        tr.innerHTML = `<td>${c.id.slice(0,8)}</td><td>${c.matter_id}</td><td>${c.change_type}</td><td>${c.requested_by}</td><td>${c.status}</td><td>${c.impact||""}</td>`;
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
        tr.innerHTML = `<td>${a.id.slice(0,8)}</td><td>${a.matter_id}</td><td>${a.kind}</td><td>${a.scheduled_at}</td><td>${a.status}</td><td>${a.note||""}</td>`;
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
        tr.innerHTML = `<td>${d.matter_id}</td><td>${d.name}</td><td>${d.version}</td><td>${d.status}</td>`;
        rows.appendChild(tr);
      });
    }
  } catch(e){}
}
async function loadReport() {
  try {
    const report = await request("/reports/friday");
    if (document.getElementById("report")) document.getElementById("report").textContent = JSON.stringify(report, null, 2);
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
