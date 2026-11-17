#!/usr/bin/env python3
"""Прогон английской анкеты DISC — шим над quiz/runner.py.

Вся механика (вызовы, парсинг, scoring, облака, decision-протокол) — общая,
язык задаётся ключом (key-en.json: lang=en + английские формулировки) и
машинной директорией прогонов (models/<модель>/quiz-en/run-XX). Отчёт
(report.py) агрегирует оба языка в общий reports/QUIZ.md/.html.

Запуск: python3 quiz-en/runner.py --model <тег> [--runs 5] [--thinking LVL]
"""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent          # quiz-en/
sys.path.insert(0, str(HERE.parent / "quiz"))
import runner as R  # noqa: E402

R.KEY = json.loads((HERE / "reference" / "key-en.json").read_text(encoding="utf-8"))
R.LANG = R.KEY["lang"]
R.QUIZ_DIRNAME = "quiz-en"
R.MATRIX_PATH = HERE / "models.json"
data = json.loads((HERE / "prompts" / "prompt.json").read_text(encoding="utf-8"))
R.PROMPT_VER = data["version"]
R.PROMPT_SHA = hashlib.sha256(data["prompt"].encode()).hexdigest()
R.PROMPT = data["prompt"]

if __name__ == "__main__":
    sys.exit(R.main())
