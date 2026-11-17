# qwen4-max-preview

> Карточка перенесена из сестринского workspace `~/MyProjects/Models` (2026-11-14).
> Разделы о результатах других исследований (собесы, карта знаний, их этап 2 «биллинг») —
> контекст того workspace и в выводы disc не переносится; операционные наблюдения
> (контекст/токены/провайдерские нюансы/поведение агентом) применимы напрямую.
> Свежие факты по тегу: см. `/api/show` nserv, сверка 2026-11-14. Результаты disc —
> в разделе «disc» внизу.

<!-- источник: ~/MyProjects/Models/models/qwen4-max-preview-low/model.md -->

# qwen4-max-preview (alibabacloud qwen-token-plan)

## Характеристики

- Модель: `qwen4-max-preview` — флагманская Qwen следующего поколения
  на подписке alibabacloud (Model Studio token plan); в pi-каталоге
  числится, custom id через `--provider qwen-token-plan-individual`
- Транспорт: `knowledge-map/runner_pi.py` (pi -p --no-session per
  клетка, `--mode json` отдаёт usage: input/output/cacheRead/reasoning)
- **Нюанс off (исправлено 2026-11-12)**: pi не передаёт alibabacloud
  `enable_thinking:false` — запрошенный off эскалируется в low;
  «off»-прогон от 2026-11-12 фактически был low и перенесён в run-02
  этой серии. Нативная шкала провайдера: off (enable_thinking:false) /
  low / medium / high (xhigh) — будущие прогоны off/medium пойдут
  через прямой транспорт runner_cloud.py

## Карта знаний PHP (2026-11-12, 2 прогона low)

- run-01 (low): база **237/240 = 98.8%**, Глубина **54/56 = 96.4%**,
  всего **291/296 = 98.3%**; 54k вх + 33k вых; 25.7 мин
- run-02 (low, изначально запущен как «off»): база **233/240 = 97.1%**,
  Глубина **54/56 = 96.4%**, всего **287/296 = 97.0%**; 60k вх + 35k вых;
  27.7 мин
- Оба прогона low: верх доски карты (рядом sol 98.2 — solo-прогон);
  «97.0% на off» из первого объявления было вторым прогоном low
- Ошибки run-02 (6): T07-L8 (PHPUnit-детали), VC-L8 и VF-L1 (версии
  «текущая минорная» — ответил 8.5 вместо 8.6), VF-L3, T12-L10
  (бит E_STRICT), T21-L10 (Twig-исключение)
- Токены: alibabacloud считает reasoning отдельно и в output не включает

Результаты: knowledge-map/run-01, run-02 (report.html, session.json,
answers.csv).

## disc — копирование DISC-теста (агентные прогоны pi)

(заполняется по мере прогонов; условия — в run.json, машинные проверки — в check.json, вердикты судей — рядом)

## quiz — анкета DISC (2026-11-17, ru + en, по 2 прогона на уровень)

Транспорт: прямой API alibabacloud (quiz/runner.py; enable_thinking=False
для off — честный off: reasoning=0, ~6 с, пилот подтвердил). Версия API:
`qwen4.0-max-preview`.

**ru: off 17.0 (71%) → low 14.5 → medium 14.0 → high 15.0**
**en: off 18.5 (80%) → low 15.5 → medium 14.5 → high 15.0**

Флагман Qwen — середняк анкеты, и лестница уровней **обратная**: лучший
результат на off, любое рассуждение снижает балл (−5…−3). Язык: +9.6 п.п.
на английском (как у всех qwen-моделей). Похожий профиль у карты знаний
(98% — верх доски): общие знания велики, методология курса — нет.
Квота: 2×4×2 = 16 прогонов, 9.2k вх / 21.1k вых токенов (reasoning
отдельно) — `reports/spend.csv`.
Детали: `quiz/run-01…08`, `quiz-en/run-01…08`.
