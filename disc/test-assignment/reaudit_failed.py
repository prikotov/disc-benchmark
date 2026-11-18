#!/usr/bin/env python3
"""Самопроверка FAILED-прогонов обновлённым инструментарием.

Для каждого FAILED-прогона (машина: чек + автопрохождение + отображённые числа):
1. перезапускает чекер (с рендер-извлечением данных для динамических приложений);
2. если приложение живое (слова находятся) — переигрывает автопрохождение
   текущим драйвером (все починенные форматы парсера и эвристики);
3. если и в отрисованном DOM данных нет — помечает «приложение мертво»,
   драйвер не тратит время.

Итог: reports/REAUDIT.md + reports/REAUDIT.json (старый статус → новый,
перевороты FAILED→PASSED отдельно). Запуск: python3 reaudit_failed.py
"""
from __future__ import annotations
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PT = ROOT / "test-assignment"


def load(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def machine_status(run: Path):
    chk = load(run / "check.json")
    pt = load(run / "playthrough.json")
    check_passed = bool(chk.get("passed"))
    flow_ok = bool(pt.get("flow_ok"))
    has_display = pt.get("displayed") is not None
    has_app = (run / "index.html").is_file()
    passed = has_app and check_passed and flow_ok and has_display
    return {"has_app": has_app, "check": check_passed, "flow": flow_ok,
            "display": has_display, "passed": passed,
            "displayed": pt.get("displayed"),
            "match": pt.get("displayed_match")}


def run_cmd(cmd, cwd, timeout):
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return p.returncode == 0
    except Exception:
        return False


def main() -> int:
    rows, flips = [], []
    dead_skipped = 0
    runs = sorted(p for p in (ROOT / "models").glob("*/test-assignment/run-*")
                  if "_original" not in str(p) and (p / "index.html").is_file())
    failed = [r for r in runs if not machine_status(r)["passed"]]
    print(f"FAILED-прогонов с решением: {len(failed)} из {len(runs)}", flush=True)
    for i, run in enumerate(failed, 1):
        rel = str(run.relative_to(ROOT / "models"))
        old = machine_status(run)
        t0 = time.time()

        # 1) чекер заново (рендер-извлечение внутри)
        run_cmd([sys.executable, "check.py", "--run", str(run)], cwd=PT, timeout=180)
        chk = load(run / "check.json")
        words = (chk.get("data") or {}).get("adjectives_found") or 0

        note = ""
        if not chk.get("passed") and words == 0:
            dead_skipped += 1
            new = machine_status(run)
            note = "приложение мертво: данных нет даже в отрисованном DOM"
        else:
            # 2) переиграть автопрохождение текущим драйвером
            run_cmd(["node", "playthrough.mjs",
                     "--html", str(run / "index.html"),
                     "--ref", "reference/questions.json",
                     "--out-dir", str(run / "screenshots"),
                     "--json", str(run / "playthrough.json")],
                    cwd=PT, timeout=300)
            new = machine_status(run)

        verdict = ("ПЕРЕВОРОТ → PASSED" if new["passed"] and not old["passed"]
                   else "подтверждён FAILED" if not new["passed"]
                   else "стал FAILED (был PASSED?!)")
        if new["passed"] and not old["passed"]:
            flips.append({"run": rel, "old": old, "new": new})
        rows.append({"run": rel, "old": old, "new": new,
                     "note": note, "sec": round(time.time() - t0),
                     "verdict": verdict})
        print(f"[{i}/{len(failed)}] {rel}: {verdict}"
              + (f" ({note})" if note else ""), flush=True)

    # отчёт
    md = ["# Самопроверка FAILED-прогонов", "",
          f"Дата: {time.strftime('%Y-%m-%d %H:%M')} · FAILED с решением: {len(failed)} · "
          f"переворотов: {len(flips)} · мёртвых пропущено: {dead_skipped}", ""]
    if flips:
        md += ["## Перевороты FAILED → PASSED", ""]
        for f in flips:
            md.append(f"- **{f['run']}**: displayed={f['new']['displayed']}")
        md.append("")
        md.append("Такие прогоны требуют переоценки судьёй (артефакты изменились).")
        md.append("")
    md += ["## Все проверки", "", "| прогон | было | стало | вывод |",
           "|---|---|---|---|"]
    for r in rows:
        o, n = r["old"], r["new"]
        o_s = "PASSED" if o["passed"] else ("нет flow" if not o["flow"] else
              ("нет чисел" if not o["display"] else "чек FAIL"))
        n_s = "PASSED" if n["passed"] else "FAILED"
        md.append(f"| {r['run']} | {o_s} | {n_s} | {r['verdict']} |")
    (ROOT / "reports" / "REAUDIT.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (ROOT / "reports" / "REAUDIT.json").write_text(
        json.dumps({"rows": rows, "flips": flips}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    print(f"ИТОГ: переворотов {len(flips)}, отчёты записаны", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
