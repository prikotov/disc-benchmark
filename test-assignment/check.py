#!/usr/bin/env python3
"""Машинные проверки решения прогона (ярус 0, до судей).

Проверяет run-каталог (см. runner.py):
1. files       — инвентарь созданного, наличие index.html в корне;
2. external    — решение самодостаточно: нет внешних запросов (CDN, fetch,
                 XHR, sendBeacon, WebSocket, внешние ресурсы в разметке);
3. data        — точность данных: все 96 прилагательных из эталона
                 (reference/questions.json) присутствуют посимвольно;
                 отображение (текст -> тип) извлекается из разметки/данных
                 решения и сравнивается с эталоном как мультимножество пар;
4. smoke       — рендер в headless Chrome (google-chrome --headless):
                 страница открывается, DOM отрисовался, нет Uncaught-ошибок
                 в консоли; симуляция полного прохождения — отдельная задача
                 (playwright), в pilote не выполняется.

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
    """(pass, находки-паттерны, уникальные внешние URL)."""
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
    ]
    for name, pat in patterns:
        m = re.findall(pat, html, re.I)
        if m:
            findings.append(f"{name}: {len(m)}")
    for m in re.finditer(r"https?://[^\s\"'<>)]+", html):
        u = m.group(0).rstrip("\\")
        if "w3.org" not in u and "stratoplan" not in u:  # w3.org — часто в xmlns/svg
            urls.add(u[:120])
    return (not findings and not urls), findings, sorted(urls)


def extract_pairs(html: str) -> Counter:
    """Извлечение пар (текст, тип) из разметки/данных решения, best effort.
    Мультимножество: прилагательные могут повторяться с разными типами."""
    pairs: Counter = Counter()
    pats = [
        # разметка оригинала: <li data-type="d">Волевой</li>
        r"data-type=[\"']([disc])[\"'][^>]*>\s*([^<>{]{2,40}?)\s*<",
        # JS-объекты в обоих порядках ключей
        r"type\s*:\s*[\"']([disc])[\"']\s*,\s*text\s*:\s*[\"']([^\"']{2,40})[\"']",
        r"text\s*:\s*[\"']([^\"']{2,40})[\"']\s*,\s*type\s*:\s*[\"']([disc])[\"']",
        # массивы пар ["d","Волевой"] / ["Волевой","d"]
        r"\[\s*[\"']([disc])[\"']\s*,\s*[\"']([^\"']{2,40})[\"']\s*\]",
        r"\[\s*[\"']([^\"']{2,40})[\"']\s*,\s*[\"']([disc])[\"']\s*\]",
        # type: "d", label/title/word/content
        r"type\s*:\s*[\"']([disc])[\"']\s*,\s*(?:label|title|word|content)\s*:\s*[\"']([^\"']{2,40})[\"']",
        r"(?:label|title|word|content)\s*:\s*[\"']([^\"']{2,40})[\"']\s*,\s*type\s*:\s*[\"']([disc])[\"']",
    ]
    for pat in pats:
        for m in re.finditer(pat, html):
            g = m.groups()
            t, txt = (g[0], g[1]) if g[0] in ("d", "i", "s", "c") else (g[1], g[0])
            txt = txt.strip()
            if 2 <= len(txt) <= 40:
                pairs[(txt, t)] += 1
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
        ok = ok and not missing

        pairs = extract_pairs(html)
        common = pairs & ref_pairs                      # пересечение мультимножеств
        correct = sum(common.values())                  # верные пары (текст, тип)
        mismatches: dict = {}
        for (txt, tp), n in (ref_pairs - pairs).items():
            mismatches[f"{txt} -> {tp}"] = f"не хватает ×{n}"
        for (txt, tp), n in (pairs - ref_pairs).items():
            mismatches[f"{txt} -> {tp}"] = mismatches.get(f"{txt} -> {tp}", "") + f" лишних ×{n}"
        result["types"] = {"extracted": sum(pairs.values()), "correct": correct,
                           "total": sum(ref_pairs.values()), "mismatches": mismatches}
        # типы извлекаются не из любой реализации: слабое извлечение —
        # не провал (ручная проверка/судьи), но фиксируется
        if sum(pairs.values()) >= 96 * 0.9:
            ok = ok and correct >= 96 * 0.9

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
