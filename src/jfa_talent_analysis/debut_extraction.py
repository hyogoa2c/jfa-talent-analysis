from __future__ import annotations

import re
from dataclasses import dataclass

# The plain-text 出場歴 lines Japanese Wikipedia football biographies carry
# (surviving the plaintext extract API, unlike infobox/成績 tables) state the
# J.League debut with an explicit league token, e.g.:
#   "Jリーグ初出場 - 2010年3月21日 J2 第3節 対ギラヴァンツ北九州戦"
#   "Jリーグ初出場： 2009年8月2日 J2第31節 vsアビスパ福岡戦"
#   "Jリーグ初出場・初得点 : 2008年10月19日 J2第40節 対モンテディオ山形"
#   "公式戦・Jリーグ初出場 - 2009年11月8日 J1第31節 清水エスパルス戦"
#   "2010年07月14日：Jリーグ初出場 - J1第14節 vs湘南ベルマーレ" (date first)
# All variants keep the label, a YYYY年 date, and a J1/J2/J3 league token on
# ONE line, so line-scoped extraction is robust to the ordering differences.
JLEAGUE_DEBUT_LABEL = "Jリーグ初出場"
J1_DEBUT_LABEL_RE = re.compile(r"J1(?:リーグ)?(?:初出場|デビュー)")
YEAR_RE = re.compile(r"(\d{4})年")
LEAGUE_TOKEN_RE = re.compile(r"J([123])")
SENTENCE_SPLIT_RE = re.compile(r"[。\n]")

# How far BEFORE the label a date may sit in the date-first line variant
# ("2010年07月14日：Jリーグ初出場 - J1第14節"). Keeping this window tight stops a
# long unbroken prose paragraph (one "line" after splitting on newlines) from
# donating an unrelated year mentioned sentences earlier (real case: 圍謙太朗's
# injury paragraph starts "2015年は…" but his debut is 2016 J3).
LABEL_LOOKBEHIND_CHARS = 25

# A "J1初出場" mention that actually describes a CUP match is not a J1 league
# debut (real case: 白井康介's article labels a ヤマザキナビスコカップ match
# "J1リーグ初出場"; his true J1 league debut per SFPR01 is three years later).
CUP_GUARD_RE = re.compile(r"カップ|ナビスコ|ルヴァン|天皇杯")


@dataclass(frozen=True)
class DebutEvidence:
    jleague_debut_year: int | None
    jleague_debut_league: str | None  # "J1" / "J2" / "J3"
    j1_debut_year: int | None
    j1_debut_basis: str  # "debut_line_j1" / "j1_mention_with_year" / "" (none found)


def normalize_fullwidth(text: str) -> str:
    """Normalize full-width Ｊ/digits to ASCII so one pattern set covers both."""
    return text.translate(str.maketrans("Ｊ０１２３４５６７８９", "J0123456789"))


def extract_debut_evidence(extract_text: str) -> DebutEvidence:
    """Extract J.League / J1 debut evidence from a full Wikipedia plaintext extract.

    Returns candidate evidence for backfilling pre-2014 debuts (see
    docs/data_collection_revision_proposal_2026-07-07.md item 1) — the caller is
    responsible for validating extracted years against SFPR01 ground truth where
    the debut falls inside the 2014+ observed window before trusting the
    out-of-window years.
    """
    text = normalize_fullwidth(extract_text)

    jleague_year, jleague_league = extract_jleague_debut_line(text)

    if jleague_league == "J1" and jleague_year is not None:
        return DebutEvidence(jleague_year, jleague_league, jleague_year, "debut_line_j1")

    j1_year = extract_j1_mention_year(text)
    basis = "j1_mention_with_year" if j1_year is not None else ""
    return DebutEvidence(jleague_year, jleague_league, j1_year, basis)


def extract_jleague_debut_line(text: str) -> tuple[int | None, str | None]:
    """Parse the structured "Jリーグ初出場" line: the year just before or after
    the label, and the league token after it. Returns the first line where both
    parse; (None, None) when no line does."""
    fallback: tuple[int | None, str | None] = (None, None)
    for line in text.split("\n"):
        label_index = line.find(JLEAGUE_DEBUT_LABEL)
        if label_index == -1:
            continue
        window = line[max(0, label_index - LABEL_LOOKBEHIND_CHARS) :]
        year_match = YEAR_RE.search(window)
        league_match = LEAGUE_TOKEN_RE.search(line[label_index:])
        year = int(year_match.group(1)) if year_match else None
        league = f"J{league_match.group(1)}" if league_match else None
        if year is not None and league is not None:
            return year, league
        if fallback == (None, None) and (year is not None or league is not None):
            fallback = (year, league)
    return fallback


def extract_j1_mention_year(text: str) -> int | None:
    """Find a J1-specific debut mention (e.g. "2011年、J1第8節…でJ1初出場を果たした")
    and return the year stated in the same sentence/line, or None.

    Only a year in the SAME sentence counts — Wikipedia prose often states the
    year one sentence earlier ("2011年に加入。第8節でJ1初出場。"), but resolving
    that requires season-context tracking that risks picking up an unrelated
    year, so those cases deliberately return None (left for SFPR01 or review).
    """
    for sentence in SENTENCE_SPLIT_RE.split(text):
        mention = J1_DEBUT_LABEL_RE.search(sentence)
        if mention is None:
            continue
        if CUP_GUARD_RE.search(sentence):
            continue
        years = YEAR_RE.findall(sentence[: mention.start()]) or YEAR_RE.findall(sentence)
        if years:
            return int(years[0])
    return None
