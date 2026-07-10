import pytest

from jfa_talent_analysis.matching import (
    index_players_by_name,
    match_appearances,
    normalize_name,
    valid_overrides,
)


def player(source_player_id: str, name_ja: str, **extra: str) -> dict[str, str]:
    return {
        "source_player_id": source_player_id,
        "name_ja": name_ja,
        "name_en": extra.get("name_en", "Taro YAMADA"),
        "birth_date": extra.get("birth_date", "1995/07/01"),
        "position": extra.get("position", "MF"),
        "last_belong_team": extra.get("last_belong_team", "東京"),
        "source_url": extra.get("source_url", "player-source"),
    }


def appearance(name_ja: str, **extra: str) -> dict[str, str]:
    return {
        "name_ja": name_ja,
        "season": extra.get("season", "2014"),
        "league": extra.get("league", "Ｊ１リーグ"),
        "team_id": extra.get("team_id", "1"),
        "team_name": extra.get("team_name", "東京"),
        "shirt_number": extra.get("shirt_number", "10"),
        "appearances": extra.get("appearances", "10"),
        "minutes": extra.get("minutes", "900"),
        "goals": extra.get("goals", "2"),
        "source_url": extra.get("source_url", "appearance-source"),
    }


def test_normalize_name_collapses_whitespace():
    assert normalize_name(" 山田　 太郎 ") == "山田 太郎"


def test_index_players_by_name_groups_same_name_players():
    players = [player("1", "山田 太郎"), player("2", "山田  太郎"), player("3", "鈴木 次郎")]

    index = index_players_by_name(players)

    assert [p["source_player_id"] for p in index["山田 太郎"]] == ["1", "2"]
    assert [p["source_player_id"] for p in index["鈴木 次郎"]] == ["3"]


def test_match_appearances_joins_single_exact_name_match():
    result = match_appearances(
        appearances=[appearance("山田 太郎")],
        players=[player("1", "山田 太郎")],
        overrides=[],
    )

    assert len(result.joined) == 1
    assert result.joined[0]["source_player_id"] == "1"
    assert result.joined[0]["match_method"] == "exact_name"
    assert result.unmatched_name_counts == {}
    assert result.ambiguous == []


def test_match_appearances_counts_unmatched_names():
    result = match_appearances(
        appearances=[appearance("該当 なし"), appearance("該当 なし")],
        players=[player("1", "山田 太郎")],
        overrides=[],
    )

    assert result.joined == []
    assert result.unmatched_name_counts == {"該当 なし": 2}


def test_match_appearances_reports_ambiguous_names():
    result = match_appearances(
        appearances=[appearance("山田 太郎")],
        players=[player("1", "山田 太郎"), player("2", "山田 太郎")],
        overrides=[],
    )

    assert result.joined == []
    assert len(result.ambiguous) == 1
    assert [p["source_player_id"] for p in result.ambiguous[0].candidates] == ["1", "2"]


def test_match_appearances_override_resolves_ambiguity():
    override = {
        "season": "2014",
        "league": "Ｊ１リーグ",
        "team_name": "東京",
        "name_ja": "山田 太郎",
        "source_player_id": "2",
    }

    result = match_appearances(
        appearances=[appearance("山田 太郎")],
        players=[player("1", "山田 太郎"), player("2", "山田 太郎")],
        overrides=[override],
    )

    assert len(result.joined) == 1
    assert result.joined[0]["source_player_id"] == "2"
    assert result.joined[0]["match_method"] == "manual_override"
    assert result.ambiguous == []


def test_match_appearances_override_only_applies_to_matching_context():
    override = {
        "season": "2015",
        "league": "Ｊ１リーグ",
        "team_name": "東京",
        "name_ja": "山田 太郎",
        "source_player_id": "2",
    }

    result = match_appearances(
        appearances=[appearance("山田 太郎", season="2014")],
        players=[player("1", "山田 太郎"), player("2", "山田 太郎")],
        overrides=[override],
    )

    assert result.joined == []
    assert len(result.ambiguous) == 1


def test_match_appearances_raises_on_unknown_override_id():
    override = {
        "season": "2014",
        "league": "Ｊ１リーグ",
        "team_name": "東京",
        "name_ja": "山田 太郎",
        "source_player_id": "999",
    }

    with pytest.raises(ValueError, match="source_player_id=999"):
        match_appearances(
            appearances=[appearance("山田 太郎")],
            players=[player("1", "山田 太郎")],
            overrides=[override],
        )


def test_valid_overrides_drops_incomplete_rows():
    rows = [
        {"source_player_id": "1", "name_ja": "山田 太郎"},
        {"source_player_id": "", "name_ja": "山田 太郎"},
        {"source_player_id": "2", "name_ja": ""},
    ]

    assert valid_overrides(rows) == [rows[0]]
