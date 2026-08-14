"""The v10 rating allocation has to hold (SAP §6b-2b-rate).

Synthetic inputs only: the worksheet is derived from a gitignored build artefact.
"""

import csv
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_gold_batches.py"

WORKSHEET_COLUMNS = [
    "worksheet_id",
    "name_ja",
    "name_en",
    "birth_date",
    "first_observed_season",
    "last_observed_season",
    "senior_clubs",
]


def build_inputs(tmp_path: Path) -> None:
    worksheet, key = [], []
    strata = ["academy_out", "academy_in", "both_agree", "club_list_only"]
    number = 0
    for stratum in strata:
        for _ in range(20):
            number += 1
            worksheet_id = f"W{number:03d}"
            worksheet.append(
                {
                    "worksheet_id": worksheet_id,
                    "name_ja": f"選手{number}",
                    "name_en": f"Player {number}",
                    "birth_date": "1990/01/01",
                    "first_observed_season": "2010",
                    "last_observed_season": "2015",
                    "senior_clubs": "テストFC",
                }
            )
            key.append({"worksheet_id": worksheet_id, "stratum": stratum})

    for path, columns, rows in (
        (tmp_path / "worksheet.csv", WORKSHEET_COLUMNS, worksheet),
        (tmp_path / "key.csv", ["worksheet_id", "stratum"], key),
    ):
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)

    # the first five rows stand in for the pilot
    with (tmp_path / "done.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["worksheet_id"])
        writer.writeheader()
        writer.writerows({"worksheet_id": f"W{n:03d}"} for n in range(1, 6))


def run(tmp_path: Path) -> list[dict[str, str]]:
    outdir = tmp_path / "batches"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--worksheet",
            str(tmp_path / "worksheet.csv"),
            "--key",
            str(tmp_path / "key.csv"),
            "--done",
            str(tmp_path / "done.csv"),
            "--outdir",
            str(outdir),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    with (outdir / "batch_index.csv").open(encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def rows_by_mode(index: list[dict[str, str]]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for entry in index:
        out.setdefault(entry["mode"], set()).update(entry["worksheet_ids"].split())
    return out


def test_important_strata_stay_double_rated(tmp_path: Path):
    build_inputs(tmp_path)
    index = run(tmp_path)
    modes = rows_by_mode(index)

    # 40 rows in the two important strata, minus the 5 already done
    assert len(modes["dual_important"]) == 35
    for mode in ("dual_important", "dual_reliability"):
        for worksheet_id in modes[mode]:
            raters = {e["rater"] for e in index if worksheet_id in e["worksheet_ids"].split()}
            assert raters == {"a", "b"}, f"{worksheet_id} is not double-rated"


def test_single_rated_rows_go_to_one_rater_and_stay_balanced(tmp_path: Path):
    build_inputs(tmp_path)
    index = run(tmp_path)
    modes = rows_by_mode(index)

    for worksheet_id in modes["single"]:
        raters = [e["rater"] for e in index if worksheet_id in e["worksheet_ids"].split()]
        assert len(raters) == 1

    counts = {"a": 0, "b": 0}
    for entry in index:
        if entry["mode"] == "single":
            counts[entry["rater"]] += int(entry["size"])
    assert abs(counts["a"] - counts["b"]) <= 2


def test_already_rated_rows_are_not_reissued(tmp_path: Path):
    build_inputs(tmp_path)
    index = run(tmp_path)

    issued = {w for entry in index for w in entry["worksheet_ids"].split()}
    assert not issued & {f"W{n:03d}" for n in range(1, 6)}
    assert len(issued) == 75


def test_batches_are_small_and_important_rows_come_first(tmp_path: Path):
    build_inputs(tmp_path)
    index = run(tmp_path)

    assert all(int(entry["size"]) <= 5 for entry in index)
    modes = [entry["mode"] for entry in index]
    assert modes.index("single") > max(i for i, m in enumerate(modes) if m == "dual_important")
