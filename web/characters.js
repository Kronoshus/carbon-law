(() => {
  const DISPLAY_NAME = { calavera: "La Calavera", oso: "El Oso", pinata: "Piñata" };
  const UNITS = ["will", "trust", "ahcd", "poa", "final", "bonus", "games", "sensitive", "intake"];
  const UNIT_LABELS = {
    will: "El testamento", trust: "El fideicomiso", ahcd: "La directiva de salud",
    poa: "El poder notarial", final: "Cuide sus documentos", bonus: "Lecciones extra",
    games: "Juegos", sensitive: "Temas difíciles", intake: "Tus datos",
  };

  async function call(path, method, body) {
    const res = await fetch(CARBON_API_BASE + path, {
      method: method || "GET",
      headers: { "Content-Type": "application/json", Authorization: authHeader() },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) { const txt = await res.text(); const err = new Error(txt); err.status = res.status; throw err; }
    return res.json();
  }

  function status(msg) {
    const el = document.getElementById("charactersStatus");
    if (el) el.textContent = msg;
  }

  async function loadCharacters() {
    const box = document.getElementById("charactersList");
    if (!box) return;
    box.replaceChildren();
    let data;
    try { data = await call("/staff/characters"); } catch (e) { status(String(e.message || e)); return; }
    for (const c of data) {
      const art = document.createElement("article");
      const h = document.createElement("h2");
      h.textContent = DISPLAY_NAME[c.id] || c.id;
      art.appendChild(h);

      const name = DISPLAY_NAME[c.id] || c.id;

      const activeWrap = document.createElement("div");
      const activeCb = document.createElement("input");
      activeCb.type = "checkbox";
      activeCb.setAttribute("aria-label", "Activo");
      activeCb.checked = !!c.enabled;
      if (c.id === "calavera") activeCb.disabled = true;
      const activeLabel = document.createElement("label");
      activeLabel.appendChild(activeCb);
      activeLabel.append(" Activo");
      activeWrap.appendChild(activeLabel);
      art.appendChild(activeWrap);
      if (c.id === "calavera") {
        const note = document.createElement("span");
        note.textContent = "La Calavera no se puede desactivar.";
        art.appendChild(note);
      }

      for (const u of UNITS) {
        const cb = document.createElement("input");
        cb.type = "checkbox";
        cb.setAttribute("aria-label", UNIT_LABELS[u]);
        cb.checked = (c.units || []).indexOf(u) >= 0;
        cb.dataset.unit = u;
        const lab = document.createElement("label");
        lab.appendChild(cb);
        lab.append(" " + UNIT_LABELS[u]);
        art.appendChild(lab);
      }

      const phraseWrap = document.createElement("div");
      const phraseLabel = document.createElement("label");
      phraseLabel.textContent = "Frase para escuchar";
      const phraseInput = document.createElement("input");
      phraseInput.type = "text";
      phraseInput.setAttribute("aria-label", "Frase para escuchar");
      phraseInput.value = `Hola, soy ${name}. Soy un programa de inteligencia artificial, no soy el abogado.`;
      phraseWrap.appendChild(phraseLabel);
      phraseWrap.appendChild(phraseInput);
      art.appendChild(phraseWrap);

      const langWrap = document.createElement("div");
      const langLabel = document.createElement("label");
      langLabel.textContent = "Idioma";
      const langSelect = document.createElement("select");
      langSelect.setAttribute("aria-label", "Idioma");
      const optEs = document.createElement("option"); optEs.value = "es"; optEs.textContent = "es";
      const optEn = document.createElement("option"); optEn.value = "en"; optEn.textContent = "en";
      langSelect.appendChild(optEs);
      langSelect.appendChild(optEn);
      langWrap.appendChild(langLabel);
      langWrap.appendChild(langSelect);
      art.appendChild(langWrap);

      const previewBtn = document.createElement("button");
      previewBtn.type = "button";
      previewBtn.className = "btn secondary sm";
      previewBtn.textContent = "Escuchar voz";
      previewBtn.addEventListener("click", () => {
        const line = phraseInput.value;
        const lang = langSelect.value === "en" ? "en-US" : "es-MX";
        window.speechSynthesis.cancel();
        const utt = new SpeechSynthesisUtterance(line);
        utt.lang = lang;
        window.speechSynthesis.speak(utt);
      });
      art.appendChild(previewBtn);

      const saveBtn = document.createElement("button");
      saveBtn.type = "button";
      saveBtn.className = "btn sm";
      saveBtn.textContent = "Guardar";
      saveBtn.addEventListener("click", async () => {
        const enabled = activeCb.checked;
        const units = [];
        for (const cbx of art.querySelectorAll('input[type="checkbox"][data-unit]')) {
          if (cbx.checked) units.push(cbx.dataset.unit);
        }
        try {
          await call(`/characters/${c.id}`, "PATCH", { enabled, units });
          status("Guardado.");
        } catch (e) {
          status(String(e.message || e));
        }
      });
      art.appendChild(saveBtn);

      const container = document.getElementById("charactersList");
      container.appendChild(art);
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    const box = document.getElementById("charactersList");
    if (box) loadCharacters();
  });
})();
