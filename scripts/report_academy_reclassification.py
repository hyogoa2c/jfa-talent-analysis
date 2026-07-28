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
from jfa_talent_analysis.j_club_registry import (
    build_clubs,
    classify_academy,
    development_window,
    match_club,
)


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
        "--force", action="store_true", help="Overwrite a queue that already holds adjudications."
    )
    parser.add_argument(
        "--infobox-youth", type=Path, default=Path("data/interim/infobox_youth.csv")
    )
    parser.add_argument(
        "--output", type=Path, default=Path("data/manual/academy_reclassification_queue.csv")
    )
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


WHY = {
    "j_club_boundary": "クラブのJ加盟期間が育成年代の一部としか重なっていない",
    "non_j_club_academy": "名簿上Jリーグ加盟クラブの下部組織ではない（海外クラブを含む）",
    "institution_unknown": "所属クラブ欄から最終育成機関を特定できない（判断材料なし）",
}


def format_history(rows: list[dict[str, str]]) -> str:
    ordered = sorted(rows, key=lambda row: int(row["line_index"]))
    parts = []
    for row in ordered:
        years = "-".join(filter(None, (row.get("from_year", ""), row.get("to_year", ""))))
        formality = "[2種/特別指定]" if row.get("registration_formality") == "1" else ""
        parts.append(f"{row['institution']}{f'({years})' if years else ''}{formality}")
    return " → ".join(parts)


def stint_years(stints: list[dict[str, str]], institution: str) -> str:
    """Years recorded for the stint the label rests on, if the list has any.

    academy_window is inferred from the birth year, so a boundary call made
    against it is an assumption about when the player was there. Where the list
    states the years, they are the better evidence; where it does not, the row
    needs an external check and this column says so.
    """
    for row in stints:
        if row["institution"] == institution:
            years = "-".join(filter(None, (row.get("from_year", ""), row.get("to_year", ""))))
            return years or "（記載なし）"
    return "（記載なし）"


def recorded_years(stints: list[dict[str, str]], institution: str) -> tuple[int, int] | None:
    """The stint's own from/to years, when the career list records them."""
    for row in stints:
        if row["institution"] != institution:
            continue
        start, end = row.get("from_year", ""), row.get("to_year", "")
        if start.isdigit():
            return (int(start), int(end) if end.isdigit() else int(start))
    return None


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

    # Names make the rows checkable against club and school sources, which is the
    # only way to settle the academy years the career list leaves blank.
    names: dict[str, str] = {}
    for directory, pattern, keys in (
        (Path("data/interim/pathway_national_team"), "pathway_tier_{k}_labeled.csv", "abc"),
        (Path("data/interim/pre2014"), "priority{k}_pathway_labeled.csv", "12"),
    ):
        for key in keys:
            path = directory / pattern.format(k=key)
            if path.exists():
                for row in read_csv(path):
                    names.setdefault(row["source_player_id"], row.get("name_ja", ""))

    # Infobox youth fields, where they have been fetched. Evidence for the human
    # call on boundary rows -- never a label (see fetch_infobox_youth.py).
    infobox: dict[str, list[dict[str, str]]] = {}
    if args.infobox_youth.exists():
        for row in read_csv(args.infobox_youth):
            infobox.setdefault(row["source_player_id"], []).append(row)

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
                    institution,
                    int(year) if year.isdigit() else None,
                    clubs,
                    recorded_years(by_player.get(player_id, []), institution),
                )
            counts[label][verdict] += 1
            if verdict != "j_club_academy" and player_id not in seen:
                seen.add(player_id)
                club = match_club(institution, clubs) if institution else None
                if year.isdigit():
                    low, high = development_window(int(year))
                    window = f"{low}-{high}"
                else:
                    window = ""
                queue.append(
                    {
                        "source_player_id": player_id,
                        "name_ja": names.get(player_id, ""),
                        "phase": label,
                        "era": row.get("era", ""),
                        "birth_year": year,
                        "final_institution": institution,
                        "auto_verdict": verdict,
                        "why_flagged": WHY.get(
                            verdict.split("(")[0], "経路ラベル自体が誤っている疑い"
                        ),
                        "matched_club": club.canonical_name if club else "",
                        "club_j_seasons": (
                            f"{club.entry_season}-{club.last_season}"
                            if club and club.entry_season
                            else ""
                        ),
                        "academy_window": window,
                        "academy_years_in_list": stint_years(
                            by_player.get(player_id, []), institution
                        ),
                        "club_history": format_history(by_player.get(player_id, [])),
                        "infobox_youth": " / ".join(
                            f"{e['youth_club']}({e['youth_years'] or '年なし'})"
                            for e in infobox.get(player_id, [])
                            if e["youth_club"]
                        ),
                        "reviewed_category": "",
                        "evidence_url": "",
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

    # Regenerating over an adjudicated queue silently discards the judgements,
    # which is how the composite queue was lost once already.
    if args.output.exists():
        adjudicated = [
            row
            for row in read_csv(args.output)
            if any(row.get(col, "").strip() for col in ("reviewed_category", "reviewer_note"))
        ]
        if adjudicated and not args.force:
            raise SystemExit(
                f"{args.output} already holds {len(adjudicated)} adjudicated rows; "
                "refusing to overwrite. Pass --force to replace it."
            )

    queue.sort(key=lambda r: (r["phase"], r["auto_verdict"], int(r["source_player_id"])))
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(queue[0].keys()))
        writer.writeheader()
        writer.writerows(queue)
    print(f"\nwrote={args.output} rows={len(queue)}")


if __name__ == "__main__":
    main()
