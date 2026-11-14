# huihui_ai-Qwen3.8-abliterated-ctx100k

> Карточка перенесена из сестринского workspace `~/MyProjects/Models` (2026-11-14).
> Разделы о результатах других исследований (собесы, карта знаний, их этап 2 «биллинг») —
> контекст того workspace и в выводы disc не переносится; операционные наблюдения
> (контекст/токены/провайдерские нюансы/поведение агентом) применимы напрямую.
> Свежие факты по тегу: см. `/api/show` nserv, сверка 2026-11-14. Результаты disc —
> в разделе «disc» внизу.

<!-- источник: ~/MyProjects/Models/models/huihui_ai-Qwen3.8-abliterated-latest/model.md -->

# huihui_ai/Qwen3.8-abliterated:latest

Источник: ollama на ollama-host (`http://ollama-host:11434`).

- Архитектура/семейство: qwen35
- Параметры: 27.3B
- Квантизация: Q4_K_M
- Контекст: 262144
- Размер: 16.5 GB
- Возможности: completion, vision, tools, thinking
- Мышление: та же ручка, что у qwen3.8 — `false / low / medium / xhigh`,
  дефолт `medium` (проверено на ollama-host, ollama 0.40.0; `/api/show` →
  `thinking.values`). Выставлять — полем верхнего уровня тела `/api/chat`
  (не в `options`), уровень строкой:
  `curl http://ollama-host:11434/api/chat -d '{"model":"huihui_ai/Qwen3.8-abliterated:latest","messages":[…],"think":"low"}'`.
  Серии backend run-01…10 — `think: false` поверх дефолтного `medium`,
  т.е. напрямую сопоставимы с qwen3.8 `think: false`.
- Дайджест: `bdc5e13cd1645bc4…`
- Обновлён: 2026-10-12

Статус: папка создана, тестов пока не было. Результаты — рядом, в этой папке.

## disc — копирование DISC-теста (агентные прогоны pi)

(заполняется по мере прогонов; условия — в run.json, машинные проверки — в check.json, вердикты судей — рядом)
