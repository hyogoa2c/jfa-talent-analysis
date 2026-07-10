from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path

from jfa_talent_analysis.sources.wikidata import (
    AUDIT_COLUMNS,
    SUMMARY_COLUMNS,
    WikidataTeamStint,
    classify_wikidata_audit,
    fetch_player_team_stints,
    foreign_stints_in_gap,
    summarize_stints,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit Wikidata coverage for J.League reappearance candidates."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/processed/reappearance_candidates_2023_2025_gap2.csv"),
        help="Reappearance candidates CSV.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/interim/source_audit/wikidata_reappearance_candidates.csv"),
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--sleep", type=float, default=0.5)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    candidates = read_csv(args.input)
    if args.limit is not None:
        candidates = candidates[: args.limit]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    if not candidates:
        args.output.write_text("", encoding="utf-8")
        print("rows=0")
        print(f"wrote={args.output}")
        return

    fieldnames = list(candidates[0].keys()) + [
        column
        for column in SUMMARY_COLUMNS + AUDIT_COLUMNS
        if column not in candidates[0]
    ]
    # Write each row as it is audited so a mid-run failure keeps prior results.
    count = 0
    with args.output.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for index, candidate in enumerate(candidates, start=1):
            print(f"[{index}/{len(candidates)}] {candidate['name_ja']} / {candidate['name_en']}")
            stints = fetch_player_team_stints(candidate["name_ja"], candidate["name_en"])
            summary = summarize_stints(stints)
            summary.update(
                gap_summary(
                    stints,
                    previous_observed_season=candidate.get("previous_observed_season", ""),
                    reappearance_season=candidate.get("reappearance_season", ""),
                )
            )
            writer.writerow(
                {
                    **candidate,
                    **summary,
                    **classify_wikidata_audit(candidate["name_ja"], summary),
                }
            )
            file.flush()
            count += 1
            if args.sleep > 0 and index < len(candidates):
                time.sleep(args.sleep)

    print(f"rows={count}")
    print(f"wrote={args.output}")


def gap_summary(
    stints: list[WikidataTeamStint],
    *,
    previous_observed_season: str,
    reappearance_season: str,
) -> dict[str, str]:
    """Compute in-gap foreign stint columns, or blanks if the seasons can't be parsed."""
    previous_season = parse_season(previous_observed_season)
    next_season = parse_season(reappearance_season)
    if previous_season is None or next_season is None:
        return {
            "wikidata_foreign_team_in_gap_count": "",
            "wikidata_foreign_teams_in_gap": "",
        }
    in_gap_teams = foreign_stints_in_gap(
        stints,
        gap_start_season=previous_season + 1,
        gap_end_season=next_season - 1,
    )
    return {
        "wikidata_foreign_team_in_gap_count": str(len(in_gap_teams)),
        "wikidata_foreign_teams_in_gap": "|".join(in_gap_teams),
    }


def parse_season(value: str) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


if __name__ == "__main__":
    main()
