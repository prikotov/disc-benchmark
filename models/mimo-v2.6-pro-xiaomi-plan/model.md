# mimo-v2.6-pro-xiaomi-plan (подписка Xiaomi token plan)

MiMo V2.6 Pro (старшая модель семейства MiMo) на подписке Xiaomi
(token plan). В disc участвует в анкете DISC: `quiz/` (ru) + `quiz-en/`
(en), по 1 прогону на уровень (решение владельца).

- Провайдер: xiaomi (token-plan-sgp); endpoint
  `https://token-plan-sgp.xiaomimimo.com/v1`; ключ — запись
  `xiaomi-token-plan-sgp` в `~/.pi/agent/auth.json` (в репо не живёт)
- Мышление: reasoning_effort = none/low/medium/high (ошибка 400 API
  перечисляет шкалу); off = `none` (проба 2026-11-17: 0 reasoning).
  Проба pro: none 0 / low 105 / medium 114 / high 128 симв reasoning на
  простом вопросе — рассуждение лёгкое даже на high
- Транспорт: прямой API (quiz/runner.py, cloud_provider=xiaomi)

Провенанс: карточка новая; сестринская карточка flash
(`~/MyProjects/Models/models/mimo-v2.6-flash-*`) — про flash; pro там не
тестировалась. Flash-сестра в disc-копировании: волна завершена
(high 3 PASSED / 2 FAILED, off 3 FAILED — из заголовка main).

## quiz — анкета DISC (2026-11-17, ru + en, по 1 прогону на уровень)

| | off | low | medium | high |
|---|---|---|---|---|
| ru | **20.0 (83%)** | 17.0 (71%) | 16.0 (67%) | 16.0 (67%) |
| en | 15.0 (65%) | **19.0 (83%)** | **19.0 (83%)** | **19.0 (83%)** |

- **ru off 20/24 (83%) — лучший ru-результат всей серии** (ни одна модель
  на ru не набрала больше).
- Зеркальное противофазье с языком: ru — off лучший (рассуждение отнимает
  −3…−4 п.п.), en — thinking лучше off (+18 п.п., 15 → 19). Самый сильный
  «язык × уровень» эффект в сетке.
- Прогон pro en medium шёл 606 с (10 мин, ~21k reasoning-токенов) —
  think-бюджет модели большой.
- Квота подписки Xiaomi — `reports/spend.csv`.
Прогоны: `quiz/run-01…04`, `quiz-en/run-01…04` (транспорт: прямой API
xiaomi), свод `reports/QUIZ.md/.html`.
