#!/usr/bin/env bash
# Самопроверка песочницы pi-sandbox.sh: гарантирует обещанное в README ДО серии.
# Проверки (по официальным предупреждениям model card inkling — деструктивные
# действия и неверные отчёты — плюс общий риск контейнмента):
#   1. секреты хоста не видны из песочницы
#   2. env без секретов (--clearenv)
#   3. запись возможна только в workdir
#   4. сеть до ollama есть (при SANDBOX_NETWORK=host)
#   5. pi жив внутри: LLM отвечает верно (санити-вопрос)
# Использование: SANDBOX_WORKDIR=… PI_MODEL=… ./selfcheck.sh
#                (остальные env — как у pi-sandbox.sh)
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${SANDBOX_WORKDIR:?задай SANDBOX_WORKDIR}"
MODEL="${PI_MODEL:?задай PI_MODEL}"
mkdir -p "$WORKDIR"
PASS=0; FAIL=0
ok()  { echo "ok   - $1"; PASS=$((PASS+1)); }
bad() { echo "FAIL - $1"; FAIL=$((FAIL+1)); }

# --- 1-3: изоляция ФС и env --------------------------------------------------
# PI_PROVIDER пинаем явно: из хостового env может утекать другое значение
# (например PI_PROVIDER=zai) — selfcheck не должен зависеть от ambient env.
cat > "$WORKDIR/.selfcheck-inner.sh" <<'EOF'
set -u
R=0
for p in /home/dp/.pi/agent/auth.json \
         /home/dp/MyProjects/disc/.env.local \
         /home/dp/MyProjects/disc/AGENTS.md; do
  [ ! -e "$p" ] || { echo "VISIBLE_HOST_PATH $p"; R=1; }
done
env | grep -Ei 'key|token|secret|password|proxy' >/dev/null 2>&1 \
  && { echo "ENV_HAS_SECRETISH"; R=1; }
touch /usr/share/.pwn-test 2>/dev/null && { echo "WROTE_USR"; R=1; }
echo t > /work/.w-test || { echo "CANNOT_WRITE_WORK"; R=1; }
exit $R
EOF
OUT="$(SANDBOX_CMD='bash /work/.selfcheck-inner.sh' PI_PROVIDER=ollama "$HERE/pi-sandbox.sh" 2>&1)"
if grep -qE 'VISIBLE_HOST_PATH|ENV_HAS_SECRETISH|WROTE_USR|CANNOT_WRITE_WORK' <<<"$OUT"; then
  bad "изоляция ФС/env: $OUT"
else
  ok "изоляция ФС/env (секреты невидимы, env чист, запись только в workdir)"
fi

# --- 4: сеть до ollama --------------------------------------------------------
BASE="$(printf %s "${PI_BASE_URL:-${OLLAMA_BASE_URL:-}}" | sed -E 's#https?://##; s#/?v1/?$##; s#/$##')"
if [ -n "$BASE" ]; then
  VER="$(SANDBOX_CMD="curl -s --max-time 10 http://$BASE/api/version" PI_PROVIDER=ollama "$HERE/pi-sandbox.sh" 2>/dev/null | tail -1)"
  grep -q '"version"' <<<"$VER" && ok "сеть до ollama ($VER)" || bad "сеть до ollama: «$VER»"
fi

# --- 5: живой LLM-ответ (stdout чист: лог argv идёт в stderr) -----------------
ANS="$(SANDBOX_PROMPT="Ответь одним словом: сколько будет 9*9?" \
      PI_PROVIDER=ollama "$HERE/pi-sandbox.sh" 2>/dev/null | tail -1)"
grep -q '81' <<<"$ANS" && ok "LLM-санити ($ANS)" \
  || bad "LLM-санити: «$ANS» | debug: $(SANDBOX_PROMPT='Ответь одним словом: сколько будет 9*9?' PI_PROVIDER=ollama "$HERE/pi-sandbox.sh" 2>&1 | tail -2)"

rm -f "$WORKDIR/.selfcheck-inner.sh" "$WORKDIR/.w-test"
echo "---- selfcheck: $PASS ok, $FAIL fail"
exit "$FAIL"
