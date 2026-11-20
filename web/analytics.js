(() => {
  async function loadAnalytics() {
    const section = document.getElementById("analitica");
    if (!section) return;
    let data;
    try {
      const res = await fetch(CARBON_API_BASE + "/staff/analytics", {
        headers: { Authorization: authHeader() || "" },
      });
      if (!res.ok) throw new Error(await res.text());
      data = await res.json();
    } catch (e) {
      const msg = document.createElement("p");
      msg.setAttribute("role", "status");
      msg.textContent = "No se pudo cargar la analítica.";
      section.appendChild(msg);
      return;
    }

    const wrap = document.createElement("div");

    const lessonCard = document.createElement("div");
    lessonCard.className = "card table-wrap";
    const lessonTable = document.createElement("table");
    const lh = document.createElement("thead");
    const lhr = document.createElement("tr");
    for (const h of ["Lección", "Empezaron", "Terminaron", "% terminaron", "Dejaron antes de empezar"]) {
      const th = document.createElement("th");
      th.textContent = h;
      lhr.appendChild(th);
    }
    lh.appendChild(lhr);
    lessonTable.appendChild(lh);
    const lb = document.createElement("tbody");
    for (const l of data.lessons || []) {
      const tr = document.createElement("tr");
      const cells = [l.lesson_id, l.started, l.completed,
        l.completion_rate == null ? "—" : Math.round(l.completion_rate * 100) + "%",
        l.dropped_before_first_item];
      for (const c of cells) {
        const td = document.createElement("td");
        td.textContent = String(c);
        tr.appendChild(td);
      }
      lb.appendChild(tr);
    }
    lessonTable.appendChild(lb);
    lessonCard.appendChild(lessonTable);
    wrap.appendChild(lessonCard);

    const itemCard = document.createElement("div");
    itemCard.className = "card table-wrap";
    const itemTable = document.createElement("table");
    const ih = document.createElement("thead");
    const ihr = document.createElement("tr");
    for (const h of ["Pregunta", "Respondieron", "Acertaron a la primera", "% acierto", "Dejaron aquí"]) {
      const th = document.createElement("th");
      th.textContent = h;
      ihr.appendChild(th);
    }
    ih.appendChild(ihr);
    itemTable.appendChild(ih);
    const ib = document.createElement("tbody");
    for (const it of data.items || []) {
      const tr = document.createElement("tr");
      const cells = [it.item_id, it.answered, it.first_try_correct,
        it.accuracy == null ? "—" : Math.round(it.accuracy * 100) + "%",
        it.drop_off];
      for (const c of cells) {
        const td = document.createElement("td");
        td.textContent = String(c);
        tr.appendChild(td);
      }
      ib.appendChild(tr);
    }
    itemTable.appendChild(ib);
    itemCard.appendChild(itemTable);
    wrap.appendChild(itemCard);

    const conv = data.conversion || {};
    const ot = data.on_time || {};
    const p1 = document.createElement("p");
    const r1 = conv.rate == null ? "—" : Math.round(conv.rate * 100);
    p1.textContent = `Pagaron: ${conv.paid} de ${conv.journeys} (${r1} %)`;
    wrap.appendChild(p1);
    const p2 = document.createElement("p");
    const r2 = ot.rate == null ? "—" : Math.round(ot.rate * 100);
    p2.textContent = `Terminaron a tiempo: ${ot.on_time} de ${ot.finished} (${r2} %)`;
    wrap.appendChild(p2);

    const heading = section.querySelector("h2");
    const note = section.querySelector("p.analitica-note");
    section.replaceChildren();
    if (heading) section.appendChild(heading);
    if (note) section.appendChild(note);
    section.appendChild(wrap);
  }

  document.addEventListener("DOMContentLoaded", loadAnalytics);
})();
