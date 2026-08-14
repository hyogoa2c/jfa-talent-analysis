"""The rater worksheet has to stay blind (SAP §6b-2b, §11-2).

Synthetic inputs only: the real rosters are gitignored build artefacts.
"""

import csv
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_gold_worksheet.py"

STRATA = ("academy_out", "academy_in", "institution_unknown", "both_agree", "club_list_only")


def write(path: Path, columns: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def build_inputs(tmp_path: Path, per_stratum: int = 12) -> None:
    sample, phase1, career = [], [], []
    player_id, order = 1000, 0
    for stratum in STRATA:
        for _ in range(per_stratum + 2):  # the last two are reserves
            player_id += 1
            order += 1
            role = "target" if _ < per_stratum else "reserve"
            sample.append(
                {
                    "draw_order": str(order),
                    "source_player_id": str(player_id),
                    "era": "era1",
                    "observed_pathway": "university",
                    "stratum": stratum,
                    "role": role,
                }
            )
            phase1.append(
                {
                    "source_player_id": str(player_id),
                    "name_ja": f"選手{player_id}",
                    "name_en": f"Player {player_id}",
                    "birth_date": "1990/01/01",
                    "first_observed_season": "2010",
                    "last_observed_season": "2015",
                }
            )
            career.append(
                {
                    "source_player_id": str(player_id),
                    "season": "2010",
                    "team_names": "テストFC",
                }
            )

    write(
        tmp_path / "sample.csv",
        ["draw_order", "source_player_id", "era", "observed_pathway", "stratum", "role"],
        sample,
    )
    write(
        tmp_path / "phase1.csv",
        [
            "source_player_id",
            "name_ja",
            "name_en",
            "birth_date",
            "first_observed_season",
            "last_observed_season",
        ],
        phase1,
    )
    write(tmp_path / "career.csv", ["source_player_id", "season", "team_names"], career)
    write(
        tmp_path / "pre2014.csv",
        [
            "source_player_id",
            "name_ja",
            "name_en",
            "birth_date",
            "first_season",
            "last_season",
        ],
        [],
    )


def run(tmp_path: Path, pilot: int = 10) -> dict[str, list[dict[str, str]]]:
    outdir = tmp_path / "out"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--sample",
            str(tmp_path / "sample.csv"),
            "--phase1",
            str(tmp_path / "phase1.csv"),
            "--pre2014-roster",
            str(tmp_path / "pre2014.csv"),
            "--career",
            str(tmp_path / "career.csv"),
            "--outdir",
            str(outdir),
            "--pilot",
            str(pilot),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    files = {}
    for name in ("gold_holdout_worksheet", "gold_holdout_worksheet_key"):
        with (outdir / f"{name}.csv").open(encoding="utf-8-sig") as handle:
            files[name] = list(csv.DictReader(handle))
    with (outdir / "gold_holdout_verdicts_rater_a.csv").open(encoding="utf-8-sig") as handle:
        files["rater_a"] = list(csv.DictReader(handle))
    return files


def test_the_worksheet_hides_the_label_under_test(tmp_path: Path):
    build_inputs(tmp_path)
    files = run(tmp_path)

    columns = set(files["gold_holdout_worksheet"][0])
    assert not columns & {"stratum", "observed_pathway", "draw_order", "source_player_id"}
    assert "name_ja" in columns and "birth_date" in columns

    # every target appears exactly once, and the key maps back
    assert len(files["gold_holdout_worksheet"]) == len(STRATA) * 12
    ids = [row["source_player_id"] for row in files["gold_holdout_worksheet_key"]]
    assert len(set(ids)) == len(ids)


def test_rows_are_not_ordered_by_stratum(tmp_path: Path):
    build_inputs(tmp_path)
    key = run(tmp_path)["gold_holdout_worksheet_key"]

    rest = [row["stratum"] for row in key if row["batch"] == "rest"]
    blocks = sum(1 for a, b in zip(rest, rest[1:], strict=False) if a != b)
    # contiguous blocks would give len(strata)-1 changes; a shuffle gives many more
    assert blocks > len(STRATA)

    order = [int(row["draw_order"]) for row in key]
    assert order != sorted(order)


def test_the_pilot_spans_every_stratum(tmp_path: Path):
    build_inputs(tmp_path)
    key = run(tmp_path)["gold_holdout_worksheet_key"]

    pilot = [row["stratum"] for row in key if row["batch"] == "pilot"]
    assert len(pilot) == 10
    assert set(pilot) == set(STRATA)


def test_verdict_sheets_start_empty_but_carry_the_rater(tmp_path: Path):
    build_inputs(tmp_path)
    rows = run(tmp_path)["rater_a"]

    assert all(row["rater"] == "a" for row in rows)
    assert all(row["gold_pathway_category"] == "" for row in rows)
    assert all(row["determination"] == "" for row in rows)
    assert all(row["evidence_quote"] == "" for row in rows)
