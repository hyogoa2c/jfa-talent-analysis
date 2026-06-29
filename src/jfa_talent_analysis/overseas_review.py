from __future__ import annotations


ALLOWED_MANUAL_DECISIONS = {
    "",
    "confirmed_foreign_stint",
    "confirmed_no_foreign_stint",
    "identity_resolved_no_decision",
    "unresolved",
}

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
    "wikipedia_titles",
    "wikipedia_urls",
    "wikipedia_search_error",
    "manual_decision",
    "manual_note",
    "evidence_url",
]


def validate_manual_review_rows(rows: list[dict[str, str]]) -> list[str]:
    errors: list[str] = []
    for index, row in enumerate(rows, start=2):
        row_label = f"line {index} source_player_id={row.get('source_player_id', '')}"
        decision = row.get("manual_decision", "").strip()
        evidence_url = row.get("evidence_url", "").strip()
        manual_note = row.get("manual_note", "").strip()

        if decision not in ALLOWED_MANUAL_DECISIONS:
            errors.append(
                f"{row_label}: manual_decision must be one of "
                f"{sorted(ALLOWED_MANUAL_DECISIONS)}; got {decision!r}"
            )
        if decision == "confirmed_foreign_stint" and not evidence_url:
            errors.append(f"{row_label}: confirmed_foreign_stint requires evidence_url")
        if decision == "confirmed_no_foreign_stint" and not evidence_url and not manual_note:
            errors.append(
                f"{row_label}: confirmed_no_foreign_stint requires evidence_url or manual_note"
            )
        if decision == "identity_resolved_no_decision" and not evidence_url:
            errors.append(f"{row_label}: identity_resolved_no_decision requires evidence_url")
        if decision == "unresolved" and not manual_note:
            errors.append(f"{row_label}: unresolved requires manual_note")
        if evidence_url and not looks_like_url(evidence_url):
            errors.append(f"{row_label}: evidence_url must start with http:// or https://")
    return errors


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
        if column
        not in {
            "wikipedia_titles",
            "wikipedia_urls",
            "wikipedia_search_error",
            "manual_decision",
            "manual_note",
            "evidence_url",
        }
    }
    values.update(
        {
            "wikipedia_titles": "",
            "wikipedia_urls": "",
            "wikipedia_search_error": "",
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


def looks_like_url(value: str) -> bool:
    urls = [part.strip() for part in value.split("|") if part.strip()]
    return bool(urls) and all(url.startswith(("http://", "https://")) for url in urls)
