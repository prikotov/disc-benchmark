#!/usr/bin/env python3
"""Сводный отчёт по анкете DISC: reports/QUIZ.md + reports/QUIZ.html.

Читает models/*/quiz/run-*/run.json, агрегирует по (модель × уровень):
баллы, стабильность (уникальные наборы ответов и попарные совпадения),
json_ok/unparsed/skipped, токены, время, p_correct для decision-моделей.
Плюс heatmap сложности по 24 вопросам и точность по цветам D/I/S/C.

Запуск:
    python3 quiz/report.py            # QUIZ.md + QUIZ.html
    python3 quiz/report.py --print    # ещё и таблицу в stdout
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPORTS = ROOT / "reports"

MODEL_ORDER = [m["folder"] for m in json.loads(
    (HERE / "models.json").read_text(encoding="utf-8"))["models"]]
LEVEL_ORDER = {m["folder"]: m.get("doc_levels") or [None]
               for m in json.loads((HERE / "models.json").read_text(encoding="utf-8"))["models"]}
KEY = json.loads((HERE / "reference" / "key.json").read_text(encoding="utf-8"))
COLOR_OF = {"Красный": "D", "Желтый": "I", "Зеленый": "S", "Синий": "C"}
COLOR_TITLE = {"D": "красный (D)", "I": "жёлтый (I)", "S": "зелёный (S)", "C": "синий (C)"}


def load_runs() -> list[dict]:
    runs = []
    for p in sorted(ROOT.glob("models/*/quiz/run-*/run.json")):
        try:
            r = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"  ! битый run.json: {p}", file=sys.stderr)
            continue
        # нормализация: chat-прогоны хранят вердикт строкой, decision — булевым
        # флагом; сводим к correct: bool, чтобы все агрегации были едины
        for x in r["verdict"]["per_question"]:
            if not isinstance(x.get("correct"), bool):
                x["correct"] = x.get("verdict") == "correct"
        r["_dir"] = str(p.parent)
        runs.append(r)
    return runs


def group_key(r: dict) -> tuple[str, str]:
    lvl = r["thinking"]["requested"]
    return r["folder"], ("decision" if lvl is None else str(lvl))


def sort_key(g: tuple[str, str]):
    folder, lvl = g
    mi = MODEL_ORDER.index(folder) if folder in MODEL_ORDER else 99
    dl = LEVEL_ORDER.get(folder) or [None]
    li = dl.index(None if lvl == "decision" else lvl) if lvl in dl or lvl == "decision" else 99
    return mi, li


def agg_group(runs: list[dict]) -> dict:
    n = len(runs)
    scores = [r["verdict"]["score"] for r in runs]
    provider = runs[0]["provider"]
    # стабильность: набор ответов на вопрос (выбранный текст / выбранный вариант)
    vectors = []
    for r in runs:
        pq = r["verdict"]["per_question"]
        if provider == "decision":
            vec = tuple(x.get("chosen") for x in pq)
        else:
            vec = tuple(str(x.get("answer", "")).strip().lower() for x in pq)
        vectors.append(vec)
    distinct = len(set(vectors))
    pairs = [vectors[i] == vectors[j]
             for i in range(n) for j in range(i + 1, n)]
    identical = (sum(pairs) / len(pairs)) if pairs else None
    flags = defaultdict(int)
    for r in runs:
        st = r["verdict"].get("stats") or {}
        for k, v in st.items():
            flags[k] += v
    toks = defaultdict(list)
    for r in runs:
        u = r.get("usage") or {}
        for k in ("prompt_eval_count", "eval_count", "input_tokens", "output_tokens",
                  "prompt_tokens", "completion_tokens"):
            if u.get(k):
                toks[k].append(u[k])
    mean = lambda k: round(sum(toks[k]) / len(toks[k])) if toks.get(k) else None
    pc = [r["verdict"].get("p_correct_mean") for r in runs
          if r["verdict"].get("p_correct_mean") is not None]
    # json_ok осмыслен для chat и cloud (decision отвечает noul-пробами)
    jok = (sum(1 for r in runs if (r.get("parsed") or {}).get("json_ok")) / n) \
        if n and provider in ("chat", "cloud") else None
    return {
        "n": n, "provider": provider,
        "mean": sum(scores) / n if n else 0,
        "min": min(scores) if scores else 0, "max": max(scores) if scores else 0,
        "distinct": distinct, "identical": identical,
        "unparsed": flags["unparsed"], "skipped": flags["skipped"],
        "ambiguous": flags["ambiguous"], "near": flags["near"],
        "json_ok": jok,
        "tok_in": mean("prompt_eval_count") or mean("input_tokens") or mean("prompt_tokens"),
        "tok_out": mean("eval_count") or mean("output_tokens") or mean("completion_tokens"),
        "dur": round(sum(r.get("duration_s") or 0 for r in runs) / n, 1) if n else None,
        "p_correct": round(sum(pc) / len(pc), 3) if pc else None,
        "contention": any(r.get("ollama_contention") for r in runs),
        "runs": runs,
    }


def pct(v: float, total: int = 24) -> str:
    return f"{v / total * 100:.0f}%"


def heat_color(rate: float) -> str:
    # 0 -> красный, 1 -> зелёный
    h = int(8 + 116 * max(0.0, min(1.0, rate)))
    return f"background:hsl({h},72%,86%)"


def matrix_rows(groups: dict) -> dict:
    """(folder, level) -> [доля верных на вопрос по всем прогонам группы]."""
    out = {}
    for g, a in groups.items():
        per_q = defaultdict(lambda: [0, 0])
        for r in a["runs"]:
            for x in r["verdict"]["per_question"]:
                per_q[x["n"]][0] += 1 if x.get("correct") else 0
                per_q[x["n"]][1] += 1
        out[g] = [((okc / tot) if tot else None) for okc, tot in
                  (per_q[q["n"]] for q in KEY["questions"])]
    return out


def build_html(groups: dict, runs: list[dict], out: Path) -> None:
    total_runs = len(runs)
    # heatmap по вопросам (все прогоны, оба формата)
    q_correct = defaultdict(lambda: [0, 0])
    for r in runs:
        for x in r["verdict"]["per_question"]:
            q_correct[x["n"]][0] += 1 if x.get("correct") else 0
            q_correct[x["n"]][1] += 1
    # по цветам (20 single-цветных вопросов)
    color_stats = defaultdict(lambda: [0, 0])
    for r in runs:
        for x, q in zip(r["verdict"]["per_question"], KEY["questions"]):
            if q["kind"] == "color":
                c = COLOR_OF[q["key"]]
                color_stats[c][0] += 1 if x.get("correct") else 0
                color_stats[c][1] += 1

    parts = []
    parts.append("""<!doctype html><html lang="ru"><head><meta charset="utf-8">
