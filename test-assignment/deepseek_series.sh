#!/bin/bash
# Серия DeepSeek V4.1 Flash 1017 через qwen-подписку (token-plan): 1 прогон на уровень
cd /home/dp/MyProjects/disc
KEY=$(python3 -c "import json; print(json.load(open('/home/dp/.pi/agent/auth.json'))['qwen-token-plan-individual']['key'])")
BASE=https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1
MODEL=deepseek-v4.1-flash-1017
DIR=models/deepseek-v4.1-flash-1017-qwen-plan/test-assignment
# каталожная конфигурация (models-store.json → qwen-token-plan-individual → deepseek-v4.1-flash-1017):
# thinkingFormat qwen; поддержаны ТОЛЬКО уровни low, high, max (medium/xhigh/off = null)
LEVEL_MAP='{"off":null,"minimal":null,"low":"low","medium":null,"high":"high","xhigh":null,"max":"max"}'
COMPAT='{"supportsStrictMode":true,"thinkingFormat":"qwen","supportsDeveloperRole":false,"supportsStore":false,"supportsReasoningEffort":true}' 
LOG=reports/deepseek_series.log
ts() { date "+%H:%M:%S"; }
for LVL in low high max; do
  N=1
  while [ -f "$DIR/run-$(printf %02d $N)/run.json" ]; do N=$((N+1)); done
  D="$DIR/run-$(printf %02d $N)"
  echo "[$(ts)] [$LVL] RUN → $D" >> $LOG
  timeout 3700 python3 test-assignment/runner.py \
    --provider qwen-token-plan-individual --base-url $BASE --api-key "$KEY" \
    --model $MODEL --thinking $LVL --level-map "$LEVEL_MAP" --compat "$COMPAT" --results "$D" >> $LOG 2>&1
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
echo "[$(ts)] ГОТОВО: серия deepseek-v4.1-flash-1017 завершена" >> $LOG
