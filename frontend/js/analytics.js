// Страница аналитики: 4 блока.
(function () {
  const { $, esc, emptyState, mountLayout } = UI;
  mountLayout("analytics");

  const nf = new Intl.NumberFormat("ru-RU");

  function renderTop(list) {
    const el = $("#top");
    if (!list.length) { el.innerHTML = '<li class="meta">Данных пока нет.</li>'; return; }
    const max = Math.max(...list.map((x) => x.count || 0), 1);
    el.innerHTML = list.map((x, i) => `
      <li>
        <span class="n">${i + 1}</span>
        <span class="q"><i style="width:${x.count ? Math.max(6, Math.round((x.count / max) * 100)) : 0}%"></i>${esc(x.query)}</span>
        <span class="c">${x.count == null ? "" : nf.format(x.count)}</span>
      </li>`).join("");
  }

  function renderZero(list) {
    const el = $("#zero");
    el.innerHTML = list.length
      ? list.map((x) => `<li><span>${esc(x.query)}</span><span class="c">${x.count == null ? "" : nf.format(x.count)}</span></li>`).join("")
      : '<li style="background:var(--green-soft)">Все запросы нашли результат.</li>';
  }

  function renderChart(cmp) {
    const msg = $("#chart-msg");
    if (!cmp || !Array.isArray(cmp.labels) || !cmp.labels.length) {
      msg.hidden = false; msg.textContent = "Данных для сравнения пока нет."; return;
    }
    if (typeof Chart === "undefined") {
      msg.hidden = false; msg.textContent = "Не удалось загрузить библиотеку графиков. Проверьте подключение к интернету."; return;
    }
    const all = [...(cmp.baseline || []), ...(cmp.smart || [])];
    new Chart($("#chart"), {
      type: "bar",
      data: {
        labels: cmp.labels,
        datasets: [
          { label: "Обычный поиск", data: cmp.baseline, backgroundColor: "#B9C4DA", borderRadius: 6 },
          { label: "Умный поиск", data: cmp.smart, backgroundColor: "#2250F4", borderRadius: 6 }
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        font: { family: "Manrope, system-ui, sans-serif" },
        scales: { y: { beginAtZero: true, max: Math.max(...all) <= 100 ? 100 : undefined, ticks: { callback: (v) => v + "%" } } },
        plugins: {
          legend: { position: "bottom" },
          tooltip: { callbacks: { label: (c) => `${c.dataset.label}: ${c.parsed.y}%` } }
        }
      }
    });
  }

  async function load() {
    try {
      const d = await Api.analytics();
      $("#total").textContent = nf.format(d.totalSearches);
      renderTop(d.topQueries);
      renderZero(d.zeroResults);
      renderChart(d.comparison);
    } catch (e) {
      UI.errorState(e, $("#stats"), () => location.reload());
    }
  }
  load();
})();
