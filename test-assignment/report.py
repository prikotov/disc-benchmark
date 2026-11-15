#!/usr/bin/env python3
"""Агрегация прогонов и отчёты.

- report.py --run <dir>     — свод одного прогона: <run>/summary.md
                              + строка в scorecard модели;
- report.py --all           — кросс-модельный reports/RUNS.md;
- report.py --html          — reports/RUNS.html (скриншоты инлайном, 1:1);
- report.py --report        — сводный reports/REPORT.html.
"""
from __future__ import annotations

import argparse
import html as html_mod
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(run, name):
    p = Path(run) / name
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}


def fmt_dur(s):
    if s is None:
        return "—"
    m, sec = divmod(int(s), 60)
    return f"{m}:{sec:02d}"


def run_row(run):
    run = Path(run)
    meta = load(run, "run.json")
    chk = load(run, "check.json")
    st = load(run, "session-stats.json")
    pt = load(run, "playthrough.json")
    jd = load(run, "judge-tier1.json").get("verdict") or {}
    uxjf = run / "judge-ux.json"
    uxj = json.loads(uxjf.read_text(encoding="utf-8")).get("verdict") or {} if uxjf.is_file() else {}
    model = meta.get("model") or run.parts[-3]
    return {
        "model": model, "run": run.name,
        "thinking": meta.get("thinking"),
        "duration_s": meta.get("duration_s"),
        "exit_code": meta.get("exit_code"),
        "killed": meta.get("killed"),
        "tokens_in": st.get("tokens_in") or 0,
        "tokens_out": st.get("tokens_out") or 0,
        "tool_calls": st.get("tool_calls") or 0,
        "curl_source": st.get("curl_to_source") or 0,
        "files": len(meta.get("files", [])),
        "index_html": (run / "index.html").is_file(),
        "external_pass": (chk.get("external") or {}).get("pass"),
        "data_found": (chk.get("data") or {}).get("adjectives_found"),
        "data_total": (chk.get("data") or {}).get("adjectives_total"),
        "types_correct": (chk.get("types") or {}).get("correct"),
        "types_total": (chk.get("types") or {}).get("total"),
        "smoke_ok": (chk.get("smoke") or {}).get("ok"),
        "check_passed": chk.get("passed"),
        "flow_ok": pt.get("flow_ok"),
        "questions_processed": pt.get("questions_processed"),
        "displayed_match": pt.get("displayed_match"),
        "ux_score": pt.get("ux_score"),
        "judge": {"data": jd.get("data"), "logic": jd.get("logic"),
                  "ux": jd.get("ux"), "impl": jd.get("impl"),
                  "total": jd.get("total")} if jd else None,
        "ux_judge": uxj.get("score") if isinstance(uxj, dict) else None,
        "ux_judge_notes": (uxj.get("notes") or "")[:300] if isinstance(uxj, dict) else "",
    }


def one_run_summary(run):
    r = run_row(run)
    meta = load(Path(run), "run.json")
    lines = [
        f"# Прогон: {r['model']} — {r['run']} (thinking {r['thinking']})",
        "",
        f"- запущен: {meta.get('started_at', '—')}, длительность: {fmt_dur(r['duration_s'])}, "
        f"exit: {r['exit_code']}, убит: {'да' if r['killed'] else 'нет'}",
        f"- контекст/бюджет выхода: {meta.get('context')} / {meta.get('max_tokens')}; "
        f"промпт: v{meta.get('prompt_version')} (sha {meta.get('prompt_sha256')})",
    ]
    if st := load(Path(run), "session-stats.json"):
        lines.append(f"- сессия: {st.get('turns', '—')} ходов, {r['tool_calls']} вызовов инструментов; "
                     f"токены: вх {r['tokens_in']:,} / вых {r['tokens_out']:,}")
        lines.append(f"- сеть в bash: {r['curl_source']} обращений к источнику "
                     f"(curl/wget всего {st.get('bash_with_network', '—')})")
    lines += [
        f"- масштаб параллельной нагрузки (VRAM): "
        f"{', '.join(meta.get('ollama_foreign_models', [])) or 'чисто'}",
        "",
        "## Машинные проверки (check.json)",
        "",
        f"- файлы агента: {r['files']}; index.html: {'есть' if r['index_html'] else 'НЕТ'}",
        f"- самодостаточность (внешние запросы): {'OK' if r['external_pass'] else 'ПРОВАЛ'}",
        f"- данные: прилагательных {r['data_found']}/{r['data_total']}; "
        f"пар текст+тип верно {r['types_correct']}/{r['types_total']}",
        f"- рендер-смоук (headless Chrome): {'OK' if r['smoke_ok'] else 'ПРОВАЛ/не выполнялся'}",
        f"- автопрохождение (поток): {'OK, вопросов ' + str(pt.get('questions_processed')) if (pt := load(Path(run), 'playthrough.json')).get('flow_ok') else '—'}; "
        f"совпадение баллов с планом: {pt.get('displayed_match')}",
        f"- судья яруса 1: " + (f"data {r['judge']['data']}, logic {r['judge']['logic']}, "
                                f"ux {r['judge']['ux']}, impl {r['judge']['impl']} — "
                                f"**{r['judge']['total']}/16**" if r.get('judge') else "не выполнялся"),
        f"- **итог чека: {'PASSED' if r['check_passed'] else 'FAILED'}**",
        "",
    ]
    return "\n".join(lines)


def scorecard_append(model_dir, r):
    sc = Path(model_dir) / "test-assignment" / "scorecard.md"
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


