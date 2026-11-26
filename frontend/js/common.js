// Общие функции интерфейса: шапка, карточки товаров, форматирование.
(function () {
  const cfg = window.APP_CONFIG;
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const param = (n) => new URLSearchParams(location.search).get(n);
  const debounce = (fn, ms = 200) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; };

  function money(value, currency) {
    const cur = !currency || currency === "RUB" ? "₽" : currency;
    return new Intl.NumberFormat("ru-RU").format(value) + " " + cur;
  }

  function formatPrice(p) {
    if (p.price == null || Number(p.price) <= 0) {
      return "Цена по запросу";
    }

    return money(p.price, p.currency);
  }

  // Заглушка вместо картинки: инициалы на цветном фоне
  function placeholder(name) {
    const words = String(name || "?").replace(/[^A-Za-zА-Яа-яЁё0-9\s]/g, "").split(/\s+/).filter(Boolean);
    const ini = ((words[0] || "?")[0] + ((words[1] || "")[0] || "")).toUpperCase();
    let h = 0;
    for (const ch of String(name)) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
    const palette = [["#DCE6FF", "#2250F4"], ["#E7EEF9", "#34507F"], ["#E3F1F7", "#1D6A8C"], ["#ECEBFA", "#4B45B5"], ["#E5EEF2", "#3F5A66"]];
    const [bg, fg] = palette[h % palette.length];
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300"><rect width="400" height="300" fill="${bg}"/><text x="200" y="170" font-family="Arial, sans-serif" font-size="96" font-weight="700" fill="${fg}" text-anchor="middle">${esc(ini)}</text></svg>`;
    return "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
  }

  // Если картинка не загрузилась — подставляем заглушку
  document.addEventListener("error", (e) => {
    const img = e.target;
    if (img && img.tagName === "IMG" && img.dataset.ph && img.src !== img.dataset.ph) img.src = img.dataset.ph;
  }, true);

  // Карточка товара. options: { query, position, badge }
  function card(p, o = {}) {
    const ph = placeholder(p.name);
    const href = "product.html?id=" + encodeURIComponent(p.id) + (o.query ? "&q=" + encodeURIComponent(o.query) : "");
    const discount = p.old_price > p.price && p.price > 0 ? Math.round((1 - p.price / p.old_price) * 100) : 0;
    const out = p.available === false;

    const roleLabel = {
      match: "Подходит по запросу",
      alternative: "Похожий товар",
      upsell: "Рекомендуем дополнительно"
    }[p.role] || "";

    return `<article class="card" data-id="${esc(p.id)}" data-pos="${o.position ?? ""}">
      <a class="card-link" href="${href}">
        <div class="card-img">
          <img src="${esc(p.image_url || ph)}" data-ph="${ph}" alt="" loading="lazy">
          ${discount ? `<span class="tag tag-sale">−${discount}%</span>` : ""}
          ${o.badge ? `<span class="tag tag-smart">${esc(o.badge)}</span>` : ""}
        </div>
        <div class="card-body">
          <div class="card-cat">${esc(p.category_name || "")}</div>
          <h3 class="card-title">${esc(p.name)}</h3>
          <div class="card-vendor">${esc(p.vendor || "")}</div>
          ${roleLabel ? `<div class="meta">${esc(roleLabel)}</div>` : ""}
          ${p.reason ? `<div class="meta">${esc(p.reason)}</div>` : ""}
          <div class="card-foot">
            <div class="price">
              <span class="price-now">${esc(formatPrice(p))}</span>
              ${discount ? `<span class="price-old">${esc(money(p.old_price, p.currency))}</span>` : ""}
            </div>
            <span class="stock ${out ? "out" : "in"}">${out ? "Нет в наличии" : "В наличии"}</span>
          </div>
        </div>
      </a>
    </article>`;
  }

  function skeletons(n = 6) {
    return Array.from({ length: n }, () => `<div class="card skeleton" aria-hidden="true"><div class="card-img"></div><div class="card-body"><i></i><i></i><i class="short"></i></div></div>`).join("");
  }

  // Отправка кликов по карточкам: getCtx() возвращает { query, mode }
  function trackClicks(container, getCtx) {
    container.addEventListener("click", (e) => {
      const c = e.target.closest(".card[data-id]");
      if (!c) return;
      window.Api.event({
        type: "click",
        product_id: c.dataset.id,
        position: c.dataset.pos === "" ? null : Number(c.dataset.pos),
        ...getCtx()
      });
    });
  }

  function mountLayout(active) {
    const nav = [
      ["index.html", "Каталог", "home"],
      ["compare.html", "Сравнение поиска", "compare"],
      ["analytics.html", "Аналитика", "analytics"]
    ];

    $("#app-header").innerHTML = `
      <div class="container header-row">
        <a class="logo" href="index.html">Hackathonai Store</a>
        <nav class="nav" aria-label="Основное меню">
          ${nav.map(([h, t, k]) => `<a href="${h}" ${k === active ? 'aria-current="page"' : ""}>${t}</a>`).join("")}
        </nav>
      </div>
      <div id="demo-banner" class="demo-banner" hidden></div>`;

    const footer = $("#app-footer");
    if (footer) footer.innerHTML = `<div class="container">Hackathonai Store. Учебный проект хакатона: умный поиск по каталогу программного обеспечения.</div>`;

    const banner = $("#demo-banner");
    const showDemo = (on) => {
      banner.hidden = !on;
      banner.textContent = cfg.USE_MOCK
        ? "Демо-режим: показаны тестовые данные. Чтобы подключить бэкенд, поменяйте USE_MOCK в js/config.js."
        : "Бэкенд сейчас недоступен, поэтому показаны демонстрационные данные.";
    };

    window.Api.onDemoChange(showDemo);
    showDemo(window.Api.isDemo());
  }

  function emptyState(title, text, extra = "") {
    return `<div class="empty"><h3>${esc(title)}</h3><p>${esc(text)}</p>${extra}</div>`;
  }

  window.UI = { $, $$, esc, param, debounce, money, formatPrice, placeholder, card, skeletons, trackClicks, mountLayout, emptyState };
})();