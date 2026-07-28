"""Fetch infobox youth-career fields for a set of players.

Targeted, not a census. The rows it is run over are academy labels already
flagged as J-membership boundary cases, where the decision rests on when the
player was actually in the academy and the 所属クラブ list records no years --
so the call is currently made against a window inferred from the birth year.

Adopting these fields as a *labelling* source is a separate question with a
separate bar (SAP §1b-3's coverage census, gold validation and era-symmetry
check; a 30-player probe already shows era-1 100% against era-2 77%). Nothing
here writes a pathway label.
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

from jfa_talent_analysis.sources.wikipedia_infobox import fetch_wikitext, parse_youth_entries

TITLE_SOURCES = (
    (Path("data/interim/pathway_national_team"), "pathway_tier_{key}_verified.csv", "abc"),
    (Path("data/interim/pre2014"), "priority{key}_pathway_verified.csv", "12"),
)
COLUMNS = ["source_player_id", "wikipedia_title", "youth_index", "youth_club", "youth_years"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--queue", type=Path, default=Path("data/manual/academy_reclassification_queue.csv")
    )
    parser.add_argument(
        "--verdict",
        default="j_club_boundary",
        help="Only fetch rows carrying this auto_verdict.",
    )
    parser.add_argument("--output", type=Path, default=Path("data/interim/infobox_youth.csv"))
    parser.add_argument("--sleep", type=float, default=1.0)
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def load_titles() -> dict[str, str]:
    titles: dict[str, str] = {}
    for directory, pattern, keys in TITLE_SOURCES:
        for key in keys:
            path = directory / pattern.format(key=key)
            if not path.exists():
                continue
            for row in read_csv(path):
                if row.get("wikipedia_title") and row.get("identity_check") == "confirmed":
                    titles.setdefault(row["source_player_id"], row["wikipedia_title"])
    return titles


def main() -> None:
    csv.field_size_limit(sys.maxsize)
    args = parse_args()
    titles = load_titles()

    # Resume rather than refetch: this runs against a live wiki and the earlier
    # rate-limit incident on this project came from repeated sustained access.
    done: set[str] = set()
    existing: list[dict[str, str]] = []
    if args.output.exists():
        existing = read_csv(args.output)
        done = {row["source_player_id"] for row in existing}

    targets = [
        row
        for row in read_csv(args.queue)
        if row["auto_verdict"] == args.verdict and row["source_player_id"] not in done
    ]
    print(f"targets={len(targets)} (already fetched {len(done)})")

    rows = list(existing)
    for row in targets:
        player_id = row["source_player_id"]
        title = titles.get(player_id)
        if not title:
            print(f"  - {player_id} {row.get('name_ja', '')}: no confirmed title")
            continue
        entries = parse_youth_entries(fetch_wikitext(title))
        time.sleep(args.sleep)
        if not entries:
            rows.append(
                {
                    "source_player_id": player_id,
                    "wikipedia_title": title,
                    "youth_index": "",
                    "youth_club": "",
                    "youth_years": "",
                }
            )
            print(f"  x {player_id} {row.get('name_ja', '')}: no youth fields")
            continue
        for entry in entries:
            rows.append(
                {
                    "source_player_id": player_id,
                    "wikipedia_title": title,
                    "youth_index": entry.index,
                    "youth_club": entry.club,
                    "youth_years": entry.years,
                }
            )
        summary = " / ".join(f"{e.club}({e.years or '年なし'})" for e in entries)
        print(f"  o {player_id} {row.get('name_ja', '')}: {summary}")

    rows.sort(key=lambda r: (int(r["source_player_id"]), r["youth_index"]))
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote={args.output} rows={len(rows)}")


if __name__ == "__main__":
    main()
