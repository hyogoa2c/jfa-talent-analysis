from __future__ import annotations


MANUAL_REVIEW_COLUMNS = [
    "source_player_id",
    "name_ja",
    "name_en",
    "previous_observed_season",
    "reappearance_season",
    "absent_seasons",
    "reappearance_leagues",
    "reappearance_teams",
    "reappearance_minutes",
    "wikidata_person_ids",
    "wikidata_foreign_teams",
    "audit_status",
    "manual_review_reason",
    "manual_decision",
    "manual_note",
    "evidence_url",
]


def build_manual_review_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    manual_rows = [row for row in rows if row.get("audit_status") == "needs_manual_review"]
    manual_rows.sort(
        key=lambda row: (
            parse_int(row.get("absent_seasons", "")) * -1,
            parse_int(row.get("reappearance_season", "")),
            row.get("name_ja", ""),
        )
    )
    return [build_manual_review_row(row) for row in manual_rows]


def build_manual_review_row(row: dict[str, str]) -> dict[str, str]:
    values = {
        column: row.get(column, "")
        for column in MANUAL_REVIEW_COLUMNS
        if column not in {"manual_decision", "manual_note", "evidence_url"}
    }
    values.update(
        {
            "manual_decision": "",
            "manual_note": "",
            "evidence_url": "",
        }
    )
    return values


def parse_int(value: str) -> int:
    try:
        return int(value)
    except ValueError:
        return 0
