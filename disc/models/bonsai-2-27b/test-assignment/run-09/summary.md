# Прогон: bonsai-2:ctx100k — run-09 (thinking medium)

- запущен: 2026-11-14T18:30:15.201449+00:00, длительность: 60:00, exit: 143, убит: да
- контекст/бюджет выхода: 102400 / 32768; промпт: v3 (sha 4b0ca9799499ed5b)
- сессия: 206 ходов, 205 вызовов инструментов; токены: вх 385,713 / вых 179,305
- сеть в bash: 11 обращений к источнику (curl/wget всего 14)
- масштаб параллельной нагрузки (VRAM): чисто

## Машинные проверки (check.json)

- файлы агента: 45; index.html: есть
- самодостаточность (внешние запросы): OK
- данные: прилагательных 84/84; пар текст+тип верно 96/96
- рендер-смоук (headless Chrome): OK
- автопрохождение (поток): OK, вопросов 24; баллы на экране — справочно (симуляция drag&drop не воспроизводима, логику проверяет судья по коду)
- скриншоты: /home/dp/MyProjects/disc/models/bonsai-2-27b/test-assignment/run-09/screenshots/start.png, /home/dp/MyProjects/disc/models/bonsai-2-27b/test-assignment/run-09/screenshots/step.png, /home/dp/MyProjects/disc/models/bonsai-2-27b/test-assignment/run-09/screenshots/result.png
- судья яруса 1: data 4, logic 4, ux 3, impl 4 — **15/16**
- **итог чека: PASSED**

Дальше: судья яруса 2 (обзор + сверка), при расхождениях — доработки в тот же run.