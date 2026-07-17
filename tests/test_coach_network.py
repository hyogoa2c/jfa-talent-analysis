from jfa_talent_analysis.coach_network import (
    is_gap_placeholder,
    normalize_institution_name,
    years_overlap,
)


def test_university_club_suffix_is_stripped():
    assert normalize_institution_name("阪南大学サッカー部") == "阪南大学"
    assert normalize_institution_name("早稲田大学ア式蹴球部") == "早稲田大学"
    assert normalize_institution_name("筑波大学蹴球部") == "筑波大学"
    assert normalize_institution_name("阪南大学") == "阪南大学"


def test_high_school_abbreviation_is_expanded():
    assert normalize_institution_name("大津高校") == "大津高等学校"
    assert normalize_institution_name("大津高等学校") == "大津高等学校"


def test_prefecture_qualified_high_school_collides_with_bare_name():
    """熊本県立大津高等学校 (player-side, prefecture-qualified per Wikipedia's
    club-history convention) must resolve to the same key as 大津高等学校 (the
    coach-tenure table's plain researched name) — this was the real collision
    found when merging hs_batch1's data against player_institution_stints.csv."""
    assert normalize_institution_name("熊本県立大津高等学校") == normalize_institution_name(
        "大津高等学校"
    )


def test_city_qualified_name_reorders_correctly():
    """静岡市立清水商業高等学校 (player-side) vs 清水商業高等学校 (coach-tenure
    side) — same collision, different qualifier type (市立 not 県立)."""
    assert normalize_institution_name(
        "静岡市立清水商業高等学校"
    ) == normalize_institution_name("清水商業高等学校")


def test_city_name_moved_in_front_of_qualifier_still_collides():
    """The 市立船橋高等学校 vs 船橋市立船橋高等学校 alias found during target-list
    generation: the city name can appear either only once (folded into 船橋高校)
    or twice (once before 市立, once as part of the school's own name)."""
    assert normalize_institution_name(
        "船橋市立船橋高等学校"
    ) == normalize_institution_name("市立船橋高等学校")


def test_unrelated_proper_name_prefix_is_not_stripped():
    """北大津高等学校 is a different, real school from 大津高等学校 (Otsu) — 北 is
    part of its own name, not an administrative qualifier, and must survive
    normalization untouched so the two are never conflated."""
    assert normalize_institution_name("北大津高等学校") != normalize_institution_name(
        "大津高等学校"
    )


def test_j_academy_names_pass_through_unchanged():
    assert normalize_institution_name("FC東京U-18") == "FC東京U-18"
    assert normalize_institution_name("ガンバ大阪ユース") == "ガンバ大阪ユース"


def test_academy_space_and_hyphen_variants_collapse():
    """Real corpus variants: internal spaces ("京都サンガF.C. U-18") and missing
    U-hyphen ("名古屋グランパスU18") split one team into several join keys."""
    assert normalize_institution_name("京都サンガF.C. U-18") == "京都サンガF.C.U-18"
    assert normalize_institution_name("FC東京 U-18") == "FC東京U-18"
    assert normalize_institution_name("名古屋グランパスU18") == "名古屋グランパスU-18"
    assert normalize_institution_name("大宮アルディージャU18") == "大宮アルディージャユース"


def test_renamed_academy_aliases_map_to_researched_name():
    """Historical club names are the same continuing team: 読売日本SC→ヴェルディ,
    京都パープルサンガ→京都サンガF.C., グランパスエイト→グランパス,
    レッドダイヤモンズ→レッズ, 札幌 without the 北海道 prefix."""
    assert normalize_institution_name("読売日本SCユース") == "東京ヴェルディユース"
    assert normalize_institution_name("東京ヴェルディ1969ユース") == "東京ヴェルディユース"
    assert normalize_institution_name("京都パープルサンガユース") == "京都サンガF.C.U-18"
    assert normalize_institution_name("名古屋グランパスエイトユース") == "名古屋グランパスU-18"
    assert normalize_institution_name("浦和レッドダイヤモンズユース") == "浦和レッズユース"
    assert normalize_institution_name("コンサドーレ札幌U-18") == "北海道コンサドーレ札幌U-18"
    assert normalize_institution_name("柏レイソルユース") == "柏レイソルU-18"
    assert normalize_institution_name("ジェフユナイテッド市原ユース") == (
        "ジェフユナイテッド市原・千葉U-18"
    )


def test_leading_parse_junk_is_stripped():
    assert normalize_institution_name("2011 - 2013年度 鹿島アントラーズユース") == (
        "鹿島アントラーズユース"
    )
    assert normalize_institution_name("同年10月 京都サンガF.C.U-18") == "京都サンガF.C.U-18"
    assert normalize_institution_name("：柏レイソルU-18") == "柏レイソルU-18"


def test_similarly_named_but_different_clubs_are_not_aliased():
    """ヴェルディS.S.相模原 and 札幌ジュニアFC are separate clubs; 読売日本SCユースS
    is the junior section (現・ヴェルディジュニア), not the U-18 team."""
    assert normalize_institution_name("ヴェルディS.S.相模原ユース") != "東京ヴェルディユース"
    assert normalize_institution_name("札幌ジュニアFCユース") != "北海道コンサドーレ札幌U-18"
    assert normalize_institution_name("読売日本SCユースS") != "東京ヴェルディユース"


def test_years_overlap_handles_open_ended_ranges():
    assert years_overlap(2010, 2013, 2012, None) is True
    assert years_overlap(2010, 2013, 2020, None) is False
    assert years_overlap(2010, None, 2005, 2008) is False
    assert years_overlap(2010, None, 2005, None) is True


def test_years_overlap_treats_fully_open_range_as_matching_everything():
    assert years_overlap(None, None, 2005, 2008) is True


def test_years_overlap_touching_boundaries_count_as_overlap():
    assert years_overlap(2010, 2013, 2013, 2015) is True


def test_gap_placeholder_coach_name_is_detected():
    assert is_gap_placeholder("不明", "その他(記載)") is True
    assert is_gap_placeholder("不明(名ばかり監督)", "監督") is True


def test_gap_placeholder_role_type_alone_is_detected():
    assert is_gap_placeholder("誰かの名前", "その他(記載)") is True


def test_real_coach_row_is_not_a_gap_placeholder():
    assert is_gap_placeholder("風間八宏", "監督") is False


def test_unnamed_figurehead_is_a_gap_placeholder():
    """The 国見 figurehead row names a real but unidentified person — unusable
    as an identifiable coach for exposure or lineage purposes."""
    assert is_gap_placeholder("(氏名不詳・サッカー未経験の教諭)", "監督") is True
