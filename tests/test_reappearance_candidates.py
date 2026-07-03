from jfa_talent_analysis.reappearance import build_reappearance_candidates


def test_build_reappearance_candidates_flags_target_window_gap():
    rows = [
        player_season("1", "山田 太郎", 2018, 100, "Ｊ１リーグ", "東京"),
        player_season("1", "山田 太郎", 2024, 200, "Ｊ１リーグ", "浦和"),
        player_season("2", "佐藤 次郎", 2022, 100, "Ｊ２リーグ", "水戸"),
        player_season("2", "佐藤 次郎", 2024, 200, "Ｊ２リーグ", "水戸"),
        player_season("3", "鈴木 三郎", 2019, 100, "Ｊ３リーグ", "長野"),
        player_season("3", "鈴木 三郎", 2022, 200, "Ｊ３リーグ", "長野"),
        player_season("4", "田中 四郎", 2020, 0, "Ｊ１リーグ", "鹿島"),
        player_season("4", "田中 四郎", 2024, 100, "Ｊ１リーグ", "鹿島"),
    ]

    candidates = build_reappearance_candidates(
        rows,
        target_start_season=2023,
        target_end_season=2025,
        min_gap_seasons=2,
    )

    assert [row["source_player_id"] for row in candidates] == ["1"]
    assert candidates[0]["previous_observed_season"] == "2018"
    assert candidates[0]["reappearance_season"] == "2024"
    assert candidates[0]["absent_seasons"] == "5"


def player_season(
    player_id: str,
    name: str,
    season: int,
    minutes: int,
    leagues: str,
    teams: str,
) -> dict[str, str]:
    return {
        "source_player_id": player_id,
        "name_ja": name,
        "name_en": name,
        "season": str(season),
        "minutes": str(minutes),
        "leagues": leagues,
        "teams": teams,
    }
