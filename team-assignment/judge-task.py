#!/usr/bin/env python3
"""Судья выполнения задания team-assignment: «выполнено ли задание полностью?»

Изолированный LLM-судья (внешний к тестируемой команде): получает задание
(TASK.md), скоуп прогона (SCOPE.md), состав (team.md), отчёты команды,
результаты браузерного/UI-судей, дефекты владельца и рубрику — возвращает
строгий JSON: вердикт по каждому требованию задания + оси рубрики 0–4 +
итоговый ответ «выполнено полностью / частично / нет».

Запуск:
  python3 team-assignment/judge-task.py --run runs/team-inkling/run-01 \
      [--model glm-5.3-flash] [--thinking low]
Выход: <run>/judgments/judge-task.json (+ judge-task-run.log)
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

# требования задания, по которым судья даёт поэлементный вердикт
PROMPT_TMPL = """Ты — строгий судья командного тестового задания. Вопрос главного: ВЫПОЛНЕНО
ЛИ ЗАДАНИЕ ПОЛНОСТЬЮ? Отвечай не по отчётам команды (команда может
приукрашивать), а по совокупности evidence: независимого браузерного
прохождения, vision-оценки UI, дефектов владельца, журнала и отчётов.

## Требования задания (пройдись по каждому, вердикт: done / partial / fail / out-of-scope)
1. Веб-приложение DISC с нуля: PHP/Symfony бэкенд + фронтенд.
2. Анкета: 24 вопроса, 8 шагов × 3, ранжирование 4 прилагательных
   («наиболее/наименее похоже»), данные посимвольно как в questions.json.
3. Типы d/i/s/c не показываются пользователю.
4. Подсчёт баллов на бэкенде: позиция 1 = +1, позиция 4 = −1, средние = 0;
   шкалы ∈ [−24;+24], сумма = 0.
5. Экран результата: баллы + индивидуальная LLM-интерпретация на русском;
   при недоступности LLM — честная пометка, баллы показываются.
6. Отправка результата на почту (Symfony Mailer, DISC_SMTP_DSN).
7. Мобильный + десктоп браузеры.
8. Деплой на https://ai-aid.pro/disc-v-<имя версии>/, продукт реально работает.
9. Процесс: роли работают по назначению, журнал, отчёты, ревью, тесты.

## Формат ответа — ТОЛЬКО валидный JSON:
{{"requirements": [
    {{"req": 1, "verdict": "done|partial|fail|out-of-scope",
      "evidence": "кратко, со ссылками на evidence"}},
    … (по всем 9)
 ],
 "scores": {{"spec": 0, "prod": 0, "quality": 0, "team": 0}},
 "completed": "fully|partial|no",
 "completed_note": "одно предложение: что именно выполнено, что нет",
 "defects_confirmed": ["дефекты владельца/судей, которые судья подтверждает"],
 "notes": "резюме"}}

Шкала осей 0–4: 4 — полностью и точно; 3 — верно с мелочами; 2 — в целом
верно, единичные расхождения; 1 — существенно неполно; 0 — не выполнено
или переврано. Учитывай SCOPE: если пункт объявлен вне скоупа прогона —
верdict out-of-scope (но только если это честно зафиксировано и команда
не имела ресурсов его выполнить).

"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True, help="runs/<слаг>/run-XX")
    ap.add_argument("--model", default="glm-5.3-flash")
    ap.add_argument("--thinking", default="low")
    ap.add_argument("--timeout", type=int, default=900)
    args = ap.parse_args()

    run = Path(args.run).resolve()
    j = run / "judgments"
    j.mkdir(exist_ok=True)

    def read(p: Path, limit: int = 14000) -> str:
        return p.read_text(encoding="utf-8", errors="replace")[:limit] if p.is_file() else "(нет файла)"

    rubric = read(TA / "rubrics" / "scorecard.md")
    sections = {
        "ЗАДАНИЕ (TASK.md)": read(run / "workspace" / "TASK.md"),
        "СКОУП ПРОГОНА (SCOPE.md)": read(run / "workspace" / "SCOPE.md"),
        "СОСТАВ КОМАНДЫ (team.md)": read(run / "team.md"),
        "run.json (провенанс)": read(run / "run.json"),
        "ФИНАЛЬНЫЙ ОТЧЁТ КОМАНДЫ (team/final-report.md)": read(run / "workspace" / "team" / "final-report.md"),
        "ОТЧЁТ ТЕСТИРОВЩИКА (team/test-report.md)": read(run / "workspace" / "team" / "test-report.md"),
        "ЖУРНАЛ (team/journal.md)": read(run / "workspace" / "team" / "journal.md", 6000),
        "ДЕПЛОЙ-ИНСТРУКЦИЯ (team/deploy.md)": read(run / "workspace" / "team" / "deploy.md", 4000),
        "БРАУЗЕРНЫЙ СУДЬЯ (judge-browser.json)": read(run / "judgments" / "judge-browser.json"),
        "UI-СУДЬЯ (judge-ui.json)": read(run / "judgments" / "judge-ui.json"),
        "ДЕФЕКТЫ ВЛАДЕЛЬЦА (defects-owner.md)": read(run / "defects-owner.md"),
        "РУБРИКА (scorecard.md)": rubric,
    }
    body = "\n\n".join(f"# {k}\n{v}" for k, v in sections.items())
    prompt = PROMPT_TMPL + body

    log = j / "judge-task-run.log"
    cmd = ["pi", "-p", "--no-context-files", "--no-session",
           "--model", args.model, "--thinking", args.thinking]
    started = time.time()
    with log.open("w", encoding="utf-8") as out:
        p = subprocess.run(cmd + [prompt], cwd=run, stdout=out,
                           stderr=subprocess.STDOUT, text=True, timeout=args.timeout)
    dur = round(time.time() - started, 1)
    out_text = log.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"\{.*\}", out_text, re.S)
    verdict = json.loads(m.group(0)) if m else None

    meta = {
        "judge_model": args.model,
        "tier": "task-completion-external",
        "isolated": True,
        "question": "выполнено ли задание полностью",
        "completed": verdict.get("completed") if verdict else None,
        "scores": verdict.get("scores") if verdict else None,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "duration_s": dur,
        "exit_code": p.returncode,
        "verdict": verdict,
    }
    out = j / "judge-task.json"
    out.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if verdict is None:
        print("судья не вернул JSON — сырой ответ в", log)
        return 1
    print("Выполнено полностью?", meta["completed"], "| оси:", meta["scores"])
    print(json.dumps(verdict.get("requirements", []), ensure_ascii=False, indent=1)[:1200])
    print("verdict →", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
