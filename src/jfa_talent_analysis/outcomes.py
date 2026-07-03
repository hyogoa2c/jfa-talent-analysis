from __future__ import annotations

OUTCOME_COLUMNS = [
    "source_player_id",
    "name_ja",
    "name_en",
    "previous_observed_season",
    "reappearance_season",
    "absent_seasons",
    "moved_overseas",
    "moved_overseas_basis",
    "evidence_url",
]

# Only these manual decisions resolve moved_overseas to a boolean; other decisions
# (identity_resolved_no_decision, unresolved) or a blank review leave it unknown ("").
# Rows never routed to manual review (audit_status == no_wikidata_foreign_stint) are
# intentionally excluded rather than defaulted to "0": absence of a Wikidata P54 hint
# is not proof of no overseas stint (see docs/source_audit_overseas_transfers.md).
DECISION_TO_MOVED_OVERSEAS = {
    "confirmed_foreign_stint": "1",
    "confirmed_no_foreign_stint": "0",
}


def build_overseas_transfer_outcomes(queue_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Materialize a moved_overseas outcome table from a manual review queue.

    Every queue row is kept so callers can see review coverage (moved_overseas is
    blank for rows without a resolving decision), but rows outside the queue are
    never labeled here.
    """
    return [build_outcome_row(row) for row in queue_rows]


def build_outcome_row(row: dict[str, str]) -> dict[str, str]:
    decision = row.get("manual_decision", "")
    return {
        "source_player_id": row.get("source_player_id", ""),
        "name_ja": row.get("name_ja", ""),
        "name_en": row.get("name_en", ""),
        "previous_observed_season": row.get("previous_observed_season", ""),
        "reappearance_season": row.get("reappearance_season", ""),
        "absent_seasons": row.get("absent_seasons", ""),
        "moved_overseas": DECISION_TO_MOVED_OVERSEAS.get(decision, ""),
        "moved_overseas_basis": decision,
        "evidence_url": row.get("evidence_url", ""),
    }
