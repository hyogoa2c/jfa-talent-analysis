import subprocess
import sys
from pathlib import Path


def test_build_multi_season_features_script(tmp_path: Path):
    processed_dir = tmp_path / "processed"
    interim_dir = tmp_path / "interim"
    processed_dir.mkdir()
    (processed_dir / "appearance_records_2014_J1_J2_J3_japanese_matched.csv").write_text(
        (
            "source_player_id,match_method,name_ja,name_en,birth_date,position_master,"
            "season,league,team_id,team_name,shirt_number,appearances,minutes,goals,"
            "appearance_source_url,player_source_url\n"
            "1,exact_name,山田 太郎,Taro YAMADA,1995/07/01,MF,2014,Ｊ２リーグ,1,"
            "東京,10,10,600,2,source,player\n"
        ),
        encoding="utf-8",
    )
    processed_dir.mkdir(exist_ok=True)
    (processed_dir / "appearance_records_2015_J1_J2_J3_japanese_matched.csv").write_text(
        (
            "source_player_id,match_method,name_ja,name_en,birth_date,position_master,"
            "season,league,team_id,team_name,shirt_number,appearances,minutes,goals,"
            "appearance_source_url,player_source_url\n"
            "1,exact_name,山田 太郎,Taro YAMADA,1995/07/01,MF,2015,Ｊ１リーグ,1,"
            "東京,10,5,120,0,source,player\n"
        ),
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_multi_season_features.py",
            "--start-season",
            "2014",
            "--end-season",
            "2015",
            "--processed-dir",
            str(processed_dir),
            "--interim-dir",
            str(interim_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    output = result.stdout
    assert "combined_rows=2" in output
    assert "player_season_rows=2" in output
    assert (
        processed_dir / "appearance_records_2014_2015_J1_J2_J3_japanese_matched.csv"
    ).exists()
    features = (processed_dir / "player_season_features_2014_2015_J1_J2_J3.csv").read_text(
        encoding="utf-8"
    )
    assert "first_j1_season" in features
    assert "2015" in features
