from pathlib import Path

from jfa_talent_analysis.sources.pre2014_appearances import (
    normalize_text,
    parse_appearance_page,
    parse_index,
    parse_int,
)

FIXTURES = Path(__file__).parent / "fixtures"


def read_fixture(name: str) -> str:
    return (FIXTURES / name).read_bytes().decode("cp932")


def test_normalize_text_folds_fullwidth_digits_and_ideographic_space():
    assert normalize_text("２００５Ｊリーグ　ディビジョン１　１ｓｔステージ") == (
        "2005Jリーグ ディビジョン1 1stステージ"
    )
    assert normalize_text("名良橋　晃") == "名良橋 晃"


def test_parse_int_handles_thousands_separator_and_blank():
    assert parse_int("464") == 464
    assert parse_int("1,426") == 1426
    assert parse_int("0") == 0
    assert parse_int("") is None
    assert parse_int("　") is None


def test_parse_index_extracts_year_url_and_link_text():
    html = read_fixture("pre2014_appearance_index_sample.html")

    links = parse_index(html)

    assert len(links) == 9
    years = {link.year for link in links}
    assert years == {1999, 2005, 2013}

    kashima_1999 = next(link for link in links if link.filename == "1999010001_000001_W0707_J.html")
    assert kashima_1999.year == 1999
    assert kashima_1999.link_text == "鹿島アントラーズ"
    assert kashima_1999.url == (
        "https://data.j-league.or.jp/SS/jpn/team/1999010001_000001_W0707_J.html"
    )


def test_parse_appearance_page_extracts_header_and_ground_truth_rows():
    html = read_fixture("pre2014_appearance_sample_1999_kashima_j1_1st.html")

    records = parse_appearance_page(
        html,
        season_year=1999,
        source_url="https://data.j-league.or.jp/SS/jpn/team/1999010001_000001_W0707_J.html",
    )

    assert len(records) == 4
    for record in records:
        assert record.team_name == "鹿島アントラーズ"
        assert record.competition_label == "1999Jリーグ ディビジョン1 1stステージ"
        assert record.season_year == 1999
        assert record.source_url.endswith("1999010001_000001_W0707_J.html")

    by_name = {record.player_name: record for record in records}

    furukawa = by_name["古川 昌明"]
    assert furukawa.player_no == "1"
    assert furukawa.appearances == 0
    assert furukawa.minutes == 0
    assert furukawa.goals == 0

    narahashi = by_name["名良橋 晃"]
    assert narahashi.player_no == "2"
    assert narahashi.appearances == 5
    assert narahashi.minutes == 464
    assert narahashi.goals == 0


def test_parse_appearance_page_skips_non_player_rows():
    html = read_fixture("pre2014_appearance_sample_1999_kashima_j1_1st.html")

    records = parse_appearance_page(
        html,
        season_year=1999,
        source_url="https://data.j-league.or.jp/SS/jpn/team/1999010001_000001_W0707_J.html",
    )

    # The header row itself ("No"/"選手"/...) must never be emitted as a player row.
    assert all(record.player_name != "選手" for record in records)
