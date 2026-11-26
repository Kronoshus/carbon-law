(() => {
  const DISPLAY_NAME = {
    calavera: "La Calavera", oso: "El Oso", pinata: "Piñata",
    girasol: "Girasol", colibri: "Colibrí", velita: "Velita", tortuga: "Doña Tortuga",
  };
  // The theme hosts' device voices: voices.json next to this page, the same file the app imports
  // (aprende/src/core/character/voice.ts). Loaded with the characters in loadCharacters().
  let VOICES = {};
  const LOCALES = { es: ["es-US", "es-MX"], en: ["en-US"] };

  function hostVoice(id, lang) {
    const want = VOICES[id];
    if (!want) return null;
    const rank = (v) => { const i = LOCALES[lang].indexOf(v.lang.replace("_", "-")); return i < 0 ? LOCALES[lang].length : i; };
    const ours = window.speechSynthesis.getVoices().filter((v) => v.lang.toLowerCase().startsWith(lang)).sort((a, b) => rank(a) - rank(b));
    for (const name of want[lang]) { const v = ours.find((o) => o.name.includes(name)); if (v) return v; }
    return ours[0] || null;
  }
  const UNITS = ["will", "trust", "ahcd", "poa", "final", "bonus", "games", "sensitive", "intake"];
  const UNIT_LABELS = {
    will: "The will", trust: "The living trust", ahcd: "Health care directive",
    poa: "Power of attorney", final: "Take care of your documents", bonus: "Extra lessons",
    games: "Games", sensitive: "Hard topics", intake: "Your details questions",
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
    try {
      [data, VOICES] = await Promise.all([call("/staff/characters"), fetch("voices.json").then((r) => r.json())]);
    } catch (e) { status("Could not load the characters. Try again later."); return; }
    if (!data.length) { status("No characters are set up."); return; }
    for (const c of data) {
      const art = document.createElement("article");
      const h = document.createElement("h2");
      h.textContent = DISPLAY_NAME[c.id] || c.id;
      art.appendChild(h);

      const name = DISPLAY_NAME[c.id] || c.id;

      const activeWrap = document.createElement("div");
      const activeCb = document.createElement("input");
      activeCb.type = "checkbox";
      activeCb.setAttribute("aria-label", "Active");
      activeCb.checked = !!c.enabled;
      if (c.id === "calavera") activeCb.disabled = true;
      const activeLabel = document.createElement("label");
      activeLabel.appendChild(activeCb);
      activeLabel.append(" Active");
      activeWrap.appendChild(activeLabel);
      art.appendChild(activeWrap);
      if (c.id === "calavera") {
        const note = document.createElement("span");
        note.textContent = "La Calavera cannot be turned off.";
        art.appendChild(note);
      }

      const unitsBox = document.createElement("fieldset");
      unitsBox.className = "unit-list";
      const legend = document.createElement("legend");
      legend.textContent = "Lessons this character hosts";
      unitsBox.appendChild(legend);
      for (const u of UNITS) {
        const cb = document.createElement("input");
        cb.type = "checkbox";
        cb.setAttribute("aria-label", UNIT_LABELS[u]);
        cb.checked = (c.units || []).indexOf(u) >= 0;
        cb.dataset.unit = u;
        const lab = document.createElement("label");
        lab.appendChild(cb);
        lab.append(" " + UNIT_LABELS[u]);
        unitsBox.appendChild(lab);
      }
      art.appendChild(unitsBox);

      const phraseWrap = document.createElement("div");
      const phraseLabel = document.createElement("label");
      phraseLabel.textContent = "Test phrase";
      const phraseInput = document.createElement("input");
      phraseInput.type = "text";
      phraseInput.setAttribute("aria-label", "Test phrase");
      phraseInput.value = `Hola, soy ${name}. Soy un programa de inteligencia artificial, no soy el abogado.`;
      phraseWrap.appendChild(phraseLabel);
      phraseWrap.appendChild(phraseInput);
      art.appendChild(phraseWrap);

      const langWrap = document.createElement("div");
      const langLabel = document.createElement("label");
      langLabel.textContent = "Voice language";
      const langSelect = document.createElement("select");
      langSelect.setAttribute("aria-label", "Voice language");
      const optEs = document.createElement("option"); optEs.value = "es"; optEs.textContent = "Spanish";
      const optEn = document.createElement("option"); optEn.value = "en"; optEn.textContent = "English";
      langSelect.appendChild(optEs);
      langSelect.appendChild(optEn);
      langWrap.appendChild(langLabel);
      langWrap.appendChild(langSelect);
      art.appendChild(langWrap);

      const previewBtn = document.createElement("button");
      previewBtn.type = "button";
      previewBtn.className = "btn secondary sm";
      previewBtn.textContent = "Play voice";
      previewBtn.addEventListener("click", () => {
        const line = phraseInput.value;
        const lang = langSelect.value === "en" ? "en" : "es";
        window.speechSynthesis.cancel();
        const utt = new SpeechSynthesisUtterance(line);
        utt.lang = lang === "en" ? "en-US" : "es-MX";
        const voice = hostVoice(c.id, lang);
        if (voice) { utt.voice = voice; utt.lang = voice.lang.replace("_", "-"); }
        if (VOICES[c.id]) { utt.pitch = VOICES[c.id].pitch; utt.rate = VOICES[c.id].rate; }
        window.speechSynthesis.speak(utt);
      });
      art.appendChild(previewBtn);

      const saveBtn = document.createElement("button");
      saveBtn.type = "button";
      saveBtn.className = "btn sm";
      saveBtn.textContent = "Save";
      saveBtn.addEventListener("click", async () => {
        const enabled = activeCb.checked;
        const units = [];
        for (const cbx of art.querySelectorAll('input[type="checkbox"][data-unit]')) {
          if (cbx.checked) units.push(cbx.dataset.unit);
        }
        try {
          await call(`/characters/${c.id}`, "PATCH", { enabled, units });
          status(`${name} saved.`);
        } catch (e) {
          status(e.status && e.status < 500 ? `${name} was not saved. Check the choices and try again.` : `${name} was not saved. The server had a problem; try again.`);
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
