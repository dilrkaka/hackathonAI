// Демо-данные. Товары и ссылки взяты из тестовых запросов.
// «Умный» поиск понимает синонимы, транслит и слитное/раздельное написание,
// «обычный» ищет только точную подстроку в названии — так видна разница.
(function () {
  const PRODUCTS = [
    {
      id: "1001", group_id: "10", name: "Astra Linux Special Edition", vendor: "РусБИТех-Астра", vendor_code: "AL-SE-17",
      description: "Российская операционная система для защищённых рабочих станций и серверов. Подходит для госсектора и организаций с требованиями к сертификации.",
      category_id: "11", category_name: "Операционные системы", price: 14900, old_price: 16900, currency: "RUB", available: true,
      image_url: "", url: "https://store.softline.ru/astralinux/astra-linux-special-edition/",
      params: { platform: "Linux", license_type: "Бессрочная", certification: "ФСТЭК России" },
      _kw: ["astra linux", "астра линукс", "астра", "линукс", "linux", "операционная система", "ос", "импортозамещение", "русбитех"]
    },
    {
      id: "1002", group_id: "20", name: "Microsoft Office 2024 для дома и бизнеса", vendor: "Microsoft", vendor_code: "T5D-03490",
      description: "Классические приложения Word, Excel, PowerPoint и Outlook с бессрочной лицензией на один компьютер.",
      category_id: "21", category_name: "Офисные приложения", price: 39900, old_price: 44900, currency: "RUB", available: true,
      image_url: "", url: "https://store.softline.ru/microsoft/microsoft-office-dlya-doma-i-biznesa-2024/",
      params: { platform: "Windows, macOS", license_type: "Бессрочная", devices: "1 ПК" },
      _kw: ["microsoft office", "office", "офис", "ворд", "word", "excel", "эксель", "для дома и бизнеса", "офисный пакет", "майкрософт офис"]
    },
    {
      id: "1003", group_id: "30", name: "Kaspersky Small Office Security", vendor: "Kaspersky", vendor_code: "KL4541",
      description: "Защита компьютеров, серверов и мобильных устройств для небольших компаний до 50 сотрудников. Управление через облачную консоль.",
      category_id: "31", category_name: "Антивирусы", price: 4990, old_price: 5990, currency: "RUB", available: true,
      image_url: "", url: "https://store.softline.ru/kaspersky/kaspersky-small-office-security/",
      params: { platform: "Windows, macOS, Android", license_type: "Подписка на 1 год", users: "5–50" },
      _kw: ["kaspersky", "касперский", "антивирус", "small office", "kso", "защита малого офиса", "малый офис"]
    },
    {
      id: "1004", group_id: "40", name: "КриптоПро CSP 5.0", vendor: "Крипто-Про", vendor_code: "CP-CSP-50",
      description: "Криптографический провайдер для электронной подписи и защищённого обмена данными. Сертифицирован ФСБ России.",
      category_id: "41", category_name: "Криптография и ЭЦП", price: 2700, old_price: null, currency: "RUB", available: true,
      image_url: "", url: "https://store.softline.ru/kripto-pro/cryptopro-csp/",
      params: { platform: "Windows, Linux, macOS", license_type: "Бессрочная", certification: "ФСБ России" },
      _kw: ["крипто про", "криптопро", "cryptopro", "csp", "эцп", "электронная подпись", "криптопровайдер", "крипто про csp 5.0"]
    },
    {
      id: "1005", group_id: "50", name: "AnyDesk", vendor: "AnyDesk Software", vendor_code: "AD-SOLO",
      description: "Удалённый доступ к рабочему столу: поддержка пользователей, работа из дома, передача файлов.",
      category_id: "51", category_name: "Удалённый доступ", price: 1990, old_price: null, currency: "RUB", available: true,
      image_url: "", url: "https://store.softline.ru/anydesk/anydesk/",
      params: { platform: "Windows, macOS, Linux, Android, iOS", license_type: "Подписка на 1 месяц", devices: "1 устройство" },
      _kw: ["anydesk", "эни деск", "анидеск", "удаленный доступ", "удаленный рабочий стол", "remote"]
    },
    {
      id: "1006", group_id: "60", name: "Cyber Protect: резервное копирование", vendor: "Киберпротект", vendor_code: "CP-BKP-10",
      description: "Резервное копирование серверов, рабочих станций и виртуальных машин с защитой от шифровальщиков.",
      category_id: "61", category_name: "Резервное копирование", price: 8900, old_price: 9900, currency: "RUB", available: true,
      image_url: "", url: "https://store.softline.ru/cyberprotect/?filter%5Bcategory%5D%5B%5D=1033",
      params: { platform: "Windows, Linux, VMware", license_type: "Подписка на 1 год" },
      _kw: ["кибер бэкап", "кибер бекап", "cyber backup", "cyberprotect", "киберпротект", "резервное копирование", "бэкап", "бекап", "backup"]
    },
    {
      id: "1007", group_id: "70", name: "Эшелон Сканер-ВС", vendor: "НПО Эшелон", vendor_code: "ESH-SVS",
      description: "Сканер уязвимостей для оценки защищённости информационных систем. Сертифицирован ФСТЭК России.",
      category_id: "71", category_name: "Информационная безопасность", price: 56000, old_price: null, currency: "RUB", available: false,
      image_url: "", url: "https://store.softline.ru/npo-echelon/eshelon-skaner-vs/",
      params: { platform: "Windows, Linux", license_type: "Бессрочная", certification: "ФСТЭК России" },
      _kw: ["сканер-вс", "сканер вс", "эшелон", "echelon", "уязвимости", "сканер уязвимостей"]
    },
    {
      id: "1008", group_id: "80", name: "Вебинар: облачная телефония для бизнеса", vendor: "МТС", vendor_code: "WEB-MTS",
      description: "Онлайн-встреча с экспертами МТС: как перевести офисную телефонию в облако и сократить расходы на связь.",
      category_id: "81", category_name: "Вебинары", price: 0, old_price: null, currency: "RUB", available: true,
      image_url: "", url: "https://store.softline.ru/webinar/",
      params: { format: "Онлайн", duration: "1 час" },
      _kw: ["мтс", "mts", "вебинар", "webinar", "облачная атс", "телефония", "связь"]
    },
    {
      id: "1009", group_id: "90", name: "MaxPatrol Endpoint Protection Platform", vendor: "Positive Technologies", vendor_code: "MP-EPP",
      description: "Платформа защиты конечных точек: обнаружение и остановка атак на рабочих станциях и серверах.",
      category_id: "31", category_name: "Антивирусы", price: 12500, old_price: null, currency: "RUB", available: true,
      image_url: "", url: "https://store.softline.ru/positive-technologies/maxpatrol-endpoint-protection-platform/",
      params: { platform: "Windows, Linux", license_type: "Подписка на 1 год" },
      _kw: ["max patrol", "maxpatrol", "макс патрол", "positive technologies", "позитив текнолоджис", "edr", "endpoint", "защита конечных точек", "антивирус"]
    },
    {
      id: "1010", group_id: "20", name: "Microsoft 365 для семьи", vendor: "Microsoft", vendor_code: "6GQ-01897",
      description: "Подписка на Word, Excel, PowerPoint и 1 ТБ облачного хранилища OneDrive для шести человек.",
      category_id: "21", category_name: "Офисные приложения", price: 5990, old_price: 6990, currency: "RUB", available: true,
      image_url: "", url: "https://store.softline.ru/microsoft/microsoft-365-for-family/",
      params: { platform: "Windows, macOS, iOS, Android", license_type: "Подписка на 1 год", users: "до 6 человек" },
      _kw: ["365", "microsoft 365", "office 365", "офис 365", "для семьи", "family", "подписка"]
    }
  ];

  const norm = (s) => String(s || "").toLowerCase().replace(/ё/g, "е").replace(/[^a-zа-я0-9.\s]/g, " ").replace(/\s+/g, " ").trim();
  const squash = (s) => norm(s).replace(/\s/g, "");
  const clean = (p) => { const { _kw, ...rest } = p; return rest; };
  const wait = (ms = 250) => new Promise((r) => setTimeout(r, ms + Math.random() * 150));

  function baselineMatch(q) {
    const nq = norm(q);
    if (!nq) return PRODUCTS.slice();
    return PRODUCTS.filter((p) => norm(p.name).includes(nq));
  }

  function smartMatch(q) {
    const nq = norm(q);
    if (!nq) return PRODUCTS.slice();
    const sq = squash(q);
    const tokens = nq.split(" ").filter(Boolean);
    return PRODUCTS.map((p) => {
      const hay = norm([p.name, p.vendor, p.category_name, ...p._kw].join(" "));
      const hayS = hay.replace(/\s/g, "");
      let score = 0;
      if (squash(p.name).includes(sq)) score = 100;
      else if (p._kw.some((k) => norm(k) === nq || squash(k) === sq)) score = 90;
      else if (p._kw.some((k) => norm(k).includes(nq) || nq.includes(norm(k)) && norm(k).length > 2)) score = 75;
      else if (hayS.includes(sq)) score = 60;
      else {
        const hit = tokens.filter((t) => hay.includes(t)).length;
        if (hit === tokens.length) score = 50;
        else if (hit > 0 && hit >= tokens.length / 2) score = 25;
      }
      return { p, score };
    }).filter((x) => x.score > 0).sort((a, b) => b.score - a.score).map((x) => x.p);
  }

  const mock = {
    async search(query, mode, limit = 24) {
      await wait();
      // Демо исправления опечаток (только умный поиск)
      const CORRECTIONS = { "каспрский": "kaspersky", "микрософт офис": "microsoft office", "антивирс": "антивирус", "эни дэск": "anydesk" };
      let q = query, corrected = null;
      if (mode !== "baseline" && CORRECTIONS[norm(query)]) { corrected = CORRECTIONS[norm(query)]; q = corrected; }
      const found = (mode === "baseline" ? baselineMatch(q) : smartMatch(q)).slice(0, limit);
      // Альтернативы: другие товары той же категории, что и первый результат
      const alts = mode !== "baseline" && found.length
        ? PRODUCTS.filter((p) => !found.includes(p) && p.category_name === found[0].category_name).slice(0, 3)
        : [];
      return {
        items: found.map(clean), alternatives: alts.map(clean), corrected_query: corrected,
        intent: mode !== "baseline" && found.length ? "Поиск программного обеспечения" : "",
        categories: mode !== "baseline" && found.length ? [found[0].category_name] : [],
        total: found.length,
        tookMs: mode === "baseline" ? 12 + Math.round(Math.random() * 10) : 40 + Math.round(Math.random() * 30)
      };
    },

    async suggestions(q) {
      await wait(80);
      const nq = norm(q);
      if (nq.length < 2) return [];
      const pool = [
        ...window.APP_CONFIG.EXAMPLE_QUERIES,
        ...PRODUCTS.map((p) => p.name),
        "антивирус для бизнеса", "резервное копирование", "электронная подпись", "удалённый доступ"
      ];
      const seen = new Set();
      return pool
        .filter((s) => { const k = norm(s); if (seen.has(k)) return false; seen.add(k); return k.includes(nq); })
        .sort((a, b) => (norm(b).startsWith(nq) ? 1 : 0) - (norm(a).startsWith(nq) ? 1 : 0))
        .slice(0, 6);
    },

    async product(id) {
      await wait(150);
      const p = PRODUCTS.find((x) => x.id === String(id));
      if (!p) throw new Error("Товар не найден");
      return clean(p);
    },

    async recommendations(id) {
      await wait(150);
      const cur = PRODUCTS.find((x) => x.id === String(id));
      const others = PRODUCTS.filter((x) => x.id !== String(id));
      const same = others.filter((x) => cur && x.category_name === cur.category_name);
      const rest = others.filter((x) => !same.includes(x));
      return [...same, ...rest].slice(0, 4).map(clean);
    },

    async analytics() {
      await wait(300);
      return {
        total_searches: 1284,
        top_queries: [
          { query: "антивирус", count: 142 }, { query: "microsoft office", count: 118 }, { query: "kaspersky", count: 97 },
          { query: "кибер бэкап", count: 86 }, { query: "365", count: 74 }, { query: "крипто про csp 5.0", count: 63 },
          { query: "max patrol", count: 51 }, { query: "anydesk", count: 44 }, { query: "astra linux", count: 39 }, { query: "сканер-вс", count: 27 }
        ],
        zero_results: [
          { query: "касперский эндпоинт", count: 12 }, { query: "1с бухгалтерия", count: 9 }, { query: "vpn для офиса", count: 7 },
          { query: "ВМ ware", count: 4 }, { query: "adobe фотошоп", count: 3 }
        ],
        comparison: {
          labels: ["Нашлось хоть что-то", "Нужный товар в топ-1", "Нужный товар в топ-5"],
          baseline: [58, 31, 44],
          smart: [93, 74, 88]
        }
      };
    }
  };

  window.Mock = mock;
})();
