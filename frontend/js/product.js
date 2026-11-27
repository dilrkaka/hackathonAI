// Страница товара + рекомендации.
(function () {
  const { $, esc, param, card, placeholder, formatPrice, money, emptyState, trackClicks, mountLayout } = UI;
  mountLayout("home");

  const id = param("id");
  const q = param("q"), searchId = param("sid");
  const root = $("#product");
  if (q) $("#back").href = "index.html?q=" + encodeURIComponent(q);

  const PARAM_NAMES = {
    platform: "Платформа", license_type: "Тип лицензии", certification: "Сертификация",
    devices: "Устройства", users: "Пользователи", format: "Формат", duration: "Длительность"
  };

  async function load() {
    if (!id) { root.innerHTML = emptyState("Товар не выбран", "Вернитесь в каталог и откройте карточку товара.", '<a class="btn btn-ghost btn-lg" href="index.html">В каталог</a>'); return; }
    root.innerHTML = '<div class="grid">' + UI.skeletons(1) + "</div>";
    try {
      const p = await Api.product(id);
      render(p);
      Api.event({ type: "product_view", product_id: String(p.id), query: q || null, search_id: searchId || null });
      loadRecs(p.id);
    } catch (e) {
      if (e && e.status === 404) {
        root.innerHTML = emptyState("Товар не найден", "Возможно, он удалён или ссылка неверна.", '<a class="btn btn-ghost btn-lg" href="index.html">В каталог</a>');
      } else {
        UI.errorState(e, root, load);
      }
    }
  }

  function render(p) {
    document.title = p.name + ": Hackathonai Store";
    const ph = placeholder(p.name);
    const discount = p.old_price > p.price && p.price > 0 ? Math.round((1 - p.price / p.old_price) * 100) : 0;
    const out = p.available === false;
    const params = Object.entries(p.params || {});
    root.innerHTML = `
      <div class="product">
        <div class="product-img"><img src="${esc(p.image_url || ph)}" data-ph="${ph}" alt="${esc(p.name)}"></div>
        <div class="product-info">
          <div class="product-sub">${esc(p.category_name || "")}</div>
          <h1>${esc(p.name)}</h1>
          <div class="product-sub">${esc(p.vendor || "")}${p.vendor_code ? ", артикул " + esc(p.vendor_code) : ""}</div>
          <div class="buy-box">
            <div class="price">
              <span class="price-now">${esc(formatPrice(p))}${discount ? `<span class="discount">−${discount}%</span>` : ""}</span>
              ${p.old_price > p.price ? `<span class="price-old">${esc(money(p.old_price, p.currency))}</span>` : ""}
            </div>
            <span class="stock ${out ? "out" : "in"}">${out ? "Нет в наличии" : "В наличии"}</span>
            ${p.url ? `<a id="buy" class="btn btn-primary btn-lg" href="${esc(p.url)}" target="_blank" rel="noopener">Перейти в магазин</a>` : ""}
          </div>
          ${p.description ? `<p class="desc">${esc(p.description)}</p>` : ""}
          ${params.length ? `<h2 class="subhead">Характеристики</h2>
            <div class="table-wrap"><table class="params"><tbody>${params.map(([k, v]) => `<tr><th>${esc(PARAM_NAMES[k] || k)}</th><td>${esc(v)}</td></tr>`).join("")}</tbody></table></div>` : ""}
        </div>
      </div>`;
    const buy = $("#buy");
    if (buy) buy.addEventListener("click", () => Api.event({ type: "buy_click", product_id: String(p.id), query: q || null, search_id: searchId || null }));
  }

  async function loadRecs(pid) {
    try {
      const items = await Api.recommendations(pid);
      if (!items.length) return;
      $("#recs").innerHTML = items.map((p, i) => card(p, { position: i + 1, query: q, searchId })).join("");
      $("#recs-section").hidden = false;
      trackClicks($("#recs"), () => ({ query: q || null, source: "recommendations", from_product_id: String(pid), search_id: searchId || null }));
    } catch (_) { /* рекомендации необязательны */ }
  }

  load();
})();
