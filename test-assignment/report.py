#!/usr/bin/env python3
"""Агрегация прогонов и отчёты.

- report.py --run <dir>            — свод одного прогона: <run>/summary.md
                                     + строка в scorecard модели;
- report.py --all                  — кросс-модельный reports/RUNS.md по всем
                                     найденным прогонам models/*/test-assignment/run-*.

Источники: run.json, check.json, session-stats.json, вердикты судей (позже).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(run: Path, name: str) -> dict:
    p = run / name
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}


def fmt_dur(s: float | None) -> str:
    if s is None:
        return "—"
    m, sec = divmod(int(s), 60)
    return f"{m}:{sec:02d}"


def run_row(run: Path) -> dict:
    meta = load(run, "run.json")
    chk = load(run, "check.json")
    st = load(run, "session-stats.json")
    model = meta.get("model") or run.parts[-3]
    return {
        "model": model,
        "run": run.name,
        "thinking": meta.get("thinking"),
        "duration_s": meta.get("duration_s"),
        "exit_code": meta.get("exit_code"),
        "killed": meta.get("killed"),
        "tokens_in": st.get("tokens_in"),
        "tokens_out": st.get("tokens_out"),
        "tool_calls": st.get("tool_calls"),
        "curl_source": st.get("curl_to_source"),
        "files": len(meta.get("files", [])),
        "index_html": chk.get("index_html", run.joinpath("index.html").is_file()),
        "external_pass": (chk.get("external") or {}).get("pass"),
        "data_found": (chk.get("data") or {}).get("adjectives_found"),
        "data_total": (chk.get("data") or {}).get("adjectives_total"),
        "types_correct": (chk.get("types") or {}).get("correct"),
        "types_extracted": (chk.get("types") or {}).get("extracted"),
        "smoke_ok": (chk.get("smoke") or {}).get("ok"),
        "check_passed": chk.get("passed"),
    }


def one_run_summary(run: Path) -> str:
    r = run_row(run)
    meta = load(run, "run.json")
    chk = load(run, "check.json")
    st = load(run, "session-stats.json")
    lines = [
        f"# Прогон: {r['model']} — {r['run']} (thinking {r['thinking']})",
        "",
        f"- запущен: {meta.get('started_at','—')}, длительность: {fmt_dur(r['duration_s'])}, "
        f"exit: {r['exit_code']}, убит: {'да' if r['killed'] else 'нет'}",
        f"- контекст/бюджет выхода: {meta.get('context')} / {meta.get('max_tokens')}; "
        f"промпт: v{meta.get('prompt_version')} (sha {meta.get('prompt_sha256')})",
        f"- сессия: {st.get('turns', '—')} ходов, {r['tool_calls']} вызовов инструментов; "
        f"токены: вх {r['tokens_in']:,} / вых {r['tokens_out']:,}" if st else "- сессия: нет статистики",
        f"- сеть в bash: {r['curl_source']} обращений к источнику "
        f"(curl/wget всего {st.get('bash_with_network', '—')})",
        f"- масштаб параллельной нагрузки (VRAM): "
        f"{', '.join(meta.get('ollama_foreign_models', [])) or 'чисто'}",
        "",
        "## Машинные проверки (check.json)",
        "",
        f"- файлы агента: {r['files']}; index.html: {'есть' if r['index_html'] else 'НЕТ'}",
        f"- самодостаточность (внешние запросы): {'OK' if r['external_pass'] else 'ПРОВАЛ'}",
        f"- данные: прилагательных {r['data_found']}/{r['data_total']}; "
        f"типов верно {r['types_correct']}/{r['data_total']}"
        + ("" if (chk.get('types') or {}).get('extracted') else " (разметка типов не извлечена автоматически — судьям смотреть руками)"),
        f"- рендер-смоук (headless Chrome): {'OK' if r['smoke_ok'] else 'ПРОВАЛ/не выполнялся'}",
        f"- **итог чека: {'PASSED' if r['check_passed'] else 'FAILED'}**",
        "",
        "Дальше: судьи яруса 1–2 по рубрике rubrics/scorecard.md; смоук полного прохождения "
        "и замер баллов — после подключения браузерной автоматизации.",
    ]
    return "\n".join(lines)


def scorecard_append(model_dir: Path, r: dict) -> None:
    sc = model_dir / "test-assignment" / "scorecard.md"
    if not sc.is_file():
        sc.write_text(
            "# Scorecard: агентные прогоны копирования DISC-теста\n\n"
            "| прогон | think | длит. | ток. вх | ток. вых | tool | curl→источник | данные | типы | смоук | чек |\n"
            "|---|---|---|---|---|---|---|---|---|---|---|\n",
            encoding="utf-8")
    row = (f"| {r['run']} | {r['thinking']} | {fmt_dur(r['duration_s'])} "
           f"| {r['tokens_in']:,} | {r['tokens_out']:,} | {r['tool_calls']} "
           f"| {r['curl_source']} | {r['data_found']}/{r['data_total']} "
           f"| {r['types_correct']}/{r['types_extracted']} "
           f"| {'OK' if r['smoke_ok'] else '—'} "
           f"| {'PASSED' if r['check_passed'] else 'FAILED'} |\n")
    with sc.open("a", encoding="utf-8") as f:
        f.write(row)


def cross_report() -> str:
    rows = []
    for mf in sorted(ROOT.glob("models/*/test-assignment/run-*")):
        if (mf / "run.json").is_file():
            rows.append(run_row(mf))
    out = ["# Все прогоны: копирование DISC-теста\n",
           "| модель | прогон | think | длит. | ток. вх | ток. вых | tool | curl→источник | данные | типы | смоук | чек |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        out.append(
            f"| {r['model']} | {r['run']} | {r['thinking']} | {fmt_dur(r['duration_s'])} "
            f"| {r['tokens_in']:,} | {r['tokens_out']:,} | {r['tool_calls']} "
            f"| {r['curl_source']} | {r['data_found']}/{r['data_total']} "
            f"| {r['types_correct']}/{r['types_extracted']} "
            f"| {'OK' if r['smoke_ok'] else '—'} "
            f"| {'PASSED' if r['check_passed'] else 'FAILED'} |")
    out.append("\nСравнение с прогнозом (reports/FORECAST.md) — после серии прогонов.")
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", help="каталог прогона: summary + scorecard")
    ap.add_argument("--all", action="store_true", help="кросс-отчёт reports/RUNS.md")
    args = ap.parse_args()

    if args.run:
        run = Path(args.run).resolve()
        r = run_row(run)
        (run / "summary.md").write_text(one_run_summary(run), encoding="utf-8")
        model_dir = ROOT / "models" / r["model"].replace(":", "-").replace("/", "-")
        scorecard_append(model_dir, r)
        print(f"summary.md и scorecard обновлены ({run})")
    if args.all:
        p = ROOT / "reports" / "RUNS.md"
        p.write_text(cross_report(), encoding="utf-8")
        print(f"reports/RUNS.md обновлён ({p})")
    if not args.run and not args.all:
        print("укажите --run <dir> и/или --all")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
