from jfa_talent_analysis.club_history_extraction import (
    is_registration_formality,
    parse_club_history,
)

# Section formats below are real corpus examples (中谷進之介, 金城クリストファー達樹,
# 鈴木義宜, 西川周作 — see docs/pathway_source_pilot_2026-07-03.md's golden table).

NAKATANI = """前文。

== 所属クラブ ==
2002年 - 2004年 間野台サッカークラブ (佐倉市立西志津小学校)
2005年 - 2007年 柏レイソルU-12 (佐倉市立西志津小学校)
2011年 - 2013年 柏レイソルU-18 (千葉県立柏中央高等学校)
2013年 柏レイソル (2種登録選手)
2014年 - 2018年6月  柏レイソル
2024年 -  ガンバ大阪

== 個人成績 ==
略
"""


def test_parses_year_ranges_and_annotations():
    stints = parse_club_history(NAKATANI)
    assert [s.institution for s in stints] == [
        "間野台サッカークラブ",
        "柏レイソルU-12",
        "柏レイソルU-18",
        "柏レイソル",
        "柏レイソル",
        "ガンバ大阪",
    ]
    first = stints[0]
    assert (first.from_year, first.to_year) == (2002, 2004)
    assert first.annotation == "佐倉市立西志津小学校"
    assert first.youth_flag is True


def test_single_year_line_closes_same_year():
    stints = parse_club_history(NAKATANI)
    registration = stints[3]
    assert (registration.from_year, registration.to_year) == (2013, 2013)
    assert is_registration_formality(registration) is True


def test_open_ended_line_has_no_to_year():
    stints = parse_club_history(NAKATANI)
    last = stints[-1]
    assert (last.from_year, last.to_year) == (2024, None)


def test_month_precision_and_block_markers():
    text = """== 所属クラブ ==
ユース経歴
2006年 - 2011年 JFAアカデミー福島 (広野町立広野中学校→福島県立富岡高等学校)
2011年7月 - 2012年5月   フォルトゥナ・デュッセルドルフU-19
プロ経歴
2016年3月 - 7月  いわきFC
"""
    stints = parse_club_history(text)
    assert stints[0].block == "youth"
    assert stints[0].annotation == "広野町立広野中学校→福島県立富岡高等学校"
    assert (stints[1].from_year, stints[1].to_year) == (2011, 2012)
    assert stints[2].block == "pro"
    # month-only end: same calendar year
    assert (stints[2].from_year, stints[2].to_year) == (2016, 2016)


def test_yearless_childhood_clubs_are_kept():
    text = """== 所属クラブ ==
広瀬サッカースポーツ少年団
宮崎日本大学高等学校
2011年 - 2014年 宮崎産業経営大学
"""
    stints = parse_club_history(text)
    assert stints[0].institution == "広瀬サッカースポーツ少年団"
    assert stints[0].from_year is None
    assert stints[1].youth_flag is True
    assert stints[2].institution == "宮崎産業経営大学"


def test_missing_section_returns_empty():
    assert parse_club_history("== 来歴 ==\nプロ入り。") == []


def test_fullwidth_parens_annotation():
    text = """== 所属クラブ ==
2002年 - 2004年 大分トリニータU-18（大分東明高校）
"""
    stints = parse_club_history(text)
    assert stints[0].annotation == "大分東明高校"
    assert stints[0].institution == "大分トリニータU-18"
