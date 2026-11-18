#!/usr/bin/env python3
"""Судья яруса 1: изолированный LLM-вердикт по рубрике (scorecard.md).

Судья получает: рубрику, машинные проверки (check.json, playthrough.json),
статистику сессии и ПОЛНЫЙ КОД решения — и возвращает строгий JSON-вердикт
по четырём осям 0–4 (data / logic / ux / impl) с примерами.

Модель судьи — по умолчанию glm-5.3-flash (z.ai, через дефолтный конфиг pi);
судья — НЕ кандидат (см. AGENTS.md «Не кандидаты»). Судья изолирован:
один ответ → один вызов, cwd — каталог прогона, --no-context-files.

Запуск: python3 test-assignment/judge.py --run models/<м>/test-assignment/run-01
Выход: <run>/judge-tier1.json (вердикт) + <run>/judge-session/ (след судьи).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent


def build_prompt(run: Path) -> str:
    rubric = (HERE / "rubrics" / "scorecard.md").read_text(encoding="utf-8")
    check = (run / "check.json").read_text(encoding="utf-8") if (run / "check.json").is_file() else "{}"
    play = (run / "playthrough.json").read_text(encoding="utf-8") if (run / "playthrough.json").is_file() else "{}"
    stats = (run / "session-stats.json").read_text(encoding="utf-8") if (run / "session-stats.json").is_file() else "{}"
    solution = ""
    index = run / "index.html"
    if index.is_file():
        solution = index.read_text(encoding="utf-8", errors="replace")
    ref = (HERE / "reference" / "questions.json").read_text(encoding="utf-8")

    return f"""Ты — строгий судья тестового задания для LLM: модель должна была самостоятельно
изучить DISC-тест на сайте Stratoplan и воспроизвести его как самодостаточное
HTML-приложение (один файл index.html, без бэкенда, без отправки данных, без внешних
запросов, работает офлайн).

Оцени решение по рубрике ниже. Оси: data (точность переноса данных теста),
logic (точность переноса подсчёта), ux (точность переноса потока и работоспособность),
impl (качество реализации и адаптации под ограничения). Каждая ось 0–4.
Рабочие файлы агента рядом с index.html (скачанные исходники, тест-скрипты) —
НЕ недостаток и не штрафуются.

# РУБРИКА
{rubric}

# ЭТАЛОН ДАННЫХ (questions.json; типы — служебные)
{ref}

# МАШИННЫЕ ПРОВЕРКИ (check.json)
{check}

# АВТОПРОХОЖДЕНИЕ (playthrough.json). Раскладка драйвера воспроизводима и
# одинакова во всех прогонах: при эталонной раскладке на экране ДОЛЖНО быть
# ровно D=5, I=2, S=-3, C=-4. Если "displayed" отличается от эталона — в
# приложении баг подсчёта В РАНТАЙМЕ (код может выглядеть верно): ставь
# logic не выше 1 и опиши расхождение в notes. Совпадает — логику дополнительно
# сверяй с кодом.
{play}

# СТАТИСТИКА СЕССИИ АГЕНТА
{stats}

# КОД РЕШЕНИЯ (index.html, полный)
```html
{solution}
```

Верди по КОДУ подсчёта (проследи алгоритм: мажор = позиция 1 (+1), минор = позиция 4 (−1),
балл типа = разность; проверь вручную на контрольном примере: 24 вопроса, мажор/минор
по раскладке на твой выбор — пересчитай, что выведет код).
Верни ТОЛЬКО валидный JSON без пояснений вокруг:
{{"data": 0, "logic": 0, "ux": 0, "impl": 0, "total": 0,
 "notes": "краткое резюме", "examples": "конкретные примеры по каждой оси"}}"""


def extract_json(text: str) -> dict | None:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True)
    ap.add_argument("--model", default="glm-5.3-flash")
    ap.add_argument("--thinking", default="low")
    ap.add_argument("--timeout", type=int, default=1200)
    args = ap.parse_args()

    run = Path(args.run).resolve()
    prompt = build_prompt(run)
    log = run / "judge-run.log"
    started = time.time()

    # промпт передаём через stdin: длинные решения упираются в лимит
    # одного argv (MAX_ARG_STRLEN ~128KB)
    cmd = ["pi", "-p", "--no-context-files", "--no-session",
           "--model", args.model, "--thinking", args.thinking]
    with log.open("w", encoding="utf-8") as out:
        p = subprocess.run(cmd, cwd=run, input=prompt, stdout=out,
                           stderr=subprocess.STDOUT, text=True,
                           timeout=args.timeout)
    dur = round(time.time() - started, 1)
    out_text = log.read_text(encoding="utf-8", errors="replace")
    verdict = extract_json(out_text)

    meta = {
        "judge_model": args.model,
        "thinking": args.thinking,
        "tier": 1,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "duration_s": dur,
        "exit_code": p.returncode,
        "prompt_chars": len(prompt),
        "verdict": verdict,
    }
    (run / "judge-tier1.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if verdict is None:
        print("судья не вернул JSON — сырой ответ в judge-run.log")
        return 1
    print(json.dumps(verdict, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
