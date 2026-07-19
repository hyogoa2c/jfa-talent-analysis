import pytest

from jfa_talent_analysis.career_table import build_career_seasons, sfpr01_division


def pre_row(
    player_id: str = "1",
    season: str = "1999",
    category: str = "j1_league",
    minutes: str = "464",
    appearances: str = "5",
    team: str = "鹿島アントラーズ",
) -> dict[str, str]:
    return {
        "source_player_id": player_id,
        "season_year": season,
        "competition_category": category,
        "is_league": "true",
        "team_name": team,
        "appearances": appearances,
        "minutes": minutes,
        "goals": "0",
        "birth_date": "1980/01/01",
    }


def sfpr_row(
    player_id: str = "1", season: str = "2014", league: str = "Ｊ１リーグ"
) -> dict[str, str]:
    return {
        "source_player_id": player_id,
        "season": season,
        "league": league,
        "team_name": "仙台",
        "appearances": "1",
        "minutes": "90",
        "goals": "0",
        "birth_date": "1980/01/01",
    }


def test_sfpr01_division_normalizes_fullwidth() -> None:
    assert sfpr01_division("Ｊ１リーグ") == "J1"
    assert sfpr01_division("Ｊ３リーグ") == "J3"
    assert sfpr01_division("天皇杯") is None


def test_two_stage_seasons_sum_into_annual_total() -> None:
    rows = build_career_seasons(
        [
            pre_row(minutes="464", appearances="5"),
            pre_row(minutes="894", appearances="10"),  # 2nd stage, same season+division
        ],
        [],
    )
    assert len(rows) == 1
    assert rows[0].minutes == 1358 and rows[0].appearances == 15
    assert rows[0].division == "J1" and rows[0].source == "pre2014_archive"


def test_sources_combine_without_overlap() -> None:
    rows = build_career_seasons([pre_row(season="2013")], [sfpr_row(season="2014")])
    assert [(r.season, r.source) for r in rows] == [
        (2013, "pre2014_archive"),
        (2014, "sfpr01"),
    ]


def test_non_league_pre2014_rows_are_skipped() -> None:
    cup = pre_row(category="league_cup")
    cup["is_league"] = "false"
    assert build_career_seasons([cup], []) == []


def test_out_of_window_seasons_raise() -> None:
    with pytest.raises(ValueError):
        build_career_seasons([pre_row(season="2014")], [])
    with pytest.raises(ValueError):
        build_career_seasons([], [sfpr_row(season="2013")])
