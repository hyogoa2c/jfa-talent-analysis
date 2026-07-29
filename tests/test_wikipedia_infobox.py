from jfa_talent_analysis.sources.wikipedia_infobox import (
    clean_value,
    parse_year_range,
    parse_youth_entries,
)

# Shape taken from 明神智和: club and years share a line, and the club carries a
# flag template plus a wikilink.
SAME_LINE = (
    "{{サッカー選手\n"
    "| 名前 = 明神 智和\n"
    "| ユースクラブ1 = {{Flagicon|JPN}} [[柏レイソル]]ユース| ユース年1 = 1993-1995\n"
    "| クラブ1 = {{Flagicon|JPN}} [[柏レイソル]]| 年1 = 1996-2005| 出場1 = 252\n"
    "}}\n"
)

MULTIPLE = (
    "{{サッカー選手\n"
    "| ユースクラブ1 = 太陽SC| ユース年1 = 2010-2012\n"
    "| ユースクラブ2 = [[鹿児島ユナイテッドFC]] U-18| ユース年2 = 2013-2015\n"
    "}}\n"
)


def test_youth_club_and_years_are_read_from_a_shared_line():
    entries = parse_youth_entries(SAME_LINE)
    assert len(entries) == 1
    assert entries[0].club == "柏レイソルユース"
    assert (entries[0].from_year, entries[0].to_year) == (1993, 1995)


def test_senior_club_parameters_are_not_mistaken_for_youth_ones():
    # クラブ1/年1 sit right next to ユースクラブ1/ユース年1 in every article.
    assert [entry.club for entry in parse_youth_entries(SAME_LINE)] == ["柏レイソルユース"]


def test_entries_keep_infobox_order():
    entries = parse_youth_entries(MULTIPLE)
    assert [entry.club for entry in entries] == ["太陽SC", "鹿児島ユナイテッドFC U-18"]
    assert entries[1].from_year == 2013


def test_years_are_matched_by_index_not_position():
    # Only the second club has years. Pairing positionally would hand them to
    # the first, which is how a player acquires an academy stint they never had.
    text = "| ユースクラブ1 = A\n| ユースクラブ2 = B\n| ユース年2 = 2011-2013\n"
    entries = parse_youth_entries(text)
    assert (entries[0].club, entries[0].from_year) == ("A", None)
    assert (entries[1].club, entries[1].from_year) == ("B", 2011)


def test_a_club_with_no_value_is_dropped():
    assert parse_youth_entries("| ユースクラブ1 = \n| ユースクラブ2 = B\n") == [
        entry for entry in parse_youth_entries("| ユースクラブ2 = B\n")
    ] or [entry.club for entry in parse_youth_entries("| ユースクラブ1 = \n| ユースクラブ2 = B\n")] == ["B"]


def test_open_ended_and_unknown_end_years():
    assert parse_year_range("2023-") == (2023, None)
    assert parse_year_range("2016-????") == (2016, None)
    assert parse_year_range("1993-1995") == (1993, 1995)
    assert parse_year_range("") == (None, None)


def test_markup_is_stripped_but_display_text_kept():
    assert clean_value("{{Flagicon|JPN}} [[名古屋グランパスエイト|名古屋グランパス]]") == "名古屋グランパス"
    assert clean_value("[[柏レイソル]]ユース<ref name=x/>") == "柏レイソルユース"
