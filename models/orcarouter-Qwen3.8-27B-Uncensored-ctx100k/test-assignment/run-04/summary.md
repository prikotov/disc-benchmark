# Прогон: orcarouter/Qwen3.8-27B-Uncensored:ctx100k — run-04 (thinking medium)

- запущен: 2026-11-15T06:59:16.002281+00:00, длительность: 3:27, exit: 0, убит: нет
- контекст/бюджет выхода: 102400 / 8192; промпт: v3 (sha 4b0ca9799499ed5b)
- сессия: 19 ходов, 19 вызовов инструментов; токены: вх 26,833 / вых 14,495
- сеть в bash: 3 обращений к источнику (curl/wget всего 3)
- масштаб параллельной нагрузки (VRAM): чисто

## Машинные проверки (check.json)

- файлы агента: 1; index.html: есть
- самодостаточность (внешние запросы): OK
- данные: прилагательных 83/84; пар текст+тип верно 95/96
- рендер-смоук (headless Chrome): OK
- автопрохождение (поток): OK, вопросов 26; баллы на экране — справочно (симуляция drag&drop не воспроизводима, логику проверяет судья по коду)
- скриншоты: /home/dp/MyProjects/disc/models/orcarouter-Qwen3.8-27B-Uncensored-ctx100k/test-assignment/run-04/screenshots/start.png, /home/dp/MyProjects/disc/models/orcarouter-Qwen3.8-27B-Uncensored-ctx100k/test-assignment/run-04/screenshots/step.png, /home/dp/MyProjects/disc/models/orcarouter-Qwen3.8-27B-Uncensored-ctx100k/test-assignment/run-04/screenshots/result.png
- судья яруса 1: data 2, logic 4, ux 4, impl 4 — **14/16**
- **итог чека: FAILED**

Дальше: судья яруса 2 (обзор + сверка), при расхождениях — доработки в тот же run.