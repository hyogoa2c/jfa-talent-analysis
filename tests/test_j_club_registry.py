from pathlib import Path

import pytest

from jfa_talent_analysis.j_club_registry import (
    CAREER_SEASONS_PATH,
    J_CLUB_BOUNDARY,
    NON_J_CLUB_ACADEMY,
    Club,
    build_clubs,
    classify_academy,
    match_club,
    strip_youth_affixes,
)

# The real career table is a build artefact and gitignored, so the unit tests run
# against a committed extract holding only the clubs they name. Without it these
# tests pass locally and error in CI, which is how they sat red for four commits.
SAMPLE_CAREER = Path("tests/fixtures/career_seasons_sample.csv")


@pytest.fixture(scope="module")
def clubs():
    return build_clubs(career_path=SAMPLE_CAREER)


@pytest.mark.parametrize(
    ("institution", "expected"),
    [
        ("ガンバ大阪ユース", "ガンバ大阪"),
        ("FC東京U-18", "FC東京"),
        ("柏レイソルU-18（千葉県立柏中央高等学校→ウィザス高等学校）", "柏レイソル"),
        ("横浜F・マリノスジュニアユース", "横浜F・マリノス"),
        ("三菱養和SCユース", "三菱養和SC"),
    ],
)
def test_youth_affixes_are_stripped(institution, expected):
    assert strip_youth_affixes(institution) == expected


@pytest.mark.skipif(
    not CAREER_SEASONS_PATH.exists(), reason="career table is a gitignored build artefact"
)
def test_registry_covers_every_club_in_the_league_table():
    # Data integrity, not a unit test: a club with no appearances means an alias
    # is wrong, which would silently turn its academy graduates into non-J. Runs
    # only where the real table has been built.
    assert [club.canonical_name for club in build_clubs() if club.first_season is None] == []


def test_longest_alias_wins_so_similar_names_do_not_collide(clubs):
    assert match_club("栃木シティユース", clubs).canonical_name == "栃木シティ"
    assert match_club("栃木SCユース", clubs).canonical_name == "栃木SC"
    assert match_club("北海道コンサドーレ札幌U-18", clubs).canonical_name == "北海道コンサドーレ札幌"


def test_j_club_academy_requires_membership_across_the_whole_window(clubs):
    assert classify_academy("ガンバ大阪ユース", 1990, clubs) == "j_club_academy"


def test_a_club_outside_the_league_is_not_the_reference_category(clubs):
    # 三菱養和 and 横河武蔵野 run academies but have never been J clubs.
    assert classify_academy("三菱養和SCユース", 1987, clubs) == NON_J_CLUB_ACADEMY
    assert classify_academy("横河武蔵野FCユース", 1997, clubs) == NON_J_CLUB_ACADEMY


def test_an_unmatched_name_is_non_j_rather_than_a_guess(clubs):
    # Overseas academies land here; the domestic/overseas split is assigned in
    # review, since neither enters the three main pathways.
    assert classify_academy("レスター・シティFCユース", 1995, clubs) == NON_J_CLUB_ACADEMY
    assert classify_academy("メトロスポックポート・アカデミー", 1988, clubs) == NON_J_CLUB_ACADEMY


def test_a_club_that_joined_after_the_players_academy_years_is_not_j(clubs):
    # 奈良クラブ joined J3 in 2023; a 1995-born player was in its academy ~2009-14.
    assert classify_academy("奈良クラブユース", 1995, clubs) == NON_J_CLUB_ACADEMY


def test_a_club_joining_mid_window_is_a_boundary_case(clubs):
    # Y.S.C.C. joined J3 in 2014, partway through a 1997-born player's window.
    assert classify_academy("Y.S.C.C.横浜U-18", 1997, clubs) == J_CLUB_BOUNDARY


def test_founding_members_are_not_censored_by_the_1999_data_start(clubs):
    # The career table starts in 1999, so without j_entry_year a 1993 founding
    # member looks like a 1999 entrant and era-1 players become boundary cases.
    assert classify_academy("読売日本SCユース", 1982, clubs) == "j_club_academy"
    assert classify_academy("柏レイソルユース", 1981, clubs) == "j_club_academy"


def test_missing_birth_year_cannot_be_time_stamped():
    club = Club("テスト", (), first_season=2000, last_season=2020, j_entry_year=None)
    assert classify_academy("テストユース", None, [club]) == J_CLUB_BOUNDARY


def test_short_abbreviations_do_not_match_by_containment(clubs):
    # 鹿児島 and 相模原 are league-table abbreviations. Matching them inside
    # another club's name would put amateur academies in the reference category.
    assert match_club("アミーゴス鹿児島U-18", clubs) is None
    assert match_club("FCグラシア相模原ユース", clubs) is None
    assert match_club("鹿児島ユナイテッドFC U-18", clubs).canonical_name == "鹿児島ユナイテッドFC"


def test_club_is_not_stripped_as_a_youth_affix(clubs):
    # 奈良クラブ and 三菱養和サッカークラブ carry it as part of the name.
    assert strip_youth_affixes("奈良クラブユース") == "奈良クラブ"
    assert strip_youth_affixes("三菱養和サッカークラブユース") == "三菱養和サッカークラブ"


def test_leading_date_fragments_do_not_defeat_the_match(clubs):
    # Career lines carry these before the club name; left in, a real J academy
    # lands in the non-J bucket.
    assert match_club("シーズン途中 - 2025年6月  愛媛FC U-18", clubs).canonical_name == "愛媛FC"
    assert match_club("- 2019年 鹿児島ユナイテッドFC U-18", clubs).canonical_name == "鹿児島ユナイテッドFC"


def test_curated_entry_years_resolve_the_oldest_players(clubs):
    # G大阪 joined in 1993, so a 1979-born player's whole window is covered even
    # though the league table only starts in 1999.
    assert classify_academy("ガンバ大阪ユース", 1979, clubs) == "j_club_academy"
    assert classify_academy("鹿島アントラーズユース", 1979, clubs) == "j_club_academy"
    # 京都 joined in 1996, so a 1978-born player genuinely straddles the line.
    assert classify_academy("京都パープルサンガユース", 1978, clubs) == J_CLUB_BOUNDARY


def test_recorded_stint_years_beat_the_inferred_window(clubs):
    # 神戸 joined in 1997 and the inferred window for a 1981-born player starts in
    # 1996, so the inference alone calls it a boundary. The list says 1997-1999.
    assert classify_academy("ヴィッセル神戸ユース", 1981, clubs) == J_CLUB_BOUNDARY
    assert classify_academy("ヴィッセル神戸ユース", 1981, clubs, (1997, 1999)) == "j_club_academy"
