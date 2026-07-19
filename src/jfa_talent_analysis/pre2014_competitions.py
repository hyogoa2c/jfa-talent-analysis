"""Competition classification for pre-2014 archive pages: reproduce the league-only filter.

The 2014-2025 pipeline counts SFPR01 *league* appearances only (no Levain/Emperor's Cup),
so pre-2014 aggregates are comparable with the existing feature definitions only if
non-league competitions are excluded the same way. This module classifies the raw
`competition_label` text (kept verbatim by the collector exactly so this step could be
done without re-scraping) into structural categories; `is_league_competition` is the
filter that reproduces the SFPR01 definition.

Classification is by substring on the NFKC-normalized label, per the source audit
(docs/source_audit_pre2014_appearances.md "Competitions observed"): filename competition
codes are NOT reliable classifiers (002006 and 002000 are both the Nabisco Cup), and
labels cannot be assumed to start with a 4-digit year ('99Jリーグ ヤマザキナビスコカップ).
Non-league markers are checked first so a hypothetical combined label would not silently
count as league play.
"""

from __future__ import annotations

from jfa_talent_analysis.sources.pre2014_appearances import normalize_text

CATEGORY_J1_LEAGUE = "j1_league"
CATEGORY_J2_LEAGUE = "j2_league"
CATEGORY_LEAGUE_CUP = "league_cup"
CATEGORY_CHAMPIONSHIP = "championship"
CATEGORY_PROMOTION_PLAYOFF = "promotion_playoff"
CATEGORY_RELEGATION_PLAYOFF = "relegation_playoff"
CATEGORY_SATELLITE = "satellite"
CATEGORY_UNCLASSIFIED = "unclassified"

LEAGUE_CATEGORIES = frozenset({CATEGORY_J1_LEAGUE, CATEGORY_J2_LEAGUE})

# Checked in order; first hit wins. Every marker is taken from a label actually observed
# in the 1999-2013 index sample (see the audit doc's competition table).
_NON_LEAGUE_MARKERS: list[tuple[str, str]] = [
    ("ナビスコ", CATEGORY_LEAGUE_CUP),
    ("チャンピオンシップ", CATEGORY_CHAMPIONSHIP),
    ("昇格プレーオフ", CATEGORY_PROMOTION_PLAYOFF),
    ("入れ替え戦", CATEGORY_RELEGATION_PLAYOFF),
    ("サテライト", CATEGORY_SATELLITE),
]


def classify_competition_label(label: str) -> str:
    normalized = normalize_text(label)
    for marker, category in _NON_LEAGUE_MARKERS:
        if marker in normalized:
            return category
    if "ディビジョン1" in normalized:
        return CATEGORY_J1_LEAGUE
    if "ディビジョン2" in normalized:
        return CATEGORY_J2_LEAGUE
    return CATEGORY_UNCLASSIFIED


def is_league_competition(label: str) -> bool:
    """True for J1/J2 regular-league pages — the SFPR01-equivalent appearance universe."""
    return classify_competition_label(label) in LEAGUE_CATEGORIES
