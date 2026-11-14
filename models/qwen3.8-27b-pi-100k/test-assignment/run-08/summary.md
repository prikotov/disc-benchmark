# Прогон: qwen3.8:27b-pi-100k — run-08 (thinking medium)

- запущен: 2026-11-14T21:23:26.496425+00:00, длительность: 2:46, exit: 0, убит: нет
- контекст/бюджет выхода: 102400 / 32768; промпт: v3 (sha 4b0ca9799499ed5b)
- сессия: 23 ходов, 25 вызовов инструментов; токены: вх 38,456 / вых 19,481
- сеть в bash: 4 обращений к источнику (curl/wget всего 4)
- масштаб параллельной нагрузки (VRAM): чисто

## Машинные проверки (check.json)

- файлы агента: 10; index.html: есть
- самодостаточность (внешние запросы): OK
- данные: прилагательных 84/84; пар текст+тип верно 96/96
- рендер-смоук (headless Chrome): OK
- автопрохождение (поток): OK, вопросов 24; баллы на экране — справочно (симуляция drag&drop не воспроизводима, логику проверяет судья по коду)
- скриншоты: /home/dp/MyProjects/disc/models/qwen3.8-27b-pi-100k/test-assignment/run-08/screenshots/start.png, /home/dp/MyProjects/disc/models/qwen3.8-27b-pi-100k/test-assignment/run-08/screenshots/step.png, /home/dp/MyProjects/disc/models/qwen3.8-27b-pi-100k/test-assignment/run-08/screenshots/result.png
- судья яруса 1: data 4, logic 4, ux 2, impl 4 — **14/16**
- **итог чека: PASSED**

Дальше: судья яруса 2 (обзор + сверка), при расхождениях — доработки в тот же run.