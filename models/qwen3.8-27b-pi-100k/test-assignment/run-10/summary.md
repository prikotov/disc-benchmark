# Прогон: qwen3.8:27b-pi-100k — run-10 (thinking xhigh)

- запущен: 2026-11-15T03:44:28.838501+00:00, длительность: 21:08, exit: 0, убит: нет
- контекст/бюджет выхода: 102400 / 32768; промпт: v3 (sha 4b0ca9799499ed5b)
- сессия: 91 ходов, 94 вызовов инструментов; токены: вх 196,091 / вых 91,291
- сеть в bash: 4 обращений к источнику (curl/wget всего 5)
- масштаб параллельной нагрузки (VRAM): чисто

## Машинные проверки (check.json)

- файлы агента: 4; index.html: есть
- самодостаточность (внешние запросы): OK
- данные: прилагательных 84/84; пар текст+тип верно 96/96
- рендер-смоук (headless Chrome): OK
- автопрохождение (поток): OK, вопросов 24; баллы на экране — справочно (симуляция drag&drop не воспроизводима, логику проверяет судья по коду)
- скриншоты: /home/dp/MyProjects/disc/models/qwen3.8-27b-pi-100k/test-assignment/run-10/screenshots/start.png, /home/dp/MyProjects/disc/models/qwen3.8-27b-pi-100k/test-assignment/run-10/screenshots/step.png, /home/dp/MyProjects/disc/models/qwen3.8-27b-pi-100k/test-assignment/run-10/screenshots/result.png
- судья яруса 1: data 4, logic 4, ux 4, impl 4 — **16/16**
- **итог чека: PASSED**

Дальше: судья яруса 2 (обзор + сверка), при расхождениях — доработки в тот же run.