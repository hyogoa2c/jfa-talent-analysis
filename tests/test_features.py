from jfa_talent_analysis.features import age_in_season, build_player_season_features


def test_age_in_season_uses_midseason_reference_date():
    assert age_in_season("2000/06/30", 2020) == 20
    assert age_in_season("2000/07/01", 2020) == 19
    assert age_in_season("", 2020) is None


def test_build_player_season_features_aggregates_rows_and_career_flags():
    rows = [
        {
            "source_player_id": "1",
            "name_ja": "山田 太郎",
            "name_en": "Taro YAMADA",
            "birth_date": "1995/07/01",
            "position_master": "MF",
            "season": "2014",
            "league": "Ｊ２リーグ",
            "team_name": "東京",
            "appearances": "10",
            "minutes": "600",
            "goals": "2",
        },
        {
            "source_player_id": "1",
            "name_ja": "山田 太郎",
            "name_en": "Taro YAMADA",
            "birth_date": "1995/07/01",
            "position_master": "MF",
            "season": "2015",
            "league": "Ｊ１リーグ",
            "team_name": "東京",
            "appearances": "5",
            "minutes": "120",
            "goals": "0",
        },
        {
            "source_player_id": "1",
            "name_ja": "山田 太郎",
            "name_en": "Taro YAMADA",
            "birth_date": "1995/07/01",
            "position_master": "MF",
            "season": "2015",
            "league": "Ｊ１リーグ",
            "team_name": "横浜",
            "appearances": "3",
            "minutes": "90",
            "goals": "1",
        },
    ]

    features = build_player_season_features(rows)

    assert len(features) == 2
    assert features[0]["season"] == "2014"
    assert features[0]["age_in_season"] == "18"
    assert features[0]["u21_minutes_to_date"] == "600"
    assert features[0]["first_j1_season"] == "2015"
    assert features[0]["reached_j1"] == "1"
    assert features[1]["appearances"] == "8"
    assert features[1]["minutes"] == "210"
    assert features[1]["goals"] == "1"
    assert features[1]["j1_minutes"] == "210"
    assert features[1]["teams"] == "東京|横浜"
    assert features[1]["u21_minutes_to_date"] == "810"
    assert features[1]["first_j1_age"] == "19"


def test_zero_appearance_j1_roster_row_does_not_count_as_reaching_j1():
    """A J1 roster registration with no actual appearance (bench-only,
    特別指定/2種登録 players) is not J1 attainment: counting those inflated
    reached_j1 by 24% before this was caught by Wikipedia debut-line
    cross-validation (real case: 伊東純也's 0-appearance 2014 registration vs
    his actual 2015 J1 debut)."""
    rows = [
        {
            "source_player_id": "1",
            "name_ja": "伊東 純也",
            "name_en": "Junya ITO",
            "birth_date": "1993/03/09",
            "position_master": "MF",
            "season": "2014",
            "league": "Ｊ１リーグ",
            "team_name": "甲府",
            "appearances": "0",
            "minutes": "0",
            "goals": "0",
        },
        {
            "source_player_id": "1",
            "name_ja": "伊東 純也",
            "name_en": "Junya ITO",
            "birth_date": "1993/03/09",
            "position_master": "MF",
            "season": "2015",
            "league": "Ｊ１リーグ",
            "team_name": "甲府",
            "appearances": "30",
            "minutes": "1392",
            "goals": "3",
        },
    ]

    features = build_player_season_features(rows)

    assert features[0]["first_j1_season"] == "2015"
    assert features[0]["reached_j1"] == "1"


def test_roster_only_player_never_reaches_j1():
    rows = [
        {
            "source_player_id": "1",
            "name_ja": "控え 一郎",
            "name_en": "Ichiro HIKAE",
            "birth_date": "1995/01/01",
            "position_master": "GK",
            "season": "2015",
            "league": "Ｊ１リーグ",
            "team_name": "東京",
            "appearances": "0",
            "minutes": "0",
            "goals": "0",
        },
    ]

    features = build_player_season_features(rows)

    assert features[0]["reached_j1"] == "0"
    assert features[0]["first_j1_season"] == ""


def test_missing_appearances_falls_back_to_minutes():
    rows = [
        {
            "source_player_id": "1",
            "name_ja": "分数 太郎",
            "name_en": "Taro FUNSU",
            "birth_date": "1995/01/01",
            "position_master": "DF",
            "season": "2016",
            "league": "Ｊ１リーグ",
            "team_name": "東京",
            "appearances": "",
            "minutes": "45",
            "goals": "0",
        },
    ]

    features = build_player_season_features(rows)

    assert features[0]["reached_j1"] == "1"
    assert features[0]["first_j1_season"] == "2016"
