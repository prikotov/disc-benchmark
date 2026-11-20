# kimi-k3.1-pro (Kimi K3.1 Pro, подписка Kimi coding через pi)

Флагманская reasoning-модель Moonshot AI (открытые веса, релиз 2026-10-23)
на подписке Kimi coding plan. В disc участвует в анкете DISC:
`quiz/` (ru) + `quiz-en/` (en), по 1 прогону на уровень (решение владельца).

- Провайдер: kimi-coding (pi-подписка); endpoint
  `https://api.kimi.com/coding/v1`; OAuth-токен — запись `kimi-coding`
  в `~/.pi/agent/auth.json` (pi сам refresh'ит; в репо не живёт)
- Транспорт: **прямой non-stream** (pi-streaming рвётся на длинной
  генерации: UND_ERR_SOCKET/ECONNRESET, 6/6 прогонов v1 — evidence в
  `*/failed-pi-streaming-attempt/`); access-токен тот же (pi-refresh при 401)
- Мышление (дока Kimi API Platform): thinking **всегда включён** (off нет);
  reasoning_effort = **low / high / max** (дефолт max); pi передаёт уровень
  verbatim (thinkingLevelMap у модели пуст)
- usage в run.json не сохранялся (шим без usage — доработать при следующих
  прогонах); расход квоты подписки — `reports/spend.csv`

Провенанс: карточка новая. Источники доки: platform.kimi.ai/docs/guide/
use-reasoning-effort, kimi-k3-1-pro-quickstart.

## quiz — анкета DISC (2026-11-17, ru + en, по 1 прогону на уровень)

| | low | high | max |
|---|---|---|---|
| ru | 17.0 (71%) | 16.0 (67%) | **18.0 (75%)** |
| en | **19.0 (83%)** | **19.0 (83%)** | **19.0 (83%)** |

- **en 19/24 на всех трёх уровнях** — делит верх сетки с deepseek en@low
  (19.0); ru max 18.0 — уровень лидеров ru (huihui off 18.4, qwen3.8 low 18.6).
- Первая модель, у которой max не хуже low/high на обоих языках (у остальных
  максимальное рассуждение проседало). Время: low 24–31 с, high 62–79 с,
  max 243–323 с — самый дорогой max в сетке.
- Язык: +5 п.п. на en (в общем тренде).
Детали: `quiz/run-01…03`, `quiz-en/run-01…03`, свод `reports/QUIZ.md/.html`.
