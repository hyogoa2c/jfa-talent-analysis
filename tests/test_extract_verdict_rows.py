import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "extract_verdict_rows", Path(__file__).resolve().parents[1] / "scripts/extract_verdict_rows.py"
)
extract = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(extract)


def ids(text):
    return sorted(extract.verdict_rows(text))


def test_a_quote_spread_over_several_lines_is_kept():
    # W383 志知孝明: the club's career block is one field over three lines, and
    # reading line by line dropped the row and called the batch short.
    raw = (
        "W379,石川 慧,high_school,新潟明訓高等学校,confirmed,https://example.jp/a,"
        '"経歴=関屋中-新潟明訓高-仙台",news,a,2026-07-31,8,"卒業後加入"\n'
        "W383,志知孝明,university,東海学園大学,confirmed,https://example.jp/b,"
        '"FC岐阜U-18\n東海学園大学\n松本山雅FC",official_club,a,2026-07-31,15,"公式の経歴欄"\n'
    )
    rows = extract.verdict_rows(raw)
    assert sorted(rows) == ["W379", "W383"]
    assert rows["W383"][6] == "FC岐阜U-18\n東海学園大学\n松本山雅FC"


def test_jfa_academy_is_recognised_as_a_verdict():
    # The category column is how a verdict is told from prose, so a category
    # missing from the list is a rating paid for and silently thrown away.
    raw = (
        "W155,三幸 秀稔,jfa_academy,JFAアカデミー福島,confirmed,https://example.jp/c,"
        '"2006年～2012年：JFAアカデミー福島",official_club,a,2026-07-31,4,""\n'
    )
    assert ids(raw) == ["W155"]


def test_prose_around_the_rows_is_ignored():
    raw = (
        "承知しました。以下が結果です。\n"
        "W001,選手 一郎,university,法政大学,confirmed,https://example.jp/d,"
        '"法政大学→富山",official_club,a,2026-07-31,3,""\n'
        "以上です。\n"
    )
    assert ids(raw) == ["W001"]


def test_output_that_will_not_parse_whole_still_yields_its_good_lines():
    # An unbalanced quote breaks a whole-document parse; the line pass is why
    # the rest of the batch survives it.
    raw = (
        'ここで " が閉じられていない行がある\n'
        "W002,選手 二郎,high_school,静岡学園高等学校,confirmed,https://example.jp/e,"
        '"静岡学園高－神戸",news,a,2026-07-31,5,""\n'
    )
    assert ids(raw) == ["W002"]
