// Настройки фронтенда. Меняйте только здесь.
window.APP_CONFIG = {
  // Адрес бэкенда на Railway
  API_URL: "https://hackathonai-production.up.railway.app",

  // true  — всё работает на демо-данных (бэкенд не нужен)
  // false — запросы идут на реальный бэкенд
  USE_MOCK: true,

  // Если бэкенд не ответил — показать демо-данные вместо ошибки
  FALLBACK_TO_MOCK: true,

  // Тестовые запросы (со скриншота) — показываются под строкой поиска
  EXAMPLE_QUERIES: [
    "astra linux",
    "Microsoft Office для дома и бизнеса",
    "kaspersky small office security",
    "крипто про csp 5.0",
    "anydesk",
    "кибер бэкап",
    "сканер-вс",
    "мтс",
    "max patrol",
    "365"
  ]
};
