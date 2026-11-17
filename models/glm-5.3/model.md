# glm-5.3 (z.ai подписка, coding plan)

Флагман GLM-5.3 на подписке z.ai (coding plan). В disc участвует в анкете
DISC: `quiz/` (ru) + `quiz-en/` (en).

- Провайдер: z.ai; endpoint `https://api.z.ai/api/coding/paas/v4`;
  ключ — запись `zai` в `~/.pi/agent/auth.json` (в репо не живёт)
- Мышление (дока z.ai + проба 2026-11-17): thinking только enabled;
  reasoning_effort = **low / high / max** (дефолт max — проба: без effort
  4.8k символов reasoning). **low фактически отключает thinking**
  (0 reasoning, 8 с) — единственный способ «off» у glm-5.3.
  Проба по уровням: low 0 / high 5.6k / max 7.7k символов reasoning.
- Транспорт: прямой API (quiz/runner.py, cloud_provider=zai)

Провенанс: карточка новая (в сестринском workspace есть только
glm-5.3-flash-{low,medium,max} — это другая модель, flash).

## quiz — анкета DISC (2026-11-17, ru + en, по 2 прогона на уровень)

| | low (≈off) | high | max |
|---|---|---|---|
| ru | **18.0 (75%)** | **18.0 (75%)** | 15.5 (65%) |
| en | 18.0 (78%) | **18.5 (80%)** | 17.5 (76%) |

- **Флагман сильнее флеша**: ru 18.0 против glm-5.3-flash@low 15.4;
  на en high 18.5 — уровень лидеров сетки (huihui 18.4 ru, deepseek en 19.0).
- Рассуждение на ru не помогает (low=high 18.0, max проседает — выброс
  13/24 на run-06), на en высокое рассуждение чуть добавляет (high 18.5).
- Язык: +5.4 п.п. (en лучше) — в общем тренде.
- Время: low ~4–8 с, high 60–138 с, max 25–178 с. Квота: 12 прогонов,
  2.9k вх / 13.8k вых токенов — `reports/spend.csv`.
- Провалы — те же ловушки методологии: Q1/Q2 (совместимость — пары общего
  DISC), Q19 «assimilate new ideas» → «Yellow» (предлагает ≠ воспринимает).
Детали: `quiz/run-01…06`, `quiz-en/run-01…06`, свод `reports/QUIZ.md/.html`.
