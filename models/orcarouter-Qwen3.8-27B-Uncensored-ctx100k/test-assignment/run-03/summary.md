# Прогон: orcarouter/Qwen3.8-27B-Uncensored:ctx100k — run-03 (thinking off)

- запущен: 2026-11-15T06:45:46.677728+00:00, длительность: 12:51, exit: 0, убит: нет
- контекст/бюджет выхода: 102400 / 8192; промпт: v3 (sha 4b0ca9799499ed5b)
- сессия: 105 ходов, 104 вызовов инструментов; токены: вх 134,179 / вых 42,223
- сеть в bash: 7 обращений к источнику (curl/wget всего 7)
- масштаб параллельной нагрузки (VRAM): чисто

## Машинные проверки (check.json)

- файлы агента: 1471; index.html: есть
- самодостаточность (внешние запросы): ПРОВАЛ
- данные: прилагательных 84/84; пар текст+тип верно 96/96
- рендер-смоук (headless Chrome): OK
- автопрохождение (поток): OK, вопросов 24; баллы на экране — справочно (симуляция drag&drop не воспроизводима, логику проверяет судья по коду)
- скриншоты: /home/dp/MyProjects/disc/models/orcarouter-Qwen3.8-27B-Uncensored-ctx100k/test-assignment/run-03/screenshots/start.png, /home/dp/MyProjects/disc/models/orcarouter-Qwen3.8-27B-Uncensored-ctx100k/test-assignment/run-03/screenshots/step.png, /home/dp/MyProjects/disc/models/orcarouter-Qwen3.8-27B-Uncensored-ctx100k/test-assignment/run-03/screenshots/result.png
- судья яруса 1: data 4, logic 4, ux 3, impl 4 — **15/16**
- **итог чека: FAILED**

Дальше: судья яруса 2 (обзор + сверка), при расхождениях — доработки в тот же run.