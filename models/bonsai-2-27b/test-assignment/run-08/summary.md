# Прогон: bonsai-2:ctx100k — run-08 (thinking medium)

- запущен: 2026-11-14T17:46:34.495285+00:00, длительность: 43:13, exit: 0, убит: нет
- контекст/бюджет выхода: 102400 / 32768; промпт: v3 (sha 4b0ca9799499ed5b)
- сессия: 236 ходов, 235 вызовов инструментов; токены: вх 380,480 / вых 175,225
- сеть в bash: 9 обращений к источнику (curl/wget всего 9)
- масштаб параллельной нагрузки (VRAM): чисто

## Машинные проверки (check.json)

- файлы агента: 15; index.html: есть
- самодостаточность (внешние запросы): OK
- данные: прилагательных 84/84; пар текст+тип верно 96/96
- рендер-смоук (headless Chrome): OK
- автопрохождение (поток): OK, вопросов 24; баллы на экране — справочно (симуляция drag&drop не воспроизводима, логику проверяет судья по коду)
- скриншоты: /home/dp/MyProjects/disc/models/bonsai-2-27b/test-assignment/run-08/screenshots/start.png, /home/dp/MyProjects/disc/models/bonsai-2-27b/test-assignment/run-08/screenshots/step.png, /home/dp/MyProjects/disc/models/bonsai-2-27b/test-assignment/run-08/screenshots/result.png
- судья яруса 1: data 4, logic 4, ux 4, impl 4 — **16/16**
- **итог чека: PASSED**

Дальше: судья яруса 2 (обзор + сверка), при расхождениях — доработки в тот же run.