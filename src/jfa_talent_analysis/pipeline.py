from __future__ import annotations

import csv
from pathlib import Path


DEFAULT_LEAGUES = ("J1", "J2", "J3")
J3_START_SEASON = 2014


def leagues_for_season(season: int, requested_leagues: list[str] | None = None) -> list[str]:
    leagues = requested_leagues or list(DEFAULT_LEAGUES)
    if season < J3_START_SEASON:
        leagues = [league for league in leagues if league != "J3"]
    return leagues


def season_dataset_paths(
    *,
    season: int,
    leagues: list[str],
    interim_dir: Path,
    processed_dir: Path,
) -> dict[str, Path]:
    league_suffix = "_".join(leagues)
    return {
        "combined_appearances": interim_dir / f"appearance_records_{season}_{league_suffix}.csv",
        "joined": processed_dir
        / f"appearance_records_{season}_{league_suffix}_japanese_matched.csv",
        "unmatched": interim_dir / f"unmatched_appearance_names_{season}_{league_suffix}.csv",
        "ambiguous": interim_dir / f"ambiguous_appearance_names_{season}_{league_suffix}.csv",
    }


def summarize_season_dataset(
    *,
    season: int,
    leagues: list[str],
    interim_dir: Path,
    processed_dir: Path,
) -> dict[str, str]:
    paths = season_dataset_paths(
        season=season,
        leagues=leagues,
        interim_dir=interim_dir,
        processed_dir=processed_dir,
    )
    appearances = read_csv(paths["combined_appearances"])
    joined = read_csv(paths["joined"])
    unmatched = read_csv(paths["unmatched"])
    ambiguous = read_csv(paths["ambiguous"])
    appearance_rows = len(appearances)
    matched_rows = len(joined)
    unmatched_appearance_rows = sum(parse_int(row.get("appearance_rows")) for row in unmatched)
    ambiguous_names = {row["name_ja"] for row in ambiguous if row.get("name_ja")}
    leagues_seen = {row["league"] for row in appearances if row.get("league")}
    teams_seen = {
        (row.get("league", ""), row.get("team_id", ""), row.get("team_name", ""))
        for row in appearances
        if row.get("team_name")
    }

    return {
        "season": str(season),
        "requested_leagues": "|".join(leagues),
        "appearance_rows": str(appearance_rows),
        "matched_rows": str(matched_rows),
        "match_rate": format_rate(matched_rows, appearance_rows),
        "unmatched_unique_names": str(len(unmatched)),
        "unmatched_appearance_rows": str(unmatched_appearance_rows),
        "ambiguous_unique_names": str(len(ambiguous_names)),
        "ambiguous_candidate_rows": str(len(ambiguous)),
        "league_count": str(len(leagues_seen)),
        "team_count": str(len(teams_seen)),
    }


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def parse_int(value: str | None) -> int:
    if not value:
        return 0
    normalized = value.replace(",", "").strip()
    return int(normalized) if normalized.isdigit() else 0


def format_rate(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return ""
    return f"{numerator / denominator:.4f}"
