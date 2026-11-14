#!/usr/bin/env python3
"""Машинные проверки решения прогона (ярус 0, до судей).

Проверяет run-каталог (см. runner.py):
1. files       — инвентарь созданного, наличие index.html в корне;
2. external    — решение самодостаточно: в index.html нет ни внешних запросов
                 (CDN, fetch, XHR, sendBeacon, WebSocket), ни ЛОКАЛЬНЫХ
                 зависимостей (script src/link href/img src с относительными
                 путями — решение должно быть одним файлом);
3. data        — точность данных: все прилагательные из эталона
                 (reference/questions.json) присутствуют посимвольно
                 (включая латинскую «c» в «Экспресcивный»);
4. types       — пары (текст, тип) извлекаются из разметки/данных решения
                 (разнообразные форматы: data-type-разметка, JS-объекты
                 с полными и короткими ключами, массивы пар) и сравниваются
                 с эталоном как мультимножество — повторяющиеся прилагательные
                 с разными типами ловятся;
5. smoke       — рендер в headless Chrome: DOM отрисовался, нет
                 Uncaught-ошибок; симуляция полного прохождения —
                 playthrough.mjs (поток) и судья (логика по коду).

Результат: <run>/check.json; код возврата 0, если чек пройден.
Запуск: python3 test-assignment/check.py --run models/<м>/test-assignment/run-01
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REFERENCE = HERE / "reference" / "questions.json"


def scan_external(html: str) -> tuple[bool, list[str], list[str]]:
    """(pass, находки-паттерны, уникальные внешние URL). Локальные
    относительные зависимости (script src="disc.js" и т.п.) — тоже нарушение:
    решение должно быть одним самодостаточным файлом."""
    findings: list[str] = []
    urls: set[str] = set()
    patterns = [
        ("script src внешний", r"<script[^>]+src=[\"'](https?:)?//[^\"']+"),
        ("link href внешний", r"<link[^>]+href=[\"'](https?:)?//[^\"']+"),
        ("img src внешний", r"<img[^>]+src=[\"'](https?:)?//[^\"']+"),
        ("css url() внешний", r"url\(\s*[\"']?(https?:)?//[^)\"']+"),
        ("fetch(", r"\bfetch\s*\("),
        ("XMLHttpRequest", r"\bXMLHttpRequest\b"),
        ("sendBeacon", r"\bsendBeacon\b"),
        ("WebSocket", r"\bnew\s+WebSocket\b|\bWebSocket\s*\("),
        ("EventSource", r"\bEventSource\b"),
        ("form action", r"<form[^>]+action=[\"'](?!#|javascript:)[^\"']+"),
        ("import( внешний", r"\bimport\s*\(\s*[\"'](https?:)?//"),
        # локальные зависимости: src/href с путями (решение — один файл)
        ("script src локальный", r"<script[^>]+src=[\"'](?!#|data:|javascript:)[^\"']+"),
        ("link href локальный", r"<link[^>]+href=[\"'](?!#|data:)[^\"']+\.(?:css|js)[\"']"),
        ("img src локальный", r"<img[^>]+src=[\"'](?!#|data:)[^\"']+\.(?:png|jpe?g|gif|svg|webp)[\"']"),
    ]
    for name, pat in patterns:
        m = re.findall(pat, html, re.I)
        if m:
            findings.append(f"{name}: {len(m)}")
    for m in re.finditer(r"https?://[^\s\"'<>)]+", html):
        u = m.group(0).rstrip("\\")
        if "w3.org" not in u:  # w3.org — часто в xmlns/svg
            urls.add(u[:120])
    return (not findings and not urls), findings, sorted(urls)


def extract_pairs(html: str) -> Counter:
    """Извлечение пар (текст, тип) из разметки/данных решения, best effort.
    Мультимножество: прилагательные могут повторяться с разными типами.
    Поддержанные форматы: data-type-разметка, JS-объекты с полными ключами
    (type/text/label/...), короткими (t/l/w), с ключами в кавычках (JSON),
    массивы пар ["d","Текст"] — в обоих порядках."""
    pairs: Counter = Counter()
    # ключи могут быть в кавычках (JSON) и без; полный (type/text) и короткий (t/l/w)
    T = r"[\"']?(?:t|type)[\"']?"
    X = r"[\"']?(?:l|w|text|label|title|word|content|name|t|q)[\"']?"
    pats = [
        # разметка оригинала: <li data-type="d">Волевой</li>
        r"data-type=[\"']([disc])[\"'][^>]*>\s*([^<>{]{2,40}?)\s*<",
        # JS-объекты, тип первым
        rf"{T}\s*:\s*[\"']([disc])[\"']\s*,\s*{X}\s*:\s*[\"']([^\"']{{2,40}})[\"']",
        # JS-объекты, текст первым
        rf"{X}\s*:\s*[\"']([^\"']{{2,40}})[\"']\s*,\s*{T}\s*:\s*[\"']([disc])[\"']",
        # массивы пар ["d","Волевой"] / ["Волевой","d"]
        r"\[\s*[\"']([disc])[\"']\s*,\s*[\"']([^\"']{2,40})[\"']\s*\]",
        r"\[\s*[\"']([^\"']{2,40})[\"']\s*,\s*[\"']([disc])[\"']\s*\]",
    ]
    for pat in pats:
        for m in re.finditer(pat, html):
            g = m.groups()
            t, txt = (g[0], g[1]) if g[0] in ("d", "i", "s", "c") else (g[1], g[0])
            txt = txt.strip()
            if 2 <= len(txt) <= 40:
                pairs[(txt, t)] += 1

    # позиционный разбор: data-type в атрибуте, текст элемента — где-то внутри
    # (вложенные span'ы: <li data-type="d"><span>1</span><span>Волевой</span></li>)
    for m in re.finditer(r'data-type=["\']([disc])["\']', html):
        chunk = html[m.end():m.end() + 300]
        for tm in re.finditer(r">([^<>{}]{2,40})<", chunk):
            txt = tm.group(1).strip()
            if txt and not txt.isdigit():
                pairs[(txt, m.group(1))] += 1
                break
    return pairs


def chrome_smoke(index_html: Path) -> dict:
    """Рендер в headless Chrome: DOM отрисовался, нет Uncaught-ошибок."""
    out: dict = {"tool": "google-chrome --headless=new --virtual-time-budget=8000"}
    if not index_html.is_file():
        return {**out, "ran": False, "note": "index.html отсутствует"}
    try:
        p = subprocess.run(
            ["google-chrome", "--headless=new", "--disable-gpu", "--no-sandbox",
             "--virtual-time-budget=8000", "--enable-logging=stderr", "--v=0",
             "--dump-dom", f"file://{index_html.resolve()}"],
            capture_output=True, text=True, timeout=120)
        dom = p.stdout or ""
        out["ran"] = True
        out["dom_bytes"] = len(dom)
        out["has_button"] = "<button" in dom
        out["uncaught_errors"] = len(re.findall(r"Uncaught\s+", p.stderr or ""))
        out["ok"] = bool(p.returncode == 0 and len(dom) > 2000
                         and (out["has_button"] or "<input" in dom)
                         and out["uncaught_errors"] == 0)
    except Exception as e:
        out.update({"ran": False, "ok": False, "error": str(e)[:200]})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True, help="каталог run-XX")
    args = ap.parse_args()
    run = Path(args.run).resolve()

    ref = json.loads(REFERENCE.read_text(encoding="utf-8"))
    ref_pairs: Counter = Counter()
    for q in ref["questions"]:
        for it in q["items"]:
            ref_pairs[(it["text"], it["type"])] += 1
    unique_texts = {t for t, _ in ref_pairs}

    run_json = {}
    if (run / "run.json").is_file():
        run_json = json.loads((run / "run.json").read_text(encoding="utf-8"))

    files = sorted({str(p.relative_to(run)) for p in run.rglob("*")
                    if p.is_file() and "pi-session" not in p.parts})
    index = run / "index.html"
    result: dict = {"run": str(run), "model": run_json.get("model"),
                    "thinking": run_json.get("thinking"), "files": files,
                    "index_html": index.is_file()}

    ok = index.is_file()

    if index.is_file():
        html = index.read_text(encoding="utf-8", errors="replace")

        ext_pass, findings, urls = scan_external(html)
        result["external"] = {"pass": ext_pass, "findings": findings, "urls": urls}
        ok = ok and ext_pass

        missing = [t for t in unique_texts if t not in html]
        found = len(unique_texts) - len(missing)
        result["data"] = {"adjectives_total": len(unique_texts),
                          "adjectives_found": found, "missing": missing}

        pairs = extract_pairs(html)
        common = pairs & ref_pairs                      # пересечение мультимножеств
        correct = sum(common.values())                  # верные пары (текст, тип)
        total = sum(ref_pairs.values())
        mismatches: dict = {}
        for (txt, tp), n in (ref_pairs - pairs).items():
            mismatches[f"{txt} -> {tp}"] = f"не хватает ×{n}"
        for (txt, tp), n in (pairs - ref_pairs).items():
            mismatches[f"{txt} -> {tp}"] = f"лишних ×{n}"
        result["types"] = {"extracted": sum(pairs.values()), "correct": correct,
                           "total": total, "mismatches": mismatches}

        # Известные странности оригинала: их исправление моделью — НЕ провал
        # (решение владельца 2026-11-14). Факт посимвольного отклонения
        # остаётся в отчёте выше; гейт считается по нормализованному виду:
        # латинская «c» в «Экспресcивный» ≡ кириллической.
        KNOWN_QUIRKS = {"Экспресcивный": "Экспрессивный"}
        norm = lambda s: KNOWN_QUIRKS.get(s, s)
        ref_norm: Counter = Counter({(norm(t2), tp): n for (t2, tp), n in ref_pairs.items()})
        pairs_norm: Counter = Counter({(norm(t2), tp): n for (t2, tp), n in pairs.items()})
        correct_n = sum((pairs_norm & ref_norm).values())
        missing_n = [t2 for t2 in missing if norm(t2) not in html]
        quirk_fixed = (correct < total or missing) and correct_n == total and not missing_n
        if quirk_fixed:
            result["known_quirk_normalized"] = True
            result["quirk_fix_plus"] = True
            result["data"]["note"] = ("+ модели: исправлена известная опечатка оригинала "
                                      "(латинская «c» в «Экспресcивный» — косяк Stratoplan)")
            result["data"]["missing"] = missing_n
            result["types"]["note"] = "посимвольно 95/96 из-за исправленной опечатки оригинала"

        types_extracted_ok = sum(pairs.values()) >= total * 0.9
        if quirk_fixed:
            ok = ok and True
        elif types_extracted_ok:
            ok = ok and (not missing) and correct >= total * 0.9
        else:
            ok = ok and not missing

        smoke = chrome_smoke(index)
        result["smoke"] = smoke
        ok = ok and bool(smoke.get("ok"))
    else:
        result["external"] = {"pass": False, "note": "нет index.html"}
        result["data"] = {"note": "нет index.html"}
        result["smoke"] = {"ran": False, "ok": False}

    result["passed"] = bool(ok)
    (run / "check.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "types"},
                     ensure_ascii=False, indent=2)[:1600])
    print("типы (пары текст+тип):", result.get("types", {}).get("correct"), "/",
          result.get("types", {}).get("total"))
    print("PASSED" if result["passed"] else "FAILED")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
