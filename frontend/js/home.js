// Главная: поиск, подсказки, выдача.
(function () {
  const { $, esc, param, debounce, card, skeletons, emptyState, trackClicks, mountLayout } = UI;
  mountLayout("home");

  const form = $("#search-form"), input = $("#q"), box = $("#suggest");
  const grid = $("#results"), title = $("#results-title"), meta = $("#results-meta");
  const compareLink = $("#compare-link"), modeBox = $("#mode");

  let mode = param("mode") === "baseline" ? "baseline" : "smart";
  let currentQuery = "";
  let sug = [], active = -1, reqId = 0, sugId = 0;

  // ---------- Режим поиска ----------
  function paintMode() {
    modeBox.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.mode === mode)));
  }
  modeBox.addEventListener("click", (e) => {
    const b = e.target.closest("button[data-mode]");
    if (!b || b.dataset.mode === mode) return;
    mode = b.dataset.mode;
    paintMode();
    if (currentQuery) runSearch(currentQuery);
  });

  // ---------- Примеры запросов ----------
  $("#chips").innerHTML = APP_CONFIG.EXAMPLE_QUERIES.map((q) => `<button type="button" class="chip">${esc(q)}</button>`).join("");
  $("#chips").addEventListener("click", (e) => {
    const c = e.target.closest(".chip");
    if (!c) return;
    input.value = c.textContent;
    hideSuggest();
    runSearch(c.textContent);
  });

  // ---------- Подсказки ----------
  function hideSuggest() {
    box.hidden = true; active = -1; input.setAttribute("aria-expanded", "false"); input.removeAttribute("aria-activedescendant");
  }
  function highlight(text, q) {
    const i = text.toLowerCase().indexOf(q.toLowerCase());
    if (i < 0) return esc(text);
    return esc(text.slice(0, i)) + "<mark>" + esc(text.slice(i, i + q.length)) + "</mark>" + esc(text.slice(i + q.length));
  }
  function renderSuggest(q) {
    if (!sug.length) return hideSuggest();
    box.innerHTML = sug.map((s, i) => `<li role="option" id="s-${i}" data-i="${i}" aria-selected="false">${highlight(s, q)}</li>`).join("");
    box.hidden = false; active = -1;
    input.setAttribute("aria-expanded", "true");
  }
  function setActive(i) {
    const items = box.querySelectorAll("li");
    items.forEach((li, k) => li.setAttribute("aria-selected", String(k === i)));
    active = i;
    if (i >= 0) input.setAttribute("aria-activedescendant", "s-" + i); else input.removeAttribute("aria-activedescendant");
  }
  const loadSuggest = debounce(async () => {
    const q = input.value.trim();
    if (q.length < 2) { sug = []; return hideSuggest(); }
    const id = ++sugId;
    try {
      const list = await Api.suggestions(q);
      if (id !== sugId) return;
      sug = list.slice(0, 8);
      renderSuggest(q);
    } catch (_) { hideSuggest(); }
  }, 180);

  input.addEventListener("input", loadSuggest);
  input.addEventListener("keydown", (e) => {
    if (box.hidden) return;
    if (e.key === "ArrowDown") { e.preventDefault(); setActive((active + 1) % sug.length); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActive((active - 1 + sug.length) % sug.length); }
    else if (e.key === "Escape") hideSuggest();
    else if (e.key === "Enter" && active >= 0) {
      e.preventDefault();
      input.value = sug[active];
      hideSuggest();
      runSearch(sug[active]);
    }
  });
  box.addEventListener("mousedown", (e) => {
    const li = e.target.closest("li[data-i]");
    if (!li) return;
    e.preventDefault();
    input.value = sug[Number(li.dataset.i)];
    hideSuggest();
    runSearch(input.value);
  });
  document.addEventListener("click", (e) => { if (!e.target.closest(".search-field")) hideSuggest(); });

  // ---------- Поиск ----------
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    hideSuggest();
    runSearch(input.value.trim());
  });

  function updateUrl(q) {
    const u = new URL(location.href);
    q ? u.searchParams.set("q", q) : u.searchParams.delete("q");
    mode === "baseline" ? u.searchParams.set("mode", "baseline") : u.searchParams.delete("mode");
    history.replaceState(null, "", u);
  }

  async function runSearch(q) {
    if (!q) return showFeatured();
    currentQuery = q;
    updateUrl(q);
    compareLink.href = "compare.html?q=" + encodeURIComponent(q);
    title.textContent = "Результаты по запросу «" + q + "»";
    meta.textContent = "";
    grid.innerHTML = skeletons(6);
    const id = ++reqId;
    try {
      const r = await Api.search(q, mode);
      if (id !== reqId) return;
      meta.textContent = `Найдено: ${r.total}. Время ответа: ${r.tookMs} мс. Режим: ${mode === "smart" ? "умный поиск" : "обычный поиск"}`;
      if (!r.items.length) {
        const extra = mode === "baseline" ? '<button class="btn btn-ghost" id="to-smart" type="button">Попробовать умный поиск</button>' : "";
        grid.innerHTML = emptyState("Ничего не нашлось", "Проверьте написание или попробуйте другое название. Примеры запросов есть под строкой поиска.", extra);
        const b = $("#to-smart");
        if (b) b.addEventListener("click", () => { mode = "smart"; paintMode(); runSearch(q); });
      } else {
        grid.innerHTML = r.items.map((p, i) => card(p, { query: q, position: i + 1 })).join("");
      }
      Api.event({ type: "search", query: q, mode, results_count: r.items.length });
    } catch (err) {
      if (id !== reqId) return;
      grid.innerHTML = emptyState("Не удалось выполнить поиск", "Сервер не ответил. Проверьте подключение и повторите запрос.", '<button class="btn btn-ghost" id="retry" type="button">Повторить</button>');
      $("#retry").addEventListener("click", () => runSearch(q));
    }
  }

  async function showFeatured() {
    currentQuery = "";
    updateUrl("");
    compareLink.href = "compare.html";
    title.textContent = "Популярные товары";
    meta.textContent = "";
    grid.innerHTML = skeletons(6);
    try {
      const r = await Api.search(APP_CONFIG.USE_MOCK ? "" : "антивирус", "smart", 12);
      grid.innerHTML = r.items.length ? r.items.map((p, i) => card(p, { position: i + 1 })).join("") : "";
    } catch (_) {
      grid.innerHTML = emptyState("Каталог пока недоступен", "Введите запрос в строку поиска или попробуйте позже.");
    }
  }

  trackClicks(grid, () => ({ query: currentQuery || null, mode }));

  // ---------- Старт ----------
  paintMode();
  const initial = param("q");
  if (initial) { input.value = initial; runSearch(initial); } else showFeatured();
})();
