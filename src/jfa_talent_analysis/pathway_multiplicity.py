"""Multi-stage pathway descriptors (docs/research_plan_phase1.md §7).

Descriptive/exploratory only — the multi-pathway hypothesis itself is tested
as 多最終経路 by H1/H2 (SAP §0/§2 note); these variables just quantify how
often players cross final-stage institutions (e.g. 高校→途中からクラブユース),
which the SAP expects to be rare special cases.

Only final-stage-age (roughly U-16..U-22) institutions count. Junior stages
(ジュニアユース/中学 etc.) are excluded: 中学クラブ→高校 is the ordinary route,
not a multi-pathway signal, and counting it would swamp the statistic.
"""

from __future__ import annotations

import re

import pandas as pd

from .coach_exposure import institution_stage
from .coach_network import normalize_institution_name

STAGES = ("j_club_academy", "high_school", "university", "jfa_academy")

# Institutions below final-stage age: junior youth, junior high, elementary,
# and U-15-or-younger club teams.
JUNIOR_STAGE_RE = re.compile(r"中学|小学|ジュニア|Jr|U-?1[0-5](?![0-9])")


def stint_stage(institution: str) -> str | None:
    """Map a raw stint institution name to a final-stage category, or None
    for junior-age institutions that do not count toward multiplicity."""
    if JUNIOR_STAGE_RE.search(institution):
        return None
    if "JFAアカデミー" in institution:
        return "jfa_academy"
    return institution_stage(normalize_institution_name(institution))


def build_multipath_rows(stints: pd.DataFrame) -> pd.DataFrame:
    """One row per player: has_* stage flags, pathway_count (distinct stages),
    pathway_sequence (stage order with consecutive duplicates collapsed)."""
    dev = stints[
        (stints["youth_flag"] == "1") & (stints["registration_formality"] != "1")
    ].copy()
    dev["line_index"] = dev["line_index"].astype(int)
    dev["stage"] = dev["institution"].apply(stint_stage)
    dev = dev[dev["stage"].notna()].sort_values(["source_player_id", "line_index"])

    records = []
    for player_id, group in dev.groupby("source_player_id", sort=False):
        sequence: list[str] = []
        for stage in group["stage"]:
            if not sequence or sequence[-1] != stage:
                sequence.append(stage)
        distinct = set(sequence)
        record = {
            "source_player_id": player_id,
            "pathway_count": len(distinct),
            "pathway_sequence": ">".join(sequence),
        }
        for stage in STAGES:
            record[f"has_{stage}"] = int(stage in distinct)
        records.append(record)
    columns = [
        "source_player_id",
        *[f"has_{stage}" for stage in STAGES],
        "pathway_count",
        "pathway_sequence",
    ]
    return pd.DataFrame(records, columns=columns)
