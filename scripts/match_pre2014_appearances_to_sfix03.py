"""Match pre-2014 (1999-2013) appearance records to SFIX03 player identities by name.

Reads the per-year CSVs produced by scripts/collect_pre2014_appearance_records.py and the
SFIX03 Japanese player universe, and joins them with the name-based resolution in
jfa_talent_analysis.pre2014_identity (kanji variant folding + registered-name alias
expansion). No network access; this is a pure local join.

Outputs, under --output-dir:
- matched_appearance_records_pre2014.csv        (rows joined to a unique source_player_id)
- pre2014_ambiguous_names.csv                   (2+ universe candidates -> SFIX04 queue)
- pre2014_nickname_candidates.csv               (katakana-nickname alias hits, review only)
- pre2014_unmatched_names.csv                   (no candidate; katakana_only flags likely
                                                 non-Japanese players, who are outside the
                                                 SFIX03 Japanese universe by construction)

Diagnostics are deduplicated per (season_year, competition_label, team_name, player_name)
with a row count, since the same player-season appears once per competition page.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

from jfa_talent_analysis.pre2014_identity import match_pre2014_records


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Match pre-2014 appearance records to SFIX03 player IDs by name."
    )
    parser.add_argument(
        "--players",
        type=Path,
        default=Path("data/interim/player_universe_sample.csv"),
        help="Japanese player universe CSV from SFIX03.",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("data/interim/pre2014"),
        help="Directory holding appearance_records_pre2014_<year>.csv files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/interim/pre2014"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    players = read_csv(args.players)
    input_paths = sorted(args.input_dir.glob("appearance_records_pre2014_*.csv"))
    if not input_paths:
        raise SystemExit(f"no appearance_records_pre2014_*.csv found in {args.input_dir}")
    records = [row for path in input_paths for row in read_csv(path)]
    print(f"players={len(players)} input_files={len(input_paths)} rows={len(records)}")

    result = match_pre2014_records(records, players)

    matched_path = args.output_dir / "matched_appearance_records_pre2014.csv"
    write_csv(matched_path, result.matched)
    write_csv(
        args.output_dir / "pre2014_ambiguous_names.csv",
        dedupe_diagnostics(result.ambiguous),
    )
    write_csv(
        args.output_dir / "pre2014_nickname_candidates.csv",
        dedupe_diagnostics(result.nickname_candidates),
    )
    write_csv(
        args.output_dir / "pre2014_unmatched_names.csv",
        dedupe_diagnostics(result.unmatched),
    )

    total = len(records)
    matched = len(result.matched)
    method_counts = Counter(row["match_method"] for row in result.matched)
    print(f"matched={matched}/{total} ({matched / total:.1%}) methods={dict(method_counts)}")
    print(
        f"ambiguous_rows={len(result.ambiguous)} "
        f"nickname_rows={len(result.nickname_candidates)} "
        f"unmatched_rows={len(result.unmatched)}"
    )
    katakana_rows = sum(
        1 for row in result.unmatched if row["katakana_only"] == "true"
    )
    print(f"unmatched katakana-only (likely non-Japanese) rows={katakana_rows}")
    print(f"wrote {matched_path}")


def dedupe_diagnostics(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Collapse per-row diagnostics to one row per player-season-competition with a count."""
    counts: dict[tuple[str, ...], dict[str, str]] = {}
    for row in rows:
        key = (
            row["season_year"],
            row["competition_label"],
            row["team_name"],
            row["player_name"],
        )
        if key in counts:
            counts[key]["row_count"] = str(int(counts[key]["row_count"]) + 1)
        else:
            counts[key] = {**row, "row_count": "1"}
    return sorted(
        counts.values(),
        key=lambda row: (
            row["season_year"],
            row["team_name"],
            row["player_name"],
            row["competition_label"],
        ),
    )


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
