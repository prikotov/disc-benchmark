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

**По 3 прогона на уровень:**

| | off | low | medium | high |
|---|---|---|---|---|
| ru | **19.3 (81%)** | 16.3 (68%) | 17.3 (72%) | 16.7 (69%) |
| en | 17.0 (74%) | 18.7 (81%) | **19.0 (83%)** | 18.3 (80%) |

- **ru off 19.3 (81%) — лучший ru-результат серии** (единичные 20/24
  были в первом прогоне; n=3 подтвердил уверенное лидерство off).
- Зеркальное противофазье с языком подтвердилось на n=3: ru — off лучший
  (рассуждение −2…−3 п.п.), en — thinking лучше off (+9…+12 п.п.). Самый
  сильный «язык × уровень» эффект в сетке.
- pro en medium шёл до 606 с (~21k reasoning-токенов) — think-бюджет
  большой. Квота подписки Xiaomi — `reports/spend.csv`.
Прогоны: `quiz/run-01…12`, `quiz-en/run-01…12` (прямой API xiaomi),
свод `reports/QUIZ.md/.html`.
