// Главная: поиск, подсказки, основная выдача,
// альтернативы, рекомендации и популярные товары.
(function () {
  const {
    $, esc, param, debounce, card, skeletons,
    emptyState, errorState, trackClicks, mountLayout
  } = UI;

  mountLayout("home");

  const PAGE = Math.min(20, APP_CONFIG.PAGE_SIZE || 20);

  const form = $("#search-form");
  const input = $("#q");
  const box = $("#suggest");

  const grid = $("#results");
  const title = $("#results-title");
  const meta = $("#results-meta");

  const notice = $("#notice");
  const moreWrap = $("#more-wrap");
  const moreBtn = $("#more");

  const altSec = $("#alt-section");
  const alts = $("#alts");

  const recSec = $("#rec-section");
  const recs = $("#recs");

  const compareLink = $("#compare-link");
  const modeBox = $("#mode");

  let mode = param("mode") === "baseline"
    ? "baseline"
    : "smart";

  let currentQuery = "";
  let limit = PAGE;

  let sug = [];
  let active = -1;
  let reqId = 0;
  let sugId = 0;

  // ---------- Режим поиска ----------

  function paintMode() {
    modeBox.querySelectorAll("button").forEach((b) => {
      b.setAttribute(
        "aria-pressed",
        String(b.dataset.mode === mode)
      );
    });
  }

  modeBox.addEventListener("click", (e) => {
    const b = e.target.closest("button[data-mode]");

    if (!b || b.dataset.mode === mode) return;

    mode = b.dataset.mode;
    paintMode();

    if (currentQuery) runSearch(currentQuery);
  });

  // ---------- Примеры запросов ----------

  $("#chips").innerHTML = APP_CONFIG.EXAMPLE_QUERIES
    .map((q) => `
      <button type="button" class="chip">
        ${esc(q)}
      </button>
    `).join("");

  $("#chips").addEventListener("click", (e) => {
    const c = e.target.closest(".chip");

    if (!c) return;

    input.value = c.textContent.trim();

    hideSuggest();
    runSearch(input.value);
  });

  // ---------- Подсказки ----------

  function hideSuggest() {
    sugId++;
    box.hidden = true;
    active = -1;

    input.setAttribute("aria-expanded", "false");
    input.removeAttribute("aria-activedescendant");
  }

  function highlight(text, q) {
    const i = text.toLowerCase().indexOf(q.toLowerCase());

    if (i < 0) return esc(text);

    return esc(text.slice(0, i))
      + "<mark>"
      + esc(text.slice(i, i + q.length))
      + "</mark>"
      + esc(text.slice(i + q.length));
  }

  function renderSuggest(q) {
    if (!sug.length) return hideSuggest();

    box.innerHTML = sug.map((s, i) => `
      <li
        role="option"
        id="s-${i}"
        data-i="${i}"
        aria-selected="false"
      >
        ${highlight(s, q)}
      </li>
    `).join("");

    box.hidden = false;
    active = -1;

    input.setAttribute("aria-expanded", "true");
  }

  function setActive(i) {
    box.querySelectorAll("li").forEach((li, k) => {
      li.setAttribute("aria-selected", String(k === i));
    });

    active = i;

    if (i >= 0) {
      input.setAttribute("aria-activedescendant", "s-" + i);
    } else {
      input.removeAttribute("aria-activedescendant");
    }
  }

  const loadSuggest = debounce(async () => {
    const q = input.value.trim();

    if (q.length < 2) {
      sug = [];
      return hideSuggest();
    }

    const id = ++sugId;

    try {
      const list = await Api.suggestions(q);

      if (id !== sugId || input.value.trim() !== q) return;

      sug = list.slice(0, 8);
      renderSuggest(q);

    } catch (_) {
      if (id === sugId) hideSuggest();
    }
  }, 180);

  input.addEventListener("input", loadSuggest);

  input.addEventListener("keydown", (e) => {
    if (box.hidden || !sug.length) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((active + 1) % sug.length);

    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((active - 1 + sug.length) % sug.length);

    } else if (e.key === "Escape") {
      hideSuggest();

    } else if (e.key === "Enter" && active >= 0) {
      e.preventDefault();

      input.value = sug[active];

      hideSuggest();
      runSearch(input.value);
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

  document.addEventListener("click", (e) => {
    if (!e.target.closest(".search-field")) {
      hideSuggest();
    }
  });

  form.addEventListener("submit", (e) => {
    e.preventDefault();

    hideSuggest();
    runSearch(input.value.trim());
  });

  // ---------- Вспомогательные функции ----------

  function updateUrl(q) {
    const u = new URL(location.href);

    if (q) {
      u.searchParams.set("q", q);
    } else {
      u.searchParams.delete("q");
    }

    if (mode === "baseline") {
      u.searchParams.set("mode", "baseline");
    } else {
      u.searchParams.delete("mode");
    }

    history.replaceState(null, "", u);
  }

  function resetExtras() {
    notice.hidden = true;
    notice.innerHTML = "";

    moreWrap.hidden = true;

    altSec.hidden = true;
    alts.innerHTML = "";

    recSec.hidden = true;
    recs.innerHTML = "";
  }

  // Исправление запроса, пояснения и намерение.

  function renderNotice(r, q) {
    const parts = [];
    const categories = r.categories ?? [];

    if (r.correctedQuery) {
      parts.push(`
        <p>
          Мы исправили запрос:
          показываем результаты по
          «<strong>${esc(r.correctedQuery)}</strong>».
          Вы искали «${esc(q)}».
        </p>
      `);
    }

    if (r.note) {
      parts.push(`
        <p class="notice-sub">${esc(r.note)}</p>
      `);
    }

    if (mode === "smart" && (r.intent || categories.length)) {
      const bits = [];

      if (r.intent) {
        bits.push("Что поняли: " + esc(r.intent));
      }

      if (categories.length) {
        bits.push(
          "Ищем в категориях: "
          + categories.map(esc).join(", ")
        );
      }

      parts.push(`
        <p class="notice-sub">${bits.join(". ")}.</p>
      `);
    }

    notice.innerHTML = parts.join("");
    notice.hidden = !parts.length;

    notice.classList.toggle(
      "notice-fix",
      !!r.correctedQuery
    );
  }

  // Популярные товары не являются совпадениями.

  function renderPopular(items, q, searchId) {
    if (!items.length) return "";

    return `
      <section
        class="popular-fallback"
        style="grid-column: 1 / -1"
      >
        <h3>Популярные товары</h3>

        <p class="meta">
          Эти товары показаны отдельно и не являются
          результатами вашего поиска.
        </p>

        <div class="grid">
          ${items.map((p, i) => card(p, {
            query: q,
            searchId,
            position: i + 1,
            badge: "Популярное"
          })).join("")}
        </div>
      </section>
    `;
  }

  // ---------- Поиск ----------

  async function runSearch(q, { more = false } = {}) {
    q = q.trim();

    if (!q) return showFeatured();

    if (!more) {
      limit = PAGE;
      resetExtras();

      grid.innerHTML = skeletons(6);
      meta.textContent = "";
    }

    currentQuery = q;

    updateUrl(q);

    compareLink.href =
      "compare.html?q=" + encodeURIComponent(q);

    title.textContent =
      "Результаты по запросу «" + q + "»";

    const id = ++reqId;

    if (more) {
      moreBtn.disabled = true;
      moreBtn.textContent = "Загружаем…";
    }

    try {
      const r = await Api.search(q, mode, limit);

      if (id !== reqId) return;

      const items = r.items ?? [];
      const alternatives = r.alternatives ?? [];
      const recommendations = r.recommendations ?? [];
      const popular = r.popularRecommendations ?? [];

      // Считаем только основные результаты.
      meta.textContent =
        `Основных совпадений: ${items.length}. ` +
        `Время ответа: ${r.tookMs} мс. ` +
        `Режим: ${mode === "smart"
          ? "умный поиск"
          : "обычный поиск"}`;

      renderNotice(r, q);

      // Основные результаты.

      if (!items.length && !alternatives.length) {
        const extra = mode === "baseline"
          ? `<button
               class="btn btn-ghost"
               id="to-smart"
               type="button"
             >
               Попробовать умный поиск
             </button>`
          : "";

        grid.innerHTML = emptyState(
          "Ничего не нашлось",
          "Проверьте написание или попробуйте другое название.",
          extra
        );

        const b = $("#to-smart");

        if (b) {
          b.addEventListener("click", () => {
            mode = "smart";
            paintMode();
            runSearch(q);
          });
        }

      } else if (!items.length) {
        grid.innerHTML = emptyState(
          "Основных совпадений нет",
          "Похожие товары показаны отдельно ниже."
        );

      } else {
        grid.innerHTML = items.map((p, i) => card(p, {
          query: q,
          searchId: r.searchId,
          position: i + 1
        })).join("");
      }

      // Популярные товары выводятся отдельно.
      // Не входят в количество основных совпадений.

      if (popular.length) {
        grid.insertAdjacentHTML(
          "beforeend",
          renderPopular(popular, q, r.searchId)
        );
      }

      // Пагинация отключена.

      moreWrap.hidden = true;
      moreBtn.disabled = false;
      moreBtn.textContent = "Показать ещё";

      // Альтернативные товары.

      if (alternatives.length) {
        alts.innerHTML = alternatives.map((p, i) => card(p, {
          query: q,
          searchId: r.searchId,
          position: i + 1
        })).join("");

        altSec.hidden = false;

      } else {
        altSec.hidden = true;
        alts.innerHTML = "";
      }

      // Рекомендации.

      if (recommendations.length) {
        recs.innerHTML = recommendations.map((p, i) => card(p, {
          query: q,
          searchId: r.searchId,
          position: i + 1
        })).join("");

        recSec.hidden = false;

      } else {
        recSec.hidden = true;
        recs.innerHTML = "";
      }

      // Событие поиска.
      // results_count содержит только основные совпадения.

      if (!more) {
        Api.event({
          type: "search",
          query: q,
          mode,
          results_count: items.length,
          corrected_query: r.correctedQuery,
          search_id: r.searchId
        });
      }

    } catch (err) {
      if (id !== reqId) return;

      if (more) {
        limit -= PAGE;
        moreBtn.disabled = false;
        moreBtn.textContent = "Показать ещё";
        return;
      }

      errorState(err, grid, () => runSearch(q));
    }
  }

  // API пока не поддерживает offset-пагинацию.
  moreBtn.hidden = true;

  // ---------- Главная витрина ----------

  async function showFeatured() {
    const id = ++reqId;

    currentQuery = "";

    resetExtras();
    updateUrl("");

    compareLink.href = "compare.html";

    title.textContent = "Рекомендуемые товары";
    meta.textContent = "";

    grid.innerHTML = skeletons(6);

    try {
      const r = await Api.search(
        APP_CONFIG.USE_MOCK ? "" : "антивирус",
        "smart",
        12,
        { log: false }
      );

      if (id !== reqId) return;

      const items = r.items ?? [];
      const popular = r.popularRecommendations ?? [];

      const featured = items.length ? items : popular;

      grid.innerHTML = featured.length
        ? featured.map((p, i) => card(p, {
            position: i + 1
          })).join("")
        : emptyState(
            "Товаров пока нет",
            "Попробуйте воспользоваться поиском."
          );

    } catch (err) {
      if (id !== reqId) return;

      errorState(err, grid, showFeatured);
    }
  }

  // ---------- Аналитика кликов ----------

  trackClicks(grid, () => ({
    query: currentQuery || null,
    mode: currentQuery ? mode : null,
    source: currentQuery ? "results" : "featured"
  }));

  trackClicks(alts, () => ({
    query: currentQuery || null,
    mode,
    source: "alternatives"
  }));

  trackClicks(recs, () => ({
    query: currentQuery || null,
    mode,
    source: "recommendations"
  }));

  // Отдельная маркировка кликов по популярным товарам.
  // Основной обработчик на grid перехватывать их не должен
  // повторно, поэтому отдельное событие здесь не отправляем.

  // ---------- Старт ----------

  paintMode();

  const initial = param("q");

  if (initial) {
    input.value = initial;
    runSearch(initial);
  } else {
    showFeatured();
  }
})();