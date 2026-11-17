# mimo-v2.6-flash-xiaomi-plan (подписка Xiaomi token plan)

MiMo V2.6 Flash на подписке Xiaomi (token plan sgp). В disc участвует в
двух типах экспериментов: копирование (`test-assignment/`, волна завершена
до ветвления) и анкета DISC (`quiz/` ru + `quiz-en/` en).

- Провайдер: xiaomi; endpoint `https://token-plan-sgp.xiaomimimo.com/v1`;
  ключ — запись `xiaomi-token-plan-sgp` в `~/.pi/agent/auth.json`
- Мышление: reasoning_effort none/low/medium/high (шкала из ошибки 400 API);
  off = `none` (0 reasoning, проверено)
- Транспорт анкеты: прямой API (quiz/runner.py, cloud_provider=xiaomi)

Провенанс: карточка создана 2026-11-17 (в main tree карточки не было —
только прогоны копирования; в сестринском workspace карточки по уровням:
`~/MyProjects/Models/models/mimo-v2.6-flash-{off,low,medium,high}`).

## quiz — анкета DISC (2026-11-17, ru + en, по 1 прогону на уровень)

| | off | low | medium | high |
|---|---|---|---|---|
| ru | 17.0 (71%) | 15.0 (62%) | 16.0 (67%) | **18.0 (75%)** |
| en | 18.0 (78%) | **19.0 (83%)** | 18.0 (78%) | 18.0 (78%) |

ru high 18.0 и en low 19.0 — на уровне лидеров; лучший en — low (против
ru, где low худший). Язык: +8 п.п. на en (в общем тренде). Прогоны:
`quiz/run-01…04`, `quiz-en/run-01…04` (транспорт: прямой API xiaomi),
свод `reports/QUIZ.md/.html`.
