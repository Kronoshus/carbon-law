
const REVIEW_API = "https://carbon-law.onrender.com";
function reviewAuthHeaders() { const t = (window.CarbonAuth && window.CarbonAuth.getToken) ? window.CarbonAuth.getToken() : localStorage.getItem("carbon_token"); return t ? { "Authorization": "Bearer " + t, "Content-Type": "application/json" } : { "Content-Type": "application/json" }; }
async function reviewFetch(path, method="GET", body=null) {
  const opts = { method, headers: reviewAuthHeaders() };
  if (body) opts.body = JSON.stringify(body);
  let res;
  try { res = await fetch(REVIEW_API + path, opts); }
  catch (_) { throw new Error("Could not reach the server. Try again."); }
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    if (res.status < 500 && typeof data.detail === "string") throw new Error(data.detail);
    throw new Error("The server had a problem. Try again in a minute.");
  }
  return res;
}
function formatReviewDate(value) {
  const date = new Date(String(value || "").slice(0, 10) + "T00:00:00");
  return Number.isNaN(date.getTime()) ? String(value || "") : date.toLocaleDateString("en-US", { dateStyle: "long" });
}
function appendInline(el, text) {
  // **bold** is the only inline markup a draft uses
  for (const piece of text.split(/(\*\*[^*]+\*\*)/g)) {
    if (!piece) continue;
    const bold = piece.match(/^\*\*([^*]+)\*\*$/);
    if (bold) { const strong = document.createElement("strong"); strong.textContent = bold[1]; el.appendChild(strong); }
    else el.appendChild(document.createTextNode(piece));
  }
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
    // an item has text inside the brackets; the notice's bare "[ATTORNEY TO COMPLETE]" is not an item
    const parts = text.split(/(\[ATTORNEY TO (?:COMPLETE|CONFIRM)[^\]]+\])/g);
    for (const part of parts) {
      const m = part.match(/^\[ATTORNEY TO (COMPLETE|CONFIRM)/);
      if (m) {
        const mark = document.createElement("mark");
        mark.className = m[1].toLowerCase() === "complete" ? "complete" : "confirm";
        mark.textContent = part;
        el.appendChild(mark);
      } else if (part) {
        appendInline(el, part);
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
    if (!data.length) {
      const tr = document.createElement("tr"); tr.className = "empty-row";
      const td = document.createElement("td"); td.colSpan = 2; td.textContent = "No drafts are waiting for review.";
      tr.appendChild(td); rows.appendChild(tr);
    }
    for (const item of data) {
      const tr = document.createElement("tr");
      const td = document.createElement("td");
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "btn secondary sm";
      btn.textContent = item.client_name;
      btn.addEventListener("click", () => openReview(item));
      td.appendChild(btn);
      if (item.late) {
        const span = document.createElement("span");
        span.className = "late-label";
        span.textContent = "Late";
        td.appendChild(span);
      }
      tr.appendChild(td);
      const td2 = document.createElement("td");
      td2.textContent = item.due ? formatReviewDate(item.due) : "";
      tr.appendChild(td2);
      rows.appendChild(tr);
    }
  } catch (e) {
    const msg = document.getElementById("reviewMessage");
    if (msg) { msg.className = "error-message"; msg.textContent = "Could not load the review queue. " + e.message; }
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
      // download, on its own row under the draft
      const tools = document.createElement("div");
      tools.className = "draft-tools";
      const dl = document.createElement("button");
      dl.type = "button"; dl.className = "btn secondary sm"; dl.textContent = "Download .docx";
      dl.addEventListener("click", async () => {
        const r = await reviewFetch("/staff/drafts/" + doc.id + "/docx");
        const blob = await r.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url; a.download = doc.name + ".docx"; a.click();
        URL.revokeObjectURL(url);
      });
      tools.appendChild(dl);
      card.appendChild(tools);
      // upload
      const taLabel = document.createElement("label");
      taLabel.htmlFor = "draft-" + doc.id; taLabel.textContent = "Corrected text";
      card.appendChild(taLabel);
      const ta = document.createElement("textarea");
      ta.id = "draft-" + doc.id;
      ta.value = d.content;
      card.appendChild(ta);
      const saveBtn = document.createElement("button");
      saveBtn.type = "button"; saveBtn.className = "btn sm"; saveBtn.textContent = "Upload corrected version";
      saveBtn.addEventListener("click", async () => {
        await reviewFetch("/staff/drafts/" + doc.id + "/versions", "POST", { content: ta.value });
        await openReview(item);
      });
      card.appendChild(saveBtn);
    } catch (e) { draftWrap.className = "error-message"; draftWrap.textContent = "Could not open this draft. " + e.message; }
    detail.appendChild(card);
  }
  // approve / changes controls
  const controls = document.createElement("div");
  controls.className = "card";
  const actions = document.createElement("div");
  actions.className = "review-actions";
  const noteLabel = document.createElement("label");
  noteLabel.htmlFor = "reviewDraftNote"; noteLabel.textContent = "Note when requesting changes";
  const note = document.createElement("textarea");
  note.id = "reviewDraftNote";
  const reqBtn = document.createElement("button");
  reqBtn.type = "button"; reqBtn.className = "btn secondary"; reqBtn.textContent = "Request changes";
  reqBtn.addEventListener("click", async () => {
    await reviewFetch("/staff/journeys/" + item.journey_id + "/review", "POST", { decision: "changes", note: note.value });
    await loadReviewQueue();
  });
  const apprBtn = document.createElement("button");
  apprBtn.type = "button"; apprBtn.className = "btn"; apprBtn.textContent = "Approve";

  apprBtn.addEventListener("click", async () => {
    const msg = document.getElementById("reviewMessage");
    try {
      await reviewFetch("/staff/journeys/" + item.journey_id + "/review", "POST", { decision: "approve" });
    } catch (e) {                                   // e.g. a cited section that is not on the verified list
      if (msg) msg.textContent = String(e.message || e);
      return;
    }
    if (msg) msg.textContent = "";
    await loadReviewQueue();
    detail.hidden = true;
  });
  controls.appendChild(noteLabel);
  controls.appendChild(note);
  actions.appendChild(reqBtn);
  actions.appendChild(apprBtn);
  // approval waits for every [ATTORNEY TO COMPLETE] item in these drafts; say why when it is blocked
  const open = detail.querySelectorAll(".draft mark.complete").length;
  apprBtn.disabled = open > 0;
  if (open) {
    const why = document.createElement("p");
    why.textContent = `Complete the ${open === 1 ? "yellow [ATTORNEY TO COMPLETE] item" : `${open} yellow [ATTORNEY TO COMPLETE] items`} to approve.`;
    actions.appendChild(why);
  }
  controls.appendChild(actions);
  detail.appendChild(controls);
}

function initReview() {
  loadReviewQueue();
}
if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initReview);
else initReview();
window.addEventListener("hashchange", () => { if (location.hash === "#review") loadReviewQueue(); });
