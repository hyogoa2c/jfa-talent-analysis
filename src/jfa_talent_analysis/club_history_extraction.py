from __future__ import annotations

import re
from dataclasses import dataclass

# The plain-text 所属クラブ section of Japanese Wikipedia football biographies
# follows a stable line grammar (verified across the cached 3,403-player
# corpus; 97.3% of players have the section):
#
#   [YYYY年[M月] [- [YYYY年][M月]]] INSTITUTION [（ANNOTATION）]
#
#   2011年 - 2013年 柏レイソルU-18 (千葉県立柏中央高等学校)
#   2016年3月 - 7月  いわきFC              <- month-only end, same year
#   2013年 柏レイソル (2種登録選手)         <- single year
#   2014年 -  浦和レッズ                    <- open-ended
#   広瀬サッカースポーツ少年団               <- childhood club, no years
#
# Optional block markers ユース経歴/プロ経歴 split some articles' lists.
SECTION_RE = re.compile(r"==\s*所属クラブ\s*==\n(.*?)(?=\n==[^=]|\Z)", re.DOTALL)

LINE_RE = re.compile(
    r"^(?:(?P<from_year>\d{4})年(?:(?P<from_month>\d{1,2})月)?"
    r"(?:\s*-\s*(?:(?P<to_year>\d{4})年)?(?:(?P<to_month>\d{1,2})月)?)?)?"
    r"\s*(?P<rest>\S.*)$"
)
ANNOTATION_RE = re.compile(r"[（(](?P<annotation>[^）)]*)[）)]\s*$")
BLOCK_MARKERS = {"ユース経歴": "youth", "プロ経歴": "pro", "その他の経歴": "other"}

# Institution-name features that mark a development-stage (pre-professional)
# stint. Soft flag only: downstream joins against a coach table of known youth
# institutions do the authoritative filtering.
YOUTH_NAME_RE = re.compile(
    r"ユース|ジュニア|Jr|U-?1[0-8]|高等学校|高校|高等部|中学|小学|大学|アカデミー|"
    r"少年団|スクール|キッズ|サッカークラブ"
)

# Registration statuses that mean the line is a pro-club affiliation formality
# during the youth years, not a development institution itself.
REGISTRATION_STATUSES = ("2種登録", "特別指定")


@dataclass(frozen=True)
class ClubStint:
    line_index: int
    from_year: int | None
    to_year: int | None
    institution: str
    annotation: str  # concurrent school, registration status, loan note...
    block: str  # "youth" / "pro" / "other" / "" (article had no block markers)
    youth_flag: bool


def extract_club_section(extract_text: str) -> str | None:
    match = SECTION_RE.search(extract_text)
    return match.group(1).strip() if match else None


def parse_club_history(extract_text: str) -> list[ClubStint]:
    """Parse the 所属クラブ section into ordered stints.

    Returns [] when the article has no parseable section. Lines that are
    section furniture (block markers, tournament names leaking in from
    adjacent lists) are skipped, not guessed at.
    """
    section = extract_club_section(extract_text)
    if section is None:
        return []

    stints: list[ClubStint] = []
    block = ""
    for index, raw_line in enumerate(section.split("\n")):
        line = raw_line.strip()
        if not line or len(line) > 80:
            continue
        if line in BLOCK_MARKERS:
            block = BLOCK_MARKERS[line]
            continue

        match = LINE_RE.match(line)
        if match is None:
            continue
        rest = match.group("rest").strip()

        annotation = ""
        annotation_match = ANNOTATION_RE.search(rest)
        if annotation_match:
            annotation = annotation_match.group("annotation").strip()
            rest = rest[: annotation_match.start()].strip()
        if not rest:
            continue

        from_year = int(match.group("from_year")) if match.group("from_year") else None
        to_year = int(match.group("to_year")) if match.group("to_year") else None
        # "2016年3月 - 7月" (month-only end) means the stint ended the same year;
        # "2013年 柏レイソル" (no dash parsed) is a single-year stint only when a
        # dash was absent — LINE_RE can't see the dash once consumed, so detect
        # open-endedness from the original line instead.
        if from_year is not None and to_year is None:
            if match.group("to_month"):
                to_year = from_year
            elif "-" not in line.split(rest)[0]:
                to_year = from_year

        stints.append(
            ClubStint(
                line_index=index,
                from_year=from_year,
                to_year=to_year,
                institution=rest,
                annotation=annotation,
                block=block,
                youth_flag=bool(YOUTH_NAME_RE.search(rest)),
            )
        )
    return stints


def is_registration_formality(stint: ClubStint) -> bool:
    """True for 2種登録/特別指定 lines: a pro-club registration held while the
    player still belonged to a development institution — kept in the data (the
    registration year is analytically useful) but not itself a development
    stint for coach-linkage purposes."""
    return any(status in stint.annotation for status in REGISTRATION_STATUSES)
