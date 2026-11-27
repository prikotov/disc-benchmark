#!/usr/bin/env python3
"""Командный прогон team-assignment: тимлид pi + ролевые сабагенты в песочнице.

Один прогон = одна команда = одна сессия тимлида pi (расширение subagent
порождает ролевые сабагентов-процессы). Раннер собирает:

  - изолированный pi-home: расширение subagent, карточки ролей
    ({{model}} из композиции), models.json (ollama + модель композиции);
  - workspace: TASK.md, questions.json, AGENTS.md, (smoke: SCOPE.md);
  - песочницу bubblewrap (sandbox/pi-sandbox.sh, сеть host);
  - run.json c провенансом (composition_commit, methodology_commit...).

Использование:
  python3 team-assignment/runner.py --composition team-inkling \
      [--scope smoke] [--timeout 14400]

Определение состава: compositions/<composition>.json (status: approved).
Результаты: runs/<слаг>/run-XX/ внутри team-assignment/.
"""
import argparse
import datetime as dt
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent  # корень репо
TA = BASE / "team-assignment"


def env_var(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        sys.exit(f"ошибка: задай переменную окружения {name}")
    return v


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def git_commit(path: str) -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=BASE,
                          capture_output=True, text=True).stdout.strip()


def next_run_dir(slug: str) -> Path:
    runs = TA / "runs" / slug
    runs.mkdir(parents=True, exist_ok=True)
    n = 0
    while (runs / f"run-{n:02d}").exists():
        n += 1
    return runs / f"run-{n:02d}"


def assemble_pi_home(pi_home: Path, model: str, base_url: str, ctx: int) -> None:
    """pi-home: расширение subagent + карточки ролей + models.json."""
    pi_home.mkdir(parents=True)
    # 1. расширение subagent из поставки pi
    pkg = Path(os.environ.get(
        "PI_PKG_EXAMPLES",
        Path.home() / ".npm-global/lib/node_modules/@earendil-works/pi-coding-agent/examples"))
    src = pkg / "extensions" / "subagent"
    if not (src / "index.ts").exists():
        sys.exit(f"не найдено расширение subagent: {src}")
    (pi_home / "extensions" / "subagent").mkdir(parents=True)
    for f in ("index.ts", "agents.ts"):
        shutil.copy2(src / f, pi_home / "extensions" / "subagent" / f)
    # 2. карточки ролей ({{model}} → модель композиции)
    roles_dir = TA / json.load(open(TA / "compositions" / f"{args.composition}.json"))["roles_dir"]
    agents = pi_home / "agents"
    agents.mkdir()
    for card in sorted(roles_dir.glob("*.md")):
        text = card.read_text(encoding="utf-8").replace("{{model}}", model)
        (agents / card.name).write_text(text, encoding="utf-8")
    # 3. models.json
    providers = {"ollama": {
        "baseUrl": base_url.rstrip("/") + "/v1", "api": "openai-completions",
        "apiKey": "ollama",
        "models": [{"id": model, "contextWindow": ctx, "maxTokens": 32768,
                    "reasoning": True,
                    "thinkingLevelMap": {"off": "false", "low": "low",
                                         "medium": "medium", "high": "high"}}]}}
    (pi_home / "models.json").write_text(
        json.dumps({"providers": providers}, ensure_ascii=False, indent=2),
        encoding="utf-8")


