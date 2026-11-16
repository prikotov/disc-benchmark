#!/bin/bash
# Универсальная серия для облачных провайдеров pi: RUNS прогонов на каждый уровень LEVELS.
# Параметры модели (ctx, maxTokens, level-map, compat) — из каталога pi (models-store.json),
# ничего не зажимаем: рекомендуемые настройки провайдера.
# Использование (env):
#   MODEL, PROVIDER, DIR, LEVELS, RUNS, CTX, MAXTOK, LEVEL_MAP, COMPAT, LOG
cd /home/dp/MyProjects/disc
API_KEY=$(python3 -c "import json,sys; print(json.load(open('/home/dp/.pi/agent/auth.json'))['$PROVIDER']['key'])")
ts() { date "+%H:%M:%S"; }
echo "[$(ts)] === СЕРИЯ $MODEL ($PROVIDER): уровни [$LEVELS] × $RUNS, ctx=$CTX, maxTokens=$MAXTOK" >> $LOG
for LVL in $LEVELS; do
  for i in $(seq 1 $RUNS); do
    N=1
    while [ -f "$DIR/run-$(printf %02d $N)/run.json" ]; do N=$((N+1)); done
    D="$DIR/run-$(printf %02d $N)"
    echo "[$(ts)] [$LVL #$i/$RUNS] RUN → $D" >> $LOG
    timeout 7000 python3 test-assignment/runner.py \
      --provider "$PROVIDER" \
      --base-url "$BASE_URL" \
      --api-key "$API_KEY" \
      --model "$MODEL" \
      --thinking "$LVL" \
      --level-map "$LEVEL_MAP" \
      --compat "$COMPAT" \
      --context "$CTX" --max-tokens "$MAXTOK" \
      --results "$D" >> $LOG 2>&1
    RC=$?
    echo "[$(ts)]   runner: rc=$RC" >> $LOG
    if [ ! -f "$D/index.html" ]; then echo "[$(ts)]   нет index.html — пропуск проверок" >> $LOG; continue; fi
    python3 test-assignment/check.py --run "$D" >> $LOG 2>&1; echo "[$(ts)]   check: rc=$?" >> $LOG
    node test-assignment/playthrough.mjs --html "$D/index.html" \
      --ref test-assignment/reference/questions.json \
      --out-dir "$D/screenshots" --json "$D/playthrough.json" >> $LOG 2>&1
    echo "[$(ts)]   playthrough: rc=$?" >> $LOG
    python3 test-assignment/judge.py --run "$D" >> $LOG 2>&1; echo "[$(ts)]   judge: rc=$?" >> $LOG
    python3 test-assignment/judge_ux.py --run "$D" >> $LOG 2>&1; echo "[$(ts)]   judge_ux: rc=$?" >> $LOG
  done
done
echo "[$(ts)] ГОТОВО: серия $MODEL завершена" >> $LOG
