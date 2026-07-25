"""Resolve pre-2014 ambiguous / nickname identity queues via SFIX04 season histories.

Reads pre2014_ambiguous_names.csv and pre2014_nickname_candidates.csv (produced by
scripts/match_pre2014_appearances_to_sfix03.py), fetches each candidate player's SFIX04
season/team history once (cached to --output-dir/sfix04_cache/), and accepts a candidate
when it is the only one whose history covers that (season, club) — the same evidence rule
as scripts/suggest_identity_overrides_from_profiles.py, adapted to the archive's full club
names via sfix04_team_matches.

Output: pre2014_identity_resolutions.csv with one row per distinct
(season_year, team_name, player_name), resolution in {resolved, none_matched,
multiple_matched}. Feed the resolved rows back into the matcher with
`match_pre2014_appearances_to_sfix03.py --resolutions ...`.
"""

from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path

from jfa_talent_analysis.pre2014_identity import resolve_candidates_with_history
from jfa_talent_analysis.sources.jleague_data_site import (
    fetch_sfix04_player_profile,
    parse_sfix04_player_season_history,
    sfix04_player_url,
)

QUEUE_FILENAMES = ["pre2014_ambiguous_names.csv", "pre2014_nickname_candidates.csv"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resolve pre-2014 identity queues via SFIX04 season histories."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("data/interim/pre2014"),
        help="Directory holding the queue CSVs from the matcher.",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("data/interim/pre2014"))
    parser.add_argument(
        "--sleep",
        type=float,
        default=1.0,
        help="Delay between live SFIX04 fetches (not applied to cache hits).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    entries = read_queue_entries(args.input_dir)
    candidate_ids = sorted(
        {player_id for entry in entries for player_id in entry["candidate_ids"]}
    )
    print(f"queue_entries={len(entries)} distinct_candidates={len(candidate_ids)}")

    cache_dir = args.output_dir / "sfix04_cache"
    histories = {
        player_id: fetch_history(player_id, cache_dir, sleep_seconds=args.sleep)
        for player_id in candidate_ids
    }

    resolutions = []
    for entry in entries:
        candidates = [{"source_player_id": player_id} for player_id in entry["candidate_ids"]]
        player, resolution = resolve_candidates_with_history(
            candidates,
            histories,
            season_year=entry["season_year"],
            team_name=entry["team_name"],
        )
        resolutions.append(
            {
                "season_year": entry["season_year"],
                "team_name": entry["team_name"],
                "player_name": entry["player_name"],
                "queue": entry["queue"],
                "candidate_player_ids": ";".join(entry["candidate_ids"]),
                "resolution": resolution,
                "source_player_id": player["source_player_id"] if player else "",
                "note": sfix04_player_url(player["source_player_id"]) if player else "",
            }
        )

    out_path = args.output_dir / "pre2014_identity_resolutions.csv"
    with out_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(resolutions[0].keys()))
        writer.writeheader()
        writer.writerows(resolutions)

    resolved = sum(1 for row in resolutions if row["resolution"] == "resolved")
    unresolved = {
        row["resolution"] for row in resolutions if row["resolution"] != "resolved"
    }
    print(f"resolved={resolved}/{len(resolutions)} (other outcomes: {sorted(unresolved)})")
    print(f"wrote {out_path}")


def read_queue_entries(input_dir: Path) -> list[dict]:
    """One entry per distinct (season_year, team_name, player_name) across both queues."""
    entries: dict[tuple[str, str, str], dict] = {}
    for filename in QUEUE_FILENAMES:
        path = input_dir / filename
        if not path.exists() or path.stat().st_size == 0:
            continue
        with path.open(encoding="utf-8-sig", newline="") as file:
            for row in csv.DictReader(file):
                key = (row["season_year"], row["team_name"], row["player_name"])
                entry = entries.setdefault(
                    key,
                    {
                        "season_year": row["season_year"],
                        "team_name": row["team_name"],
                        "player_name": row["player_name"],
                        "queue": filename,
                        "candidate_ids": [],
                    },
                )
                for player_id in row["candidate_player_ids"].split(";"):
                    if player_id and player_id not in entry["candidate_ids"]:
                        entry["candidate_ids"].append(player_id)
    return sorted(
        entries.values(),
        key=lambda entry: (entry["season_year"], entry["team_name"], entry["player_name"]),
    )


def fetch_history(
    player_id: str, cache_dir: Path, *, sleep_seconds: float
) -> list[dict[str, str]]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{player_id}.html"
    if cache_path.exists():
        html = cache_path.read_text(encoding="utf-8")
    else:
        html = fetch_sfix04_player_profile(player_id)
        cache_path.write_text(html, encoding="utf-8")
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)
    return [
        {"season": record.season, "team_name": record.team_name}
        for record in parse_sfix04_player_season_history(
            html, source_player_id=player_id
        )
    ]


if __name__ == "__main__":
    main()
