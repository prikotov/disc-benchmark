#!/usr/bin/env python3
"""Статистика агентной сессии pi из JSONL-следа (pi-session/).

Считает: ходы, вызовы инструментов по именам, токены (usage из assistant-
сообщений), продолжительность, факты сети (curl/wget в bash-командах),
обращения к источнику, ошибки. Пишет JSON (--out) или печатает.

Запуск: python3 test-assignment/session_stats.py --run models/<м>/test-assignment/run-01
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path


def parse(session_dir: Path) -> dict:
    files = sorted(session_dir.glob("*.jsonl"))
    if not files:
        return {"error": "нет JSONL-файлов сессии"}
    f = files[-1]  # последняя сессия (перезапуски копят файлы)
    turns = tool_calls = 0
    tools: Counter = Counter()
    tokens_in = tokens_out = 0
    bash_cmds: list[str] = []
    errors: list[str] = []
    first_ts = last_ts = None
    for line in f.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = d.get("timestamp")
        if ts:
            first_ts = first_ts or ts
            last_ts = ts
        m = d.get("message") or {}
        role = m.get("role")
        if role == "assistant":
            turns += 1
            us = m.get("usage") or {}
            tokens_in += int(us.get("input") or 0)
            tokens_out += int(us.get("output") or 0)
            for c in (m.get("content") or []) if isinstance(m.get("content"), list) else []:
                if isinstance(c, dict) and c.get("type") == "toolCall":
                    tool_calls += 1
                    tools[c.get("name", "?")] += 1
        if role == "toolResult" or d.get("type") == "tool_result":
            pass
        if role == "tool":
            pass
        # bash-команды: и из toolCall-args, и из content
        raw = json.dumps(d, ensure_ascii=False)
        for mm in re.finditer(r'"command"\s*:\s*"((?:[^"\\]|\\.)*)"', raw):
            cmd = mm.group(1).replace("\\n", " ")
            if any(w in cmd for w in ("curl", "wget", "http")):
                bash_cmds.append(cmd[:300])
        if re.search(r'"isError"\s*:\s*true', raw):
            errors.append(raw[:200])

    net = [c for c in bash_cmds if re.search(r"\b(curl|wget)\b", c)]
    src_touches = [c for c in net if "stratoplan" in c]
    return {
        "session_file": f.name,
        "turns": turns,
        "tool_calls": tool_calls,
        "tools_by_name": dict(tools),
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "bash_total": len(bash_cmds),
        "bash_with_network": len(net),
        "curl_to_source": len(src_touches),
        "network_cmds_sample": src_touches[:5] or net[:5],
        "errors": len(errors),
        "first_ts": first_ts,
        "last_ts": last_ts,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--out", default=None, help="куда писать JSON (по умолчанию <run>/session-stats.json)")
    args = ap.parse_args()
    run = Path(args.run).resolve()
    stats = parse(run / "pi-session")
    out = Path(args.out) if args.out else run / "session-stats.json"
    out.write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
