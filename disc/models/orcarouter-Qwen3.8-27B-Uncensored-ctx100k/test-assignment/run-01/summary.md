# Прогон: orcarouter/Qwen3.8-27B-Uncensored:ctx100k — run-01 (thinking off)

- запущен: 2026-11-15T06:29:06.152465+00:00, длительность: 6:39, exit: 0, убит: нет
- контекст/бюджет выхода: 102400 / 8192; промпт: v3 (sha 4b0ca9799499ed5b)
- сессия: 26 ходов, 25 вызовов инструментов; токены: вх 58,748 / вых 25,550
- сеть в bash: 3 обращений к источнику (curl/wget всего 3)
- масштаб параллельной нагрузки (VRAM): muse-glimmer:ctx100k

## Машинные проверки (check.json)

- файлы агента: 1; index.html: есть
- самодостаточность (внешние запросы): OK
- данные: прилагательных 84/84; пар текст+тип верно 96/96
- рендер-смоук (headless Chrome): OK
- автопрохождение (поток): не прошло/не выполнялось; баллы на экране — справочно (симуляция drag&drop не воспроизводима, логику проверяет судья по коду)
- скриншоты: /home/dp/MyProjects/disc/models/orcarouter-Qwen3.8-27B-Uncensored-ctx100k/test-assignment/run-01/screenshots/start.png, /home/dp/MyProjects/disc/models/orcarouter-Qwen3.8-27B-Uncensored-ctx100k/test-assignment/run-01/screenshots/result.png
- судья яруса 1: не выполнялся
- **итог чека: PASSED**

Дальше: судья яруса 2 (обзор + сверка), при расхождениях — доработки в тот же run.