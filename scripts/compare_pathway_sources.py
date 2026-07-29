"""Compare the prose classifier against the 所属クラブ derivation, per era.

Outcome-free by construction: only era, birth_year, eligibility and the two
exposure labels are read from the pooled table, never an outcome column. This
produces the agreement table quoted in SAP §1b-3 and in review request Q2, where
it matters that the two procedures disagree at different rates in the two eras.
"""

from __future__ import annotations

import collections
import csv
from pathlib import Path

from jfa_talent_analysis.club_history_pathway import derive_pathway

POOLED = Path("data/processed/pooled_player_outcomes_1999_2025.csv")
STINTS = Path("data/interim/coach_network/player_institution_stints.csv")

# The only pooled columns this script is allowed to read. Listing them keeps the
# outcome-free guarantee checkable rather than a claim in a docstring.
POOLED_COLUMNS = (
    "era",
    "birth_year",
    "eligible_confirmatory",
    "pathway_category",
    "pathway_category_source",
)


def load_pooled() -> dict[str, dict[str, str]]:
    with POOLED.open(encoding="utf-8-sig") as handle:
        return {
            row["source_player_id"]: {key: row[key] for key in POOLED_COLUMNS}
            for row in csv.DictReader(handle)
        }


def load_stints() -> dict[str, list[dict[str, str]]]:
    stints: dict[str, list[dict[str, str]]] = collections.defaultdict(list)
    with STINTS.open(encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            stints[row["source_player_id"]].append(row)
    return stints


def prose_label(row: dict[str, str]) -> str:
    """The prose label, with "unknown" treated as absence of a label.

    unknown is not a competing claim about the pathway, so counting it as a
    disagreement would inflate the disagreement rate with rows the club list
    merely recovers.
    """
    category = row["pathway_category"]
    return "" if category == "unknown" else category


def main() -> None:
    pooled = load_pooled()
    stints = load_stints()

    for era in ("era1", "era2"):
        ids = [
            pid
            for pid, row in pooled.items()
            if row["eligible_confirmatory"] == "1" and row["era"] == era
        ]
        disagreements: collections.Counter[tuple[str, str]] = collections.Counter()
        both = agree = club_only = prose_only = neither = parsed = 0

        for pid in ids:
            birth_year = int(pooled[pid]["birth_year"]) if pooled[pid]["birth_year"] else None
            player_stints = stints.get(pid, [])
            if player_stints:
                parsed += 1
            club = derive_pathway(player_stints, birth_year).pathway_category
            prose = prose_label(pooled[pid])

            if club and prose:
                both += 1
                if club == prose:
                    agree += 1
                else:
                    disagreements[(prose, club)] += 1
            elif club:
                club_only += 1
            elif prose:
                prose_only += 1
            else:
                neither += 1

        changed = (both - agree) + club_only
        print(f"== {era}: 適格={len(ids)} stintsあり={parsed} ({parsed / len(ids):.1%})")
        print(f"   両者ともラベルあり={both} 一致={agree} ({agree / both:.1%}) 不一致={both - agree}")
        print(f"   所属クラブのみ={club_only} 散文のみ={prose_only} どちらもなし={neither}")
        print(f"   ラベルが変わる合計={changed} / {len(ids)} = {changed / len(ids):.1%}")
        for (prose, club), count in disagreements.most_common():
            print(f"     {prose:16s} -> {club:16s} {count}")
        print()


if __name__ == "__main__":
    main()
