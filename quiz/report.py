#!/usr/bin/env python3
"""Сводный отчёт по анкете DISC (ru + en): reports/QUIZ.md + reports/QUIZ.html.

Читает models/*/quiz/run-*/run.json (ru) и models/*/quiz-en/run-*/run.json
(en), агрегирует по (модель × язык × уровень): баллы, стабильность, json_ok,
токены, время, p_correct для decision-моделей; матрицы по вопросам на каждый
язык, сложность вопросов, точность по цветам и сравнение ru vs en.

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
RUNS_GLOBS = {"ru": "models/*/quiz/run-*/run.json",
              "en": "models/*/quiz-en/run-*/run.json"}

KEYS = {lang: json.loads((HERE.parent / f"quiz{'' if lang == 'ru' else '-en'}"
                          / "reference" / f"key{'' if lang == 'ru' else '-en'}.json")
                         .read_text(encoding="utf-8")) for lang in ("ru", "en")}
LEVEL_ORDER = {m["folder"]: m.get("doc_levels") or [None]
               for m in json.loads((HERE / "models.json").read_text(encoding="utf-8"))["models"]}
COLOR_OF = {"Красный": "D", "Желтый": "I", "Зеленый": "S", "Синий": "C",
            "Red": "D", "Yellow": "I", "Green": "S", "Blue": "C"}
COLOR_TITLE = {"D": "красный (D)", "I": "жёлтый (I)", "S": "зелёный (S)", "C": "синий (C)"}
LANG_TOTAL = {"ru": 24, "en": 23}


def load_runs() -> list[dict]:
    runs = []
    for lang, pattern in RUNS_GLOBS.items():
        for p in sorted(ROOT.glob(pattern)):
            try:
                r = json.loads(p.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                print(f"  ! битый run.json: {p}", file=sys.stderr)
                continue
            for x in r["verdict"]["per_question"]:
                if not isinstance(x.get("correct"), bool):
                    x["correct"] = x.get("verdict") == "correct"
            r["_lang"] = r.get("lang") or lang
            r["_dir"] = str(p.parent)
            runs.append(r)
    return runs


def group_key(r: dict) -> tuple[str, str, str]:
    lvl = r["thinking"]["requested"]
    return r["folder"], r["_lang"], ("decision" if lvl is None else str(lvl))


def sort_key(g: tuple[str, str, str]):
    """Сортировка по имени модели (алфавит), затем язык (ru раньше en),
    затем уровень — в порядке документированной лестницы."""
    folder, lang, lvl = g
    dl = LEVEL_ORDER.get(folder) or [None]
    li = dl.index(None if lvl == "decision" else lvl) if lvl in dl or lvl == "decision" else 99
    return folder.lower(), 0 if lang == "ru" else 1, li


def folders_sorted(groups: dict) -> list[str]:
    return sorted({g[0] for g in groups}, key=lambda f: f.lower())


def agg_group(runs: list[dict]) -> dict:
    n = len(runs)
    scores = [r["verdict"]["score"] for r in runs]
    provider = runs[0]["provider"]
    total = LANG_TOTAL[runs[0]["_lang"]]
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
        "runs": runs, "total": total,
    }


def pct_lang(a: dict) -> str:
    return f"{a['mean'] / a['total'] * 100:.0f}%"


def heat_color(rate: float) -> str:
    h = int(8 + 116 * max(0.0, min(1.0, rate)))
    return f"background:hsl({h},72%,86%)"


def matrix_rows(groups: dict, lang: str) -> dict:
    out = {}
    for g, a in groups.items():
        if g[1] != lang:
            continue
        per_q = defaultdict(lambda: [0, 0])
        for r in a["runs"]:
            for x in r["verdict"]["per_question"]:
                per_q[x["n"]][0] += 1 if x.get("correct") else 0
                per_q[x["n"]][1] += 1
        out[g] = [((okc / tot) if tot else None) for okc, tot in
                  (per_q[q["n"]] for q in KEYS[lang]["questions"])]
    return out


def lang_best(groups: dict, folder: str, lang: str) -> dict | None:
    gs = [g for g in groups if g[0] == folder and g[1] == lang]
    if not gs:
        return None
    return max((groups[g] for g in gs), key=lambda a: a["mean"])


def lang_level(groups: dict, folder: str, lang: str, best: dict) -> str:
    for g, a in groups.items():
        if g[0] == folder and g[1] == lang and a is best:
            return g[2]
    return "?"


def build_html(groups: dict, runs: list[dict], out: Path,
               failed_counts: dict | None = None) -> None:
    total_runs = len(runs)
    parts = []
    LEGEND = ("<div class='muted legend'>📘 — ключ — правило методологии курса (по Эриксону): "
              "Q1 «двое жёлтых» совместимы социально, Q2 «зелёный с любым» в работе, "
              "Q18 «смешение всех цветов» — команда, Q24 «нет однозначного ответа». "
              "Из общего DISC-материала эти ответы не выводятся (типовая подача совместимости — "
              "комплементарные пары); в промпте источник не упоминается. Остальные 20 вопросов — "
              "профильные ассоциации общего DISC.</div>")
    parts = []
    parts.append("""<!doctype html><html lang="ru"><head><meta charset="utf-8">
