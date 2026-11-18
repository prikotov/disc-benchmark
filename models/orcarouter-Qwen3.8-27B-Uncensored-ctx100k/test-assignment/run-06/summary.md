# Прогон: orcarouter/Qwen3.8-27B-Uncensored:ctx100k — run-06 (thinking medium)

- запущен: 2026-11-15T07:08:40.856910+00:00, длительность: 9:03, exit: 0, убит: нет
- контекст/бюджет выхода: 102400 / 8192; промпт: v3 (sha 4b0ca9799499ed5b)
- сессия: 53 ходов, 52 вызовов инструментов; токены: вх 55,028 / вых 31,135
- сеть в bash: 4 обращений к источнику (curl/wget всего 4)
- масштаб параллельной нагрузки (VRAM): чисто

## Машинные проверки (check.json)

- файлы агента: 1; index.html: есть
- самодостаточность (внешние запросы): OK
- данные: прилагательных 82/84; пар текст+тип верно 94/96
- рендер-смоук (headless Chrome): OK
- автопрохождение (поток): OK, вопросов 26; баллы на экране — справочно (симуляция drag&drop не воспроизводима, логику проверяет судья по коду)
- скриншоты: /home/dp/MyProjects/disc/models/orcarouter-Qwen3.8-27B-Uncensored-ctx100k/test-assignment/run-06/screenshots/start.png, /home/dp/MyProjects/disc/models/orcarouter-Qwen3.8-27B-Uncensored-ctx100k/test-assignment/run-06/screenshots/step.png, /home/dp/MyProjects/disc/models/orcarouter-Qwen3.8-27B-Uncensored-ctx100k/test-assignment/run-06/screenshots/result.png
- судья яруса 1: data 3, logic 4, ux 4, impl 4 — **15/16**
- **итог чека: FAILED**

Дальше: судья яруса 2 (обзор + сверка), при расхождениях — доработки в тот же run.