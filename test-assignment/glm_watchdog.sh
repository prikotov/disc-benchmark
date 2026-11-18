#!/bin/bash
# Смотритель серии MiMo: если прогон идёт > 50 мин без index.html — мягкий SIGTERM раннеру
# (дальше модель циклит в пустую, как показала off-серия). Лог: reports/glm_watchdog.log
LOG=/home/dp/MyProjects/disc/reports/glm_watchdog.log
ts() { date "+%H:%M:%S"; }
while pgrep -f "cloud_[s]eries.sh" > /dev/null; do
  RUNNER=$(pgrep -f "runner\.py.*models/glm-5.3-flash" | head -1)
  if [ -n "$RUNNER" ]; then
    DIR=$(ps -o args -p $RUNNER | grep -o '\-\-results [^ ]*' | awk '{print $2}')
    if [ -n "$DIR" ] && [ -d "$DIR" ]; then
      ELAPSED=$(( $(date +%s) - $(stat -c %Y "$DIR") ))
      if [ ! -f "$DIR/index.html" ] && [ $ELAPSED -gt 3000 ]; then
        echo "[$(ts)] $DIR: ${ELAPSED}с без index.html — SIGTERM раннеру $RUNNER" >> $LOG
        kill -TERM $RUNNER
        sleep 10
      fi
    fi
  fi
  sleep 60
done
echo "[$(ts)] серия завершена — смотритель выключается" >> $LOG
