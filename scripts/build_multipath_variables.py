"""Build the SAP §7 multi-stage pathway descriptors (descriptive/exploratory).

Reads the parsed 所属クラブ stint rows and writes one row per player with
has_<stage> flags, pathway_count, and pathway_sequence. No confirmatory test
uses these columns (docs/research_plan_phase1.md §7).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from jfa_talent_analysis.pathway_multiplicity import STAGES, build_multipath_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stints",
        type=Path,
        default=Path("data/interim/coach_network/player_institution_stints.csv"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/player_multipath_variables.csv"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    stints = pd.read_csv(args.stints, dtype=str).fillna("")
    rows = build_multipath_rows(stints)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rows.to_csv(args.output, index=False)

    print(f"players with >=1 final-stage stint: {len(rows)}")
    for stage in STAGES:
        rate = rows[f"has_{stage}"].mean()
        print(f"  has_{stage}: {rows[f'has_{stage}'].sum()} ({rate:.1%})")
    print("pathway_count distribution:")
    print(rows["pathway_count"].value_counts().sort_index().to_string())
    print("top sequences:")
    print(rows["pathway_sequence"].value_counts().head(10).to_string())
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
