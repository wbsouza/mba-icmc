#!/usr/bin/env bash
# Stop every running experiment job (run scripts, xargs pools, algo-backtest runs) and remove LEAN containers.
for pat in 'tf-year/run.sh' 'trading-year/run-' 'xargs -P' 'algo-backtest run --strategy'; do
  for p in $(pgrep -f "$pat"); do [ "$p" != "$$" ] && [ "$p" != "$PPID" ] && kill "$p" 2>/dev/null; done
done
sleep 3
for p in $(pgrep -f 'algo-backtest run --strategy'); do kill -9 "$p" 2>/dev/null; done
docker ps --format '{{.ID}} {{.Image}}' | grep quantconnect/lean | awk '{print $1}' | xargs -r docker rm -f > /dev/null 2>&1
echo "runs left: $(pgrep -fc 'algo-backtest run --strategy') lean containers: $(docker ps --format '{{.Image}}' | grep -c quantconnect)"
