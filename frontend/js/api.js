// Слой работы с API. Все запросы к бэкенду — только здесь.
// Формат ответов бэкенда гибкий: функции-нормализаторы понимают разные названия полей.
(function () {
  const cfg = window.APP_CONFIG;
  let demo = !!cfg.USE_MOCK;
  const listeners = [];

  function setDemo(v) {
    if (demo !== v) { demo = v; listeners.forEach((f) => f(v)); }
  }

  async function http(path, options = {}) {
    const res = await fetch(cfg.API_URL + path, {
      headers: { "Content-Type": "application/json" },
      ...options
    });
    if (!res.ok) throw new Error("HTTP " + res.status);
    return res.json();
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

  const pick = (d, keys) => {
    if (Array.isArray(d)) return d;
    for (const k of keys) if (d && Array.isArray(d[k])) return d[k];
    return [];
  };

  const api = {
    isDemo: () => demo,
    onDemoChange: (f) => listeners.push(f),

    // mode: "smart" | "baseline"
    async search(query, mode = "smart", limit = 4) {
      const t0 = performance.now();

      limit = Math.max(4, Math.min(20, limit));

      const data = await call(
        () => http(
          mode === "baseline"
            ? "/api/search/baseline"
            : "/api/search/smart",
          {
            method: "POST",
            body: JSON.stringify({ query, limit })
          }
        ),
        () => window.Mock.search(query, mode, limit)
      );

      const items = pick(data, [
        "items", "results", "products", "data"
      ]);

      return {
        items,
        total: data.total ?? data.count ?? items.length,
        tookMs: Math.round(
          data.processing_time_ms ??
          data.took_ms ??
          data.tookMs ??
          data.time_ms ??
          (performance.now() - t0)
        ),
        normalizedQuery: data.normalized_query ?? query,
        note: data.note ?? "",
        fixes: data.fixes ?? [],
        searchId: data.search_id ?? null
      };
    },

    async suggestions(q) {
      const data = await call(
        () => http("/api/suggestions?q=" + encodeURIComponent(q)),
        () => window.Mock.suggestions(q)
      );
      return pick(data, ["suggestions", "items", "results"])
        .map((s) => (typeof s === "string" ? s : s.text || s.query || s.name || s.suggestion || ""))
        .filter(Boolean);
    },

    product: (id) => call(
      () => http("/api/products/" + encodeURIComponent(id)),
      () => window.Mock.product(id)
    ),

    async recommendations(id) {
      const data = await call(
        () => http("/api/recommendations/" + encodeURIComponent(id)),
        () => window.Mock.recommendations(id)
      );
      return pick(data, ["items", "recommendations", "products", "results"]);
    },

    async analytics() {
      const d = await call(() => http("/api/analytics"), () => window.Mock.analytics());
      const queries = (arr) => arr.map((x) => typeof x === "string"
        ? { query: x, count: null }
        : { query: x.query ?? x.text ?? x.name ?? "", count: x.count ?? x.total ?? x.searches ?? null });
      return {
        totalSearches: d.total_searches ?? d.totalSearches ?? d.total ?? 0,
        topQueries: queries(pick(d.top_queries ?? d.topQueries ?? [], [])).slice(0, 10),
        zeroResults: queries(pick(d.zero_results ?? d.no_results ?? d.zeroResults ?? d.noResults ?? [], [])),
        // { labels: [...], baseline: [...], smart: [...] }
        comparison: d.comparison ?? null
      };
    },

    // Клики и действия. Ошибки не мешают пользователю.
    async event(payload) {
      const body = { ...payload, ts: new Date().toISOString() };
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
