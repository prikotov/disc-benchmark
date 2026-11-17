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

## quiz — анкета DISC (2026-11-17, ru + en, 3 прогона на уровень)

| | off | low | medium | high |
|---|---|---|---|---|
| ru | **16.3 (68%)** | 15.0 (62%) | 15.7 (65%) | 16.3 (68%) |
| en | 17.3 (75%) | **18.3 (80%)** | **18.3 (80%)** | **18.3 (80%)** |

- ru: лестница плоская (15.0–16.3); en: thinking-уровни паритетом 18.3.
- Язык: +6 п.п. на en (в общем тренде). Стабильность стандартная (uniq=3).
- Сервер xiaomi эпизодически рвёт non-stream соединения (IncompleteRead) —
  первый заход добивки упал; ретраи runner.py расширены на HTTPException/
  обрыв тела, добивка прошла чисто.
Прогоны: `quiz/run-01…12`, `quiz-en/run-01…13` (прямой API xiaomi),
свод `reports/QUIZ.md/.html`.
