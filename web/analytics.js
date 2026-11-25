(() => {
  const lessonName = (id) => CONTENT_TITLES.lessons[id] || id;
  function itemName(id) {
    const item = CONTENT_TITLES.items[id];
    if (!item) return id;
    const step = CONTENT_TITLES.steps[id.split(".").slice(0, 2).join(".")];
    return step ? `${step}: ${item[1]}` : item[1];
  }
  const percent = (rate) => (rate == null ? "—" : Math.round(rate * 100) + "%");

  function table(heads, rows) {
    const card = document.createElement("div");
    card.className = "card flush table-wrap";
    const t = document.createElement("table");
    t.className = "cards";
    const head = t.createTHead().insertRow();
    for (const h of heads) head.appendChild(Object.assign(document.createElement("th"), { textContent: h }));
    const body = t.createTBody();
    for (const cells of rows) {
      const tr = body.insertRow();
      cells.forEach((c, i) => Object.assign(tr.insertCell(), { textContent: String(c) }).dataset.label = heads[i]);
    }
    card.appendChild(t);
    return card;
  }
  function figure(label, value, detail) {
    const box = document.createElement("div");
    box.append(Object.assign(document.createElement("dt"), { textContent: label }),
      Object.assign(document.createElement("dd"), { textContent: value }));
    if (detail) box.appendChild(Object.assign(document.createElement("dd"), { className: "figure-detail", textContent: detail }));
    return box;
  }

  async function loadAnalytics() {
    const body = document.getElementById("analyticsBody");
    if (!body) return;
    let data;
    try {
      const res = await fetch(CARBON_API_BASE + "/staff/analytics", { headers: { Authorization: authHeader() || "" } });
      if (!res.ok) throw new Error(String(res.status));
      data = await res.json();
    } catch (e) {
      body.replaceChildren(Object.assign(document.createElement("p"), { className: "error-message", textContent: "Could not load the analytics. Reload the page to try again." }));
      return;
    }
    const conv = data.conversion || {};
    const ot = data.on_time || {};
    const totals = document.createElement("dl");
    totals.className = "report-figures analytics-totals";
    totals.append(figure("Paid", `${conv.paid} of ${conv.journeys}`, percent(conv.rate)),
      figure("Finished on time", `${ot.on_time} of ${ot.finished}`, percent(ot.rate)));
    const lessons = table(["Lesson", "Started", "Finished", "% finished", "Left before starting"],
      (data.lessons || []).map((l) => [lessonName(l.lesson_id), l.started, l.completed, percent(l.completion_rate), l.dropped_before_first_item]));
    const items = table(["Question", "Answered", "Right first time", "% right", "Left here"],
      (data.items || []).map((it) => [itemName(it.item_id), it.answered, it.first_try_correct, percent(it.accuracy), it.drop_off]));
    const h2 = (text) => Object.assign(document.createElement("h2"), { textContent: text });
    body.replaceChildren(totals, h2("Lessons"), lessons, h2("Questions"), items);
  }

  document.addEventListener("DOMContentLoaded", loadAnalytics);
})();
