
const REVIEW_API = "https://carbon-law.onrender.com";
function reviewAuthHeaders() { const t = (window.CarbonAuth && window.CarbonAuth.getToken) ? window.CarbonAuth.getToken() : localStorage.getItem("carbon_token"); return t ? { "Authorization": "Bearer " + t, "Content-Type": "application/json" } : { "Content-Type": "application/json" }; }
async function reviewFetch(path, method="GET", body=null) {
  const opts = { method, headers: reviewAuthHeaders() };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(REVIEW_API + path, opts);
  if (!res.ok) throw new Error(await res.text());
  return res;
}

function renderDraftContent(container, content) {
  container.replaceChildren();
  const draft = document.createElement("div");
  draft.className = "draft";
  const lines = String(content || "").split(/\n/);
  for (const line of lines) {
    if (line.trim() === "") continue;
    let el;
    if (line.startsWith("## ")) { el = document.createElement("h3"); }
    else if (line.startsWith("# ")) { el = document.createElement("h2"); }
    else { el = document.createElement("p"); }
    const text = line.replace(/^#{1,2}\s*/, "");
    // split markers
    const parts = text.split(/(\[ATTORNEY TO (?:COMPLETE|CONFIRM)[^\]]*\])/g);
    for (const part of parts) {
      const m = part.match(/^\[ATTORNEY TO (COMPLETE|CONFIRM)/);
      if (m) {
        const mark = document.createElement("mark");
        mark.className = m[1].toLowerCase() === "complete" ? "complete" : "confirm";
        mark.textContent = part;
        el.appendChild(mark);
      } else if (part) {
        el.appendChild(document.createTextNode(part));
      }
    }
    draft.appendChild(el);
  }
  container.appendChild(draft);
  return draft;
}

async function loadReviewQueue() {
  const rows = document.getElementById("reviewQueueRows");
  if (!rows) return;
  rows.replaceChildren();
  try {
    const res = await reviewFetch("/staff/review-queue");
    const data = await res.json();
    for (const item of data) {
      const tr = document.createElement("tr");
      const td = document.createElement("td");
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "btn sm";
      btn.textContent = item.client_name;
      btn.addEventListener("click", () => openReview(item));
      td.appendChild(btn);
      if (item.late) {
        const span = document.createElement("span");
        span.style.color = "red";
        span.textContent = " ⚠";
        td.appendChild(span);
      }
      tr.appendChild(td);
      const td2 = document.createElement("td");
      td2.textContent = item.due || "";
      tr.appendChild(td2);
      rows.appendChild(tr);
    }
  } catch (e) {
    const msg = document.getElementById("reviewMessage");
    if (msg) msg.textContent = String(e);
  }
}

let currentReviewItem = null;
async function openReview(item) {
  currentReviewItem = item;
  const detail = document.getElementById("reviewDetail");
  if (!detail) return;
  detail.hidden = false;
  const title = document.getElementById("reviewTitle");
  if (title) title.textContent = item.client_name;
  detail.replaceChildren();
  // buttons container
  for (const doc of item.documents) {
    const card = document.createElement("div");
    card.className = "card";
    const h = document.createElement("h3");
    h.textContent = doc.name + " v" + doc.version;
    card.appendChild(h);
    const draftWrap = document.createElement("div");
    card.appendChild(draftWrap);
    try {
      const res = await reviewFetch("/staff/drafts/" + doc.id);
      const d = await res.json();
      const draft = renderDraftContent(draftWrap, d.content);
      // download
      const dl = document.createElement("button");
      dl.type = "button"; dl.className = "btn secondary sm"; dl.textContent = "Descargar .docx";
      dl.addEventListener("click", async () => {
        const r = await reviewFetch("/staff/drafts/" + doc.id + "/docx");
        const blob = await r.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url; a.download = doc.name + ".docx"; a.click();
        URL.revokeObjectURL(url);
      });
      card.appendChild(dl);
      // upload
      const ta = document.createElement("textarea");
      ta.value = d.content;
      card.appendChild(ta);
      const saveBtn = document.createElement("button");
      saveBtn.type = "button"; saveBtn.className = "btn sm"; saveBtn.textContent = "Subir versión corregida";
      saveBtn.addEventListener("click", async () => {
        await reviewFetch("/staff/drafts/" + doc.id + "/versions", "POST", { content: ta.value });
        await openReview(item);
      });
      card.appendChild(saveBtn);
    } catch (e) { draftWrap.textContent = String(e); }
    detail.appendChild(card);
  }
  // approve / changes controls
  const controls = document.createElement("div");
  const note = document.createElement("textarea");
  note.id = "reviewNote";
  const reqBtn = document.createElement("button");
  reqBtn.type = "button"; reqBtn.className = "btn secondary"; reqBtn.textContent = "Pedir cambios";
  reqBtn.addEventListener("click", async () => {
    await reviewFetch("/staff/journeys/" + item.journey_id + "/review", "POST", { decision: "changes", note: note.value });
    await loadReviewQueue();
  });
  const apprBtn = document.createElement("button");
  apprBtn.type = "button"; apprBtn.className = "btn"; apprBtn.textContent = "Aprobar";
  apprBtn.id = "approveDrafts";
  // disable if any mark.complete
  setTimeout(() => {
    const hasComplete = !!document.querySelector(".draft mark.complete");
    apprBtn.disabled = hasComplete;
  }, 0);
  apprBtn.addEventListener("click", async () => {
    await reviewFetch("/staff/journeys/" + item.journey_id + "/review", "POST", { decision: "approve" });
    await loadReviewQueue();
    detail.hidden = true;
  });
  controls.appendChild(note);
  controls.appendChild(reqBtn);
  controls.appendChild(apprBtn);
  detail.appendChild(controls);
  // disable approve based on current DOM
  const hasComplete = !!document.querySelector(".draft mark.complete");
  apprBtn.disabled = hasComplete;
}

function initReview() {
  loadReviewQueue();
}
if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initReview);
else initReview();
window.addEventListener("hashchange", () => { if (location.hash === "#review") loadReviewQueue(); });
