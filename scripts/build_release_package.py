"""Assemble what gets deposited, and nothing else (Zenodo / preprint).

The deposit line was settled in `docs/source_audit_jleague_data_site.md`: the
adjudicated gold is this project's own work product and ships with player names,
because a verdict a third party cannot check is not worth publishing; the raw
appearance records are someone else's database and do not ship, so the
collection scripts go instead.

The gold released here is the *evidence*, not just the verdict. A reader who
wants to know whether 「大学」 was the right call for a given player gets the URL
and the verbatim quote the rater worked from, per rater, plus how the row was
resolved -- two raters agreeing, an adjudicator deciding, or a single rating.

Run: uv run python scripts/build_release_package.py
"""

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path

RESOLVED = Path("data/manual/gold_holdout/gold_resolved.csv")
KEY = Path("data/manual/gold_holdout_worksheet_key.csv")
VERDICTS = (
    Path("data/manual/gold_holdout/verdicts_pilot_rater_a.csv"),
    Path("data/manual/gold_holdout/verdicts_pilot_rater_b.csv"),
    Path("data/manual/gold_holdout/verdicts_important_rater_a.csv"),
    Path("data/manual/gold_holdout/verdicts_important_rater_b.csv"),
    Path("data/manual/gold_holdout/verdicts_reliability_rater_a.csv"),
    Path("data/manual/gold_holdout/verdicts_reliability_rater_b.csv"),
    Path("data/manual/gold_holdout/verdicts_single_rater_a.csv"),
    Path("data/manual/gold_holdout/verdicts_single_rater_b.csv"),
)

GOLD_COLUMNS = [
    "worksheet_id",
    "era",
    "stratum",
    "sampling_stage",
    "name_ja",
    "gold_pathway_category",
    "gold_final_institution",
    "determination",
    "resolution",
    "note",
]

EVIDENCE_COLUMNS = [
    "worksheet_id",
    "rater",
    "gold_pathway_category",
    "gold_final_institution",
    "determination",
    "evidence_url",
    "evidence_quote",
    "evidence_source_type",
    "note",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", type=Path, default=Path("release"))
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    key = {row["worksheet_id"]: row for row in read_csv(KEY)}

    # The J.League player id stays behind: it is that database's identifier, and
    # the worksheet id is enough to join the released files to each other.
    gold = []
    for row in read_csv(RESOLVED):
        identity = key[row["worksheet_id"]]
        gold.append(
            {
                **row,
                "era": identity["era"],
                "stratum": identity["stratum"],
                "sampling_stage": identity["batch"],
            }
        )
    gold.sort(key=lambda row: row["worksheet_id"])
    write_csv(args.outdir / "gold_holdout_labels.csv", GOLD_COLUMNS, gold)

    evidence = []
    for path in VERDICTS:
        if path.exists():
            evidence.extend(read_csv(path))
    evidence.sort(key=lambda row: (row["worksheet_id"], row.get("rater", "")))
    write_csv(args.outdir / "gold_holdout_evidence.csv", EVIDENCE_COLUMNS, evidence)

    manifest = args.outdir / "MANIFEST.txt"
    lines = [
        "Deposited files (see docs/source_audit_jleague_data_site.md for why these and not others)",
        "",
    ]
    for path in sorted(args.outdir.glob("*.csv")):
        blob = path.read_bytes()
        lines.append(f"{path.name}  sha256={hashlib.sha256(blob).hexdigest()[:16]}  {len(blob)} bytes")
    lines += [
        "",
        "NOT deposited: raw appearance records from the J.League Data Site, and cached",
        "Wikipedia article text. Both are third-party data; the collection scripts in",
        "scripts/ re-derive them from the sources.",
    ]
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"gold {len(gold)} 行 / 根拠 {len(evidence)} 行 -> {args.outdir}")
    print(manifest.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
