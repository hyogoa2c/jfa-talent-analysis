from jfa_talent_analysis.pre2014_identity import (
    MATCH_ALIAS,
    MATCH_EXACT,
    MATCH_FOLDED,
    MATCH_SFIX04,
    expand_name_aliases,
    fold_name,
    is_katakana_only,
    match_pre2014_records,
    resolve_candidates_with_history,
    sfix04_team_matches,
)


def universe_player(
    player_id: str, name_ja: str, birth_date: str = "1980/01/01"
) -> dict[str, str]:
    return {
        "source_player_id": player_id,
        "name_ja": name_ja,
        "birth_date": birth_date,
        "position": "MF",
    }


def appearance(name: str, team: str = "鹿島アントラーズ") -> dict[str, str]:
    return {
        "season_year": "1999",
        "competition_label": "1999Jリーグ ディビジョン1 1stステージ",
        "team_name": team,
        "player_no": "1",
        "player_name": name,
        "appearances": "5",
        "minutes": "464",
        "goals": "0",
        "source_url": "https://example.test/page.html",
        "retrieved_at": "2026-07-18T00:00:00+00:00",
    }


def test_fold_name_variants() -> None:
    assert fold_name("楢﨑　正剛") == "楢崎 正剛"
    assert fold_name("髙木 彰人") == "高木 彰人"
    assert fold_name("相澤 清喜") == "相沢 清喜"
    assert fold_name("小川 雅已") == "小川 雅己"
    assert fold_name("辰巳 太郎") == "辰巳 太郎"
    assert fold_name("坂本 将貴") == fold_name("坂本 將貴")
    assert fold_name("薮田 光教") == fold_name("藪田 光教")


def test_is_katakana_only() -> None:
    assert is_katakana_only("アレックス")
    assert is_katakana_only("パウロ・エンリケ")
    assert not is_katakana_only("呂比須 ワグナー")


def test_expand_aliases_given_name_variant() -> None:
    full, nicknames = expand_name_aliases("黒崎 久志（比差支）")
    assert full == {"黒崎 久志", "黒崎 比差支"}
    assert nicknames == set()


def test_expand_aliases_family_name_variant() -> None:
    full, _ = expand_name_aliases("田渕（花垣） 龍二")
    assert full == {"田渕 龍二", "花垣 龍二"}


def test_expand_aliases_full_name_and_nickname() -> None:
    full, nicknames = expand_name_aliases("岩﨑 知瑳（岩崎 知瑳）")
    assert full == {"岩﨑 知瑳", "岩崎 知瑳"}
    full, nicknames = expand_name_aliases("三都主 アレサンドロ（アレックス）")
    assert full == {"三都主 アレサンドロ"}
    assert nicknames == {"アレックス"}


def test_expand_aliases_mixed_width_brackets() -> None:
    full, _ = expand_name_aliases("髙山 和真（高山 和真)")
    assert full == {"髙山 和真", "高山 和真"}


def test_match_exact_folded_and_alias() -> None:
    players = [
        universe_player("1", "名良橋 晃"),
        universe_player("2", "楢﨑 正剛"),
        universe_player("3", "黒崎 久志（比差支）"),
    ]
    records = [
        appearance("名良橋　晃"),
        appearance("楢崎 正剛"),
        appearance("黒崎 比差支"),
    ]
    result = match_pre2014_records(records, players)
    methods = {row["source_player_id"]: row["match_method"] for row in result.matched}
    assert methods == {"1": MATCH_EXACT, "2": MATCH_FOLDED, "3": MATCH_ALIAS}
    assert not result.ambiguous and not result.unmatched


def test_variant_sibling_is_ambiguous_even_on_exact_hit() -> None:
    players = [universe_player("1", "山田 太郎"), universe_player("2", "山田 太郎")]
    result = match_pre2014_records([appearance("山田 太郎")], players)
    assert not result.matched
    assert len(result.ambiguous) == 1
    assert result.ambiguous[0]["candidate_player_ids"] == "1;2"

    players = [universe_player("1", "柴﨑 晃誠"), universe_player("2", "柴崎 晃誠")]
    result = match_pre2014_records([appearance("柴崎 晃誠")], players)
    assert not result.matched
    assert len(result.ambiguous) == 1


def test_nickname_hits_are_review_candidates_not_matches() -> None:
    players = [universe_player("1", "三都主 アレサンドロ（アレックス）")]
    result = match_pre2014_records([appearance("アレックス")], players)
    assert not result.matched
    assert len(result.nickname_candidates) == 1
    assert result.nickname_candidates[0]["candidate_player_ids"] == "1"


