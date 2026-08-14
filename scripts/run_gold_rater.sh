#!/usr/bin/env bash
# Drive one rater through its batches (SAP §6b-2b-rate, v10).
#
# One engine invocation per batch of five, because a rater working a long list
# re-sends its whole transcript every turn and a dropped run replays all of it.
# Each batch writes its own file, so a crash costs one batch and a re-run skips
# what is already done.
#
# The rater gets web tools and nothing else. That is not only for cost: with no
# file access it cannot read the classifier output it is supposed to be an
# independent check on.
#
# usage: run_gold_rater.sh <a|b> [batch glob]
set -uo pipefail

RATER="${1:?rater a or b}"
BATCH_DIR="data/manual/gold_holdout/batches"
OUT_DIR="data/manual/gold_holdout/verdicts"
PROMPT_FILE="scripts/gold_rating_prompt.md"
GLOB="${2:-${BATCH_DIR}/batch_*_rater_${RATER}.csv}"

mkdir -p "$OUT_DIR"
TODAY=$(date +%Y-%m-%d)

for batch in $GLOB; do
  name=$(basename "$batch" .csv)
  out="${OUT_DIR}/${name}.csv"
  [ -s "$out" ] && { echo "skip ${name} (done)"; continue; }

  prompt=$(
    cat "$PROMPT_FILE"
    printf '\n\n## 対象（この %s 名だけを判定する）\n\n' "$(($(wc -l < "$batch") - 1))"
    cut -d, -f1-7 "$batch"
    printf '\n`rater` は `%s`、`researched_at` は `%s` と書く。\n' "$RATER" "$TODAY"
  )

  echo "=== ${name} $(date +%H:%M:%S)"
  raw="${OUT_DIR}/${name}.raw"
  started=$(date +%s)
  expected=$(($(wc -l < "$batch") - 1))
  if [ "$RATER" = "a" ]; then
    engine=claude
    # The prompt goes on stdin: --allowed-tools is variadic and would eat it.
    printf '%s' "$prompt" | claude -p --model sonnet --output-format json \
      --allowed-tools WebSearch WebFetch > "$raw" 2>&1
  else
    engine=codex
    # An empty cwd keeps the sandbox from reaching the repository at all.
    work=$(mktemp -d)
    printf '%s' "$prompt" | codex exec --json -c tools.web_search=true -m gpt-5.6-sol \
      --skip-git-repo-check -s read-only -C "$work" - > "$raw" 2>&1
    rmdir "$work" 2>/dev/null || true
  fi

  # Structured output carries the tokens and the dollar figure; record them
  # before the raw file is discarded. Cost claims should come from this log,
  # not from the `minutes_spent` the model writes about itself.
  uv run python scripts/parse_rater_output.py "$raw" --engine "$engine" \
    --rater "$RATER" --batch "$name" --rows "$expected" \
    --wall-seconds "$(( $(date +%s) - started ))" --text-out "${raw}.txt"

  if uv run python scripts/extract_verdict_rows.py "${raw}.txt" --output "$out" --expected "$expected"; then
    rm -f "$raw" "${raw}.txt"
  else
    echo "  WARN ${name}: 行数が合わない（${raw} を残した）"
    if [ ! -s "$out" ]; then
      rm -f "$out"
      # Zero rows means the engine never answered -- a usage limit, an auth
      # failure, a network outage. Whatever it is, the next batch will hit it
      # too, so stop instead of burning the queue into empty files.
      echo "  ABORT: ${name} が 1 行も返さなかった。残りは実行しない。" >&2
      exit 2
    fi
  fi
done

echo "done rater=${RATER}: $(ls "${OUT_DIR}"/batch_*_rater_"${RATER}".csv 2>/dev/null | wc -l | tr -d ' ') batches"
