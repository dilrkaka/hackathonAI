
// Сравнение обычного и умного поиска на одном запросе.
(function () {
  const {
    $, esc, param, card, skeletons,
    emptyState, trackClicks, mountLayout
  } = UI;

  mountLayout("compare");

  const form = $("#compare-form");
  const input = $("#q");
  const columns = $("#columns");
  const verdict = $("#verdict");

  const resBase = $("#res-base");
  const resSmart = $("#res-smart");
  const noteSmart = $("#note-smart");

  let baselineSearchId = null;
  let smartSearchId = null;
  let currentQuery = "";
  let reqId = 0;

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
    run(input.value);
  });

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    run(input.value.trim());
  });

  // Additional products are not main search results.
  function renderAdditional(title, items, query, badge) {
    if (!items.length) return "";

    return `
      <div style="grid-column: 1 / -1">
        <h3>${esc(title)}</h3>
      </div>

      ${items.map((p) => card(p, {
        query,
        badge
      })).join("")}
    `;
  }

  async function run(q) {
    q = q.trim();

    if (!q) {
      input.focus();
      return;
    }

    currentQuery = q;

    const u = new URL(location.href);
    u.searchParams.set("q", q);
    history.replaceState(null, "", u);

    columns.hidden = false;
    verdict.hidden = true;

    noteSmart.hidden = true;
    noteSmart.textContent = "";

    baselineSearchId = null;
    smartSearchId = null;

    resBase.innerHTML = skeletons(1);
    resSmart.innerHTML = skeletons(1);

    $("#meta-base").textContent = "";
    $("#meta-smart").textContent = "";

    const id = ++reqId;

    try {
      const limit = Math.max(
        4,
        Math.min(20, APP_CONFIG.PAGE_SIZE || 20)
      );

      const [base, smart] = await Promise.all([
        Api.search(q, "baseline", limit, { log: false }),
        Api.search(q, "smart", limit, { log: false })
      ]);

      if (id !== reqId) return;

      const baseItems = base.items ?? [];
      const smartItems = smart.items ?? [];

      const alternatives = smart.alternatives ?? [];
      const recommendations = smart.recommendations ?? [];
      const popular = smart.popularRecommendations ?? [];

      const baseIds = new Set(
        baseItems.map((p) => String(p.id))
      );

      const smartIds = new Set(
        smartItems.map((p) => String(p.id))
      );

      // Comparison requests are not saved as search logs.
      baselineSearchId = null;
      smartSearchId = null;

      noteSmart.textContent = smart.note || "";
      noteSmart.hidden = !smart.note;

      $("#meta-base").textContent =
        `Найдено: ${baseItems.length}. ${base.tookMs} мс`;

      $("#meta-smart").textContent =
        `Основных совпадений: ${smartItems.length}. ` +
        `${smart.tookMs} мс`;

      // Baseline results.
      resBase.innerHTML = baseItems.length
        ? baseItems.map((p, i) => card(p, {
            query: q,
            position: i + 1
          })).join("")
        : emptyState(
            "Ничего не нашлось",
            "Обычный поиск не нашёл совпадений в названиях и описаниях товаров."
          );

      // Smart search main results.
      resSmart.innerHTML = smartItems.length
        ? smartItems.map((p, i) => card(p, {
            query: q,
            position: i + 1,
            badge: baseIds.has(String(p.id))
              ? ""
              : "Только в умном поиске"
          })).join("")
        : emptyState(
            "Основных совпадений нет",
            "Попробуйте изменить запрос или посмотреть дополнительные предложения."
          );

      // Additional products are displayed separately.
      resSmart.innerHTML += renderAdditional(
        "Альтернативные товары",
        alternatives,
        q,
        "Альтернатива"
      );

      resSmart.innerHTML += renderAdditional(
        "Рекомендации",
        recommendations,
        q,
        "Рекомендация"
      );

      resSmart.innerHTML += renderAdditional(
        "Популярные товары",
        popular,
        q,
        "Популярное"
      );

      // Compare only main result sets.
      const extra = [...smartIds].filter(
        (productId) => !baseIds.has(productId)
      ).length;

      const missing = [...baseIds].filter(
        (productId) => !smartIds.has(productId)
      ).length;

      verdict.hidden = false;

      if (!baseItems.length && !smartItems.length) {
        verdict.textContent =
          "Оба режима не нашли основных результатов.";

      } else if (extra === 0 && missing === 0) {
        verdict.textContent =
          "Оба режима вернули одинаковый набор основных товаров.";

      } else {
        verdict.textContent =
          `По запросу «${q}»: ` +
          `только в умном поиске — ${extra}, ` +
          `только в обычном поиске — ${missing}.`;
      }

      if (smart.correctedQuery) {
        verdict.textContent +=
          ` Умный поиск исправил запрос на «${smart.correctedQuery}».`;
      }

      if (alternatives.length) {
        verdict.textContent +=
          ` Альтернатив: ${alternatives.length}.`;
      }

      if (recommendations.length) {
        verdict.textContent +=
          ` Рекомендаций: ${recommendations.length}.`;
      }

      if (popular.length) {
        verdict.textContent +=
          ` Популярных товаров: ${popular.length}.`;
      }

      // Save comparison as a separate event.
      Api.event({
        type: "compare",
        query: q,
        baseline_count: baseItems.length,
        smart_count: smartItems.length
      });

    } catch (err) {
      if (id !== reqId) return;

      verdict.hidden = false;

      verdict.textContent =
        "Не удалось выполнить сравнение. " +
        UI.describeError(err).join(" ");

      columns.hidden = true;
    }
  }

  trackClicks(resBase, () => ({
    query: currentQuery,
    source: "compare",
    mode: "baseline",
    search_id: baselineSearchId
  }));

  trackClicks(resSmart, () => ({
    query: currentQuery,
    source: "compare",
    mode: "smart",
    search_id: smartSearchId
  }));

  const initial = param("q");

  if (initial) {
    input.value = initial;
    run(initial);
  }
})();
