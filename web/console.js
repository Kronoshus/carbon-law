// The staff dashboard's screens: one screen per hash route (admin.html#review), a side menu that marks where you are and
// folds behind a Menu button on phones, and table rows that restack as labelled cards on phones.
(() => {
  const screens = [...document.querySelectorAll(".screen")];
  const names = screens.map((s) => s.dataset.screen);
  // earlier links used the Spanish section names and the old in-page anchors
  const OLD_ROUTES = { contenido: "content", personajes: "characters", analitica: "analytics", firma: "firm", clientes: "clients",
    workQueue: "queue", communications: "contacts", reportsRecords: "reports", practiceLibrary: "library" };
  const sidebar = document.getElementById("consoleSidebar");
  const menuButton = document.getElementById("menuButton");
  const navLinks = [...document.querySelectorAll('#consoleNav a[href^="#"]')];

  function setMenu(open) {
    sidebar.classList.toggle("menu-open", open);
    menuButton.setAttribute("aria-expanded", String(open));
  }

  function showScreen(moveFocus) {
    let name = location.hash.slice(1);
    if (OLD_ROUTES[name]) { name = OLD_ROUTES[name]; history.replaceState(null, "", "#" + name); }
    if (!names.includes(name)) name = "queue";
    let heading = null;
    for (const screen of screens) {
      screen.hidden = screen.dataset.screen !== name;
      if (!screen.hidden) heading = screen.querySelector("h1");
    }
    for (const link of navLinks) {
      const here = link.getAttribute("href") === "#" + name;
      link.classList.toggle("active", here);
      if (here) link.setAttribute("aria-current", "page"); else link.removeAttribute("aria-current");
    }
    document.title = `${heading.textContent} | Staff dashboard | Carbon Law Group`;
    setMenu(false);
    if (moveFocus) { window.scrollTo(0, 0); heading.focus({ preventScroll: true }); }
  }

  // each cell carries its column name, which the phone layout prints beside the value
  function labelCells(table) {
    const heads = [...table.querySelectorAll("thead th")].map((th) => th.textContent.trim());
    for (const row of table.tBodies[0]?.rows || []) {
      [...row.cells].forEach((cell, i) => { if (!cell.colSpan || cell.colSpan === 1) cell.dataset.label = heads[i] || ""; });
    }
  }
  const cardTables = [...document.querySelectorAll("table.cards")];
  const observer = new MutationObserver(() => cardTables.forEach(labelCells));
  cardTables.forEach((table) => { labelCells(table); observer.observe(table, { childList: true, subtree: true }); });

  menuButton.addEventListener("click", () => setMenu(!sidebar.classList.contains("menu-open")));
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && sidebar.classList.contains("menu-open")) { setMenu(false); menuButton.focus(); }
  });
  window.addEventListener("hashchange", () => showScreen(true));
  showScreen(false);
})();
