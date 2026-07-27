"""Time-stamped J.League club membership, for the SAP §1b-4 academy definition.

`J_CLUB_ACADEMY_RE` matches a bare "ユース" or "U-18", so any youth setup lands in
the reference category regardless of whether the club was in the J.League -- or
in Japan. The external review (`docs/review_results_phase1b_sap_v3.md` Q3) called
that a known classification error rather than an uncertainty to model, since the
cases are individually enumerable, and asked for a versioned roster deciding
whether a club *was J-affiliated while the player was in its academy*.

Membership years are derived rather than curated: a club was in the J.League in
season Y exactly when someone appeared for it in Y in the league table that
Phase 1b is built from. Only the name variants need curating, which is what
`data/manual/j_league_club_registry.csv` holds.

One exception has to be curated. The career table starts in 1999, so a club that
joined in 1993 looks like a 1999 entrant, and era-1 academy windows reach back to
1995 -- long enough for the censoring to turn founding members into boundary
cases. `j_entry_year` carries the real entry season for the pre-1999 entrants and
overrides the derived one.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

REGISTRY_PATH = Path("data/manual/j_league_club_registry.csv")
CAREER_SEASONS_PATH = Path("data/processed/career_league_seasons_1999_2025.csv")

# Categories outside the three main pathways. They are reported and excluded
# from the primary analysis rather than folded into j_club_academy.
NON_J_CLUB_ACADEMY = "non_j_club_academy"
J_CLUB_BOUNDARY = "j_club_boundary"

# Youth-team suffixes and prefixes to strip before matching a club name.
# "クラブ" is deliberately absent: it is part of club names (奈良クラブ,
# 三菱養和サッカークラブ), so stripping it turns real names into non-matches.
YOUTH_AFFIX_RE = re.compile(
    r"(ユース|アカデミー|下部組織|ジュニア|Jr\.?|U-?\d{1,2}|プライマリー|セカンド|"
    r"リザーブズ|サテライト|アマチュア|ネクスト)+$"
)
# Aliases shorter than this are J.League table abbreviations (鹿児島, 相模原, 札幌).
# They resolve membership years but must not match institution names by
# containment: アミーゴス鹿児島 and FCグラシア相模原 are not those clubs.
MIN_ALIAS_LEN_FOR_CONTAINMENT = 5


@dataclass(frozen=True)
class Club:
    canonical_name: str
    aliases: tuple[str, ...]
    first_season: int | None
    last_season: int | None
    j_entry_year: int | None = None

    @property
    def entry_season(self) -> int | None:
        """Curated entry year when known, else the first observed season."""
        return self.j_entry_year if self.j_entry_year is not None else self.first_season

    def in_league(self, season: int) -> bool:
        if self.entry_season is None or self.last_season is None:
            return False
        return self.entry_season <= season <= self.last_season


def load_registry(path: Path = REGISTRY_PATH) -> list[tuple[str, tuple[str, ...], int | None]]:
    with path.open(encoding="utf-8-sig") as handle:
        return [
            (
                row["canonical_name"],
                tuple(filter(None, (row["aliases"] or "").split("|"))),
                int(row["j_entry_year"]) if (row.get("j_entry_year") or "").strip() else None,
            )
            for row in csv.DictReader(handle)
        ]


def season_membership(path: Path = CAREER_SEASONS_PATH) -> dict[str, set[int]]:
    """Seasons each raw team name appears in the league table."""
    membership: dict[str, set[int]] = {}
    with path.open(encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            season = int(row["season"])
            for part in row["team_names"].split(";"):
                name = part.strip()
                if name:
                    membership.setdefault(name, set()).add(season)
    return membership


def build_clubs(
    registry_path: Path = REGISTRY_PATH, career_path: Path = CAREER_SEASONS_PATH
) -> list[Club]:
    membership = season_membership(career_path)
    clubs = []
    for canonical, aliases, entry_year in load_registry(registry_path):
        seasons: set[int] = set()
        for name in (canonical, *aliases):
            seasons |= membership.get(name, set())
        clubs.append(
            Club(
                canonical_name=canonical,
                aliases=aliases,
                first_season=min(seasons) if seasons else None,
                last_season=max(seasons) if seasons else None,
                j_entry_year=entry_year,
            )
        )
    return clubs


def strip_youth_affixes(institution: str) -> str:
    """Reduce "ガンバ大阪ユース" to "ガンバ大阪" so it can match the roster."""
    name = institution.strip()
    # Parenthesised trailing detail: "柏レイソルU-18（千葉県立柏中央高等学校…" -- the
    # concatenated-institution artifact recorded in SAP §13-2.
    name = re.split(r"[（(]", name, maxsplit=1)[0].strip()
    previous = None
    while previous != name:
        previous = name
        name = YOUTH_AFFIX_RE.sub("", name).strip()
    return name


def match_club(institution: str, clubs: list[Club]) -> Club | None:
    """The registered club this academy belongs to, if any.

    Longest name first, so 栃木シティ is not swallowed by 栃木SC and
    北海道コンサドーレ札幌 is not matched merely as 札幌 when both are present.
    """
    base = strip_youth_affixes(institution)
    if not base:
        return None
    candidates = []
    for club in clubs:
        for name in (club.canonical_name, *club.aliases):
            if not name:
                continue
            if base == name or (len(name) >= MIN_ALIAS_LEN_FOR_CONTAINMENT and name in base):
                candidates.append((len(name), club))
    if not candidates:
        return None
    return max(candidates, key=lambda pair: pair[0])[1]


FIRST_OBSERVED_SEASON = 1999
OBSERVATION_END_SEASON = 2025


def development_window(birth_year: int) -> tuple[int, int]:
    """Seasons the player would plausibly have been in a U-18 side.

    Wide by one year on each side: intake and graduation are not uniform, and
    the point is to decide club affiliation, not to date the enrolment.
    """
    return (birth_year + 14, birth_year + 19)


def classify_academy(institution: str, birth_year: int | None, clubs: list[Club]) -> str:
    """Refine a j_club_academy label into the SAP §1b-4 categories.

    Returns "j_club_academy" only when the club was in the J.League across the
    player's whole academy window. Partial overlap is a boundary case and is
    reported as such rather than resolved either way: Y.S.C.C. and 奈良クラブ
    joined mid-career for some players, and which side of the line they fall on
    is a judgement about the club, not something the roster settles.

    Anything with no registry match is non_j_club_academy. Overseas academies
    land here too; splitting domestic from overseas is a description, not a
    classification the analysis depends on, since neither enters the three main
    pathways, so it is assigned in review rather than guessed from the string.
    """
    club = match_club(institution, clubs)
    if club is None or club.entry_season is None:
        return NON_J_CLUB_ACADEMY
    if birth_year is None:
        return J_CLUB_BOUNDARY
    low, high = development_window(birth_year)
    # Clip to what the league table can speak about. Without this, a player
    # young enough that their window runs past the last observed season looks
    # like a boundary case for clubs that never left the league, and one old
    # enough that it starts before 1999 looks like one for clubs that never
    # joined late -- both artifacts of the observation window, not the club.
    low = max(low, FIRST_OBSERVED_SEASON)
    high = min(high, OBSERVATION_END_SEASON)
    if high < low:
        return J_CLUB_BOUNDARY
    window = list(range(low, high + 1))
    covered = sum(1 for season in window if club.in_league(season))
    if covered == 0:
        return NON_J_CLUB_ACADEMY
    if covered < len(window):
        return J_CLUB_BOUNDARY
    return "j_club_academy"