def main() -> None:
    global args
    ap = argparse.ArgumentParser()
    ap.add_argument("--composition", required=True,
                    help="слаг композиции (compositions/<слаг>.json)")
    ap.add_argument("--scope", default="smoke", choices=["smoke"],
                    help="smoke: без деплоя и реальной почты, LLM — ollama")
    ap.add_argument("--timeout", type=int, default=14400, help="секунды")
    ap.add_argument("--context", type=int, default=131072)
    args = ap.parse_args()

    comp_path = TA / "compositions" / f"{args.composition}.json"
    comp = json.load(open(comp_path, encoding="utf-8"))
    if comp.get("status") != "approved":
        sys.exit(f"композиция {comp_path.name}: status={comp.get('status')!r}, запускать только approved")
    slug = comp["slug"]
    model = next(iter(comp["roles"].values()))["model"]
    think = next(iter(comp["roles"].values()))["think"]
    base_url = env_var("OLLAMA_BASE_URL")
    run_dir = next_run_dir(slug)
    workspace = run_dir / "workspace"
    workspace.mkdir(parents=True)
    log(f"прогон: {run_dir} | композиция {slug} (модель {model}, тимлид think={think})")

    comp_commit = subprocess.run(["git", "rev-parse", f"HEAD:{comp_path.relative_to(BASE)}"],
                                 cwd=BASE, capture_output=True, text=True).stdout.strip()
    meth_commit = git_commit(BASE)

    # pi-home
    pi_home_src = run_dir / "pi-home-src"
    assemble_pi_home(pi_home_src, model, base_url, args.context)
    # ro-копия для песочницы не нужна: монтируем pi_home_src прямо (ro) и копируем внутрь
    # workspace: материалы задания
    shutil.copy2(TA / "TASK.md", workspace / "TASK.md")
    shutil.copy2(TA / "reference" / "questions.json", workspace / "questions.json")
    shutil.copy2(TA / "AGENTS.md", workspace / "AGENTS.md")
    (workspace / "tmp").mkdir()

    # промпт тимлида (+scope для smoke)
    prompt = json.load(open(TA / "prompts" / "prompt.json", encoding="utf-8"))["prompt"]
    scope_lines = []
    if args.scope == "smoke":
        scope_lines = [
            "", "---", "",
            "## Дополнение к тестовому (smoke) прогону — имеет приоритет над пунктом про деплой",
            "",
            "- Деплой на продакшен и реальная отправка почты В ЭТОМ ПРОГОНЕ НЕДОСТУПНЫ",
            "  (креды не выданы): финальный критерий — продукт собран, работает локально",
            "  (tester проверяет поток, подсчёт и интерпретацию на локальном сервере)",
            "  и подготовлена инструкция деплоя (`team/deploy.md`) для будущего полного прогона.",
            "- LLM-интерпретация: переменные DISC_LLM_BASE_URL/DISC_LLM_MODEL указывают",
            "  на локальный ollama (модель inkling-2-mini:pi-128k); ключ не нужен",
            "  (DISC_LLM_KEY_FILE указывает на пустой файл — игнорируй его).",
            "- Почта: DISC_SMTP_DSN не задан — письмо недоступно; backend честно помечает",
            "  отправку письма недоступной, не ломая поток.",
            "- В final-report явно перечисли, что выполнено, а что вне скоупа этого прогона.",
        ]
        (workspace / "SCOPE.md").write_text("\n".join(scope_lines[3:]).strip() + "\n", encoding="utf-8")
        (workspace / ".null-key").write_text("", encoding="utf-8")
    prompt += "\n".join(scope_lines)
    prompt_file = workspace / ".teamlead-prompt"
    prompt_file.write_text(prompt, encoding="utf-8")

    # run.json (провенанс)
    run_meta = {
        "assignment": "team-assignment",
        "prompt": "v1",
        "composition": slug,
        "composition_commit": comp_commit,
        "methodology_commit": meth_commit,
        "roles_dir": comp["roles_dir"],
        "scope": args.scope,
        "model": model,
        "teamlead_thinking": think,
        "subagent_thinking": "default (карточки с model: не наследуют уровень)",
        "production_version": None,
        "started_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    (run_dir / "run.json").write_text(
        json.dumps(run_meta, ensure_ascii=False, indent=2), encoding="utf-8")

    # запуск в песочнице
    inner = (
        "mkdir -p /work/.pi-home && cp -a /pi-home-ro/. /work/.pi-home/ && "
        f"PI_CODING_AGENT_DIR=/work/.pi-home pi -p "
        f"--session-dir /work/.pi-session "
        f"--provider ollama --model {model} --thinking {think} "
        f'"$(cat /work/.teamlead-prompt)"'
    )
    env = {**os.environ,
           "SANDBOX_WORKDIR": str(workspace),
           "SANDBOX_PI_HOME": str(pi_home_src),
           "SANDBOX_CMD": inner,
           "SANDBOX_ENV_PREFIX": "DISC_,OLLAMA_BASE_URL",
           "DISC_LLM_BASE_URL": base_url.rstrip("/") + "/v1",
           "DISC_LLM_MODEL": model,
           "DISC_LLM_KEY_FILE": "/work/.null-key"}
    for k in ("DISC_SMTP_DSN", "DISC_DEPLOY_HOST", "DISC_DEPLOY_USER",
              "DISC_DEPLOY_KEY_FILE", "DISC_DEPLOY_ROOT", "DISC_TEST_MAILBOX"):
        env.pop(k, None)  # smoke: без почты и деплоя

    sandbox = TA / "sandbox" / "pi-sandbox.sh"
    cmd = ["bash", str(sandbox)]
    log(f"запуск тимлида: pi --thinking {think}, тайм-аут {args.timeout}s")
    log(f"лог: {run_dir / 'pi-run.log'}")
    t0 = time.time()
    proc = subprocess.Popen(cmd, cwd=workspace, env=env,
                            stdout=open(run_dir / "pi-run.log", "w"),
                            stderr=subprocess.STDOUT, text=True,
                            start_new_session=True)

    def on_signal(signum, _f):
        log(f"сигнал {signum}: гашу группу песочницы")
        os.killpg(proc.pid, signal.SIGTERM)

    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)
    try:
        rc = proc.wait(timeout=args.timeout)
    except subprocess.TimeoutExpired:
        log(f"тайм-аут {args.timeout}s: гашу группу")
        os.killpg(proc.pid, signal.SIGTERM)
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
        rc = None
    elapsed = time.strftime("%H:%M:%S", time.gmtime(time.time() - t0))
    log(f"песочница завершилась: код={rc}, время={elapsed}")

    # сессия тимлида из workspace → run-XX/pi-session
    sess = workspace / ".pi-session"
    if sess.exists():
        shutil.move(str(sess), str(run_dir / "pi-session"))
    # .pi-home оставляем в workspace как след (изолированный конфиг прогона)

    run_meta["exit_code"] = rc
    run_meta["elapsed"] = elapsed
    run_meta["finished_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    (run_dir / "run.json").write_text(
        json.dumps(run_meta, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"run.json дополнен; прогон: {run_dir}")


if __name__ == "__main__":
    main()
