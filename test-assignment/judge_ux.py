#!/usr/bin/env python3
"""Vision-судья UX/UI: оценивает скриншоты решения (start/step/result)
через glm-5.3-flash (pi, vision). Дополняет объективные проверки драйвера.

Оценивает (0–100): первый экран и понятность старта, вёрстку шагов,
читаемость (контраст/размеры), визуальную целостность результата,
отсутствие визуального мусора. Технические ограничения (самодостаточность,
отсутствие сети) проверяет чекер — здесь только визуал/UX.

Запуск: python3 test-assignment/judge_ux.py --run models/<м>/test-assignment/run-01
Выход:  <run>/judge-ux.json  {"score": 0–100, "issues": [...], "notes": ...}
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

PROMPT = """Ты — UX/UI-ревьюер. Перед тобой три скриншота одной веб-страницы
(приложения-теста личности): стартовый экран, шаг с вопросами, экран результата.

Оцени визуальное качество и юзабилити по скриншотам строго и придирчиво.
Критерии:
1. Понятность старта: заголовок, описание, заметная кнопка начала.
2. Вёрстка шагов: сетка карточек не разваливается, элементы выровнены,
   нет наложений и обрезанного текста.
3. Читаемость: контраст, размеры шрифта, отступы.
4. Экран результата: баллы видны и читаемы, нет пустых зон и обломков вёрстки.
   На экране ШАГА с вопросами блока результата быть НЕ должно: если числа
   D:…/I:…/S:…/C:… видны до завершения теста — это серьёзный дефект потока.
5. Визуальный мусор: неотстилёванные HTML-куски, сырые {..}, битые иконки,
   дублирование блоков.

Шкала: 0–100, где 90+ — аккуратное продакшн-приложение; 70–89 — добротное;
50–69 — работает, но с заметными шероховатостями; 30–49 — бедно/глючно;
менее 30 — визуальный хаос.

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
    ap.add_argument("--run", required=True)
    ap.add_argument("--model", default="glm-5.3-flash")
    ap.add_argument("--thinking", default="low")
    ap.add_argument("--timeout", type=int, default=600)
    args = ap.parse_args()

    run = Path(args.run).resolve()
    shots = run / "screenshots"
    shots = [shots / n for n in ("start.png", "step.png", "result.png") if (shots / n).is_file()]
    if not shots:
        print("нет скриншотов — судья не выполнялся")
        return 1

    files = [f"@{p}" for p in shots]
    prompt = PROMPT + "\n\nПриложенные скриншоты: стартовый экран, шаг с вопросами, экран результата."
    # pi -p: @файлы — аттачменты, финальный позиционный аргумент — промпт
    cmd = ["pi", "-p", "--no-context-files", "--no-session",
           "--model", args.model, "--thinking", args.thinking]
    log = run / "judge-ux-run.log"
    started = time.time()
    with log.open("w", encoding="utf-8") as out:
        p = subprocess.run(cmd + files + [prompt], cwd=run, stdout=out,
                           stderr=subprocess.STDOUT, text=True, timeout=args.timeout)
    dur = round(time.time() - started, 1)
    out_text = log.read_text(encoding="utf-8", errors="replace")
    verdict = extract_json(out_text)

    meta = {
        "judge_model": args.model,
        "tier": "ux-vision",
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "duration_s": dur,
        "exit_code": p.returncode,
        "verdict": verdict,
    }
    (run / "judge-ux.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if verdict is None:
        print("судья не вернул JSON — сырой ответ в judge-ux-run.log")
        return 1
    print(json.dumps(verdict, ensure_ascii=False, indent=2)[:600])
    return 0


if __name__ == "__main__":
    sys.exit(main())
