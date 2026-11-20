# qwen4-max (alibabacloud qwen-token-plan)

Флагманская Qwen (релизная версия preview) на подписке alibabacloud.
В disc участвует в анкете DISC: `quiz/` (ru) + `quiz-en/` (en).

- Провайдер: alibabacloud, подписка; endpoint
  `https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1`;
  ключ — запись `qwen-token-plan-individual` в `~/.pi/agent/auth.json`
- Документированная шкала (help.aliyun.com, qwen4-max): reasoning_effort =
  **low / high / xhigh** (дефолт high; minimal→low, **medium→high**,
  max→xhigh); off — enable_thinking=false (дефолты non-thinking: temp 0.7).
  medium не запускали — документированный дубль high.
- Версия API: `qwen4-max`

## quiz — анкета DISC (2026-11-17, ru + en, по 2 прогона на уровень)

| | off | low | high | xhigh |
|---|---|---|---|---|
| ru | **16.0 (67%)** | 13.5 (56%) | 15.0 (62%) | 15.0 (62%) |
| en | 17.5 (76%) | 16.5 (72%) | 16.0 (70%) | **17.5 (76%)** |

Шаблон семейства повторяется: лучший результат на off (ru), на en off и
xhigh паритет (17.5). Язык: +7.4 п.п. на en. Середняк сетки — как preview
и карта знаний (общие знания велики, методология курса не улучшилась).
json_ok 100%, во всех группах 2 уникальных набора из 2 прогонов.
Квота: 16 прогонов, ~9.2k вх / ~20.5k вых токенов — `reports/spend.csv`.
Детали: `quiz/run-01…08`, `quiz-en/run-01…08`, свод `reports/QUIZ.md/.html`.
