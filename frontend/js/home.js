// Главная: поиск, подсказки, основная выдача, альтернативы, рекомендации.
(function () {
  const { $, esc, param, debounce, card, skeletons, emptyState, errorState, trackClicks, mountLayout } = UI;
  mountLayout("home");

  const PAGE = Math.min(20, APP_CONFIG.PAGE_SIZE || 20);
  const form = $("#search-form"), input = $("#q"), box = $("#suggest");
  const grid = $("#results"), title = $("#results-title"), meta = $("#results-meta");
  const notice = $("#notice"), moreWrap = $("#more-wrap"), moreBtn = $("#more");
  const altSec = $("#alt-section"), alts = $("#alts"), recSec = $("#rec-section"), recs = $("#recs");
  const compareLink = $("#compare-link"), modeBox = $("#mode");

  let mode = param("mode") === "baseline" ? "baseline" : "smart";
  let currentQuery = "", limit = PAGE;
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
    box.querySelectorAll("li").forEach((li, k) => li.setAttribute("aria-selected", String(k === i)));
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
    } catch (_) { hideSuggest(); } // подсказки необязательны: тихо скрываем
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

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    hideSuggest();
    runSearch(input.value.trim());
  });

  // ---------- Вспомогательное ----------
  function updateUrl(q) {
    const u = new URL(location.href);
    q ? u.searchParams.set("q", q) : u.searchParams.delete("q");
    mode === "baseline" ? u.searchParams.set("mode", "baseline") : u.searchParams.delete("mode");
    history.replaceState(null, "", u);
  }

  function resetExtras() {
    notice.hidden = true; notice.innerHTML = "";
    moreWrap.hidden = true; // API не поддерживает offset-пагинацию: не показываем кнопку, которая повторяла бы те же товары.
    altSec.hidden = true; alts.innerHTML = "";
    recSec.hidden = true; recs.innerHTML = "";
  }

  // Плашка: исправление запроса + определённая задача и категории
  function renderNotice(r, q) {
    const parts = [];
    if (r.correctedQuery) {
      parts.push(`<p>Мы исправили запрос: показываем результаты по «<strong>${esc(r.correctedQuery)}</strong>». Вы искали «${esc(q)}».</p>`);
    }
    if (r.note) parts.push(`<p class="notice-sub">${esc(r.note)}</p>`);
    if (mode === "smart" && (r.intent || r.categories.length)) {
      const bits = [];
      if (r.intent) bits.push("Что поняли: " + esc(r.intent));
      if (r.categories.length) bits.push("Ищем в категориях: " + r.categories.map(esc).join(", "));
      parts.push(`<p class="notice-sub">${bits.join(". ")}.</p>`);
    }
    notice.innerHTML = parts.join("");
    notice.hidden = !parts.length;
    notice.classList.toggle("notice-fix", !!r.correctedQuery);
  }

  // ---------- Поиск ----------
  async function runSearch(q, { more = false } = {}) {
    if (!q) return showFeatured();
    if (!more) { limit = PAGE; resetExtras(); grid.innerHTML = skeletons(6); meta.textContent = ""; }
    currentQuery = q;
    updateUrl(q);
    compareLink.href = "compare.html?q=" + encodeURIComponent(q);
    title.textContent = "Результаты по запросу «" + q + "»";
    const id = ++reqId;
    if (more) { moreBtn.disabled = true; moreBtn.textContent = "Загружаем…"; }

    try {
      const r = await Api.search(q, mode, limit);
      if (id !== reqId) return;
      meta.textContent = `Найдено: ${r.total}. Время ответа: ${r.tookMs} мс. Режим: ${mode === "smart" ? "умный поиск" : "обычный поиск"}`;
      renderNotice(r, q);

      if (!r.items.length && !r.alternatives.length) {
        const extra = mode === "baseline" ? '<button class="btn btn-ghost" id="to-smart" type="button">Попробовать умный поиск</button>' : "";
        grid.innerHTML = emptyState("Ничего не нашлось", "Проверьте написание или попробуйте другое название. Примеры запросов есть под строкой поиска.", extra);
        const b = $("#to-smart");
        if (b) b.addEventListener("click", () => { mode = "smart"; paintMode(); runSearch(q); });
      } else if (!r.items.length) {
        grid.innerHTML = emptyState("Точных совпадений нет", "Зато есть похожие товары, они показаны ниже.");
      } else {
        grid.innerHTML = r.items.map((p, i) => card(p, { query: q, searchId: r.searchId, position: i + 1 })).join("");
      }

      // Кнопка «Показать ещё»
      moreWrap.hidden = true; // У API поиска нет offset-параметра; повторный запрос не является следующей страницей.
      moreBtn.disabled = false; moreBtn.textContent = "Показать ещё";

      // Альтернативы и рекомендации
      if (r.alternatives.length) {
        alts.innerHTML = r.alternatives.map((p, i) => card(p, { query: q, searchId: r.searchId, position: i + 1 })).join("");
        altSec.hidden = false;
      } else { altSec.hidden = true; }
      if (r.recommendations.length) {
        recs.innerHTML = r.recommendations.map((p, i) => card(p, { query: q, searchId: r.searchId, position: i + 1 })).join("");
        recSec.hidden = false;
      } else { recSec.hidden = true; }

      if (!more) Api.event({ type: "search", query: q, mode, results_count: r.items.length, corrected_query: r.correctedQuery, search_id: r.searchId });
    } catch (err) {
      if (id !== reqId) return;
      if (more) { limit -= PAGE; moreBtn.disabled = false; moreBtn.textContent = "Показать ещё"; return; }
      errorState(err, grid, () => runSearch(q));
    }
  }

  // Пагинация намеренно отключена: текущие эндпоинты поиска не поддерживают offset.
  moreBtn.hidden = true;

  async function showFeatured() {
    currentQuery = "";
    resetExtras();
    updateUrl("");
    compareLink.href = "compare.html";
    title.textContent = "Популярные товары";
    meta.textContent = "";
    grid.innerHTML = skeletons(6);
    try {
      const r = await Api.search(APP_CONFIG.USE_MOCK ? "" : "антивирус", "smart", 12, { log: false });
      grid.innerHTML = r.items.length ? r.items.map((p, i) => card(p, { position: i + 1 })).join("") : "";
    } catch (err) {
      errorState(err, grid, showFeatured);
    }
  }

  trackClicks(grid, () => ({ query: currentQuery || null, mode, source: "results" }));
  trackClicks(alts, () => ({ query: currentQuery || null, mode, source: "alternatives" }));
  trackClicks(recs, () => ({ query: currentQuery || null, mode, source: "recommendations" }));

  // ---------- Старт ----------
  paintMode();
  const initial = param("q");
  if (initial) { input.value = initial; runSearch(initial); } else showFeatured();
})();
