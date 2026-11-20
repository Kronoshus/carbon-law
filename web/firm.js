
const DAYS = ["mon","tue","wed","thu","fri","sat","sun"];
const DAY_LABELS = {mon:"Lunes",tue:"Martes",wed:"Miércoles",thu:"Jueves",fri:"Viernes",sat:"Sábado",sun:"Domingo"};

function authHeader() { const t = (typeof getToken === "function") ? getToken() : localStorage.getItem("carbon_token"); return t ? "Bearer " + t : null; }

let initial = null;
let holidays = [];
let hours = {};
let slotMinutes = { signing: 60, consultation: 30 };

async function load() {
  const res = await fetch("/staff/firm-settings", { headers: { "Content-Type": "application/json", Authorization: authHeader() } });
  const data = await res.json();
  initial = data;
  holidays = (data.holidays || []).slice();
  hours = (data.availability && data.availability.hours) ? data.availability.hours : {};
  slotMinutes = (data.availability && data.availability.slot_minutes) ? data.availability.slot_minutes : slotMinutes;

  document.getElementById("firmVoice").checked = !!data.switches.voice_recording;
  document.getElementById("firmAi").checked = !!data.switches.ai_chat;
  document.getElementById("firmExt").checked = !!data.switches.extension;
  document.getElementById("firmLpd").value = data.lessons_per_day;
  document.getElementById("firmRetention").value = data.retention.unpaid_personal_data_days;

  const user = (typeof getUser === "function") ? getUser() : JSON.parse(localStorage.getItem("carbon_user") || "null");
  const canEdit = user && (user.role === "attorney" || user.role === "admin");
  if (!canEdit) {
    ["firmVoice","firmAi","firmExt","firmLpd","firmRetention"].forEach((id) => { const el = document.getElementById(id); if (el) el.disabled = true; });
    const save = document.getElementById("firmSave"); if (save) save.remove();
    const msg = document.getElementById("firmReadOnly");
    if (msg) { msg.removeAttribute("hidden"); msg.style.display = "block"; msg.textContent = "Solo el abogado o un administrador puede cambiar estos ajustes."; }
  }

  renderHolidays();
  renderHours();
}

function renderHolidays() {
  const ul = document.getElementById("firmHolidayList");
  ul.textContent = "";
  holidays.forEach((d) => {
    const li = document.createElement("li");
    li.textContent = d;
    ul.appendChild(li);
  });
}

function renderHours() {
  const tbody = document.getElementById("firmHoursRows");
  tbody.textContent = "";
  DAYS.forEach((day) => {
    const tr = document.createElement("tr");
    const td0 = document.createElement("td"); td0.textContent = DAY_LABELS[day]; tr.appendChild(td0);
    const td1 = document.createElement("td");
    const from = document.createElement("input"); from.type = "time"; from.dataset.day = day; from.dataset.kind = "from";
    const to = document.createElement("input"); to.type = "time"; to.dataset.day = day; to.dataset.kind = "to";
    const row = hours[day] && hours[day][0];
    if (row) { from.value = row[0]; to.value = row[1]; }
    const lblFrom = document.createElement("label"); lblFrom.textContent = "Desde "; lblFrom.appendChild(from);
    const lblTo = document.createElement("label"); lblTo.textContent = "Hasta "; lblTo.appendChild(to);
    td1.appendChild(lblFrom); td1.appendChild(lblTo);
    tr.appendChild(td1);
    tbody.appendChild(tr);
  });
}

async function saveSettings() {
  const changes = {};
  const switches = {};
  if (document.getElementById("firmVoice").checked !== !!initial.switches.voice_recording) switches.voice_recording = document.getElementById("firmVoice").checked;
  if (document.getElementById("firmAi").checked !== !!initial.switches.ai_chat) switches.ai_chat = document.getElementById("firmAi").checked;
  if (document.getElementById("firmExt").checked !== !!initial.switches.extension) switches.extension = document.getElementById("firmExt").checked;
  if (Object.keys(switches).length) changes.switches = switches;
  const lpd = Number(document.getElementById("firmLpd").value);
  if (lpd !== initial.lessons_per_day) changes.lessons_per_day = lpd;
  const ret = Number(document.getElementById("firmRetention").value);
  if (ret !== initial.retention.unpaid_personal_data_days) changes.retention = { unpaid_personal_data_days: ret };
  await fetch("/staff/firm-settings", { method: "PUT", headers: { "Content-Type": "application/json", Authorization: authHeader() }, body: JSON.stringify(changes) });
}

async function addHoliday() {
  const d = document.getElementById("firmHolidayDate").value;
  if (!d) return;
  if (!holidays.includes(d)) holidays.push(d);
  holidays.sort();
  await fetch("/staff/holidays", { method: "PUT", headers: { "Content-Type": "application/json", Authorization: authHeader() }, body: JSON.stringify({ dates: holidays }) });
  renderHolidays();
}

async function saveHours() {
  const h = {};
  DAYS.forEach((day) => {
    const from = document.querySelector(`input[data-day="${day}"][data-kind="from"]`).value;
    const to = document.querySelector(`input[data-day="${day}"][data-kind="to"]`).value;
    if (from && to) h[day] = [[from, to]];
    else h[day] = [];
  });
  await fetch("/staff/availability", { method: "PUT", headers: { "Content-Type": "application/json", Authorization: authHeader() }, body: JSON.stringify({ hours: h, slot_minutes: slotMinutes }) });
}

document.addEventListener("DOMContentLoaded", () => {
  const m = document.getElementById("adminMain"); if (m) m.hidden = false;
  load();
  const save = document.getElementById("firmSave"); if (save) save.addEventListener("click", saveSettings);
  const add = document.getElementById("firmAddHoliday"); if (add) add.addEventListener("click", addHoliday);
  const sh = document.getElementById("firmSaveHours"); if (sh) sh.addEventListener("click", saveHours);
});
