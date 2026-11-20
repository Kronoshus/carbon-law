(() => {

  const API = "https://carbon-law.onrender.com";
  function token(){ return localStorage.getItem("carbon_token"); }
  function user(){ const u=localStorage.getItem("carbon_user"); return u?JSON.parse(u):null; }
  async function api(path, method="GET", body=null) {
    const opts = { method, headers: {"Content-Type":"application/json"} };
    const t = token(); if (t) opts.headers.Authorization = "Bearer "+t;
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(API+path, opts);
    if (!res.ok) { const txt = await res.text(); const err = new Error(txt); err.status = res.status; err.body = txt; throw err; }
    return res.json();
  }

  let currentKind = "item";
  let currentEntry = null;
  let currentDetail = null;

  function setStatus(msg){ const el=document.getElementById("contentStatus"); if(el) el.textContent = msg; }

  async function loadEntries() {
    const kind = document.getElementById("contentKind").value;
    currentKind = kind;
    const data = await api(`/staff/content?kind=${kind}`);
    const box = document.getElementById("contentEntries");
    box.replaceChildren();
    for (const e of data.entries) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "btn secondary sm";
      btn.textContent = e.entry_id;
      btn.addEventListener("click", () => openEntry(e.entry_id));
      box.appendChild(btn);
    }
  }

  async function openEntry(id) {
    currentEntry = id;
    const d = await api(`/staff/content/${id}`);
    currentDetail = d;
    renderDetail(d);
  }

  function renderDetail(d) {
    const box = document.getElementById("contentDetail");
    box.hidden = false;
    // clear
    box.replaceChildren();
    const h = document.createElement("h3");
    h.textContent = d.entry_id;
    box.appendChild(h);
    const liveV = d.live ? d.live.version : null;
    const p = document.createElement("p");
    p.textContent = `Publicada: versión ${liveV === null ? "—" : liveV}`;
    box.appendChild(p);
    const pending = d.versions.find(v => v.state === "draft" || v.state === "review");
    // newest pending
    const pend = d.versions.length ? d.versions[0] : null;
    const isPending = pend && (pend.state === "draft" || pend.state === "review");
    if (isPending) {
      const p2 = document.createElement("p");
      p2.textContent = `Pendiente: versión ${pend.version} (${pend.state === "draft" ? "borrador" : "en revisión"})`;
      box.appendChild(p2);
    }
    const shownVer = isPending ? pend : (d.live ? d.versions.find(v => v && v.version === d.live.version) : (d.versions.length ? d.versions[0] : null));
    const shownErrors = shownVer ? (shownVer.errors || []) : [];
    const hasErrors = shownErrors.length > 0;
    // choose body to edit: pending version body else live body
    let body = null;
    if (isPending) body = pend.body;
    else if (d.live) body = d.live.body;
    else body = (d.versions[0] ? d.versions[0].body : {});
    if (!body) body = {};

    const form = document.createElement("div");
    // render textareas
    if (typeof body.es === "string") {
      // datos/summary
      const esTa = makeTa("texto (es)", body.es || "");
      const enTa = makeTa("texto (en)", body.en || "");
      esTa.id = "field_texto_es"; enTa.id = "field_texto_en";
      form.appendChild(labelWrap("texto (es)", esTa));
      form.appendChild(labelWrap("texto (en)", enTa));
      // store field map
      form.dataset.fields = JSON.stringify(["texto"]);
    } else {
      // item: fields in es
      const esObj = body.es || {};
      const enObj = body.en || {};
      const fields = Object.keys(esObj);
      // ensure en fields
      for (const k of Object.keys(enObj)) if (!fields.includes(k)) fields.push(k);
      for (const field of fields) {
        const ev = esObj[field];
        const nv = enObj[field];
        if (Array.isArray(ev) || Array.isArray(nv)) {
          const arrE = Array.isArray(ev) ? ev : [];
          const arrN = Array.isArray(nv) ? nv : [];
          const len = Math.max(arrE.length, arrN.length);
          // detect pairs: elements are arrays of 2
          const isPairs = len > 0 && (Array.isArray(arrE[0]) || Array.isArray(arrN[0]));
          if (isPairs) {
            for (let i=0;i<len;i++) {
              const aE = (arrE[i] && arrE[i][0]) || "";
              const bE = (arrE[i] && arrE[i][1]) || "";
              const aN = (arrN[i] && arrN[i][0]) || "";
              const bN = (arrN[i] && arrN[i][1]) || "";
              const ta = makeTa(`pairs ${i+1}a (es)`, aE); ta.dataset.field=`pairs.${i}.0`; ta.dataset.lang="es";
              const tb = makeTa(`pairs ${i+1}b (es)`, bE); tb.dataset.field=`pairs.${i}.1`; tb.dataset.lang="es";
              const ta2 = makeTa(`pairs ${i+1}a (en)`, aN); ta2.dataset.field=`pairs.${i}.0`; ta2.dataset.lang="en";
              const tb2 = makeTa(`pairs ${i+1}b (en)`, bN); tb2.dataset.field=`pairs.${i}.1`; tb2.dataset.lang="en";
              // simple: just es/en textareas labeled
              form.appendChild(labelWrap(`pairs ${i+1}a (es)`, ta));
              form.appendChild(labelWrap(`pairs ${i+1}b (es)`, tb));
              form.appendChild(labelWrap(`pairs ${i+1}a (en)`, ta2));
              form.appendChild(labelWrap(`pairs ${i+1}b (en)`, tb2));
            }
          } else {
            for (let i=0;i<len;i++) {
              const ta = makeTa(`${field} ${i+1} (es)`, arrE[i] || "");
              const tb = makeTa(`${field} ${i+1} (en)`, arrN[i] || "");
              ta.dataset.field = field; ta.dataset.index = i; ta.dataset.lang="es";
              tb.dataset.field = field; tb.dataset.index = i; tb.dataset.lang="en";
              form.appendChild(labelWrap(`${field} ${i+1} (es)`, ta));
              form.appendChild(labelWrap(`${field} ${i+1} (en)`, tb));
            }
          }
        } else {
          const ta = makeTa(`${field} (es)`, (ev===undefined?"":ev));
          const tb = makeTa(`${field} (en)`, (nv===undefined?"":nv));
          ta.dataset.field = field; ta.dataset.lang="es";
          tb.dataset.field = field; tb.dataset.lang="en";
          form.appendChild(labelWrap(`${field} (es)`, ta));
          form.appendChild(labelWrap(`${field} (en)`, tb));
        }
      }
      // answer/source not editable? spec says body can include answer/source; but UI only fields. Hidden keep.
    }
    box.appendChild(form);

    if (hasErrors) {
      const lbl = document.createElement("p");
      lbl.textContent = "Errores del validador:";
      box.appendChild(lbl);
      const ul = document.createElement("ul");
      ul.className = "content-errors";
      for (const e of shownErrors) {
        const li = document.createElement("li");
        li.textContent = e;
        ul.appendChild(li);
      }
      box.appendChild(ul);
      const warn = document.createElement("p");
      warn.textContent = "No se puede enviar ni publicar mientras haya errores.";
      box.appendChild(warn);
    }
    // buttons
    const btns = document.createElement("div");
    btns.className = "content-actions";
    const saveBtn = document.createElement("button"); saveBtn.type="button"; saveBtn.className="btn secondary sm"; saveBtn.textContent="Guardar borrador";
    const submitBtn = document.createElement("button"); submitBtn.type="button"; submitBtn.className="btn sm"; submitBtn.textContent="Enviar a revisión";
    submitBtn.disabled = hasErrors;
    const previewBtn = document.createElement("button"); previewBtn.type="button"; previewBtn.className="btn secondary sm"; previewBtn.textContent="Vista previa";
    btns.appendChild(saveBtn); btns.appendChild(submitBtn); btns.appendChild(previewBtn);

    const isLegal = d.legal;
    const isAttorney = user() && user().role === "attorney";
    if (isLegal) {
      if (isAttorney && isPending) {
        const ab = document.createElement("button"); ab.type="button"; ab.className="btn sm"; ab.textContent = `Aprobar versión ${pend.version}`;
        ab.disabled = hasErrors;
        ab.addEventListener("click", () => approveVersion(pend.version));
        btns.appendChild(ab);
      } else {
        const txt = document.createElement("p"); txt.textContent = "Solo el abogado puede aprobar y publicar este contenido.";
        box.appendChild(txt);
      }
    } else {
      if (isPending) {
        const pb = document.createElement("button"); pb.type="button"; pb.className="btn sm"; pb.textContent = `Publicar versión ${pend.version}`;
        pb.disabled = hasErrors;
        pb.addEventListener("click", () => publishVersion(pend.version));
        btns.appendChild(pb);
      }
    }
    box.appendChild(btns);

    saveBtn.addEventListener("click", () => saveDraft(body));
    submitBtn.addEventListener("click", submitEntry);
    previewBtn.addEventListener("click", () => previewEntry(isPending ? pend.version : (d.live?d.live.version:0)));
  }

  function makeTa(label, value) {
    const ta = document.createElement("textarea");
    ta.setAttribute("aria-label", label);
    ta.value = value;
    return ta;
  }
  function labelWrap(label, ta) {
    const lab = document.createElement("label");
    lab.textContent = label;
    const wrap = document.createElement("div");
    wrap.appendChild(lab);
    wrap.appendChild(ta);
    return wrap;
  }

  function collectBody() {
    const box = document.getElementById("contentDetail");
    const tas = box.querySelectorAll("textarea");
    // detect datos/summary: textareas with aria-label texto (es)
    const textoEs = box.querySelector('textarea[aria-label="texto (es)"]');
    if (textoEs) {
      const es = box.querySelector('textarea[aria-label="texto (es)"]').value;
      const en = box.querySelector('textarea[aria-label="texto (en)"]').value;
      return { es, en };
    }
    // item
    const esObj = {};
    const enObj = {};
    // simple fields
    for (const ta of tas) {
      const lab = ta.getAttribute("aria-label");
      // parse field name
    }
    // We'll reconstruct by labels
    // Group by aria-label
    const map = {};
    for (const ta of tas) {
      const lab = ta.getAttribute("aria-label");
      map[lab] = ta.value;
    }
    // Now build esObj/enObj by iterating original? Simpler: for each textarea label ending (es)/(en)
    // We'll just put all non-list fields
    // Re-scan labels
    const esFields = new Set();
    const enFields = new Set();
    for (const lab of Object.keys(map)) {
      const m = lab.match(/^(.*) \((es|en)\)$/);
      if (!m) continue;
      const field = m[1].trim();
      const lang = m[2];
      // handle list index
      const mi = field.match(/^(.*) (\d+)$/);
      if (mi) {
        const f = mi[1];
        const idx = parseInt(mi[2])-1;
        if (!esObj[f]) esObj[f]=[]; if (!enObj[f]) enObj[f]=[];
        if (lang==="es") esObj[f][idx]=map[lab]; else enObj[f][idx]=map[lab];
      } else if (field.startsWith("pairs ")) {
        // pairs 1a
        const mp = field.match(/^pairs (\d+)(a|b)$/);
        if (mp) {
          const i = parseInt(mp[1])-1;
          const ab = mp[2];
          const j = ab==="a"?0:1;
          if (!esObj.pairs) esObj.pairs=[]; if (!enObj.pairs) enObj.pairs=[];
          if (!esObj.pairs[i]) esObj.pairs[i]=["",""];
          if (!enObj.pairs[i]) enObj.pairs[i]=["",""];
          if (lang==="es") esObj.pairs[i][j]=map[lab]; else enObj.pairs[i][j]=map[lab];
        }
      } else {
        if (lang==="es") esObj[field]=map[lab]; else enObj[field]=map[lab];
      }
    }
    const body = { es: esObj, en: enObj };
    // answer/source not in UI; preserve from current detail? For draft, test expects source included. The original draft body from detail has source. But our collected body lacks source. Need add source from current body if present.
    // Find current pending/live body
    let orig = null;
    const d = currentDetail;
    const pend = d.versions[0];
    if (pend && (pend.state==="draft"||pend.state==="review")) orig = pend.body;
    else if (d.live) orig = d.live.body;
    if (orig && orig.source !== undefined) body.source = orig.source;
    if (orig && orig.answer !== undefined) body.answer = orig.answer;
    return body;
  }

  async function saveDraft(origBody) {
    const body = collectBody();
    try {
      const res = await api(`/staff/content/${currentEntry}/draft`, "PUT", { body });
      setStatus("");
      await openEntry(currentEntry);
    } catch (e) {
      handleErr(e);
    }
  }
  async function submitEntry() {
    try {
      await api(`/staff/content/${currentEntry}/submit`, "POST");
      await openEntry(currentEntry);
    } catch (e) {
      handleErr(e);
    }
  }
  async function approveVersion(v) {
    try {
      await api(`/staff/content/${currentEntry}/approve`, "POST", { version: v });
      await openEntry(currentEntry);
    } catch (e) { handleErr(e); }
  }
  async function publishVersion(v) {
    try {
      await api(`/staff/content/${currentEntry}/publish`, "POST", { version: v });
      await openEntry(currentEntry);
    } catch (e) { handleErr(e); }
  }
  async function previewEntry(v) {
    const lang = "es";
    const data = await api(`/staff/content/${currentEntry}/preview?version=${v}&lang=${lang}`);
    const box = document.querySelector(".content-preview");
    if (data.text !== undefined) {
      box.textContent = data.text;
    } else {
      // item
      const item = data.item || {};
      let txt = "";
      for (const k of Object.keys(item)) {
        txt += `${k}: ${item[k]}\n`;
      }
      if (data.explain) txt += `explain: ${data.explain}`;
      box.textContent = txt;
    }
  }
  function handleErr(e) {
    let msg = "";
    try { const j = JSON.parse(e.body); if (j.error === "languages") msg = `Faltan los dos idiomas para publicar: ${j.missing.join("/")}.`; } catch(_) {}
    if (!msg) msg = e.body || e.message;
    setStatus(msg);
  }

  document.addEventListener("DOMContentLoaded", () => {
    const sel = document.getElementById("contentKind");
    if (sel) sel.addEventListener("change", loadEntries);
    loadEntries();
  });
})();
