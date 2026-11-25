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

  let currentEntry = null;
  let currentDetail = null;

  function setStatus(msg){ const el=document.getElementById("contentStatus"); if(el) el.textContent = msg; }
  function make(tag, props, ...children) {
    const node = Object.assign(document.createElement(tag), props || {});
    node.append(...children);
    return node;
  }

  // --- the entry list: human names from content-titles.js, the code id only as a tooltip ---
  const KIND_WORDS = { explain: "Explanation", choice: "Question", truefalse: "True or false", order: "Put in order",
    match: "Match pairs", scenario: "Story question" };
  const PERSONA_NAMES = { shared: "Instructions every character follows", "modes.learn": "During lessons", "modes.intake": "During \"Your details\" questions" };
  const CHARACTER_NAMES = { calavera: "La Calavera", oso: "El Oso", pinata: "Piñata", girasol: "Girasol", colibri: "Colibrí", velita: "Velita", tortuga: "Doña Tortuga" };

  // [group, subgroup, kind word, line] for one entry
  function describe(e) {
    const id = e.entry_id;
    if (e.kind === "datos") return ["\"Your details\" questions", "", "", CONTENT_TITLES.datos[id.slice(6)] || id];
    if (e.kind === "summary") {
      const [doc, article] = id.slice(8).split(".");
      return [CONTENT_TITLES.lessons[doc] || doc, "", `Article ${article}`, CONTENT_TITLES.summaries[`${doc}.${article}`] || ""];
    }
    if (e.kind === "persona") {
      const key = id.slice(8);
      if (key.startsWith("characters.")) { const c = key.slice(11); return ["Each character", "", "", CHARACTER_NAMES[c] || c]; }
      return ["For all characters", "", "", PERSONA_NAMES[key] || key];
    }
    const lesson = e.lesson_id || id.split(".")[0];
    const item = CONTENT_TITLES.items[id];
    const step = CONTENT_TITLES.steps[id.split(".").slice(0, 2).join(".")];
    return [CONTENT_TITLES.lessons[lesson] || lesson, step || "", item ? KIND_WORDS[item[0]] || item[0] : "", item ? item[1] : id];
  }

  async function loadEntries() {
    const kind = document.getElementById("contentKind").value;
    const box = document.getElementById("contentEntries");
    box.replaceChildren();
    let data;
    try { data = await api(`/staff/content?kind=${kind}`); }
    catch (e) { setStatus("Could not load the content. Try again later."); return; }
    const entries = data.entries || [];
    setStatus(entries.length ? "" : "There is no content of this type.");
    const groups = new Map();
    for (const e of entries) {
      const [group, sub, kindWord, line] = describe(e);
      if (!groups.has(group)) groups.set(group, new Map());
      const subs = groups.get(group);
      if (!subs.has(sub)) subs.set(sub, []);
      subs.get(sub).push({ e, kindWord, line });
    }
    for (const [group, subs] of groups) {
      const section = make("section", { className: "content-group" }, make("h3", { textContent: group }));
      for (const [sub, list] of subs) {
        if (sub) section.appendChild(make("h4", { textContent: sub }));
        const ul = make("ul");
        for (const { e, kindWord, line } of list) {
          const btn = make("button", { type: "button", className: "content-entry", title: e.entry_id });
          btn.dataset.entry = e.entry_id;
          if (kindWord) btn.appendChild(make("span", { className: "entry-kind", textContent: kindWord }));
          btn.appendChild(make("span", { className: "entry-line", textContent: line }));
          if (e.pending) btn.appendChild(make("span", { className: "badge", textContent: "Pending" }));
          btn.addEventListener("click", () => openEntry(e.entry_id));
          ul.appendChild(make("li", null, btn));
        }
        section.appendChild(ul);
      }
      box.appendChild(section);
    }
  }

  async function openEntry(id) {
    currentEntry = id;
    let d;
    try { d = await api(`/staff/content/${id}`); }
    catch (e) { handleErr(e); return; }
    currentDetail = d;
    for (const b of document.querySelectorAll("#contentEntries .content-entry")) {
      if (b.dataset.entry === id) b.setAttribute("aria-current", "true"); else b.removeAttribute("aria-current");
    }
    renderDetail(d);
    if (window.matchMedia("(max-width: 1099px)").matches) document.getElementById("contentDetail").scrollIntoView();
  }

  // --- the editor: plain-English labels; each field's path in the saved body rides on the field ---
  const FIELD_WORDS = { prompt: "Question", statement: "Statement", text: "Text", explain: "Explanation", story: "Story",
    options: "Answer", steps: "Step", pairs: "Pair" };
  const LANG = { es: "Spanish", en: "English" };

  function pendingVersion(d) {
    const pend = d.versions.length ? d.versions[0] : null;
    return pend && (pend.state === "draft" || pend.state === "review") ? pend : null;
  }

  function field(label, path, value, multiline = true) {
    const input = multiline ? make("textarea") : make("input", { type: "text" });
    input.value = value;
    input.dataset.path = JSON.stringify(path);
    input.id = "cf-" + path.join("-");
    const wrap = make("div", { className: "content-field" }, make("label", { htmlFor: input.id, textContent: label }), input);
    return wrap;
  }
  // the Spanish and the English version of one field, side by side
  function pair(word, pathOf, valueOf) {
    return make("div", { className: "field-pair" }, ...["es", "en"].map((lang) => field(`${word} (${LANG[lang]})`, pathOf(lang), valueOf(lang))));
  }

  function itemFields(body) {
    const es = body.es || {}, en = body.en || {};
    const names = Object.keys(es);
    for (const k of Object.keys(en)) if (!names.includes(k)) names.push(k);
    const out = [];
    for (const name of names) {
      const word = FIELD_WORDS[name] || name;
      const ev = es[name], nv = en[name];
      if (Array.isArray(ev) || Array.isArray(nv)) {
        const arrE = Array.isArray(ev) ? ev : [], arrN = Array.isArray(nv) ? nv : [];
        const len = Math.max(arrE.length, arrN.length);
        const isPairs = len > 0 && (Array.isArray(arrE[0]) || Array.isArray(arrN[0]));
        for (let i = 0; i < len; i++) {
          if (isPairs) {
            for (const side of [0, 1]) {
              const sideWord = `${word} ${i + 1}, ${side ? "right" : "left"}`;
              out.push(pair(sideWord, (lang) => [lang, name, i, side], (lang) => ((lang === "es" ? arrE : arrN)[i] || [])[side] || ""));
            }
          } else {
            out.push(pair(`${word} ${i + 1}`, (lang) => [lang, name, i], (lang) => (lang === "es" ? arrE : arrN)[i] || ""));
          }
        }
      } else {
        out.push(pair(word, (lang) => [lang, name], (lang) => (lang === "es" ? ev : nv) ?? ""));
      }
    }
    return out;
  }

  // the correct answer, for the kinds that have one; a value the validator rejects stays selected until changed
  function answerField(body) {
    const options = (body.es || {}).options;
    const isChoice = Array.isArray(options);
    const isTrueFalse = (body.es || {}).statement !== undefined;
    if (!isChoice && !isTrueFalse) return null;
    const select = make("select", { id: "cf-answer" });
    const choices = isChoice ? options.map((_, i) => [String(i), `Answer ${i + 1}`]) : [["true", "True"], ["false", "False"]];
    const has = "answer" in body;
    const current = String(body.answer);
    const valid = has && typeof body.answer === (isChoice ? "number" : "boolean") && choices.some(([v]) => v === current);
    if (!has) select.appendChild(make("option", { value: "", textContent: "Choose the correct answer" }));
    else if (!valid) {
      const shown = isChoice && Number.isInteger(body.answer) ? `Answer ${body.answer + 1} (does not exist)` : `${current} (not valid)`;
      select.appendChild(make("option", { value: "keep", textContent: shown }));
    }
    for (const [value, text] of choices) select.appendChild(make("option", { value, textContent: text }));
    select.value = valid ? current : has ? "keep" : "";
    return make("div", { className: "content-field" }, make("label", { htmlFor: select.id, textContent: "Correct answer" }), select);
  }

  function sourceField(body, legal) {
    if (!legal && body.source === undefined) return null;
    const wrap = field("Source (law section)", ["source"], body.source ?? "", false);
    wrap.querySelector("input").placeholder = "e.g. pc-6110";
    wrap.querySelector("input").id = "cf-source";
    wrap.querySelector("label").htmlFor = "cf-source";
    return wrap;
  }

  // the validator speaks code ("will.1.2: answer out of range 5"); staff read which field is wrong and why
  function explainError(raw, body) {
    const text = raw.replace(/^[^:\s]+: /, "");
    const options = ((body.es || {}).options || []).length;
    let m;
    if ((m = text.match(/^answer out of range (-?\d+)$/))) return ["answer", `The correct answer is set to answer ${Number(m[1]) + 1}, but there ${options === 1 ? "is only 1 answer" : `are only ${options} answers`}. Choose one of them.`];
    if (text === "answer must be int") return ["answer", "The correct answer must be one of the answers. Choose one."];
    if (text === "missing answer") return ["answer", "Choose the correct answer."];
    if (text === "truefalse needs a bool") return ["answer", "The correct answer must be True or False."];
    if ((m = text.match(/^unknown source (.+)$/))) return ["source", `"${m[1]}" is not one of the checked law sections. Use a source id from the list the attorney checked.`];
    if (text === "legal item missing source") return ["source", "A legal item needs a source: the law section it is based on."];
    if (text === "missing es/en") return ["", "The Spanish or the English version is missing."];
    if (text === "es/en fields differ") return ["", "The Spanish and the English versions do not have the same fields."];
    if (text === "list lengths differ") return ["", "The Spanish and the English versions have a different number of answers, steps or pairs."];
    if ((m = text.match(/^(\w+) has no answer$/))) return ["", `This kind of item (${KIND_WORDS[m[1]] || m[1]}) cannot have a correct answer.`];
    if ((m = text.match(/^unknown kind (.+)$/))) return ["", `"${m[1]}" is not a kind of item the app knows.`];
    return ["", text];
  }

  function renderDetail(d) {
    const box = document.getElementById("contentDetail");
    document.getElementById("contentHint").hidden = true;
    box.hidden = false;
    box.replaceChildren();
    const [group, sub, kindWord, line] = describe({ entry_id: d.entry_id, kind: d.kind, lesson_id: d.entry_id.split(".")[0] });
    box.appendChild(make("p", { className: "content-where", textContent: [group, sub, kindWord].filter(Boolean).join(" · ") }));
    box.appendChild(make("h2", { textContent: line }));
    box.appendChild(make("p", { className: "muted content-id", textContent: `Entry id: ${d.entry_id}` }));
    const liveV = d.live ? d.live.version : null;
    box.appendChild(make("p", { textContent: liveV === null ? "Not live yet." : `Live: version ${liveV}` }));
    const pend = pendingVersion(d);
    if (pend) box.appendChild(make("p", { textContent: `Waiting: version ${pend.version} (${pend.state === "draft" ? "draft" : "in review"})` }));
    const shownVer = pend || (d.live ? d.versions.find(v => v && v.version === d.live.version) : d.versions[0] || null);
    const shownErrors = shownVer ? (shownVer.errors || []) : [];
    const hasErrors = shownErrors.length > 0;
    const body = (pend ? pend.body : d.live ? d.live.body : d.versions[0] ? d.versions[0].body : null) || {};

    const form = make("div", { className: "content-form" });
    if (body.text !== undefined && body.es === undefined) {
      form.appendChild(field("Text", ["text"], body.text || ""));
    } else if (body.name !== undefined || body.persona !== undefined) {
      const n = body.name || {};
      form.appendChild(pair("Name", (lang) => ["name", lang], (lang) => n[lang] || ""));
      form.appendChild(field("Instructions", ["persona"], body.persona || ""));
    } else if (typeof body.es === "string") {
      form.appendChild(pair("Text", (lang) => [lang], (lang) => body[lang] || ""));
    } else {
      form.append(...itemFields(body));
      const answer = answerField(body), source = sourceField(body, d.legal);
      const extra = make("div", { className: "field-pair" }, ...[answer, source].filter(Boolean));
      if (extra.children.length) form.appendChild(extra);
    }

    if (hasErrors) {
      const general = [];
      shownErrors.forEach((raw, i) => {
        const [where, message] = explainError(raw, body);
        const control = where && form.querySelector(where === "answer" ? "#cf-answer" : "#cf-source");
        if (!control) { general.push(message); return; }
        const note = make("p", { className: "field-error", id: `cf-error-${i}`, textContent: message });
        control.after(note);
        control.setAttribute("aria-invalid", "true");
        control.setAttribute("aria-describedby", [control.getAttribute("aria-describedby"), note.id].filter(Boolean).join(" "));
      });
      const count = shownErrors.length;
      const summary = make("div", { className: "content-errors-box", role: "alert" },
        make("p", { textContent: `${count === 1 ? "1 problem" : `${count} problems`} to fix. You cannot send this for review or publish it until ${count === 1 ? "it is" : "they are"} fixed.` }));
      if (general.length) summary.appendChild(make("ul", { className: "content-errors" }, ...general.map((m) => make("li", { textContent: m }))));
      else summary.appendChild(make("p", { className: "content-errors-where", textContent: "Each problem is shown in red under its field." }));
      box.appendChild(summary);
    }
    box.appendChild(form);

    const btns = make("div", { className: "content-actions" });
    const saveBtn = make("button", { type: "button", className: "btn secondary sm", textContent: "Save draft" });
    const submitBtn = make("button", { type: "button", className: "btn sm", textContent: "Send for review", disabled: hasErrors });
    const previewBtn = make("button", { type: "button", className: "btn secondary sm", textContent: "Preview" });
    btns.append(saveBtn, submitBtn, previewBtn);
    const isAttorney = user() && user().role === "attorney";
    if (d.legal) {
      if (isAttorney && pend) {
        const ab = make("button", { type: "button", className: "btn sm", textContent: `Approve version ${pend.version}`, disabled: hasErrors });
        ab.addEventListener("click", () => approveVersion(pend.version));
        btns.appendChild(ab);
      } else {
        box.appendChild(make("p", { className: "muted", textContent: "Only the attorney can approve and publish this content." }));
      }
    } else if (pend) {
      const pb = make("button", { type: "button", className: "btn sm", textContent: `Publish version ${pend.version}`, disabled: hasErrors });
      pb.addEventListener("click", () => publishVersion(pend.version));
      btns.appendChild(pb);
    }
    box.appendChild(btns);

    saveBtn.addEventListener("click", saveDraft);
    submitBtn.addEventListener("click", submitEntry);
    previewBtn.addEventListener("click", () => previewEntry(pend ? pend.version : (d.live ? d.live.version : 0)));
  }

  function setPath(target, path, value) {
    let node = target;
    path.forEach((key, i) => {
      if (i === path.length - 1) { node[key] = value; return; }
      if (node[key] === undefined) node[key] = typeof path[i + 1] === "number" ? [] : {};
      node = node[key];
    });
  }

  // the same body the editor always saved: { es, en, answer?, source? } for an item, the kind's own shape otherwise
  function collectBody() {
    const box = document.getElementById("contentDetail");
    const pend = pendingVersion(currentDetail);
    const orig = (pend ? pend.body : currentDetail.live ? currentDetail.live.body : null) || {};
    const body = {};
    for (const input of box.querySelectorAll("[data-path]")) {
      const path = JSON.parse(input.dataset.path);
      if (path[0] === "source") { if (input.value.trim()) body.source = input.value.trim(); continue; }
      setPath(body, path, input.value);
    }
    if (orig.source !== undefined && !box.querySelector("#cf-source")) body.source = orig.source;
    const answer = box.querySelector("#cf-answer");
    if (answer) {
      if (answer.value === "keep") body.answer = orig.answer;
      else if (answer.value === "true" || answer.value === "false") body.answer = answer.value === "true";
      else if (answer.value !== "") body.answer = Number(answer.value);
    } else if (orig.answer !== undefined) body.answer = orig.answer;
    return body;
  }

  async function saveDraft() {
    try {
      await api(`/staff/content/${currentEntry}/draft`, "PUT", { body: collectBody() });
      setStatus("Draft saved.");
      await openEntry(currentEntry);
    } catch (e) { handleErr(e); }
  }
  async function submitEntry() {
    try { await api(`/staff/content/${currentEntry}/submit`, "POST"); setStatus("Sent for review."); await openEntry(currentEntry); }
    catch (e) { handleErr(e); }
  }
  async function approveVersion(v) {
    try { await api(`/staff/content/${currentEntry}/approve`, "POST", { version: v }); setStatus(`Version ${v} approved and live.`); await openEntry(currentEntry); }
    catch (e) { handleErr(e); }
  }
  async function publishVersion(v) {
    try { await api(`/staff/content/${currentEntry}/publish`, "POST", { version: v }); setStatus(`Version ${v} is live.`); await openEntry(currentEntry); }
    catch (e) { handleErr(e); }
  }
  // the preview shows the client's text as the app shows it: in Spanish
  async function previewEntry(v) {
    const box = document.querySelector(".content-preview");
    let data;
    try { data = await api(`/staff/content/${currentEntry}/preview?version=${v}&lang=es`); }
    catch (e) { handleErr(e); return; }
    let txt = "";
    if (data.text !== undefined) txt = data.text;
    else {
      const item = data.item || {};
      for (const k of Object.keys(item)) txt += `${k}: ${item[k]}\n`;
      if (data.explain) txt += `explain: ${data.explain}`;
    }
    box.replaceChildren(make("h3", { textContent: "Preview (as the client sees it, in Spanish)" }), make("pre", { textContent: txt }));
  }
  function handleErr(e) {
    let j = null;
    try { j = JSON.parse(e.body); } catch (_) { /* not JSON */ }
    const missing = (list) => list.map((l) => LANG[l] || l).join(" and ");
    let msg = "";
    if (j && j.error === "languages") msg = `Both languages are needed. Missing: ${missing(j.missing)}.`;
    else if (j && j.error === "placeholders") msg = `The instructions must keep these placeholders: ${j.missing.join(", ")}.`;
    else if (j && j.error === "invalid") msg = "This version has problems. Fix the fields marked in red first.";
    else if (j && j.error === "no_draft") msg = "There is no draft to send. Save a draft first.";
    else if (j && j.error === "bad_shape") msg = "This content does not have the shape the app expects. Nothing was saved.";
    else if (e.status === 403) msg = "Your account cannot do this.";
    else if (e.status === 404) msg = "This entry no longer exists. Reload the list.";
    else if (e.status && e.status < 500 && j && typeof j.detail === "string") msg = j.detail;
    if (!msg) msg = e.status >= 500 || !e.status ? "The server had a problem. Try again in a minute." : "That did not work. Try again.";
    setStatus(msg);
  }

  document.addEventListener("DOMContentLoaded", () => {
    const sel = document.getElementById("contentKind");
    if (sel) sel.addEventListener("change", loadEntries);
    loadEntries();
  });
})();