def test_katakana_mononym_never_auto_matches() -> None:
    # SFIX03's ビスマルク (born 2002) is not the 1999 Kashima Brazilian of the same name.
    players = [universe_player("1", "ビスマルク", birth_date="2002/07/05")]
    result = match_pre2014_records([appearance("ビスマルク")], players)
    assert not result.matched
    # Age-implausible for 1999, so it is not even offered as a review candidate.
    assert not result.nickname_candidates
    assert len(result.unmatched) == 1

    players = [universe_player("1", "ビスマルク", birth_date="1969/09/17")]
    result = match_pre2014_records([appearance("ビスマルク")], players)
    assert not result.matched
    assert len(result.nickname_candidates) == 1


def test_age_implausible_candidate_is_not_matched() -> None:
    # Archive 1999 row vs a same-name universe player born 1996: different person.
    players = [universe_player("1", "中村 亮", birth_date="1996/12/31")]
    result = match_pre2014_records([appearance("中村 亮")], players)
    assert not result.matched
    assert len(result.unmatched) == 1


def test_age_filter_disambiguates_same_name_pair() -> None:
    players = [
        universe_player("1", "山田 太郎", birth_date="1975/01/01"),
        universe_player("2", "山田 太郎", birth_date="1999/01/01"),
    ]
    result = match_pre2014_records([appearance("山田 太郎")], players)
    assert len(result.matched) == 1
    assert result.matched[0]["source_player_id"] == "1"


def test_unmatched_flags_katakana_only() -> None:
    players = [universe_player("1", "名良橋 晃")]
    result = match_pre2014_records(
        [appearance("リカルジーニョ"), appearance("架空 選手")], players
    )
    flags = {row["player_name"]: row["katakana_only"] for row in result.unmatched}
    assert flags == {"リカルジーニョ": "true", "架空 選手": "false"}


def test_sfix04_team_matches() -> None:
    assert sfix04_team_matches("鹿島", "鹿島アントラーズ")
    assert sfix04_team_matches("市原", "ジェフユナイテッド市原")
    assert sfix04_team_matches("千葉", "ジェフユナイテッド市原")  # 2005 rename
    assert sfix04_team_matches("F東京", "FC東京")
    assert sfix04_team_matches("G大阪", "ガンバ大阪")
    assert sfix04_team_matches("横浜FM", "横浜F・マリノス")
    assert sfix04_team_matches("東京V", "ヴェルディ川崎")
    assert sfix04_team_matches("平塚", "湘南ベルマーレ")
    assert not sfix04_team_matches("横浜FM", "横浜FC")
    assert not sfix04_team_matches("F東京", "東京ヴェルディ1969")
    assert not sfix04_team_matches("鹿島", "アビスパ福岡")


def test_resolve_candidates_with_history() -> None:
    candidates = [{"source_player_id": "1"}, {"source_player_id": "2"}]
    histories = {
        "1": [{"season": "1999", "team_name": "鹿島"}],
        "2": [{"season": "1999", "team_name": "福岡"}],
    }
    player, resolution = resolve_candidates_with_history(
        candidates, histories, season_year="1999", team_name="鹿島アントラーズ"
    )
    assert resolution == "resolved" and player["source_player_id"] == "1"

    player, resolution = resolve_candidates_with_history(
        candidates, histories, season_year="1999", team_name="浦和レッズ"
    )
    assert player is None and resolution == "none_matched"

    histories["2"] = [{"season": "1999", "team_name": "鹿島"}]
    player, resolution = resolve_candidates_with_history(
        candidates, histories, season_year="1999", team_name="鹿島アントラーズ"
    )
    assert player is None and resolution == "multiple_matched"


def test_resolutions_win_over_name_matching() -> None:
    players = [
        universe_player("1", "田中 達也", birth_date="1982/11/27"),
        universe_player("2", "田中 達也", birth_date="1992/04/07"),
    ]
    resolutions = {("1999", "鹿島アントラーズ", "田中 達也"): "1"}
    result = match_pre2014_records([appearance("田中 達也")], players, resolutions)
    assert len(result.matched) == 1
    assert result.matched[0]["source_player_id"] == "1"
    assert result.matched[0]["match_method"] == MATCH_SFIX04
    assert not result.ambiguous