<title>disc quiz: анкета DISC — своды (ru + en)</title><style>
body{font:14px/1.45 -apple-system,'Segoe UI',Roboto,sans-serif;margin:24px;color:#1c2733;background:#fafbfc}
h1{font-size:22px;margin:0 0 4px}h2{font-size:17px;margin:28px 0 8px}
.sub{color:#5a6b7b;margin-bottom:18px}
table{border-collapse:collapse;margin:10px 0;background:#fff}
th,td{border:1px solid #d5dde5;padding:4px 9px;text-align:left;vertical-align:top}
th{background:#eef2f6;font-weight:600}
td.num,th.num{text-align:right}
.bar{height:9px;background:#dfe7ee;border-radius:5px;overflow:hidden;width:120px;display:inline-block;vertical-align:middle}
.bar>div{height:100%;background:#2e7d32}
.model{background:#fff;border:1px solid #d5dde5;border-radius:8px;padding:10px 14px;margin:12px 0;max-width:920px}
.model h3{margin:2px 0 6px;font-size:15px}
.muted{color:#5a6b7b;font-size:12px}
.warn{background:#fff4e5;border:1px solid #f0c987;border-radius:6px;padding:6px 12px;margin:10px 0;max-width:920px}
a{color:#0b62a4;text-decoration:none}a:hover{text-decoration:underline}
code{background:#eef2f6;border-radius:3px;padding:0 4px}
table.matrix{font-size:12px}
table.matrix td,table.matrix th{padding:3px 7px;text-align:center}
table.matrix td.model{text-align:left;position:sticky;left:0;background:#fff;z-index:1}
table.matrix th.model{text-align:left;position:sticky;left:0;background:#eef2f6;z-index:2}
table.matrix td.na{color:#9aa7b3}
.delta-up{color:#2e7d32;font-weight:600}.delta-down{color:#c62828;font-weight:600}
</style></head><body>""")

    gen = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    pv = runs[0]["prompt_version"] if runs else 1
    parts.append(
        f"<h1>Анкета DISC (блиц-тест): своды по прогонам — ru + en</h1>"
        f"<div class='sub'>24 вопроса (ru) / 23 вопроса (en) по методологии DISC "
        f"(блиц-тест курса, материалы по книге Эриксона); модель называет профиль "
        f"без вариантов. Промпт v{pv} (оба языка). Прогонов: {total_runs}. "
        f"Сформировано: {gen}. Методика: <code>quiz/README.md</code>, "
        f"<code>quiz-en/README.md</code></div>")
    parts.append(
        "<div class='warn'><b>Оговорки.</b> (1) Межформатная: chat-модели отвечают "
        "открыто, decision (clef) — argmax по кандидатам-утверждениям в пробах noul "
        "(у них кандидаты видны); баллы сравнимы, условия — нет. (2) Межъязыковая: "
        "ru — 24 вопроса, en — 23 (вопроса про болезненную реакцию на критику в "
        "английском оригинале нет), поэтому сравниваем проценты, а не сырые баллы.</div>")

    # сводная таблица
    parts.append("<h2>Сводная таблица</h2><table><tr>"
                 "<th>модель</th><th>язык</th><th>уровень</th><th>прогонов</th>"
                 "<th class='num'>балл (ср)</th><th class='num'>min–max</th><th>%</th>"
                 "<th>стабильность</th><th class='num'>json_ok</th>"
                 "<th class='num'>unparsed/skipped</th><th class='num'>сбои</th>"
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
        href = f"../models/{g[0]}/{('quiz' if g[1] == 'ru' else 'quiz-en')}/"
        fails = (failed_counts or {}).get(g, 0)
        parts.append(
            f"<tr><td><a href='{href}'>{g[0]}</a></td><td>{g[1]}</td><td>{g[2]}</td>"
            f"<td class='num'>{a['n']}</td><td class='num'><b>{a['mean']:.1f}</b></td>"
            f"<td class='num'>{a['min']}–{a['max']}</td><td>{pct_lang(a)}"
            f"<div class='bar'><div style='width:{a['mean'] / a['total'] * 100:.0f}%'></div></div></td>"
            f"<td>{stab}</td><td class='num'>{j}</td>"
            f"<td class='num'>{a['unparsed']}/{a['skipped']}</td>"
            f"<td class='num'>{fails}</td>"
            f"<td class='num'>{p}</td><td class='num'>{tok}</td>"
            f"<td class='num'>{a['dur']}</td></tr>")
    parts.append("</table>")
    parts.append("<div class='muted'>Сбои — прогоны с транспортными ошибками (run.json "
                 "error), в метриках не участвуют; сырой результат сохранён рядом.</div>")
    if any(a["contention"] for a in groups.values()):
        parts.append("<div class='warn'>У части прогонов в VRAM была чужая модель "
                     "(факт в run.json ollama_contention) — на баллы это не влияет, "
                     "но время может быть завышено.</div>")

    # Язык: ru vs en — главный вопрос исследования
    parts.append("<h2>Язык: ru vs en (влияние языка на точность и устойчивость)</h2>"
                 "<div class='muted'>лучший уровень модели на каждом языке; "
                 "Δ = en% − ru% (в п.п.; множества вопросов разные: 24/23)</div>"
                 "<table><tr><th>модель</th><th>ru: лучший балл</th><th>%</th>"
                 "<th>en: лучший балл</th><th>%</th><th class='num'>Δ п.п.</th>"
                 "<th>стабильность ru</th><th>стабильность en</th></tr>")
    deltas = []
    folders = folders_sorted(groups)
    for folder in folders:
        br = lang_best(groups, folder, "ru")
        be = lang_best(groups, folder, "en")
        if not br and not be:
            continue
        rtxt = etxt = r_pct = e_pct = "—"
        rst = est = "—"
        rp = ep = None
        if br:
            r_pct = f"{br['mean'] / br['total'] * 100:.0f}%"
            rtxt = f"{br['mean']:.1f} ({br['min']}–{br['max']}) @ {lang_level(groups, folder, 'ru', br)}"
            rp = br["mean"] / br["total"] * 100
            rst = f"{br['distinct']} уник." + (f", попарно {br['identical'] * 100:.0f}%" if br["identical"] is not None else "")
        if be:
            e_pct = f"{be['mean'] / be['total'] * 100:.0f}%"
            etxt = f"{be['mean']:.1f} ({be['min']}–{be['max']}) @ {lang_level(groups, folder, 'en', be)}"
            ep = be["mean"] / be["total"] * 100
            est = f"{be['distinct']} уник." + (f", попарно {be['identical'] * 100:.0f}%" if be["identical"] is not None else "")
        dtxt = "—"
        if rp is not None and ep is not None:
            d = ep - rp
            deltas.append(d)
            cls = "delta-up" if d > 0 else ("delta-down" if d < 0 else "")
            dtxt = f"<span class='{cls}'>{d:+.1f}</span>"
        parts.append(f"<tr><td>{folder}</td><td>{rtxt}</td><td>{r_pct}</td>"
                     f"<td>{etxt}</td><td>{e_pct}</td>"
                     f"<td class='num'>{dtxt}</td><td>{rst}</td><td>{est}</td></tr>")
    if deltas:
        avg = sum(deltas) / len(deltas)
        verdict = "en лучше" if avg > 0 else "ru лучше" if avg < 0 else "паритет"
        parts.append("</table>"
                     f"<div class='muted'>средняя Δ по моделям с обоими языками: "
                     f"<b>{avg:+.1f} п.п.</b> ({verdict})</div>")
    else:
        parts.append("</table>")

    # карточки моделей
    parts.append("<h2>Модели × языки × уровни</h2>")
    for folder in folders:
        gs = [g for g in groups if g[0] == folder]
        parts.append(f"<div class='model'><h3>{folder}</h3><table><tr>"
                     "<th>язык</th><th>уровень</th><th class='num'>балл</th><th>%</th>"
                     "<th>Δ к первому уровню языка</th><th class='num'>прогонов</th>"
                     "<th>стабильность</th></tr>")
        base = {}
        for g in sorted(gs, key=sort_key):
            a = groups[g]
            first = g[1] not in base
            if first:
                base[g[1]] = a["mean"]
            dtxt = "—" if first else f"{a['mean'] - base[g[1]]:+.1f}"
            stab = f"{a['distinct']} уник." + (f", попарно {a['identical'] * 100:.0f}%" if a["identical"] is not None else "")
            parts.append(f"<tr><td>{g[1]}</td><td>{g[2]}</td>"
                         f"<td class='num'><b>{a['mean']:.1f}</b> ({a['min']}–{a['max']})</td>"
                         f"<td>{pct_lang(a)}<div class='bar'><div "
                         f"style='width:{a['mean'] / a['total'] * 100:.0f}%'></div></div></td>"
                         f"<td class='num'>{dtxt}</td><td class='num'>{a['n']}</td>"
                         f"<td>{stab}</td></tr>")
        parts.append("</table></div>")

    # матрицы по языкам
    for lang, label in (("ru", "ru (24 вопроса)"), ("en", "en (23 вопроса)")):
        gs_lang = [g for g in sorted(groups, key=sort_key) if g[1] == lang]
        if not gs_lang:
            continue
        mx = matrix_rows(groups, lang)
        parts.append(f"<h2>Матрица «{label}»: модель × уровень × вопрос</h2>"
                     "<div class='muted'>ячейка — доля верных ответов на вопрос по прогонам "
                     "группы, 0–100 (наведение — точные «верных/всего»); 📘 — ключ — правило курса</div>")
        parts.append("<table class='matrix'><tr><th class='model'>модель @ уровень</th>")
        for q in KEYS[lang]["questions"]:
            mark = " <span class='bm'>📘</span>" if q["kind"] in ("book", "none") else ""
            parts.append(f"<th class='num'>{q['n']}{mark}</th>")
        parts.append("</tr>")
        for g in gs_lang:
            rates = mx[g]
            cells = []
            for rate in rates:
                if rate is None:
                    cells.append("<td class='num na'>—</td>")
                else:
                    okc = round(rate * groups[g]["n"])
                    cells.append(f"<td class='num' style='{heat_color(rate)}' "
                                 f"title='{okc} из {groups[g]['n']} прогонов'>{rate * 100:.0f}</td>")
            parts.append(f"<tr><td class='model'>{g[0]} "
                         f"<span class='muted'>@ {g[2]}</span></td>" + "".join(cells) + "</tr>")
        parts.append("</table>" + LEGEND)

    # сложность вопросов по языкам
    for lang in ("ru", "en"):
        rs_lang = [r for r in runs if r["_lang"] == lang]
        if not rs_lang:
            continue
        q_correct = defaultdict(lambda: [0, 0])
        for r in rs_lang:
            for x in r["verdict"]["per_question"]:
                q_correct[x["n"]][0] += 1 if x.get("correct") else 0
                q_correct[x["n"]][1] += 1
        parts.append(f"<h2>Сложность вопросов — {lang} (все прогоны языка)</h2><table><tr>"
                     "<th>вопрос</th>")
        for q in KEYS[lang]["questions"]:
            mark = " <span title='ключ — правило курса'>📘</span>" \
                if q["kind"] in ("book", "none") else ""
            parts.append(f"<th class='num'>{q['n']}{mark}</th>")
        parts.append("<th>цвет ключа</th></tr>")
        correct_row, color_row = [], []
        for q in KEYS[lang]["questions"]:
            okc, tot = q_correct[q["n"]]
            rate = okc / tot if tot else 0
            correct_row.append(f"<td class='num' style='{heat_color(rate)}' "
                               f"title='{okc}/{tot}'>{okc}/{tot}</td>")
            c = COLOR_OF.get(q["key"], "—" if q["kind"] != "color" else "?")
            cc = {"D": "#c62828", "I": "#f9a825", "S": "#2e7d32", "C": "#1565c0"}.get(c, "#999")
            color_row.append(f"<td class='num' style='background:{cc};color:#fff'>{c if c != '—' else '—'}</td>")
        parts.append("<tr><td>верных</td>" + "".join(correct_row) + "<td></td></tr>")
        parts.append("<tr><td>ключ</td>" + "".join(color_row) + "<td></td></tr>")
        parts.append("</table>" + LEGEND)

    # точность по цветам, по языкам
    for lang in ("ru", "en"):
        rs_lang = [r for r in runs if r["_lang"] == lang]
        if not rs_lang:
            continue
        color_stats = defaultdict(lambda: [0, 0])
        for r in rs_lang:
            for x, q in zip(r["verdict"]["per_question"], KEYS[lang]["questions"]):
                if q["kind"] == "color":
                    c = COLOR_OF[q["key"]]
                    color_stats[c][0] += 1 if x.get("correct") else 0
                    color_stats[c][1] += 1
        parts.append(f"<h2>Точность по профилям — {lang} (single-цветные вопросы)</h2>"
                     "<table><tr><th>профиль</th><th class='num'>верных</th><th>%</th></tr>")
        for c in ("D", "I", "S", "C"):
            okc, tot = color_stats[c]
            rate = okc / tot if tot else 0
            parts.append(f"<tr><td>{COLOR_TITLE[c]}</td><td class='num'>{okc}/{tot}</td>"
                         f"<td>{rate * 100:.0f}%<div class='bar'><div "
                         f"style='width:{rate * 100:.0f}%'></div></div></td></tr>")
        parts.append("</table>")

    parts.append("<div class='muted' style='margin-top:20px'>Флаги: unparsed — ответ не "
                 "распознан (это не «неверный ответ»); skipped — вопроса нет в JSON; "
                 "ambiguous — распознано 2+ профиля; near — верный профиль без нужного "
                 "уточнения. Стабильность — уникальные наборы ответов и попарное совпадение "
                 "прогонов группы. Ссылки — папки прогонов "
                 "<code>models/&lt;модель&gt;/quiz[-en]/</code>.</div>")
    parts.append("</body></html>")
    out.write_text("".join(parts), encoding="utf-8")


def build_md(groups: dict, runs: list[dict], out: Path) -> None:
    lines = [
        "# Анкета DISC (блиц-тест): своды (ru + en)",
        "",
        f"Прогонов: {len(runs)}. Промпт v{runs[0]['prompt_version'] if runs else 1}. "
        f"ru — 24 вопроса, en — 23 (межъязыковое сравнение — по процентам). "
        f"Методика: quiz/README.md, quiz-en/README.md. Сформировано "
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}.",
        "",
        "| модель | язык | уровень | прогонов | балл (ср) | min–max | % | стабильность | json_ok | "
        "unparsed/skipped | p_correct | токены вх/вых | время, с |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for g in sorted(groups, key=sort_key):
        a = groups[g]
        stab = f"{a['distinct']} уник. из {a['n']}"
        if a["identical"] is not None:
            stab += f", попарно {a['identical'] * 100:.0f}%"
        j = "—" if a["json_ok"] is None else f"{a['json_ok'] * 100:.0f}%"
        p = "—" if a["p_correct"] is None else str(a["p_correct"])
        lines.append(
            f"| {g[0]} | {g[1]} | {g[2]} | {a['n']} | **{a['mean']:.1f}** | {a['min']}–{a['max']} | "
            f"{pct_lang(a)} | {stab} | {j} | {a['unparsed']}/{a['skipped']} | {p} | "
            f"{a['tok_in'] or '—'}/{a['tok_out'] or '—'} | {a['dur']} |")
    lines += ["", "## Язык: ru vs en", "",
              "Лучший уровень модели на каждом языке; Δ = en% − ru% "
              "(множества вопросов разные: 24/23).",
              "",
              "| модель | ru лучший | ru % | en лучший | en % | Δ п.п. |",
              "|---|---|---|---|---|---|"]
    deltas = []
    folders = folders_sorted(groups)
    for folder in folders:
        br = lang_best(groups, folder, "ru")
        be = lang_best(groups, folder, "en")
        rp = f"{br['mean']:.1f} @ {lang_level(groups, folder, 'ru', br)}" if br else "—"
        ep = f"{be['mean']:.1f} @ {lang_level(groups, folder, 'en', be)}" if be else "—"
        r_pct = f"{br['mean'] / br['total'] * 100:.0f}%" if br else "—"
        e_pct = f"{be['mean'] / be['total'] * 100:.0f}%" if be else "—"
        d = "—"
        if br and be:
            dd = be["mean"] / be["total"] * 100 - br["mean"] / br["total"] * 100
            deltas.append(dd)
            d = f"{dd:+.1f}"
        lines.append(f"| {folder} | {rp} | {r_pct} | {ep} | {e_pct} | {d} |")
    if deltas:
        lines += ["", f"Средняя Δ: **{sum(deltas) / len(deltas):+.1f} п.п.**"]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--print", action="store_true", help="показать сводную таблицу в stdout")
    args = ap.parse_args()

    runs = load_runs()
    if not runs:
        print("нет прогонов (models/*/quiz[-en]/run-*/run.json)")
        return 1
    groups = defaultdict(list)
    for r in runs:
        groups[group_key(r)].append(r)
    # сбойные прогоны (транспортная ошибка) — вне метрик, факт в отчёте
    failed = defaultdict(int)
    clean = defaultdict(list)
    for r in runs:
        g = group_key(r)
        if r.get("error"):
            failed[g] += 1
        else:
            clean[g].append(r)
    groups = defaultdict(list)
    for g, rs in clean.items():
        groups[g] = rs
    agg = {g: agg_group(rs) for g, rs in groups.items()}
    FAILED_COUNTS = dict(failed)

    REPORTS.mkdir(exist_ok=True)
    build_md(agg, runs, REPORTS / "QUIZ.md")
    build_html(agg, runs, REPORTS / "QUIZ.html", dict(failed))
    print(f"отчёты: reports/QUIZ.md, reports/QUIZ.html ({len(runs)} прогонов)")

    if args.print:
        for g in sorted(agg, key=sort_key):
            a = agg[g]
            print(f"{g[0]:<45} {g[1]} {g[2]:<9} n={a['n']} балл={a['mean']:.1f} "
                  f"({a['min']}–{a['max']}) {pct_lang(a)} уник={a['distinct']} "
                  f"json_ok={a['json_ok']} unparsed={a['unparsed']} skipped={a['skipped']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
