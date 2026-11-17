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

## quiz — анкета DISC (2026-11-17, ru + en, 5 прогонов на уровень)

| | low (≈off) | high | max |
|---|---|---|---|
| ru | **18.4 (77%)** | 17.6 (73%) | 16.8 (70%) |
| en | 17.6 (77%) | **18.8 (82%)** | 18.2 (79%) |

- **Флагман сильнее флеша**: ru low 18.4 против glm-5.3-flash@low 15.4 (+3.0);
  en high 18.8 (82%) — среди лучших групповых результатов сетки
  (qwen3.8 en@medium 19.4, deepseek en@low 19.0, qwen4-max en@off/xhigh 18.5).
- Лестницы зеркальные: на ru лучшее — без рассуждения (low 18.4, max 16.8,
  −1.6); на en — с рассуждением (high 18.8, +1.2 к low). Max на ru при n=5
  подтвердил просадку (16.8; выброс 13/24 остался самым слабым прогоном).
- Язык: +5.1 п.п. (en лучше) — в общем тренде; стабильность стандартная
  (uniq=5, попарно 0%).
- Время: low ~4–8 с, high ~57–128 с, max ~38–178 с. Квота: 30 прогонов —
  `reports/spend.csv`.
- Провалы — те же ловушки методологии: Q1/Q2 (совместимость — пары общего
  DISC), Q19 «assimilate new ideas» → «Yellow» (предлагает ≠ воспринимает).
Детали: `quiz/run-01…10`, `quiz-en/run-01…10`, свод `reports/QUIZ.md/.html`.
