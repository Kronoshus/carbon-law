(() => {
  const DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];
  const DAY_LABELS = { mon: "Lunes", tue: "Martes", wed: "Miércoles", thu: "Jueves", fri: "Viernes", sat: "Sábado", sun: "Domingo" };
  const $ = (id) => document.getElementById(id);
  let saved = null;
  let holidays = [];

  function say(text) { $("firmaMessage").textContent = text; }

  async function call(path, method, body) {
    const res = await fetch(CARBON_API_BASE + path, {
      method: method || "GET",
      headers: { "Content-Type": "application/json", Authorization: authHeader() },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) throw new Error(String(res.status));
    return res.json();
  }

  function holidayLabel(day) {
    const date = new Date(day + "T00:00:00");
    return Number.isNaN(date.getTime()) ? day : date.toLocaleDateString("es-US", { dateStyle: "long" });
  }
  function renderHolidays() {
    $("firmHolidayList").replaceChildren(...holidays.map((d) => Object.assign(document.createElement("li"), { textContent: holidayLabel(d) })));
  }

  function renderHours(hours) {
    $("firmHoursRows").replaceChildren(...DAYS.map((day) => {
      const span = (hours[day] || [])[0] || ["", ""];
      const time = (kind, value) => {
        const input = Object.assign(document.createElement("input"), { type: "time", value });
        input.dataset.day = day; input.dataset.kind = kind;
        const label = document.createElement("label");
        label.append(kind === "from" ? "Desde " : "Hasta ", input);
        return label;
      };
      const tr = document.createElement("tr");
      const name = Object.assign(document.createElement("td"), { textContent: DAY_LABELS[day] });
      const cell = document.createElement("td");
      cell.append(time("from", span[0]), " ", time("to", span[1]));
      tr.append(name, cell);
      return tr;
    }));
  }

  function show(settings) {
    saved = settings;
    $("firmVoice").checked = settings.switches.voice_recording;
    $("firmAi").checked = settings.switches.ai_chat;
    $("firmExt").checked = settings.switches.extension;
    $("firmLpd").value = settings.lessons_per_day;
    $("firmRetention").value = settings.retention.unpaid_personal_data_days;
  }

  async function load() {
    let settings;
    try { settings = await call("/staff/firm-settings"); } catch (_) { say("No se pudieron cargar los ajustes."); return; }
    show(settings);
    holidays = (settings.holidays || []).slice().sort();
    renderHolidays();
    renderHours((settings.availability && settings.availability.hours) || {});
    const role = (getUser() || {}).role;
    if (role !== "attorney" && role !== "admin") {
      ["firmVoice", "firmAi", "firmExt", "firmLpd", "firmRetention"].forEach((id) => { $(id).disabled = true; });
      $("firmSave").remove();
      $("firmReadOnly").textContent = "Solo el abogado o un administrador puede cambiar estos ajustes.";
      $("firmReadOnly").hidden = false;
    }
  }

  async function saveSettings() {
    const changes = {};
    const switches = {};
    for (const [id, name] of [["firmVoice", "voice_recording"], ["firmAi", "ai_chat"], ["firmExt", "extension"]]) {
      if ($(id).checked !== saved.switches[name]) switches[name] = $(id).checked;
    }
    if (Object.keys(switches).length) changes.switches = switches;
    const lessons = Number($("firmLpd").value);
    if (lessons !== saved.lessons_per_day) changes.lessons_per_day = lessons;
    const days = Number($("firmRetention").value);
    if (days !== saved.retention.unpaid_personal_data_days) changes.retention = { unpaid_personal_data_days: days };
    if (!Object.keys(changes).length) { say("No hay cambios."); return; }
    try { show(await call("/staff/firm-settings", "PUT", changes)); say("Ajustes guardados."); }
    catch (_) { say("No se guardaron los ajustes. Revise los valores: lecciones por día de 1 a 4, y 30 días o más."); }
  }

  async function addHoliday() {
    const day = $("firmHolidayDate").value;
    if (!day) return;
    const next = [...new Set([...holidays, day])].sort();
    try { await call("/staff/holidays", "PUT", { dates: next }); holidays = next; renderHolidays(); say("Feriado agregado."); }
    catch (_) { say("No se pudo agregar el feriado."); }
  }

  async function saveHours() {
    const hours = {};
    for (const day of DAYS) {
      const from = document.querySelector(`#firmHoursRows input[data-day="${day}"][data-kind="from"]`).value;
      const to = document.querySelector(`#firmHoursRows input[data-day="${day}"][data-kind="to"]`).value;
      hours[day] = from && to ? [[from, to]] : [];
    }
    const slots = (saved && saved.availability && saved.availability.slot_minutes) || { signing: 60, consultation: 30 };
    try { await call("/staff/availability", "PUT", { hours, slot_minutes: slots }); say("Horario guardado."); }
    catch (_) { say("No se pudo guardar el horario."); }
  }

  document.addEventListener("DOMContentLoaded", () => {
    if (!$("firma")) return;
    load();
    $("firmSave").addEventListener("click", saveSettings);
    $("firmAddHoliday").addEventListener("click", addHoliday);
    $("firmSaveHours").addEventListener("click", saveHours);
  });
})();
