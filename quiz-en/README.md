# quiz-en: английская анкета DISC — методика

Английская версия исследования `quiz/` (см. её README — цели, решения
владельца, механика прогонов). Разница — только язык материала:

- **Источник — английский оригинал** (не перевод русской анкеты):
  Thomas Erikson, *Surrounded by Idiots*, гл. 20 «A Quick Little Quiz to
  See What You've Learned» + «The Answers to the Questions in Chapter 20».
  Снимок вербатимом: `reference/quiz-with-key.md` (epub — первичен, PDF —
  перекрёстная сверка 1:1).
- **23 вопроса** (в русской редакции 24: английского вопроса про болезненную
  реакцию на критику в оригинале нет; подробнее — `quiz/reference/quiz-with-key.md`).
  Межъязыковое сравнение — по процентам, не по сырым баллам.
- Промпт `prompts/prompt.json` v1 — адаптация английского интро главы
  (без упоминания книги), вопросы без вариантов, ответ — JSON
  «номер вопроса → ответ».
- Ключ `reference/key-en.json`: kind (color/book/none) и generic-ветки
  матчера (yellow-duo/green-anyone/all-four) — как в ru-ключе; цвета
  матчатся английскими стемами (red/yellow/green/blue + черты) и буквами
  D-I-S-C; family «нет однозначного ответа» и отказы ИИ — английские
  формулировки («no given answer», «as an AI...»).
- Прогоны: `models/<модель>/quiz-en/run-XX/` (run.json + answer.txt,
  в run.json поле `lang: "en"`); транспорт/условия — те же, что в ru
  (quiz/runner.py, все уровни из /api/show, 5 прогонов на модель×уровень).
- Отчёт — общий с русской серией: `reports/QUIZ.md/.html`, раздел
  «Язык: ru vs en» (Δ по процентам, стабильность по языкам).
