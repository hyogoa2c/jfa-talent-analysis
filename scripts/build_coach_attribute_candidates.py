from __future__ import annotations

import argparse
import csv
import time
from collections import defaultdict
from pathlib import Path

from jfa_talent_analysis.club_history_extraction import parse_club_history
from jfa_talent_analysis.coach_network import is_gap_placeholder
from jfa_talent_analysis.sources.wikipedia import resolve_wikipedia_title_and_extract

OUTPUT_COLUMNS = [
    "coach_name",
    "institutions",  # pipe-joined researched institutions this coach appears at
    "tenure_year_span",  # earliest-latest tenure year across all their rows (identity/era context)
    "wikipedia_title",
    "extract_len",
    "identity_signal",  # whether a researched institution appears in the article (coaching-role sanity check)
    "playing_clubs",  # pipe-joined parsed 所属クラブ list (their own playing career)
    "n_playing_clubs",
    "needs_review",  # blank / reason — clubs empty, no extract, or identity unconfirmed
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Phase C step 1: resolve each researched coach to their Wikipedia "
            "article and auto-extract their own playing-career club list (the "
            "raw material for the J1/overseas playing-experience attributes the "
            "user asked for). Reuses the player toolchain unchanged — a coach's "
            "所属クラブ section IS their playing career. Emits a needs_review "
            "flag so the empirical clean/review split can be measured before "
            "committing to a classification or review pass."
        )
    )
    parser.add_argument(
        "--tenures",
        type=Path,
        default=Path("data/interim/coach_network/coach_tenures_canonical.csv"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/interim/coach_network/coach_attribute_candidates.csv"),
    )
    parser.add_argument(
        "--extracts",
        type=Path,
        default=Path("data/interim/coach_network/coach_wikipedia_extracts.csv"),
    )
    parser.add_argument("--sleep", type=float, default=1.0)
    return parser.parse_args()


def load_coach_roster(tenures_path: Path) -> dict[str, dict[str, object]]:
    with tenures_path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    roster: dict[str, dict[str, object]] = defaultdict(
        lambda: {"institutions": set(), "years": set()}
    )
    for row in rows:
        if is_gap_placeholder(row["coach_name"], row["role_type"]):
            continue
        entry = roster[row["coach_name"]]
        entry["institutions"].add(row["normalized_institution"])  # type: ignore[union-attr]
        for key in ("from_year", "to_year"):
            if row[key]:
                entry["years"].add(int(row[key]))  # type: ignore[union-attr]
    return roster


def load_cached_extracts(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    csv.field_size_limit(10_000_000)
    with path.open(encoding="utf-8", newline="") as file:
        return {row["coach_name"]: row for row in csv.DictReader(file)}


def main() -> None:
    args = parse_args()
    roster = load_coach_roster(args.tenures)
    cache = load_cached_extracts(args.extracts)

    args.extracts.parent.mkdir(parents=True, exist_ok=True)
    extract_writer_needs_header = not args.extracts.exists()
    extract_file = args.extracts.open("a", encoding="utf-8", newline="")
    extract_writer = csv.DictWriter(
        extract_file, fieldnames=["coach_name", "wikipedia_title", "full_extract"]
    )
    if extract_writer_needs_header:
        extract_writer.writeheader()

    output_rows: list[dict[str, str]] = []
    fetched = 0
    for coach_name, entry in sorted(roster.items()):
        institutions = sorted(entry["institutions"])  # type: ignore[arg-type]
        years = sorted(entry["years"])  # type: ignore[arg-type]
        year_span = f"{years[0]}-{years[-1]}" if years else ""

        if coach_name in cache:
            title = cache[coach_name]["wikipedia_title"]
            extract = cache[coach_name]["full_extract"]
        else:
            title, extract = resolve_wikipedia_title_and_extract(coach_name, "")
            extract = extract or ""
            extract_writer.writerow(
                {"coach_name": coach_name, "wikipedia_title": title or "", "full_extract": extract}
            )
            extract_file.flush()
            fetched += 1
            time.sleep(args.sleep)

        clubs: list[str] = []
        if extract:
            clubs = [s.institution for s in parse_club_history(extract)]

        identity_signal = ""
        if extract:
            for institution in institutions:
                if institution and institution in extract:
                    identity_signal = institution
                    break

        needs_review = ""
        if not extract:
            needs_review = "no_extract"
        elif not identity_signal:
            needs_review = "institution_not_in_article"
        elif not clubs:
            needs_review = "no_playing_clubs_parsed"

        output_rows.append(
            {
                "coach_name": coach_name,
                "institutions": "|".join(institutions),
                "tenure_year_span": year_span,
                "wikipedia_title": title or "",
                "extract_len": str(len(extract)),
                "identity_signal": identity_signal,
                "playing_clubs": "|".join(clubs),
                "n_playing_clubs": str(len(clubs)),
                "needs_review": needs_review,
            }
        )

    extract_file.close()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(output_rows)

    total = len(output_rows)
    clean = sum(1 for r in output_rows if not r["needs_review"])
    from collections import Counter

    review_reasons = Counter(r["needs_review"] for r in output_rows if r["needs_review"])
    print(f"coaches={total}  newly_fetched={fetched}")
    print(f"clean (article confirmed + playing clubs parsed)={clean} ({clean / total * 100:.0f}%)")
    print("needs_review breakdown:")
    for reason, count in review_reasons.most_common():
        print(f"  {reason}: {count}")
    with_extract = sum(1 for r in output_rows if r["extract_len"] != "0")
    print(f"resolved to some Wikipedia extract: {with_extract}/{total}")
    print(f"wrote={args.output}")


if __name__ == "__main__":
    main()
