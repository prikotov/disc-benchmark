# Прогон: orcarouter/Qwen3.8-27B-Uncensored:ctx100k — run-02 (thinking off)

- запущен: 2026-11-15T06:36:46.250914+00:00, длительность: 8:33, exit: 0, убит: нет
- контекст/бюджет выхода: 102400 / 8192; промпт: v3 (sha 4b0ca9799499ed5b)
- сессия: 53 ходов, 53 вызовов инструментов; токены: вх 116,298 / вых 27,244
- сеть в bash: 9 обращений к источнику (curl/wget всего 9)
- масштаб параллельной нагрузки (VRAM): чисто

## Машинные проверки (check.json)

- файлы агента: 1; index.html: есть
- самодостаточность (внешние запросы): OK
- данные: прилагательных 84/84; пар текст+тип верно 96/96
- рендер-смоук (headless Chrome): OK
- автопрохождение (поток): OK, вопросов 24; баллы на экране — справочно (симуляция drag&drop не воспроизводима, логику проверяет судья по коду)
- скриншоты: /home/dp/MyProjects/disc/models/orcarouter-Qwen3.8-27B-Uncensored-ctx100k/test-assignment/run-02/screenshots/start.png, /home/dp/MyProjects/disc/models/orcarouter-Qwen3.8-27B-Uncensored-ctx100k/test-assignment/run-02/screenshots/step.png, /home/dp/MyProjects/disc/models/orcarouter-Qwen3.8-27B-Uncensored-ctx100k/test-assignment/run-02/screenshots/result.png
- судья яруса 1: data 4, logic 4, ux 4, impl 4 — **16/16**
- **итог чека: PASSED**

Дальше: судья яруса 2 (обзор + сверка), при расхождениях — доработки в тот же run.