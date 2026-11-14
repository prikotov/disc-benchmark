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
    pt = load(run, "playthrough.json")
    jd = load(run, "judge-tier1.json").get("verdict") or {}
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
        "types_total": (chk.get("types") or {}).get("total"),
        "smoke_ok": (chk.get("smoke") or {}).get("ok"),
        "check_passed": chk.get("passed"),
        "flow_ok": (pt.get("flow_ok"), pt.get("questions_processed")),
        "screenshots": [str(run / "screenshots" / s) for s in pt.get("screenshots", [])],
        "judge": {"data": jd.get("data"), "logic": jd.get("logic"),
                  "ux": jd.get("ux"), "impl": jd.get("impl"),
                  "total": jd.get("total")} if jd else None,
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
        f"пар текст+тип верно {r['types_correct']}/{r['types_total']}"
        + ("" if (chk.get('types') or {}).get('extracted') else " (разметка типов не извлечена автоматически — судьям смотреть руками)"),
        f"- рендер-смоук (headless Chrome): {'OK' if r['smoke_ok'] else 'ПРОВАЛ/не выполнялся'}",
        f"- автопрохождение (поток): {'OK, вопросов ' + str(r['flow_ok'][1]) if r['flow_ok'][0] else 'не прошло/не выполнялось'};"
        f" баллы на экране — справочно (симуляция drag&drop не воспроизводима, логику проверяет судья по коду)",
        f"- скриншоты: {', '.join(r['screenshots']) or '—'}",
        f"- судья яруса 1: " + (f"data {r['judge']['data']}, logic {r['judge']['logic']}, ux {r['judge']['ux']}, impl {r['judge']['impl']} — **{r['judge']['total']}/16**" if r['judge'] else "не выполнялся"),
        f"- **итог чека: {'PASSED' if r['check_passed'] else 'FAILED'}**",
        "",
        "Дальше: судья яруса 2 (обзор + сверка), при расхождениях — доработки в тот же run.",
    ]
    return "\n".join(lines)


def scorecard_append(model_dir: Path, r: dict) -> None:
    sc = model_dir / "test-assignment" / "scorecard.md"
    row = (f"| {r['run']} | {r['thinking']} | {fmt_dur(r['duration_s'])} "
           f"| {r['tokens_in']:,} | {r['tokens_out']:,} | {r['tool_calls']} "
           f"| {r['curl_source']} | {r['data_found']}/{r['data_total']} "
           f"| {r['types_correct']}/{r['types_total']} "
           f"| {'OK' if r['smoke_ok'] else '—'} "
           f"| {'PASSED' if r['check_passed'] else 'FAILED'} |\n")
    if not sc.is_file():
        sc.write_text(
            "# Scorecard: агентные прогоны копирования DISC-теста\n\n"
            "| прогон | think | длит. | ток. вх | ток. вых | tool | curl→источник | данные | типы | смоук | чек |\n"
            "|---|---|---|---|---|---|---|---|---|---|---|\n",
            encoding="utf-8")
    lines = sc.read_text(encoding="utf-8").splitlines()
    lines = [l for l in lines if not l.startswith(f"| {r['run']} | {r['thinking']} |")]
    lines.append(row.rstrip("\n"))
    sc.write_text("\n".join(lines) + "\n", encoding="utf-8")


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
        "\nСравнение с прогнозом (reports/FORECAST.md) — после серии прогонов.")
    return "\n".join(out) + "\n"


def html_report(runs: list[Path]) -> str:
    """Визуальный отчёт: скриншоты инлайном, чеки, судья — всё в одном файле."""
    import base64
    cards = []
    for run in runs:
        r = run_row(run)
        meta = load(run, "run.json")
        chk = load(run, "check.json")
        jd = load(run, "judge-tier1.json").get("verdict") or {}
        notes = (load(run, "judge-tier1.json").get("verdict") or {}).get("notes", "")
        shots = []
        for name, cap in (("start.png", "старт"), ("step.png", "вопрос"), ("result.png", "результат")):
            p = run / "screenshots" / name
            if p.is_file():
                b64 = base64.b64encode(p.read_bytes()).decode()
                shots.append(f"<figure><img src=\"data:image/png;base64,{b64}\" style=\"max-width:420px;border:1px solid #ccc;border-radius:6px\"><figcaption>{cap}</figcaption></figure>")
        j = (f"<b>судья:</b> data {jd.get('data')} · logic {jd.get('logic')} · ux {jd.get('ux')} · "
             f"impl {jd.get('impl')} — <b>{jd.get('total')}/16</b><br><i>{notes[:400]}</i>" if jd else "судья: не выполнялся")
        cards.append(f"""
<div style="border:1px solid #d0d4dd;border-radius:10px;padding:14px;margin:14px 0;font-family:system-ui">
  <h2 style="margin:0 0 6px">{r['model']} · think {r['thinking']} · {r['run']}</h2>
  <div style="color:#555">время {fmt_dur(r['duration_s'])}, exit {r['exit_code']}, токены вх {r['tokens_in']:,}/вых {r['tokens_out']:,},
  инструментов {r['tool_calls']}, curl к источнику {r['curl_source']}</div>
  <div style="margin:8px 0">чек: {'<b style="color:#0a7d32">PASSED</b>' if r['check_passed'] else '<b style="color:#b3261e">FAILED</b>'} ·
  данные {r['data_found']}/{r['data_total']} · типы {r['types_correct']}/{r['types_total']} ·
  внешние запросы: {'нет' if r['external_pass'] else 'ЕСТЬ'} · рендер: {'OK' if r['smoke_ok'] else '—'} ·
  автопрохождение: {'OK ' + str((r['flow_ok'] or (False, 0))[1]) + ' вопр.' if (r['flow_ok'] or (False, 0))[0] else '—'}</div>
  <div style="display:flex;gap:10px;flex-wrap:wrap">{''.join(shots)}</div>
  <div style="margin-top:8px">{j}</div>
</div>""")
    head = """<!DOCTYPE html><html lang=ru><meta charset=utf-8><title>disc — прогоны</title>
<style>body{background:#f5f6f8;margin:20px}h1{font-family:system-ui}</style>
<h1>disc: прогоны копирования DISC-теста</h1>"""
    return head + "\n".join(cards)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", help="каталог прогона: summary + scorecard")
    ap.add_argument("--all", action="store_true", help="кросс-отчёт reports/RUNS.md")
    ap.add_argument("--html", action="store_true", help="визуальный reports/RUNS.html (скриншоты инлайном)")
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
    if args.html:
        runs = sorted(ROOT.glob("models/*/test-assignment/run-*"))
        runs = [r for r in runs if (r / "run.json").is_file()]
        p = ROOT / "reports" / "RUNS.html"
        p.write_text(html_report(runs), encoding="utf-8")
        print(f"reports/RUNS.html обновлён ({p})")
    if not args.run and not args.all and not args.html:
        print("укажите --run <dir> и/или --all и/или --html")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
