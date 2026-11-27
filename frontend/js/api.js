// Слой работы с API. Все запросы к бэкенду — только здесь.
// Формат ответов гибкий: нормализаторы понимают разные названия полей.
(function () {
  const cfg = window.APP_CONFIG;
  let demo = !!cfg.USE_MOCK;
  const listeners = [];
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  function setDemo(v) {
    if (demo !== v) { demo = v; listeners.forEach((f) => f(v)); }
  }

  // kind: "http" | "timeout" | "network" | "parse"
  class ApiError extends Error {
    constructor(message, { status = null, kind = "network" } = {}) {
      super(message);
      this.name = "ApiError";
      this.status = status;
      this.kind = kind;
    }
  }

  // Таймаут 20 с и одна повторная попытка при сетевой ошибке или 5xx
  // (Railway может «просыпаться» после простоя)
  async function http(path, options = {}, { timeout = 20000, retries = 1 } = {}) {
    for (let attempt = 0; ; attempt++) {
      const ctrl = new AbortController();
      const timer = setTimeout(() => ctrl.abort(), timeout);
      try {
        const res = await fetch(cfg.API_URL + path, {
          headers: { "Content-Type": "application/json" },
          signal: ctrl.signal,
          ...options
        });
        clearTimeout(timer);
        if (!res.ok) {
          if (res.status >= 500 && attempt < retries) { await sleep(700); continue; }
          throw new ApiError("HTTP " + res.status, { status: res.status, kind: "http" });
        }
        return await res.json();
      } catch (e) {
        clearTimeout(timer);
        if (e instanceof ApiError) throw e;
        if (e instanceof SyntaxError) throw new ApiError("Некорректный JSON", { kind: "parse" });
        if (attempt < retries) { await sleep(700); continue; }
        throw new ApiError(e.message, { kind: e.name === "AbortError" ? "timeout" : "network" });
      }
    }
  }

  async function call(realFn, mockFn) {
    if (cfg.USE_MOCK) { setDemo(true); return mockFn(); }
    try {
      const r = await realFn();
      setDemo(false);
      return r;
    } catch (e) {
      if (cfg.FALLBACK_TO_MOCK) {
        console.warn("[api] бэкенд недоступен, использую демо-данные:", e.message);
        setDemo(true);
        return mockFn();
      }
      throw e;
    }
  }

  // ---------- Нормализаторы ----------
  const firstArray = (d, keys) => {
    for (const k of keys) if (d && Array.isArray(d[k])) return d[k];
    return null;
  };
  // Элемент может быть товаром или обёрткой { product: {...}, score }
  const toProduct = (x) => (x && typeof x === "object" && x.product && typeof x.product === "object")
    ? { ...x.product, _score: x.score ?? x.relevance ?? null }
    : x;
  const products = (arr) => (arr || []).map(toProduct).filter((p) => p && p.id != null);
  const label = (x) => typeof x === "string" ? x : (x && (x.name || x.label || x.intent || x.category_name || x.title)) || "";

  function normalizeSearch(data, q, t0) {
    const d = Array.isArray(data) ? { items: data } : (data || {});
    let corrected = d.corrected_query ?? d.query_correction ?? d.corrected ?? d.fixed_query ?? d.spellcheck ?? d.did_you_mean ?? d.normalized_query ?? null;
    if (corrected && typeof corrected === "object") corrected = corrected.corrected ?? corrected.query ?? corrected.text ?? null;
    if (typeof corrected !== "string" || corrected.trim().toLowerCase() === String(q).trim().toLowerCase()) corrected = null;

    // Текущий FastAPI возвращает отдельные массивы products / alternatives / recommendations.
    // Не брать d.results как основную выдачу: там роли объединены и товары продублируются.
    const items = products(firstArray(d, ["items", "products", "main", "main_results", "primary"]));
    const cats = d.categories ?? d.priority_categories ?? d.category ?? null;
    return {
      items,
      alternatives: products(firstArray(d, ["alternatives", "alternative_products", "alternative_results", "alternative"])),
      recommendations: products(firstArray(d, ["recommendations", "upsell", "upsells", "cross_sell", "related"])),
      popularRecommendations: products(firstArray(d, ["popular_recommendations"])),
      correctedQuery: corrected,
      intent: label(d.intent?.label ?? d.intent ?? d.detected_intent ?? ""),
      categories: (Array.isArray(cats) ? cats : cats ? [cats] : []).map(label).filter(Boolean).slice(0, 4),
      searchId: d.search_id ?? d.searchId ?? null,
      note: typeof d.note === "string" ? d.note : "",
      total: d.total ?? d.count ?? items.length,
      tookMs: Math.round(d.processing_time_ms ?? d.took_ms ?? d.tookMs ?? d.time_ms ?? (performance.now() - t0))
    };
  }

  const api = {
    isDemo: () => demo,
    onDemoChange: (f) => listeners.push(f),

    // mode: "smart" | "baseline"
    async search(query, mode = "smart", limit = cfg.PAGE_SIZE || 20, { log = true } = {}) {
      // Smart API accepts 4..20. Baseline accepts up to 100.
      limit = Math.max(4, Math.min(mode === "smart" ? 20 : 100, Number(limit) || 4));
      const t0 = performance.now();
      // request_id создаётся один раз на пользовательский запрос и сохраняется
      // в теле при сетевых ретраях, чтобы сервер идемпотентно записал аналитику.
      const requestId = crypto.randomUUID();
      const data = await call(
        () => http(mode === "baseline" ? "/api/search/baseline" : "/api/search/smart", {
          method: "POST", body: JSON.stringify({ query, limit, request_id: requestId, log })
        }, { retries: 1 }),
        () => window.Mock.search(query, mode, limit)
      );
      return normalizeSearch(data, query, t0);
    },

    async suggestions(q) {
      const data = await call(
        () => http("/api/suggestions?q=" + encodeURIComponent(q), {}, { retries: 0, timeout: 6000 }),
        () => window.Mock.suggestions(q)
      );
      const list = firstArray(Array.isArray(data) ? { a: data } : data, ["a", "suggestions", "items", "results"]) || [];
      return list.map(label).filter(Boolean);
    },

    async product(id) {
      const d = await call(
        () => http("/api/products/" + encodeURIComponent(id)),
        () => window.Mock.product(id)
      );
      return toProduct(d.product ? d.product : d);
    },

    async recommendations(id) {
      const data = await call(
        () => http("/api/recommendations/" + encodeURIComponent(id)),
        () => window.Mock.recommendations(id)
      );
      return products(Array.isArray(data) ? data : firstArray(data, ["items", "recommendations", "products", "results"]));
    },

    async analytics() {
      const d = await call(() => http("/api/analytics"), () => window.Mock.analytics());
      const queries = (arr) => (arr || []).map((x) => typeof x === "string"
        ? { query: x, count: null }
        : { query: x.query ?? x.text ?? x.name ?? "", count: x.count ?? x.total ?? x.searches ?? null });
      return {
        totalSearches: d.total_searches ?? d.totalSearches ?? d.total ?? 0,
        topQueries: queries(d.top_queries ?? d.topQueries).slice(0, 10),
        zeroResults: queries(d.zero_results ?? d.no_results ?? d.zeroResults ?? d.noResults),
        weakQueries: queries(d.weak_queries),
        // { labels: [...], baseline: [...], smart: [...] }
        comparison: d.comparison ?? null
      };
    },

    // Клики и действия. Ошибки не мешают пользователю.
    async event(payload) {
      const body = { ...payload, event_id: payload.event_id || crypto.randomUUID(), ts: new Date().toISOString() };
      if (cfg.USE_MOCK) {
        try {
          const log = JSON.parse(localStorage.getItem("hackathonai_events") || "[]");
          log.push(body);
          localStorage.setItem("hackathonai_events", JSON.stringify(log.slice(-200)));
        } catch (_) { /* localStorage недоступен */ }
        console.debug("[event]", body);
        return;
      }
      try {
        await fetch(cfg.API_URL + "/api/events", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body), keepalive: true
        });
      } catch (e) { console.debug("[event] не отправлено:", e.message); }
    }
  };

  window.Api = api;
})();
