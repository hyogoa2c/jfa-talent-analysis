"""The draw has to survive the extension rule (SAP §6b-2b-ext).

Raising `--both-agree-quota` must reproduce the frozen targets and take the next
rows in the same within-stratum order; otherwise the extension would be a second,
different sample and the frozen holdout would no longer be the one being verified.

Synthetic inputs only: the real pooled dataset is a gitignored build artefact and
tests must not depend on one.
"""

import csv
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_gold_allocation.py"

POOLED_COLUMNS = [
    "source_player_id",
    "era",
    "eligible_confirmatory",
    "pathway_category",
    "pathway_prose_category",
    "pathway_club_list_category",
    "pathway_category_source",
]


def write_pooled(path: Path, both_agree_per_cell: int = 120) -> None:
    """Two eras x three pathways, each with a large `both_agree` stratum."""
    rows = []
    player_id = 1000
    for era in ("era1", "era2"):
        for pathway in ("j_club_academy", "high_school", "university"):
            for _ in range(both_agree_per_cell):
                player_id += 1
                rows.append(
                    {
                        "source_player_id": str(player_id),
                        "era": era,
                        "eligible_confirmatory": "1",
                        "pathway_category": pathway,
                        "pathway_prose_category": pathway,
                        "pathway_club_list_category": pathway,
                        "pathway_category_source": "both_agree",
                    }
                )
            # a censused stratum, so the run also covers a quota that never moves
            for _ in range(5):
                player_id += 1
                rows.append(
                    {
                        "source_player_id": str(player_id),
                        "era": era,
                        "eligible_confirmatory": "1",
                        "pathway_category": pathway,
                        "pathway_prose_category": pathway,
                        "pathway_club_list_category": "",
                        "pathway_category_source": "prose_only",
                    }
                )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=POOLED_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def write_queue(path: Path) -> None:
    path.write_text("source_player_id,auto_verdict\n", encoding="utf-8")


def draw(tmp_path: Path, quota: int, tag: str) -> list[dict[str, str]]:
    sample = tmp_path / f"sample_{tag}.csv"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--pooled",
            str(tmp_path / "pooled.csv"),
            "--reclassification-queue",
            str(tmp_path / "queue.csv"),
            "--sample",
            str(sample),
            "--output",
            str(tmp_path / f"alloc_{tag}.md"),
            "--both-agree-quota",
            str(quota),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    with sample.open(encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def by_cell(rows: list[dict[str, str]], role: str | None = None) -> dict[tuple, list[str]]:
    cells: dict[tuple, list[str]] = {}
    for row in rows:
        if role is not None and row["role"] != role:
            continue
        key = (row["era"], row["observed_pathway"], row["stratum"])
        cells.setdefault(key, []).append(row["source_player_id"])
    return cells


def test_raising_the_quota_keeps_the_frozen_targets(tmp_path: Path):
    write_pooled(tmp_path / "pooled.csv")
    write_queue(tmp_path / "queue.csv")

    frozen = draw(tmp_path, 30, "frozen")
    extended = draw(tmp_path, 80, "extended")

    frozen_targets = by_cell(frozen, "target")
    extended_targets = by_cell(extended, "target")

    for key, ids in frozen_targets.items():
        assert extended_targets[key][: len(ids)] == ids, f"{key} is not a prefix"

    for key, ids in by_cell(frozen, "reserve").items():
        if key[2] != "both_agree":
            continue
        promoted = extended_targets[key][len(frozen_targets[key]) :]
        assert promoted[: len(ids)] == ids, f"{key} promoted rows are not the reserves in order"

    # censused strata are unaffected by the extension
    assert {k: v for k, v in frozen_targets.items() if k[2] == "prose_only"} == {
        k: v for k, v in extended_targets.items() if k[2] == "prose_only"
    }


def test_rerunning_at_the_same_quota_is_byte_identical(tmp_path: Path):
    write_pooled(tmp_path / "pooled.csv")
    write_queue(tmp_path / "queue.csv")

    assert draw(tmp_path, 30, "a") == draw(tmp_path, 30, "b")


def test_the_cap_is_enforced(tmp_path: Path):
    write_pooled(tmp_path / "pooled.csv")
    write_queue(tmp_path / "queue.csv")

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--pooled",
            str(tmp_path / "pooled.csv"),
            "--reclassification-queue",
            str(tmp_path / "queue.csv"),
            "--sample",
            str(tmp_path / "sample.csv"),
            "--output",
            str(tmp_path / "alloc.md"),
            "--both-agree-quota",
            "81",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "6b-2b-ext" in result.stderr
