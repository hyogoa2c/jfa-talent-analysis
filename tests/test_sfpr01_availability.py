from jfa_talent_analysis.sfpr01_availability import summarize_availability


def test_summarize_availability_reports_available_competitions():
    class Option:
        def __init__(self, select_value: str, display_name: str) -> None:
            self.select_value = select_value
            self.display_name = display_name

    rows = summarize_availability(
        season=2014,
        requested_leagues=["J1", "J2", "J3"],
        frames=[Option("1", "Ｊ１リーグ"), Option("2", "Ｊ２リーグ")],
        competitions_by_frame={
            "1": [Option("372", "")],
            "2": [Option("373", "")],
        },
    )

    assert rows[0]["league"] == "J1"
    assert rows[0]["frame_found"] == "1"
    assert rows[0]["competition_count"] == "1"
    assert rows[0]["available"] == "1"
    assert rows[2]["league"] == "J3"
    assert rows[2]["frame_found"] == "0"
    assert rows[2]["available"] == "0"
