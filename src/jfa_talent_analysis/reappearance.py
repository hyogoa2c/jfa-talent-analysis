from __future__ import annotations

from collections import defaultdict


def build_reappearance_candidates(
    rows: list[dict[str, str]],
    *,
    target_start_season: int,
    target_end_season: int,
    min_gap_seasons: int,
) -> list[dict[str, str]]:
    by_player: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if parse_int(row.get("minutes")) <= 0:
            continue
        by_player[row["source_player_id"]].append(row)

    candidates: list[dict[str, str]] = []
    for player_id, player_rows in by_player.items():
        by_season = {parse_int(row["season"]): row for row in player_rows}
        seasons = sorted(by_season)
        for previous_season, reappearance_season in zip(seasons, seasons[1:]):
            absent_seasons = reappearance_season - previous_season - 1
            if (
                target_start_season <= reappearance_season <= target_end_season
                and absent_seasons >= min_gap_seasons
            ):
                row = by_season[reappearance_season]
                candidates.append(
                    {
                        "source_player_id": player_id,
                        "name_ja": row["name_ja"],
                        "name_en": row["name_en"],
                        "previous_observed_season": str(previous_season),
                        "reappearance_season": str(reappearance_season),
                        "absent_seasons": str(absent_seasons),
                        "reappearance_leagues": row["leagues"],
                        "reappearance_teams": row["teams"],
                        "reappearance_minutes": row["minutes"],
                        "note": "Observed J.League appearance gap; not proof of overseas transfer.",
                    }
                )
                break

    return sorted(
        candidates,
        key=lambda row: (
            -parse_int(row["absent_seasons"]),
            parse_int(row["previous_observed_season"]),
            parse_int(row["reappearance_season"]),
            row["name_ja"],
        ),
    )


def parse_int(value: str | None) -> int:
    if not value:
        return 0
    normalized = value.replace(",", "").strip()
    return int(normalized) if normalized.isdigit() else 0
