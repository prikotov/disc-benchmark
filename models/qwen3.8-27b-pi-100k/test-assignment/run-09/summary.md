# Прогон: qwen3.8:27b-pi-100k — run-09 (thinking medium)

- запущен: 2026-11-14T21:26:37.576912+00:00, длительность: 2:25, exit: 0, убит: нет
- контекст/бюджет выхода: 102400 / 32768; промпт: v3 (sha 4b0ca9799499ed5b)
- сессия: 26 ходов, 25 вызовов инструментов; токены: вх 25,441 / вых 18,464
- сеть в bash: 5 обращений к источнику (curl/wget всего 5)
- масштаб параллельной нагрузки (VRAM): чисто

## Машинные проверки (check.json)

- файлы агента: 2480; index.html: есть
- самодостаточность (внешние запросы): OK
- данные: прилагательных 84/84; пар текст+тип верно 96/96
- рендер-смоук (headless Chrome): OK
- автопрохождение (поток): OK, вопросов 24; баллы на экране — справочно (симуляция drag&drop не воспроизводима, логику проверяет судья по коду)
- скриншоты: /home/dp/MyProjects/disc/models/qwen3.8-27b-pi-100k/test-assignment/run-09/screenshots/start.png, /home/dp/MyProjects/disc/models/qwen3.8-27b-pi-100k/test-assignment/run-09/screenshots/step.png, /home/dp/MyProjects/disc/models/qwen3.8-27b-pi-100k/test-assignment/run-09/screenshots/result.png
- судья яруса 1: не выполнялся
- **итог чека: PASSED**

Дальше: судья яруса 2 (обзор + сверка), при расхождениях — доработки в тот же run.