"""Apply the SAP §1b-4 time-stamped J-club definition to both phases.

The point of running one implementation over Phase 1 and Phase 1b is the reason
the external review gave for preferring a fix over a limitation note
(`review_results_phase1b_sap_v3.md` Q3): comparability comes from applying the
same corrected definition to both, not from leaving the same error in both.

Outcome-free for Phase 1b. Phase 1's outcomes are already published in
docs/results_canonical.md, so its impact table is computed here directly.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

from jfa_talent_analysis.club_history_pathway import classify_institution, derive_pathway
from jfa_talent_analysis.j_club_registry import build_clubs, classify_academy


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pooled", type=Path, default=Path("data/processed/pooled_player_outcomes_1999_2025.csv")
    )
    parser.add_argument(
        "--phase1", type=Path, default=Path("data/processed/player_pathway_outcomes.csv")
    )
    parser.add_argument(
        "--stints",
        type=Path,
        default=Path("data/interim/coach_network/player_institution_stints.csv"),
    )
    parser.add_argument(
        "--output", type=Path, default=Path("data/manual/academy_reclassification_queue.csv")
    )
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def pathway_institution(stints: list[dict[str, str]], birth_year: int | None) -> str:
    """The institution the pathway label rests on.

    Not the last youth-flagged stint: that ignores the professional-entry cut, so
    for the academy -> pro -> university players it returns the university and
    every one of them looks like a mislabel. The derivation already identifies
    the institution it based the label on, and that is what has to be classified.
    """
    return derive_pathway(stints, birth_year).institution


def main() -> None:
    args = parse_args()
    clubs = build_clubs()

    stints_rows = read_csv(args.stints)
    by_player: dict[str, list[dict[str, str]]] = {}
    for row in stints_rows:
        by_player.setdefault(row["source_player_id"], []).append(row)

    pooled = read_csv(args.pooled)
    birth = {r["source_player_id"]: r["birth_year"] for r in pooled}
    phase1 = read_csv(args.phase1)
    for row in phase1:
        birth.setdefault(row["source_player_id"], (row.get("birth_date") or "")[:4])

    queue: list[dict[str, str]] = []
    seen: set[str] = set()
    counts: dict[str, Counter[str]] = {"phase1b": Counter(), "phase1": Counter()}

    def process(rows: list[dict[str, str]], label: str, era_key: str | None) -> None:
        for row in rows:
            if row.get("pathway_category") != "j_club_academy":
                continue
            if era_key and row.get("eligible_confirmatory") != "1":
                continue
            player_id = row["source_player_id"]
            year = birth.get(player_id, "")
            institution = pathway_institution(
                by_player.get(player_id, []), int(year) if year.isdigit() else None
            )
            if not institution:
                verdict = "institution_unknown"
            elif classify_institution(institution) not in ("j_club_academy", "jfa_academy", ""):
                # The academy label itself is wrong: the last development stage
                # is a school, not a club youth side. A different finding from
                # "this club was not in the J.League", so kept separate.
                verdict = f"pathway_label_error({classify_institution(institution)})"
            else:
                verdict = classify_academy(
                    institution, int(year) if year.isdigit() else None, clubs
                )
            counts[label][verdict] += 1
            if verdict != "j_club_academy" and player_id not in seen:
                seen.add(player_id)
                queue.append(
                    {
                        "source_player_id": player_id,
                        "phase": label,
                        "era": row.get("era", ""),
                        "birth_year": year,
                        "final_institution": institution,
                        "auto_verdict": verdict,
                        "reviewed_category": "",
                        "reviewer_note": "",
                    }
                )

    process(pooled, "phase1b", "era")
    process(phase1, "phase1", None)

    for label, counter in counts.items():
        total = sum(counter.values())
        print(f"== {label}: j_club_academy ラベル {total} 名")
        for verdict, n in counter.most_common():
            print(f"   {verdict:22s} {n:4d} ({n / total:.1%})")

    queue.sort(key=lambda r: (r["phase"], r["auto_verdict"], int(r["source_player_id"])))
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(queue[0].keys()))
        writer.writeheader()
        writer.writerows(queue)
    print(f"\nwrote={args.output} rows={len(queue)}")


if __name__ == "__main__":
    main()
