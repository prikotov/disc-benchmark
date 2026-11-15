#!/usr/bin/env python3
"""Пакет дополнительных прогонов: +2 на каждый (модель × уровень мышления),
уже присутствующий в отчёте. Полный пайплайн на каждый прогон:
runner.py → check.py → playthrough.mjs → judge.py → judge_ux.py.

Нумерация run-XX сквозная по папке модели (занятые номера пропускаются).
Повторный запуск идемпотентен: существующие каталоги не трогаются.

Запуск:  nohup python3 test-assignment/batch_extra.py > reports/batch_extra.log 2>&1 &
Прогресс: tail -f reports/batch_extra.log
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
NOW = lambda: datetime.now(timezone.utc).strftime("%H:%M:%S")


def log(msg: str) -> None:
    print(f"[{NOW()}] {msg}", flush=True)


def sh(cmd: list[str], timeout: int) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=ROOT)
        tail = (r.stdout or "").strip().splitlines()[-3:]
        return r.returncode, " | ".join(tail)
    except subprocess.TimeoutExpired:
        return 124, "timeout"


def main() -> int:
    # 1) собрать пары (модель × уровень) из существующих прогонов
    pairs: dict[tuple[str, str], str] = {}
    folder_max: dict[str, int] = {}
    for rj in sorted(ROOT.glob("models/*/test-assignment/run-*/run.json")):
        d = json.loads(rj.read_text(encoding="utf-8"))
        if d.get("smoke"):
            continue
        folder = rj.relative_to(ROOT).parts[1]
        runno = int(rj.parts[-2].split("-")[1])
        folder_max[folder] = max(folder_max.get(folder, 0), runno)
        pairs[(d.get("model"), d.get("thinking"))] = folder

    # 2) план: по 2 прогона на пару, нумерация по папке
    plan: list[dict] = []
    for (model, thinking), folder in sorted(pairs.items()):
        if not model or not thinking:
            continue
        for _ in range(2):
            n = folder_max[folder] + 1
            while (Path(folder) / "test-assignment" / f"run-{n:02d}").exists():
                n += 1
            folder_max[folder] = n
            plan.append({"model": model, "thinking": thinking,
                         "dir": str(Path(folder) / "test-assignment" / f"run-{n:02d}")})

    log(f"план: {len(plan)} прогонов")
    for p in plan:
        log(f"  {p['model']} [{p['thinking']}] → {p['dir']}")

    ok = err = 0
    for i, p in enumerate(plan, 1):
        d = Path(p["dir"])
        if d.exists():
            log(f"[{i}/{len(plan)}] {d} уже есть — пропуск")
            continue
        log(f"[{i}/{len(plan)}] RUN {p['model']} [{p['thinking']}] → {d.name}")
        rc, tail = sh(["python3", str(HERE / "runner.py"),
                       "--model", p["model"], "--thinking", p["thinking"],
                       "--results", d], timeout=3700)
        log(f"  runner: rc={rc} {tail}")
        if not (d / "index.html").is_file():
            log("  нет index.html — проверки пропущены")
            err += 1
            continue
        rc2, t2 = sh(["python3", str(HERE / "check.py"), "--run", str(d)], timeout=600)
        log(f"  check: rc={rc2} {t2}")
        rc3, t3 = sh(["node", str(HERE / "playthrough.mjs"),
                      "--html", str(d / "index.html"),
                      "--ref", str(HERE / "reference" / "questions.json"),
                      "--out-dir", str(d / "screenshots"),
                      "--json", str(d / "playthrough.json")], timeout=600)
        log(f"  playthrough: rc={rc3} {t3}")
        rc4, t4 = sh(["python3", str(HERE / "judge.py"), "--run", str(d)], timeout=1300)
        log(f"  judge: rc={rc4} {t4}")
        rc5, t5 = sh(["python3", str(HERE / "judge_ux.py"), "--run", str(d)], timeout=700)
        log(f"  judge_ux: rc={rc5} {t5}")
        if rc == 0 and rc2 == 0:
            ok += 1
        else:
            err += 1

    log(f"ГОТОВО: успешно {ok}, с проблемами {err}, всего {len(plan)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