<title>disc quiz: анкета DISC — своды</title><style>
body{font:14px/1.45 -apple-system,'Segoe UI',Roboto,sans-serif;margin:24px;color:#1c2733;background:#fafbfc}
h1{font-size:22px;margin:0 0 4px}h2{font-size:17px;margin:28px 0 8px}
.sub{color:#5a6b7b;margin-bottom:18px}
table{border-collapse:collapse;margin:10px 0;background:#fff}
th,td{border:1px solid #d5dde5;padding:4px 9px;text-align:left;vertical-align:top}
th{background:#eef2f6;font-weight:600}
td.num,th.num{text-align:right}
table.matrix{font-size:12px}
table.matrix td,table.matrix th{padding:3px 7px;text-align:center}
table.matrix td.model{text-align:left;position:sticky;left:0;background:#fff;z-index:1}
table.matrix th.model{text-align:left;position:sticky;left:0;background:#eef2f6;z-index:2}
table.matrix td.na{color:#9aa7b3}
.bar{height:9px;background:#dfe7ee;border-radius:5px;overflow:hidden;width:120px;display:inline-block;vertical-align:middle}
.bar>div{height:100%;background:#2e7d32}
.model{background:#fff;border:1px solid #d5dde5;border-radius:8px;padding:10px 14px;margin:12px 0;max-width:860px}
.model h3{margin:2px 0 6px;font-size:15px}
.muted{color:#5a6b7b;font-size:12px}
.warn{background:#fff4e5;border:1px solid #f0c987;border-radius:6px;padding:6px 12px;margin:10px 0;max-width:860px}
a{color:#0b62a4;text-decoration:none}a:hover{text-decoration:underline}
code{background:#eef2f6;border-radius:3px;padding:0 4px}
.legend span{display:inline-block;margin-right:14px}
.legend i{display:inline-block;width:11px;height:11px;border-radius:2px;margin-right:4px;vertical-align:-1px}
</style></head><body>""")

    gen = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    parts.append(f"<h1>Анкета DISC (блиц-тест): своды по прогонам</h1>"
                 f"<div class='sub'>24 вопроса из книги Эриксона; модель называет профиль без вариантов. "
                 f"Промпт v{runs[0]['prompt_version'] if runs else 1}. "
                 f"Прогонов: {total_runs}. Сформировано: {gen}. "
                 f"Методика: <code>quiz/README.md</code></div>")
    parts.append("<div class='warn'><b>Оговорка межформатного сравнения:</b> chat-модели отвечают "
                 "открыто (без вариантов), decision-модели (clef) — argmax по кандидатам-утверждениям "
                 "в пробах noul (у них кандидаты видны). Баллы сравнимы, условия — нет.</div>")

    # сводная таблица
    parts.append("<h2>Сводная таблица</h2><table><tr>"
                 "<th>модель</th><th>уровень</th><th>прогонов</th><th class='num'>балл (ср)</th>"
                 "<th class='num'>min–max</th><th>%</th><th>стабильность</th>"
                 "<th class='num'>json_ok</th><th class='num'>unparsed/skipped</th>"
                 "<th class='num'>p_correct</th><th class='num'>токены вх/вых</th>"
                 "<th class='num'>время, с</th></tr>")
    for g in sorted(groups, key=sort_key):
        a = groups[g]
        stab = f"{a['distinct']} уник. из {a['n']}"
        if a["identical"] is not None:
            stab += f", попарно {a['identical'] * 100:.0f}%"
        tok = f"{a['tok_in'] or '—'}/{a['tok_out'] or '—'}"
        j = "—" if a["json_ok"] is None else f"{a['json_ok'] * 100:.0f}%"
        p = "—" if a["p_correct"] is None else str(a["p_correct"])
        parts.append(
            f"<tr><td><a href='../models/{g[0]}/quiz/'>{g[0]}</a></td><td>{g[1]}</td>"
            f"<td class='num'>{a['n']}</td><td class='num'><b>{a['mean']:.1f}</b></td>"
            f"<td class='num'>{a['min']}–{a['max']}</td><td>{pct(a['mean'])}"
            f"<div class='bar'><div style='width:{a['mean'] / 24 * 100:.0f}%'></div></div></td>"
            f"<td>{stab}</td>"
            f"<td class='num'>{j}</td>"
            f"<td class='num'>{a['unparsed']}/{a['skipped']}</td>"
            f"<td class='num'>{p}</td>"
            f"<td class='num'>{tok}</td><td class='num'>{a['dur']}</td></tr>")
    parts.append("</table>")
    if any(a["contention"] for a in groups.values()):
        parts.append("<div class='warn'>У части прогонов в VRAM была чужая модель (факт в run.json "
                     "ollama_contention) — на баллы это не влияет, но время может быть завышено.</div>")

    # карточки моделей: лестница уровней
    parts.append("<h2>Модели × уровни</h2>")
    folders = sorted({g[0] for g in groups}, key=lambda f: MODEL_ORDER.index(f) if f in MODEL_ORDER else 99)
    for folder in folders:
        gs = [g for g in groups if g[0] == folder]
        parts.append(f"<div class='model'><h3>{folder}</h3><table><tr>"
                     "<th>уровень</th><th class='num'>балл</th><th>%</th><th>Δ к off/первому</th>"
                     "<th class='num'>прогонов</th><th>стабильность</th></tr>")
        base = None
        for g in sorted(gs, key=sort_key):
            a = groups[g]
            first = base is None
            if first:
                base = a["mean"]
            dtxt = "—" if first else f"{a['mean'] - base:+.1f}"
            stab = f"{a['distinct']} уник., попарно {a['identical'] * 100:.0f}%" \
                if a["identical"] is not None else f"{a['distinct']} уник."
            parts.append(f"<tr><td>{g[1]}</td>"
                         f"<td class='num'><b>{a['mean']:.1f}</b> ({a['min']}–{a['max']})</td>"
                         f"<td>{pct(a['mean'])}<div class='bar'><div "
                         f"style='width:{a['mean'] / 24 * 100:.0f}%'></div></div></td>"
                         f"<td class='num'>{dtxt}</td><td class='num'>{a['n']}</td>"
                         f"<td>{stab}</td></tr>")
        parts.append("</table></div>")

    # матрица: модель × уровень × вопрос
    mx = matrix_rows(groups)
    parts.append("<h2>Матрица: модель × уровень × вопрос</h2>"
                 "<div class='muted'>ячейка — доля верных ответов на вопрос по прогонам группы, "
                 "0–100 (наведение — точные «верных/всего»); 📘 — ключ — утверждение книги</div>")
    parts.append("<table class='matrix'><tr><th class='model'>модель @ уровень</th>")
    for q in KEY["questions"]:
        mark = " <span class='bm'>📘</span>" if q["kind"] in ("book", "none") else ""
        parts.append(f"<th class='num'>{q['n']}{mark}</th>")
    parts.append("</tr>")
    for g in sorted(groups, key=sort_key):
        rates = mx[g]
        cells = []
        for rate in rates:
            if rate is None:
                cells.append("<td class='num na'>—</td>")
            else:
                okc = round(rate * (groups[g]["n"]))
                cells.append(f"<td class='num' style='{heat_color(rate)}' "
                             f"title='{okc} из {groups[g]['n']} прогонов'>{rate * 100:.0f}</td>")
        parts.append(f"<tr><td class='model'><a href='../models/{g[0]}/quiz/'>{g[0]}</a> "
                     f"<span class='muted'>@ {g[1]}</span></td>" + "".join(cells) + "</tr>")
    parts.append("</table>")

    # heatmap по вопросам
    parts.append("<h2>Сложность вопросов (все прогоны, оба формата)</h2><table><tr>"
                 "<th>вопрос</th>")
    for q in KEY["questions"]:
        mark = " <span title='ключ — утверждение книги'>📘</span>" \
            if q["kind"] in ("book", "none") else ""
        parts.append(f"<th class='num'>{q['n']}{mark}</th>")
    parts.append("<th>цвет ключа</th></tr>")
    correct_row, color_row = [], []
    for q in KEY["questions"]:
        okc, tot = q_correct[q["n"]]
        rate = okc / tot if tot else 0
        correct_row.append(f"<td class='num' style='{heat_color(rate)}' "
                           f"title='{okc}/{tot}'>{okc}/{tot}</td>")
        c = COLOR_OF.get(q["key"], "—" if q["kind"] != "color" else "?")
        cc = {"D": "#c62828", "I": "#f9a825", "S": "#2e7d32", "C": "#1565c0"}.get(c, "#999")
        color_row.append(f"<td class='num' style='background:{cc};color:#fff'>{c if c != '—' else '—'}</td>")
    parts.append("<tr><td>верных</td>" + "".join(correct_row) + "<td></td></tr>")
    parts.append("<tr><td>ключ</td>" + "".join(color_row) + "<td></td></tr>")
    parts.append("</table><div class='muted legend'>📘 — ключ — утверждение книги "
                 "(Q1/Q2/Q18 совместимость/команда, Q24 «нет однозначного ответа»): из общего DISC "
                 "не выводится, в промпте книга не упоминается</div>")

    # по цветам
    parts.append("<h2>Точность по профилям (20 single-цветных вопросов)</h2>"
                 "<table><tr><th>профиль</th><th class='num'>верных</th><th>%</th></tr>")
    for c in ("D", "I", "S", "C"):
        okc, tot = color_stats[c]
        rate = okc / tot if tot else 0
        parts.append(f"<tr><td>{COLOR_TITLE[c]}</td><td class='num'>{okc}/{tot}</td>"
                     f"<td>{rate * 100:.0f}%<div class='bar'><div "
                     f"style='width:{rate * 100:.0f}%'></div></div></td></tr>")
    parts.append("</table>")

    parts.append("<div class='muted' style='margin-top:20px'>Флаги: unparsed — ответ не распознан "
                 "(это не «неверный ответ»); skipped — вопроса нет в JSON; ambiguous — распознано 2+ "
                 "профиля; near — верный профиль без нужного уточнения (только Q1/Q2). "
                 "Стабильность — уникальные наборы ответов и попарное совпадение прогонов группы. "
                 "Ссылки в таблице — папки прогонов <code>models/&lt;модель&gt;/quiz/</code>.</div>")
    parts.append("</body></html>")
    out.write_text("".join(parts), encoding="utf-8")


def build_md(groups: dict, runs: list[dict], out: Path) -> None:
    lines = [
        "# Анкета DISC (блиц-тест): своды",
        "",
        f"Прогонов: {len(runs)}. Промпт v{runs[0]['prompt_version'] if runs else 1}. "
        f"Методика: quiz/README.md. Сформировано "
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}.",
        "",
        "Оговорка: chat-модели отвечают открыто, decision (clef) — argmax по кандидатам "
        "в пробах noul; баллы сравнимы, условия нет.",
        "",
        "| модель | уровень | прогонов | балл (ср) | min–max | % | стабильность | json_ok | "
        "unparsed/skipped | p_correct | токены вх/вых | время, с |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for g in sorted(groups, key=sort_key):
        a = groups[g]
        stab = f"{a['distinct']} уник. из {a['n']}"
        if a["identical"] is not None:
            stab += f", попарно {a['identical'] * 100:.0f}%"
        j = "—" if a["json_ok"] is None else f"{a['json_ok'] * 100:.0f}%"
        p = "—" if a["p_correct"] is None else str(a["p_correct"])
        lines.append(
            f"| {g[0]} | {g[1]} | {a['n']} | **{a['mean']:.1f}** | {a['min']}–{a['max']} | "
            f"{pct(a['mean'])} | {stab} | {j} | {a['unparsed']}/{a['skipped']} | {p} | "
            f"{a['tok_in'] or '—'}/{a['tok_out'] or '—'} | {a['dur']} |")
    lines += ["", "## Матрица: модель × уровень × вопрос", "",
              "Ячейка — доля верных ответов на вопрос по прогонам группы (0–100). "
              "Q1/Q2/Q18/Q24 — ключи-утверждения книги.",
              "",
              "| модель @ уровень | " + " | ".join(str(q["n"]) for q in KEY["questions"]) + " |",
              "|---|" + "---|" * len(KEY["questions"])]
    mx = matrix_rows(groups)
    for g in sorted(groups, key=sort_key):
        cells = [f"{rate * 100:.0f}" if rate is not None else "—" for rate in mx[g]]
        lines.append(f"| **{g[0]}** @ {g[1]} | " + " | ".join(cells) + " |")
    lines += ["", "## Сложность вопросов", "",
              "| вопрос | " + " | ".join(str(q["n"]) for q in KEY["questions"]) + " |",
              "|---|" + "---|" * len(KEY["questions"])]
    q_correct = defaultdict(lambda: [0, 0])
    for r in runs:
        for x in r["verdict"]["per_question"]:
            q_correct[x["n"]][0] += 1 if x.get("correct") else 0
            q_correct[x["n"]][1] += 1
    row = []
    for q in KEY["questions"]:
        okc, tot = q_correct[q["n"]]
        rate = okc / tot if tot else 0
        row.append(f"{okc}/{tot} ({rate * 100:.0f}%)")
    lines.append("| верных | " + " | ".join(row) + " |")
    lines += ["", "Q1/Q2/Q18/Q24 (📘) — ключи-утверждения книги.", "",
              "## Точность по профилям", "", "| профиль | верных | % |", "|---|---|---|"]
    color_stats = defaultdict(lambda: [0, 0])
    for r in runs:
        for x, q in zip(r["verdict"]["per_question"], KEY["questions"]):
            if q["kind"] == "color":
                c = COLOR_OF[q["key"]]
                color_stats[c][0] += 1 if x.get("correct") else 0
                color_stats[c][1] += 1
    for c in ("D", "I", "S", "C"):
        okc, tot = color_stats[c]
        rate = okc / tot if tot else 0
        lines.append(f"| {COLOR_TITLE[c]} | {okc}/{tot} | {rate * 100:.0f}% |")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--print", action="store_true", help="показать сводную таблицу в stdout")
    args = ap.parse_args()

    runs = load_runs()
    if not runs:
        print("нет прогонов (models/*/quiz/run-*/run.json)")
        return 1
    groups = defaultdict(list)
    for r in runs:
        groups[group_key(r)].append(r)
    agg = {g: agg_group(rs) for g, rs in groups.items()}

    REPORTS.mkdir(exist_ok=True)
    build_md(agg, runs, REPORTS / "QUIZ.md")
    build_html(agg, runs, REPORTS / "QUIZ.html")
    print(f"отчёты: reports/QUIZ.md, reports/QUIZ.html ({len(runs)} прогонов)")

    if args.print:
        for g in sorted(agg, key=sort_key):
            a = agg[g]
            print(f"{g[0]:<45} {g[1]:<9} n={a['n']} балл={a['mean']:.1f} "
                  f"({a['min']}–{a['max']}) {pct(a['mean'])} уник={a['distinct']} "
                  f"json_ok={a['json_ok']} unparsed={a['unparsed']} skipped={a['skipped']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
