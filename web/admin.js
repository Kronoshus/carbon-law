const API = localStorage.getItem("carbon_api") || "https://carbon-law.onrender.com";
async function request(path, method="GET", body=null) {
  const opts = { method, headers: {"Content-Type":"application/json"} };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(API + path, opts);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

async function createMatterFromForm(event) {
  event.preventDefault();
  const body = {
    id: document.getElementById("newId").value,
    client_name: document.getElementById("newClient").value,
    stage: "1 Intake",
    owner: document.getElementById("newOwner").value || "Unassigned",
    risk_level: "Low",
    priority: "Normal",
    next_action: "Complete intake"
  };
  const result = await request("/matters", "POST", body);
  document.getElementById("adminOut").textContent = "Matter created: " + result.id;
}

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("matterForm");
  if (form) form.addEventListener("submit", createMatterFromForm);
  loadMatters();
});

async function loadMatters() {
  try {
    const matters = await request("/matters");
    const rows = document.getElementById("adminMatterRows");
    if (rows) {
      rows.innerHTML = "";
      matters.forEach(m => {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td>${m.id}</td><td>${m.client_name}</td><td>${m.stage}</td><td>${m.owner}</td><td>${m.risk_level}</td>`;
        rows.appendChild(tr);
      });
    }
    const report = await request("/reports/friday");
    if (document.getElementById("report")) document.getElementById("report").textContent = JSON.stringify(report, null, 2);
  } catch (e) {
    if (document.getElementById("adminOut")) document.getElementById("adminOut").textContent = "Backend unavailable.";
  }
}
