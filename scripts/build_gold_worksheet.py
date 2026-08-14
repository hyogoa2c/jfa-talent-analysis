"""Turn the frozen holdout draw into blinded rater worksheets (SAP §6b-2b, §11-2).

The rater must not be able to guess the label being tested. Three things leak it
and are therefore stripped: the observed pathway, the stratum name (a stratum is
literally "the two sources disagreed here"), and the draw order (rows arrive
grouped by stratum). The worksheet also drops `source_player_id`, so a rater with
repository access cannot join back to the classifier output; the id mapping goes
to a separate key file that stays with the coordinator.

What is left is what identifies the person and nothing else: name, birth date,
the seasons they appear in the league data, and their senior clubs.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path

import numpy as np

# Column names that must never reach a rater, checked before writing.
FORBIDDEN = (
    "observed_pathway",
    "stratum",
    "draw_order",
    "pathway",
    "reached_j1",
    "national_team",
    "overseas",
    "source",
    "weight",
    "sampling_probability",
)

IMPORTANT_STRATA = ("academy_out", "academy_in", "institution_unknown", "disagree_other")

WORKSHEET_COLUMNS = [
    "worksheet_id",
    "batch",
    "name_ja",
    "name_en",
    "birth_date",
    "first_observed_season",
    "last_observed_season",
    "senior_clubs",
]

VERDICT_COLUMNS = [
    "gold_pathway_category",
    "gold_final_institution",
    "determination",
    "evidence_url",
    "evidence_quote",
    "evidence_source_type",
    "rater",
    "researched_at",
    "note",
]

KEY_COLUMNS = ["worksheet_id", "source_player_id", "era", "stratum", "batch", "draw_order"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=Path, default=Path("data/manual/gold_holdout_sample.csv"))
    parser.add_argument(
        "--phase1", type=Path, default=Path("data/processed/player_pathway_outcomes.csv")
    )
    parser.add_argument(
        "--pre2014-roster",
        type=Path,
        default=Path("data/interim/pre2014/collection_roster_priority1.csv"),
    )
    parser.add_argument(
        "--career",
        type=Path,
        default=Path("data/processed/career_league_seasons_1999_2025.csv"),
    )
    parser.add_argument("--pilot", type=int, default=30, help="Pilot size (SAP §11 step 2-i).")
    parser.add_argument(
        "--shuffle-seed",
        type=int,
        default=20260729,
        help="Orders the worksheet so that stratum blocks are not visible. Not the draw seed.",
    )
    parser.add_argument("--outdir", type=Path, default=Path("data/manual"))
    parser.add_argument("--raters", nargs="+", default=["a", "b"])
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def load_identity(args: argparse.Namespace) -> dict[str, dict[str, str]]:
    """Name and birth date per player, from the two rosters that carry them."""
    identity: dict[str, dict[str, str]] = {}
    for row in read_csv(args.pre2014_roster):
        identity[row["source_player_id"]] = {
            "name_ja": row["name_ja"],
            "name_en": row["name_en"],
            "birth_date": row["birth_date"],
            "first_observed_season": row["first_season"],
            "last_observed_season": row["last_season"],
        }
    # Phase 1 wins where both have the player: it is the maintained dataset.
    for row in read_csv(args.phase1):
        identity[row["source_player_id"]] = {
            "name_ja": row["name_ja"],
            "name_en": row["name_en"],
            "birth_date": row["birth_date"],
            "first_observed_season": row["first_observed_season"],
            "last_observed_season": row["last_observed_season"],
        }
    return identity


def load_senior_clubs(path: Path, wanted: set[str]) -> dict[str, str]:
    """Senior clubs in appearance order -- disambiguates players sharing a name."""
    clubs: dict[str, list[str]] = {}
    for row in read_csv(path):
        player = row["source_player_id"]
        if player not in wanted:
            continue
        for team in row.get("team_names", "").split(";"):
            team = team.strip()
            if team and team not in clubs.setdefault(player, []):
                clubs[player].append(team)
    return {player: ";".join(names) for player, names in clubs.items()}


def pilot_quota(counts: dict[str, int], total: int, pilot: int) -> dict[str, int]:
    """Spread the pilot across strata by size, largest remainder, at least one each."""
    exact = {name: pilot * count / total for name, count in counts.items()}
    quota = {name: min(counts[name], max(1, int(value))) for name, value in exact.items()}
    while sum(quota.values()) > pilot:
        name = max(quota, key=lambda n: (quota[n] - exact[n], n))
        if quota[name] > 1:
            quota[name] -= 1
        else:  # every stratum is already at its floor
            break
    room = {name for name in quota if quota[name] < counts[name]}
    while room and sum(quota.values()) < pilot:
        name = max(room, key=lambda n: (exact[n] - quota[n], n))
        quota[name] += 1
        if quota[name] >= counts[name]:
            room.discard(name)
    return quota


def assign_batches(targets: list[dict[str, str]], pilot: int) -> dict[str, str]:
    """pilot -> important strata -> the rest (SAP §11 step 2)."""
    counts: dict[str, int] = {}
    for row in targets:
        counts[row["stratum"]] = counts.get(row["stratum"], 0) + 1
    quota = pilot_quota(counts, len(targets), pilot)

    taken: dict[str, int] = {}
    batch: dict[str, str] = {}
    for row in sorted(targets, key=lambda r: int(r["draw_order"])):
        name = row["stratum"]
        if taken.get(name, 0) < quota.get(name, 0):
            taken[name] = taken.get(name, 0) + 1
            batch[row["source_player_id"]] = "pilot"
        elif name in IMPORTANT_STRATA:
            batch[row["source_player_id"]] = "important"
        else:
            batch[row["source_player_id"]] = "rest"
    return batch


def write_csv(path: Path, columns: list[str], rows: list[dict[str, str]]) -> str:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def main() -> None:
    args = parse_args()
    targets = [row for row in read_csv(args.sample) if row["role"] == "target"]
    identity = load_identity(args)
    wanted = {row["source_player_id"] for row in targets}
    missing = wanted - set(identity)
    if missing:
        raise SystemExit(f"no name for {len(missing)} targets: {sorted(missing)[:5]}")
    clubs = load_senior_clubs(args.career, wanted)
    batch = assign_batches(targets, args.pilot)

    rng = np.random.default_rng(args.shuffle_seed)
    order = {"pilot": 0, "important": 1, "rest": 2}
    targets.sort(key=lambda r: (order[batch[r["source_player_id"]]], int(r["draw_order"])))
    shuffled: list[dict[str, str]] = []
    for name in ("pilot", "important", "rest"):
        rows = [r for r in targets if batch[r["source_player_id"]] == name]
        for index in rng.permutation(len(rows)):
            shuffled.append(rows[index])

    worksheet, key = [], []
    for position, row in enumerate(shuffled, start=1):
        player = row["source_player_id"]
        worksheet_id = f"W{position:03d}"
        worksheet.append(
            {
                "worksheet_id": worksheet_id,
                "batch": batch[player],
                "senior_clubs": clubs.get(player, ""),
                **identity[player],
            }
        )
        key.append(
            {
                "worksheet_id": worksheet_id,
                "source_player_id": player,
                "era": row["era"],
                "stratum": row["stratum"],
                "batch": batch[player],
                "draw_order": row["draw_order"],
            }
        )

    leaked = [c for c in WORKSHEET_COLUMNS if any(bad in c for bad in FORBIDDEN)]
    if leaked:
        raise SystemExit(f"worksheet would expose {leaked}")

    args.outdir.mkdir(parents=True, exist_ok=True)
    digest = write_csv(args.outdir / "gold_holdout_worksheet.csv", WORKSHEET_COLUMNS, worksheet)
    key_digest = write_csv(args.outdir / "gold_holdout_worksheet_key.csv", KEY_COLUMNS, key)
    for rater in args.raters:
        blank = [
            {**row, "rater": rater, **{c: "" for c in VERDICT_COLUMNS if c != "rater"}}
            for row in worksheet
        ]
        write_csv(
            args.outdir / f"gold_holdout_verdicts_rater_{rater}.csv",
            WORKSHEET_COLUMNS + VERDICT_COLUMNS,
            blank,
        )

    sizes: dict[str, int] = {}
    for row in worksheet:
        sizes[row["batch"]] = sizes.get(row["batch"], 0) + 1
    print(f"worksheet={len(worksheet)} sha256[:12]={digest}")
    print(f"key sha256[:12]={key_digest}")
    for name in ("pilot", "important", "rest"):
        print(f"  {name:10s} {sizes.get(name, 0)}")
    print(f"raters={', '.join(args.raters)}")


if __name__ == "__main__":
    main()