def cross_report():
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
            f"| {r['types_correct']}/{r['types_total']} "
            f"| {'OK' if r['smoke_ok'] else '—'} "
            f"| {'PASSED' if r['check_passed'] else 'FAILED'} |")
    out.append("\nСравнение с прогнозом (reports/FORECAST.md) — после серии прогонов.")
    return "\n".join(out) + "\n"


def html_report(runs):
    import base64
    cards = []
    for run in runs:
        r = run_row(run)
        meta = load(Path(run), "run.json")
        chk = load(Path(run), "check.json")
        jd = load(Path(run), "judge-tier1.json").get("verdict") or {}
        esc = html_mod.escape
        jhtml = (f'<b>судья ярус 1:</b> data {jd.get("data")} · logic {jd.get("logic")} · '
                 f'ux {jd.get("ux")} · impl {jd.get("impl")} — <b>{jd.get("total")}/16</b>'
                 f'<div class="notes">{esc((jd.get("notes") or ""))[:700]}</div>'
                 f'<div class="notes">{esc((jd.get("examples") or ""))[:700]}</div>' if jd else "судья: не выполнялся")
        shots = []
        for name, cap in (("start.png", "старт"), ("step.png", "вопрос"), ("result.png", "результат")):
            p = Path(run) / "screenshots" / name
            if p.is_file():
                b64 = base64.b64encode(p.read_bytes()).decode()
                shots.append(f'<figure><img class="shot" src="data:image/png;base64,{b64}" alt="{cap}"><figcaption>{cap} (клик — 1:1)</figcaption></figure>')
        cards.append(f"""
<div class="card">
  <h3>{r['model']} · think {r['thinking']} · <span class="run">{r['run']}</span></h3>
  <div class="meta">время {fmt_dur(r['duration_s'])} · exit {r['exit_code']} · токены вх {r['tokens_in']:,}/вых {r['tokens_out']:,} ·
  инструментов {r['tool_calls']} · curl к источнику {r['curl_source']} · контекст {meta.get('context')}/выход {meta.get('max_tokens')}</div>
  <div class="checks">чек: <b class="{'pass' if r['check_passed'] else 'fail'}">{'PASSED' if r['check_passed'] else 'FAILED'}</b> ·
  данные {r['data_found']}/{r['data_total']} · пары текст+тип {r['types_correct']}/{r['types_total']} ·
  внешние запросы: {'нет' if r['external_pass'] else 'ЕСТЬ'} · рендер: {'OK' if r['smoke_ok'] else '—'} ·
  автопрохождение: {'OK' if r['flow_ok'] else '—'} · совпадение баллов: {r['displayed_match']}</div>
  <div class="shots">{''.join(shots)}</div>
  <div class="judge">{jhtml}</div>
</div>""")

    matrix_rows = "".join(f"<tr><td>{m}</td><td>{lvl}</td><td class='st {cls}'>{st}</td></tr>"
                          for m, lvl, st, cls in [
        ("huihui-ai:pi-100k", "off / low / medium (+xhigh проба)", "готово: 9+1 прогонов", "done"),
        ("qwen3.8:27b-pi-100k", "off / low / medium", "готово: 9 прогонов", "done"),
        ("ornith-1.5:35b-ctx100k", "off / on", "готово: 3 прогонов", "done"),
        ("gemma4:26b-pi-100k", "off / on", "готово: 6 прогонов", "done"),
        ("bonsai-2:ctx100k", "off / low / medium", "готово: 9 прогонов", "done"),
        ("muse-glimmer:ctx100k", "off / low / high", "готово: 9 прогонов", "done"),
        ("orcarouter/…:ctx100k", "off / on", "готово: 6 прогонов", "done"),
        ("gemma4:31b-it-qat-pi-100k", "off / on", "готово: 6 прогонов", "done"),
        ("gemma4:e2b-ctx100k", "off / on", "готово: 6 прогонов", "done"),
        ("ornith-1.5:9b", "off / on", "готово: 3 прогонов", "done"),
        ("волна 2 (остальные вариаты) и волна 3 (облака)", "см. AGENTS.md", "по решению", "todo"),
    ])

    return f"""<!DOCTYPE html><html lang=ru><head><meta charset=utf-8><title>disc — прогоны</title>
<style>
body{{background:#f5f6f8;margin:24px;font-family:system-ui;color:#1c2024;max-width:1100px;margin:auto}}
h1,h2,h3{{font-family:system-ui}} h2{{border-bottom:2px solid #c9ced8;padding-bottom:4px;margin-top:36px}}
table{{border-collapse:collapse;background:#fff;width:100%}}
th,td{{border:1px solid #d0d4dd;padding:6px 10px;font-size:14px;text-align:left}}
th{{background:#eef0f4}}
.pass{{color:#0a7d32}} .fail{{color:#b3261e}}
img.shot{{max-width:340px;border:1px solid #ccc;border-radius:6px}}
</style>
<h1>disc: прогоны копирования DISC-теста</h1>
{''.join(cards)}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", help="каталог прогона: summary + scorecard")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--html", action="store_true")
    ap.add_argument("--report", action="store_true")
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
    if args.report:
        p = ROOT / "reports" / "REPORT.html"
        p.write_text(build_report_html(), encoding="utf-8")
        print(f"reports/REPORT.html обновлён ({p})")
    if not args.run and not args.all and not args.html:
        print("укажите --run <dir> и/или --all и/или --html")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
