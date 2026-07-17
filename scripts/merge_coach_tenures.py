from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

from jfa_talent_analysis.coach_network import normalize_institution_name

# One entry per file researched this project — see docs/institution_coach_pilot_2026-07-10.md
# (pilot) and docs/coach_network_design_2026-07-10.md (batches) for what each covers.
SOURCE_FILES = [
    ("pilot", "pilot_coach_tenures.csv"),
    ("hs_batch1", "hs_batch1_coach_tenures.csv"),
    ("hs_batch2", "hs_batch2_coach_tenures.csv"),
    ("hs_batch3", "hs_batch3_coach_tenures.csv"),
    ("uni_batch1", "uni_batch1_coach_tenures.csv"),
    ("uni_batch2", "uni_batch2_coach_tenures.csv"),
    ("uni_batch3", "uni_batch3_coach_tenures.csv"),
    ("jyouth_batch1", "jyouth_batch1_coach_tenures.csv"),
    ("jyouth_era_fill", "jyouth_era_fill_coach_tenures.csv"),
]

OUTPUT_COLUMNS = [
    "institution",
    "normalized_institution",
    "coach_name",
    "role_type",
    "from_year",
    "to_year",
    "source_urls",
    "confidence",
    "notes",
    "source_batch",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Merge every hand-researched coach-tenure batch CSV into one "
            "canonical table with a normalized join key, ready for the "
            "player x coach exposure join."
        )
    )
    parser.add_argument("--input-dir", type=Path, default=Path("data/interim/coach_network"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/interim/coach_network/coach_tenures_canonical.csv"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows: list[dict[str, str]] = []

    for source_batch, filename in SOURCE_FILES:
        path = args.input_dir / filename
        with path.open(encoding="utf-8", newline="") as file:
            for row in csv.DictReader(file):
                rows.append(
                    {
                        "institution": row["institution"],
                        "normalized_institution": normalize_institution_name(row["institution"]),
                        "coach_name": row["coach_name"],
                        "role_type": row["role_type"],
                        "from_year": row["from_year"],
                        "to_year": row["to_year"],
                        "source_urls": row["source_urls"],
                        "confidence": row["confidence"],
                        "notes": row["notes"],
                        "source_batch": source_batch,
                    }
                )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"merged rows={len(rows)}")
    print(f"distinct institutions (raw)={len({r['institution'] for r in rows})}")
    print(f"distinct institutions (normalized)={len({r['normalized_institution'] for r in rows})}")
    by_batch = Counter(r["source_batch"] for r in rows)
    for batch, count in by_batch.items():
        print(f"  {batch:12s} {count:4d} rows")
    print(f"wrote={args.output}")


if __name__ == "__main__":
    main()
