"""Check verdict and adjudication files before anything reads them.

The pilot adjudication came back with `intermediate` where the vocabulary says
`indeterminate` -- a typo no downstream code would have noticed, since an
unrecognised determination silently drops the row out of every count it belongs
in. With 539 rows arriving across ~150 files, that has to fail loudly instead.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

CATEGORIES = {
    "j_club_academy",
    "jfa_academy",
    "high_school",
    "university",
    "other",
    "unknown",
}
DETERMINATIONS = {"confirmed", "indeterminate", "unreachable"}
SOURCE_TYPES = {"official_club", "official_league", "school", "news", "other", ""}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", type=Path, nargs="+")
    parser.add_argument(
        "--adjudication",
        action="store_true",
        help="Check the `adjudicated_*` columns instead of the rater columns.",
    )
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def check(path: Path, adjudication: bool) -> list[str]:
    prefix = "adjudicated_" if adjudication else "gold_"
    category_column = f"{prefix}category" if adjudication else "gold_pathway_category"
    determination_column = "adjudicated_determination" if adjudication else "determination"
    institution_column = f"{prefix}institution" if adjudication else "gold_final_institution"

    problems = []
    seen: set[str] = set()
    for number, row in enumerate(read_csv(path), start=2):
        where = f"{path.name}:{number} {row.get('worksheet_id', '?')}"
        worksheet_id = row.get("worksheet_id", "")
        if worksheet_id in seen:
            problems.append(f"{where}: worksheet_id が重複している")
        seen.add(worksheet_id)

        category = row.get(category_column, "").strip()
        determination = row.get(determination_column, "").strip()
        institution = row.get(institution_column, "").strip()

        if category not in CATEGORIES:
            problems.append(f"{where}: category `{category}` は語彙にない")
        if determination not in DETERMINATIONS:
            problems.append(f"{where}: determination `{determination}` は語彙にない")
        if determination == "confirmed":
            if category == "unknown":
                problems.append(f"{where}: confirmed なのに category が unknown")
            if category != "unknown" and not institution:
                problems.append(f"{where}: confirmed なのに機関名が空")
            if not adjudication and not row.get("evidence_quote", "").strip():
                problems.append(f"{where}: confirmed なのに逐語引用が空")
            if not adjudication and not row.get("evidence_url", "").strip():
                problems.append(f"{where}: confirmed なのに根拠 URL が空")
        if determination in ("indeterminate", "unreachable") and category not in ("unknown", ""):
            problems.append(f"{where}: {determination} なのに category が {category}")
        if not adjudication and row.get("evidence_source_type", "") not in SOURCE_TYPES:
            problems.append(f"{where}: source_type `{row['evidence_source_type']}` は語彙にない")
    return problems


def main() -> None:
    args = parse_args()
    problems = [p for path in args.files for p in check(path, args.adjudication)]
    for problem in problems:
        print(problem)
    print(f"{len(args.files)} ファイル / 問題 {len(problems)} 件")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
