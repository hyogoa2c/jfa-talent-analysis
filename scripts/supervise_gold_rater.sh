#!/usr/bin/env bash
# Keep a rater going across usage-limit resets (SAP §6b-2b-rate, v10).
#
# The driver stops as soon as a batch comes back empty, which is what a usage
# limit looks like from outside. This waits and runs it again. Since the driver
# skips batches that already have output, a retry costs nothing but the batch
# that was in flight when the limit hit, and the queue drains itself whenever
# capacity comes back rather than waiting for someone to notice.
#
# usage: supervise_gold_rater.sh <a|b> <batch glob> [retry seconds] [max hours]
set -uo pipefail

RATER="${1:?rater a or b}"
GLOB="${2:?batch glob}"
RETRY="${3:-900}"
MAX_HOURS="${4:-12}"

deadline=$(( $(date +%s) + MAX_HOURS * 3600 ))
attempt=0

while :; do
  attempt=$((attempt + 1))
  echo "=== attempt ${attempt} $(date '+%m-%d %H:%M:%S')"
  bash scripts/run_gold_rater.sh "$RATER" "$GLOB"
  status=$?

  remaining=0
  for batch in $GLOB; do
    out="data/manual/gold_holdout/verdicts/$(basename "$batch")"
    [ -s "$out" ] || remaining=$((remaining + 1))
  done

  if [ "$remaining" -eq 0 ]; then
    echo "=== rater ${RATER} 完了 $(date '+%m-%d %H:%M:%S')（attempt ${attempt}）"
    exit 0
  fi
  if [ "$(date +%s)" -ge "$deadline" ]; then
    echo "=== ${MAX_HOURS}h 経過。残り ${remaining} バッチで打ち切る。" >&2
    exit 1
  fi

  echo "=== 残り ${remaining} バッチ（driver exit=${status}）。${RETRY}s 待って再試行する。"
  sleep "$RETRY"
done
