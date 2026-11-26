// Сравнение обычного и умного поиска на одном запросе.
(function () {
  const { $, esc, param, card, skeletons, emptyState, trackClicks, mountLayout } = UI;
  mountLayout("compare");

  const form = $("#compare-form"), input = $("#q");
  const columns = $("#columns"), verdict = $("#verdict");
  const resBase = $("#res-base"), resSmart = $("#res-smart");
  let currentQuery = "", reqId = 0;

  $("#chips").innerHTML = APP_CONFIG.EXAMPLE_QUERIES.map((q) => `<button type="button" class="chip">${esc(q)}</button>`).join("");
  $("#chips").addEventListener("click", (e) => {
    const c = e.target.closest(".chip");
    if (!c) return;
    input.value = c.textContent;
    run(c.textContent);
  });

  form.addEventListener("submit", (e) => { e.preventDefault(); run(input.value.trim()); });

  function plural(n, one, few, many) {
    const m10 = n % 10, m100 = n % 100;
    if (m10 === 1 && m100 !== 11) return one;
    if (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)) return few;
    return many;
  }

  async function run(q) {
    if (!q) { input.focus(); return; }
    currentQuery = q;
    const u = new URL(location.href); u.searchParams.set("q", q); history.replaceState(null, "", u);

    columns.hidden = false; verdict.hidden = true;
    resBase.innerHTML = skeletons(1); resSmart.innerHTML = skeletons(1);
    $("#meta-base").textContent = ""; $("#meta-smart").textContent = "";
    const id = ++reqId;

    try {
      const [base, smart] = await Promise.all([Api.search(q, "baseline"), Api.search(q, "smart")]);
      if (id !== reqId) return;
      const baseIds = new Set(base.items.map((p) => String(p.id)));

      $("#meta-base").textContent = `Найдено: ${base.items.length}. ${base.tookMs} мс`;
      $("#meta-smart").textContent = `Найдено: ${smart.items.length}. ${smart.tookMs} мс`;

      resBase.innerHTML = base.items.length
        ? base.items.map((p, i) => card(p, { query: q, position: i + 1 })).join("")
        : emptyState("Ничего не нашлось", "Обычный поиск ищет только точное совпадение в названии.");
      resSmart.innerHTML = smart.items.length
        ? smart.items.map((p, i) => card(p, { query: q, position: i + 1, badge: baseIds.has(String(p.id)) ? "" : "Только в умном поиске" })).join("")
        : emptyState("Ничего не нашлось", "Даже умный поиск не нашёл подходящих товаров. Такие запросы попадают в аналитику.");

      const extra = smart.items.filter((p) => !baseIds.has(String(p.id))).length;
      verdict.hidden = false;
      verdict.textContent = extra > 0
        ? `По запросу «${q}» умный поиск нашёл ${extra} ${plural(extra, "товар", "товара", "товаров")}, которых нет в обычной выдаче.`
        : `По запросу «${q}» оба режима вернули одинаковые товары.`;

      Api.event({ type: "compare", query: q, baseline_count: base.items.length, smart_count: smart.items.length });
    } catch (err) {
      if (id !== reqId) return;
      verdict.hidden = false;
      verdict.textContent = "Не удалось выполнить сравнение: сервер не ответил. Повторите запрос позже.";
      columns.hidden = true;
    }
  }

  trackClicks($("#columns"), () => ({ query: currentQuery, source: "compare" }));

  const initial = param("q");
  if (initial) { input.value = initial; run(initial); }
})();
