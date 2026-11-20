const CHAR_API = "https://carbon-law.onrender.com";
function token(){ return localStorage.getItem("carbon_token"); }
async function api(path, method="GET", body=null) {
  const opts = { method, headers: {"Content-Type":"application/json"} };
  const t = token(); if (t) opts.headers.Authorization = "Bearer "+t;
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(CHAR_API+path, opts);
  if (!res.ok) { const txt = await res.text(); const err = new Error(txt); err.status = res.status; err.body = txt; throw err; }
  return res.json();
}

const UNITS = ["will", "trust", "ahcd", "poa", "final", "bonus", "games", "sensitive", "intake"];
const UNIT_LABELS = {
  will: "El testamento", trust: "El fideicomiso", ahcd: "La directiva de salud",
  poa: "El poder notarial", final: "Cuide sus documentos", bonus: "Lecciones extra",
  games: "Juegos", sensitive: "Temas difíciles", intake: "Tus datos",
};
const NAMES = { calavera: "La Calavera", oso: "El Oso", pinata: "Piñata" };

function labelWrap(label, el) {
  const lab = document.createElement("label");
  lab.textContent = label;
  const wrap = document.createElement("div");
  wrap.appendChild(lab);
  wrap.appendChild(el);
  return wrap;
}

async function loadCharacters() {
  const data = await api("/staff/characters");
  const box = document.getElementById("charactersList");
  if (!box) return;
  box.replaceChildren();
  for (const c of data) {
    const art = document.createElement("article");
    const h = document.createElement("h2");
    h.textContent = NAMES[c.id] || c.id;
    art.appendChild(h);

    const activeCb = document.createElement("input");
    activeCb.type = "checkbox";
    activeCb.setAttribute("aria-label", "Activo");
    activeCb.checked = !!c.enabled;
    if (c.id === "calavera") activeCb.disabled = true;
    const activeLabel = document.createElement("label");
    activeLabel.appendChild(activeCb);
    activeLabel.append(" Activo");
    art.appendChild(activeLabel);
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
      const lbl = document.createElement("label");
      lbl.appendChild(cb);
      lbl.append(" " + UNIT_LABELS[u]);
      art.appendChild(lbl);
    }

    const lineInput = document.createElement("input");
    lineInput.setAttribute("aria-label", "Frase para escuchar");
    lineInput.value = "Hola, soy " + (NAMES[c.id] || c.id) + ". Soy un programa de inteligencia artificial, no soy el abogado.";
    art.appendChild(labelWrap("Frase para escuchar", lineInput));

    const langSelect = document.createElement("select");
    langSelect.setAttribute("aria-label", "Idioma");
    const optEs = document.createElement("option"); optEs.value = "es"; optEs.textContent = "es"; langSelect.appendChild(optEs);
    const optEn = document.createElement("option"); optEn.value = "en"; optEn.textContent = "en"; langSelect.appendChild(optEn);
    art.appendChild(labelWrap("Idioma", langSelect));

    const listenBtn = document.createElement("button");
    listenBtn.type = "button";
    listenBtn.className = "btn sm";
    listenBtn.textContent = "Escuchar voz";
    listenBtn.addEventListener("click", () => {
      const lang = langSelect.value === "en" ? "en-US" : "es-MX";
      window.speechSynthesis.cancel();
      const utt = new SpeechSynthesisUtterance(lineInput.value);
      utt.lang = lang;
      window.speechSynthesis.speak(utt);
    });
    art.appendChild(listenBtn);

    const saveBtn = document.createElement("button");
    saveBtn.type = "button";
    saveBtn.className = "btn sm";
    saveBtn.textContent = "Guardar";
    saveBtn.addEventListener("click", async () => {
      const enabled = activeCb.checked;
      const units = [];
      art.querySelectorAll('input[type="checkbox"][data-unit]').forEach((cb) => { if (cb.checked) units.push(cb.dataset.unit); });
      await api("/characters/" + c.id, "PATCH", { enabled: enabled, units: units });
    });
    art.appendChild(saveBtn);

    box.appendChild(art);
  }
}

document.addEventListener("DOMContentLoaded", () => { loadCharacters().catch(e => console.error('characters err', e)); });
