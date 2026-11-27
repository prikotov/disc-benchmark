#!/usr/bin/env python3
"""Vision-судья UI team-assignment: оценивает скриншоты браузерного
прохождения (старт, шаги, email, результат) через внешнюю vision-модель
(glm-5.3-flash, pi -p с @аттачментами). Внешний = не участвует в
тестируемой команде и изолирован: один запрос, без истории.

Дополняет judge-browser.mjs (объективные проверки) эстетикой/UX.

Запуск:
  python3 team-assignment/judge-ui.py --run runs/team-inkling/run-01 \
      [--model glm-5.3-flash] [--thinking low]
Выход: runs/<слаг>/run-XX/judgments/judge-ui.json
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

TA = Path(__file__).resolve().parent

PROMPT = """Ты — строгий UX/UI-ревьюер. Перед тобой скриншоты веб-приложения
(тест личности DISC), снятые браузерным судьёй в headless Chrome:
стартовый экран, шаги с вопросами (ранжирование 4 прилагательных), шаг
ввода email, экран результата с баллами и интерпретацией.

Оцени визуальное качество и юзабилити придирчиво. Критерии:
1. Понятность старта: заголовок, описание, заметная кнопка начала.
2. Вёрстка шагов: сетка карточек не разваливается, прилагательные
   читаемы, стрелки/ручки ранжирования заметны и выровнены, прогресс
   виден.
3. Шаг email: понятное поле, валидация видна, кнопка результат заметна.
4. Экран результата: баллы D/I/S/C видны и читаемы, интерпретация —
   цельный структурированный текст (если текст визуально обрывается на
   середине предложения — это дефект, отметь), нет пустых зон.
5. Визуальный мусор: нестлилеванные HTML-куски, сырые {..}, битые
   иконки, наложения, обрезанный текст в карточках.

Шкала: 0–100, где 90+ — аккуратное продакшн-приложение; 70–89 —
добротное; 50–69 — работает, но с заметными шероховатостями; 30–49 —
бедно/глючно; менее 30 — визуальный хаос.

Верни ТОЛЬКО валидный JSON без пояснений вокруг:
{"score": 0, "issues": ["список визуальных проблем"], "notes": "краткое резюме"}"""


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
    ap.add_argument("--run", required=True, help="runs/<слаг>/run-XX")
    ap.add_argument("--model", default="glm-5.3-flash")
    ap.add_argument("--thinking", default="low")
    ap.add_argument("--timeout", type=int, default=900)
    args = ap.parse_args()

    run = Path(args.run).resolve()
    shots_dir = run / "judgments" / "browser"
    order = ["start.png", "step-01.png", "step-04.png", "step-08.png",
             "email.png", "result.png"]
    shots = [shots_dir / n for n in order if (shots_dir / n).is_file()]
    if not shots:
        print("нет скриншотов — сначала запусти judge-browser.mjs")
        return 1

    files = [f"@{p}" for p in shots]
    names = ", ".join(p.name for p in shots)
    prompt = PROMPT + f"\n\nПриложенные скриншоты, по порядку: {names}."
    cmd = ["pi", "-p", "--no-context-files", "--no-session",
           "--model", args.model, "--thinking", args.thinking]
    log = run / "judgments" / "judge-ui-run.log"
    started = time.time()
    with log.open("w", encoding="utf-8") as out:
        p = subprocess.run(cmd + files + [prompt], cwd=run, stdout=out,
                           stderr=subprocess.STDOUT, text=True, timeout=args.timeout)
    dur = round(time.time() - started, 1)
    out_text = log.read_text(encoding="utf-8", errors="replace")
    verdict = extract_json(out_text)

    meta = {
        "judge_model": args.model,
        "tier": "ui-vision-external",
        "isolated": True,
        "screenshots": [p.name for p in shots],
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "duration_s": dur,
        "exit_code": p.returncode,
        "verdict": verdict,
    }
    out_json = run / "judgments" / "judge-ui.json"
    out_json.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    if verdict is None:
        print("судья не вернул JSON — сырой ответ в", log)
        return 1
    print(json.dumps(verdict, ensure_ascii=False, indent=2)[:800])
    return 0


if __name__ == "__main__":
    sys.exit(main())
