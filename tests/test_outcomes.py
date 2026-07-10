from jfa_talent_analysis.outcomes import build_overseas_transfer_outcomes


def queue_row(**overrides: str) -> dict[str, str]:
    row = {
        "source_player_id": "1",
        "name_ja": "山田 太郎",
        "name_en": "Taro YAMADA",
        "previous_observed_season": "2019",
        "reappearance_season": "2024",
        "absent_seasons": "4",
        "manual_decision": "",
        "evidence_url": "",
    }
    row.update(overrides)
    return row


def test_confirmed_foreign_stint_maps_to_moved_overseas_one():
    rows = build_overseas_transfer_outcomes(
        [queue_row(manual_decision="confirmed_foreign_stint", evidence_url="https://example.com/a")]
    )

    assert rows[0]["moved_overseas"] == "1"
    assert rows[0]["moved_overseas_basis"] == "confirmed_foreign_stint"
    assert rows[0]["evidence_url"] == "https://example.com/a"


def test_confirmed_no_foreign_stint_maps_to_moved_overseas_zero():
    rows = build_overseas_transfer_outcomes(
        [queue_row(manual_decision="confirmed_no_foreign_stint")]
    )

    assert rows[0]["moved_overseas"] == "0"


def test_identity_resolved_no_decision_stays_unknown():
    rows = build_overseas_transfer_outcomes(
        [queue_row(manual_decision="identity_resolved_no_decision")]
    )

    assert rows[0]["moved_overseas"] == ""
    assert rows[0]["moved_overseas_basis"] == "identity_resolved_no_decision"


def test_unresolved_stays_unknown():
    rows = build_overseas_transfer_outcomes([queue_row(manual_decision="unresolved")])

    assert rows[0]["moved_overseas"] == ""


def test_blank_decision_kept_as_unreviewed():
    rows = build_overseas_transfer_outcomes([queue_row(manual_decision="")])

    assert rows[0]["moved_overseas"] == ""
    assert rows[0]["moved_overseas_basis"] == ""


def test_preserves_all_queue_rows_regardless_of_review_state():
    rows = build_overseas_transfer_outcomes(
        [
            queue_row(source_player_id="1", manual_decision="confirmed_foreign_stint"),
            queue_row(source_player_id="2", manual_decision=""),
        ]
    )

    assert [row["source_player_id"] for row in rows] == ["1", "2"]
