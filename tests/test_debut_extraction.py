from jfa_talent_analysis.debut_extraction import extract_debut_evidence

# Line variants below are real formats observed in fetched extracts
# (see docs/data_collection_revision_proposal_2026-07-07.md item 1 work).


def test_dash_separated_line_j2():
    evidence = extract_debut_evidence(
        "経歴あれこれ。\nJリーグ初出場 - 2010年3月21日 J2 第3節 対ギラヴァンツ北九州戦 (北九州)\n"
    )
    assert evidence.jleague_debut_year == 2010
    assert evidence.jleague_debut_league == "J2"
    assert evidence.j1_debut_year is None


def test_fullwidth_colon_line():
    evidence = extract_debut_evidence("Jリーグ初出場： 2009年8月2日 J2第31節 vsアビスパ福岡戦\n")
    assert evidence.jleague_debut_year == 2009
    assert evidence.jleague_debut_league == "J2"


def test_combined_debut_and_goal_line():
    evidence = extract_debut_evidence(
        "Jリーグ初出場・初得点 : 2008年10月19日 J2第40節 対モンテディオ山形\n"
    )
    assert evidence.jleague_debut_year == 2008
    assert evidence.jleague_debut_league == "J2"


def test_date_first_variant():
    evidence = extract_debut_evidence("2010年07月14日：Jリーグ初出場 - J1第14節 vs湘南ベルマーレ\n")
    assert evidence.jleague_debut_year == 2010
    assert evidence.jleague_debut_league == "J1"
    assert evidence.j1_debut_year == 2010
    assert evidence.j1_debut_basis == "debut_line_j1"


def test_j1_debut_line_sets_j1_year_directly():
    evidence = extract_debut_evidence("Jリーグ初出場 - 2008年8月9日 J1第20節 vsヴィッセル神戸戦\n")
    assert evidence.j1_debut_year == 2008
    assert evidence.j1_debut_basis == "debut_line_j1"


def test_j1_stage_league_token():
    evidence = extract_debut_evidence(
        "Jリーグ初出場 - 2015年3月7日 J1リーグ1stステージ第1節 対サガン鳥栖戦\n"
    )
    assert evidence.jleague_debut_league == "J1"
    assert evidence.j1_debut_year == 2015


def test_prose_j1_mention_with_year_in_same_sentence():
    evidence = extract_debut_evidence(
        "Jリーグ初出場： 2009年8月2日 J2第31節 vsアビスパ福岡戦\n"
        "2011年、J1第8節、ベガルタ仙台戦に途中出場し、J1初出場を果たした。"
    )
    assert evidence.jleague_debut_year == 2009
    assert evidence.jleague_debut_league == "J2"
    assert evidence.j1_debut_year == 2011
    assert evidence.j1_debut_basis == "j1_mention_with_year"


def test_prose_j1_mention_without_year_returns_none():
    evidence = extract_debut_evidence("第8節でJ1初出場を果たした。")
    assert evidence.j1_debut_year is None
    assert evidence.j1_debut_basis == ""


def test_fullwidth_league_token_normalized():
    evidence = extract_debut_evidence("Jリーグ初出場 - ２０１０年3月14日 Ｊ２第2節 ロアッソ熊本戦\n")
    assert evidence.jleague_debut_year == 2010
    assert evidence.jleague_debut_league == "J2"


def test_no_debut_information():
    evidence = extract_debut_evidence("高校卒業後に入団し、活躍した。")
    assert evidence.jleague_debut_year is None
    assert evidence.jleague_debut_league is None
    assert evidence.j1_debut_year is None


def test_long_prose_paragraph_does_not_donate_unrelated_year():
    """A whole unbroken paragraph is one "line" after newline splitting; a year
    mentioned sentences before the label must not be picked up (圍謙太朗's
    injury paragraph starts 2015 but his debut line says 2016 J3)."""
    evidence = extract_debut_evidence(
        "2015年は右第5中足骨基部骨折など苦しい一年を過ごしたが、2016年にかけて復調し、"
        "同年のJ3第1節相模原戦においてJリーグ初出場を果たした。\n"
        "2016年3月13日：Jリーグ初出場 - J3第1節 vsSC相模原 (相模原ギオンスタジアム)\n"
    )
    assert evidence.jleague_debut_year == 2016
    assert evidence.jleague_debut_league == "J3"


def test_cup_match_labeled_as_j1_debut_is_ignored():
    """Some articles mislabel a league-cup match as "J1リーグ初出場" (白井康介's
    ナビスコカップ line) — cup matches are not J1 league debuts."""
    evidence = extract_debut_evidence(
        "Jリーグ初出場 - 2014年9月28日 J2第34節 FC岐阜戦\n"
        "J1リーグ初出場 - 2015年3月18日 Jリーグヤマザキナビスコカップ予選第1節 ヴァンフォーレ甲府戦\n"
    )
    assert evidence.jleague_debut_year == 2014
    assert evidence.jleague_debut_league == "J2"
    assert evidence.j1_debut_year is None
