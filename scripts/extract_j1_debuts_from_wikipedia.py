from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

from jfa_talent_analysis.debut_extraction import extract_debut_evidence

OUTPUT_COLUMNS = [
    "source_player_id",
    "name_ja",
    "name_en",
    "wikipedia_title",
    "jleague_debut_year",
    "jleague_debut_league",
    "j1_debut_year",
    "j1_debut_basis",
    "sfpr01_first_j1_season",
    "validation",
]

TIERS = ("a", "b", "c")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Extract J.League/J1 debut evidence from cached full Wikipedia "
            "extracts and validate it against SFPR01 in-window ground truth "
            "(players whose extracted J1 debut is 2014+ should match SFPR01's "
            "first_j1_season). See "
            "docs/data_collection_revision_proposal_2026-07-07.md item 1."
        )
    )
    parser.add_argument(
        "--extracts-dir", type=Path, default=Path("data/interim/wikipedia_full_extracts")
    )
    parser.add_argument(
        "--outcomes", type=Path, default=Path("data/processed/player_pathway_outcomes.csv")
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/interim/wikipedia_full_extracts/j1_debut_evidence.csv"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sfpr01_first_j1 = read_sfpr01_first_j1(args.outcomes)

    rows: list[dict[str, str]] = []
    for tier in TIERS:
        path = args.extracts_dir / f"tier_{tier}.csv"
        if not path.exists():
            print(f"skipping missing {path}")
            continue
        for record in read_csv(path):
            evidence = extract_debut_evidence(record["full_extract"])
            sfpr01_season = sfpr01_first_j1.get(record["source_player_id"], "")
            rows.append(
                {
                    "source_player_id": record["source_player_id"],
                    "name_ja": record["name_ja"],
                    "name_en": record["name_en"],
                    "wikipedia_title": record["wikipedia_title"],
                    "jleague_debut_year": str(evidence.jleague_debut_year or ""),
                    "jleague_debut_league": evidence.jleague_debut_league or "",
                    "j1_debut_year": str(evidence.j1_debut_year or ""),
                    "j1_debut_basis": evidence.j1_debut_basis,
                    "sfpr01_first_j1_season": sfpr01_season,
                    "validation": validate(evidence.j1_debut_year, sfpr01_season),
                }
            )

    write_csv(args.output, rows)
    print(f"rows={len(rows)}")
    print("validation:")
    for status, count in sorted(Counter(row["validation"] for row in rows).items()):
        print(f"  {status}: {count}")
    with_j1 = [r for r in rows if r["j1_debut_year"]]
    print(f"rows with extracted j1_debut_year: {len(with_j1)}")
    pre2014 = [r for r in with_j1 if int(r["j1_debut_year"]) < 2014]
    print(f"  of which pre-2014 (backfill candidates): {len(pre2014)}")
    print(f"wrote={args.output}")


def validate(extracted_j1_year: int | None, sfpr01_season: str) -> str:
    """Compare Wikipedia-extracted J1 debut year with SFPR01's observed
    first_j1_season.

    - in_window_match / in_window_mismatch: extracted year is 2014+ so SFPR01
      should have seen the same debut — the accuracy measure for the extractor.
    - pre2014_backfill: extracted debut predates the SFPR01 window — the case
      this whole exercise exists to catch (SFPR01 either missed the player's J1
      history entirely or records a later return season).
    """
    if extracted_j1_year is None:
        return "no_wikipedia_j1_evidence"
    sfpr01_year = int(float(sfpr01_season)) if sfpr01_season else None
    if extracted_j1_year >= 2014:
        if sfpr01_year is None:
            return "in_window_but_sfpr01_missing"
        return "in_window_match" if extracted_j1_year == sfpr01_year else "in_window_mismatch"
    return "pre2014_backfill"


def read_sfpr01_first_j1(path: Path) -> dict[str, str]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        return {
            row["source_player_id"]: row["first_j1_season"]
            for row in csv.DictReader(file)
        }


def read_csv(path: Path) -> list[dict[str, str]]:
    csv.field_size_limit(10_000_000)
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
