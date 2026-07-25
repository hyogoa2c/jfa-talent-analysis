from pathlib import Path

from jfa_talent_analysis.pipeline import (
    leagues_for_season,
    read_csv,
    summarize_season_dataset,
    write_csv,
)


def test_read_csv_strips_utf8_bom(tmp_path: Path):
    """Manually reviewed CSVs come back from Excel with a BOM; the first
    column name must not pick up \\ufeff or every id join silently misses."""
    path = tmp_path / "bom.csv"
    path.write_text(
        "source_player_id,reviewed_pathway_category\n1,j_club_academy\n",
        encoding="utf-8-sig",
    )
    rows = read_csv(path)
    assert list(rows[0].keys()) == ["source_player_id", "reviewed_pathway_category"]
    assert rows[0]["source_player_id"] == "1"


def test_leagues_for_season_excludes_j3_before_2014():
    assert leagues_for_season(2005) == ["J1", "J2"]
    assert leagues_for_season(2014) == ["J1", "J2", "J3"]
    assert leagues_for_season(2010, requested_leagues=["J2", "J3"]) == ["J2"]


def test_summarize_season_dataset(tmp_path: Path):
    interim_dir = tmp_path / "interim"
    processed_dir = tmp_path / "processed"
    write_csv(
        interim_dir / "appearance_records_2014_J1_J2.csv",
        [
            {
                "season": "2014",
                "league": "Ｊ１リーグ",
                "team_id": "1",
                "team_name": "東京",
            },
            {
                "season": "2014",
                "league": "Ｊ２リーグ",
                "team_id": "2",
                "team_name": "横浜",
            },
        ],
    )
    write_csv(
        processed_dir / "appearance_records_2014_J1_J2_japanese_matched.csv",
        [{"source_player_id": "1"}, {"source_player_id": "2"}],
    )
    write_csv(
        interim_dir / "unmatched_appearance_names_2014_J1_J2.csv",
        [{"name_ja": "未照合", "appearance_rows": "3"}],
    )
    write_csv(
        interim_dir / "ambiguous_appearance_names_2014_J1_J2.csv",
        [
            {"name_ja": "同姓同名", "source_player_id": "1"},
            {"name_ja": "同姓同名", "source_player_id": "2"},
        ],
    )

    summary = summarize_season_dataset(
        season=2014,
        leagues=["J1", "J2"],
        interim_dir=interim_dir,
        processed_dir=processed_dir,
    )

    assert summary["appearance_rows"] == "2"
    assert summary["matched_rows"] == "2"
    assert summary["match_rate"] == "1.0000"
    assert summary["unmatched_unique_names"] == "1"
    assert summary["unmatched_appearance_rows"] == "3"
    assert summary["ambiguous_unique_names"] == "1"
    assert summary["ambiguous_candidate_rows"] == "2"
    assert summary["league_count"] == "2"
    assert summary["team_count"] == "2"
