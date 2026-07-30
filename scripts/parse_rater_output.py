"""Split a rater run into its answer and its cost (SAP §6b-2b-rate, v10).

Both engines can report what a run consumed, but only if asked in a structured
format, and the earlier driver asked for neither. The rating budget was then
discussed using the `minutes_spent` column -- a number the *model* writes about
itself, which turned out to overstate wall clock by roughly ten times. Anything
said about cost from here on should come from this log instead.

Claude reports usage and a dollar figure in one JSON object; Codex reports usage
on its `turn.completed` event and no cost, so the cost column stays empty there.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

LOG_COLUMNS = [
    "finished_at",
    "rater",
    "engine",
    "batch",
    "rows",
    "wall_seconds",
    "input_tokens",
    "output_tokens",
    "cache_read_tokens",
    "cache_write_tokens",
    "cost_usd",
    "status",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw", type=Path)
    parser.add_argument("--engine", choices=("claude", "codex"), required=True)
    parser.add_argument("--rater", required=True)
    parser.add_argument("--batch", required=True)
    parser.add_argument("--rows", type=int, default=0)
    parser.add_argument("--wall-seconds", type=float, default=0.0)
    parser.add_argument("--text-out", type=Path, required=True)
    parser.add_argument(
        "--usage-log", type=Path, default=Path("data/manual/gold_holdout/usage_log.csv")
    )
    return parser.parse_args()


def parse_claude(text: str) -> tuple[str, dict[str, float]]:
    payload = json.loads(text)
    usage = payload.get("usage", {})
    status = "aborted" if payload.get("is_error") else "ok"
    return payload.get("result", ""), {
        "status": status,
        "input_tokens": usage.get("input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0),
        "cache_read_tokens": usage.get("cache_read_input_tokens", 0),
        "cache_write_tokens": usage.get("cache_creation_input_tokens", 0),
        "cost_usd": payload.get("total_cost_usd", ""),
    }


def parse_codex(text: str) -> tuple[str, dict[str, float]]:
    messages, totals = [], {}
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "item.completed":
            item = event.get("item", {})
            if item.get("type") == "agent_message":
                messages.append(item.get("text", ""))
        elif event.get("type") == "turn.completed":
            usage = event.get("usage", {})
            totals = {
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0)
                + usage.get("reasoning_output_tokens", 0),
                "cache_read_tokens": usage.get("cached_input_tokens", 0),
                "cache_write_tokens": usage.get("cache_write_input_tokens", 0),
                "cost_usd": "",
                # No turn.completed means the run never finished its turn.
                "status": "ok",
            }
    return "\n".join(messages), totals or {"status": "aborted"}


def main() -> None:
    args = parse_args()
    text = args.raw.read_text(encoding="utf-8", errors="replace")
    try:
        answer, usage = parse_claude(text) if args.engine == "claude" else parse_codex(text)
    except (json.JSONDecodeError, KeyError):
        # A run that died before producing structured output still has to leave
        # its text behind, or the batch looks empty for the wrong reason.
        answer, usage = text, {"status": "aborted"}

    args.text_out.write_text(answer, encoding="utf-8")

    args.usage_log.parent.mkdir(parents=True, exist_ok=True)
    fresh = not args.usage_log.exists()
    with args.usage_log.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=LOG_COLUMNS)
        if fresh:
            writer.writeheader()
        writer.writerow(
            {
                "finished_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
                "rater": args.rater,
                "engine": args.engine,
                "batch": args.batch,
                "rows": args.rows,
                "wall_seconds": f"{args.wall_seconds:.0f}",
                **{column: usage.get(column, "") for column in LOG_COLUMNS[6:]},
            }
        )
    tokens = (usage.get("input_tokens") or 0) + (usage.get("output_tokens") or 0)
    print(f"  usage: {tokens} tokens, cost={usage.get('cost_usd', '')}")


if __name__ == "__main__":
    main()
