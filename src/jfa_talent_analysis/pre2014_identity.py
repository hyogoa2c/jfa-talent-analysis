"""Name-based identity resolution for pre-2014 appearance records against SFIX03.

Pre-2014 archive pages (see `sources/pre2014_appearances.py`) carry player names as plain
text with no player ID, profile link, or birth date, so resolution to SFIX03
`source_player_id` is name x team x year based. This module implements the name side:

- kanji variant folding (archive 楢崎 正剛 vs SFIX03 楢﨑 正剛),
- parenthesized-alias expansion of SFIX03 registered names
  (黒崎 久志（比差支） / 田渕（花垣） 龍二 / 三都主 アレサンドロ（アレックス）),
- classification of the leftovers (katakana-only names are almost always non-Japanese
  players, who are out of the SFIX03 Japanese-player universe by construction),
- an age-plausibility filter: with no birth date on the archive side, a same-name universe
  player born too late (or too early) to appear in that season is a different person and
  is dropped from the candidate set rather than matched.

Only unique full-name matches are auto-accepted. Katakana nickname aliases (e.g. the
アレックス in 三都主 アレサンドロ（アレックス）) are emitted as review candidates, never
auto-matched: the same mononym was worn by unrelated foreign players in other seasons, so
accepting it without a season x team check against SFIX04 would fabricate identities.
Ambiguous names (2+ universe candidates) likewise go to a queue for SFIX04-based
disambiguation, mirroring `scripts/suggest_identity_overrides_from_profiles.py`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from jfa_talent_analysis.sources.pre2014_appearances import normalize_text

# Variant folds between archive plain-text spellings and SFIX03 registered spellings,
# applied to BOTH sides before comparison. The two 斎-family groups (斎/齋 vs 斉/齊) are
# kept separate on purpose — they are distinct characters, not old/new forms of one. A fold
# that merges two distinct universe players sends the name to the ambiguous queue rather
# than silently picking one, so over-folding degrades to manual review, not to mismatches.
KANJI_VARIANT_FOLDS = str.maketrans(
    {
        "﨑": "崎",
        "髙": "高",
        "濵": "浜",
        "濱": "浜",
        "邉": "辺",
        "邊": "辺",
        "齋": "斎",
        "齊": "斉",
        "國": "国",
        "眞": "真",
        "澤": "沢",
        "廣": "広",
        "瀨": "瀬",
        "德": "徳",
        "櫻": "桜",
        "淺": "浅",
        "將": "将",
        "藪": "薮",
        # Archive 小川 雅已 vs SFIX03 小川 雅己 (1999 Cerezo). 已/己 are distinct characters
        # but this pair is a known transcription confusion; 巳 is NOT folded (real 辰巳 names).
        "已": "己",
    }
)

_PAREN_SEGMENT = re.compile(r"\(([^()]*)\)")
_KATAKANA_ONLY = re.compile(r"[ァ-ヶー・\s]+")

MATCH_EXACT = "exact_name"
MATCH_FOLDED = "folded_name"
MATCH_ALIAS = "alias_name"

# Age-plausibility window for a candidate to be the person on a season page. Bounds are
# deliberately loose: 森本貴幸 debuted at 15 (2004), 三浦知良 played J2 at 46 (2013). A
# candidate outside the window is a different person who happens to share the name (e.g.
# archive 2004 中村 亮 vs SFIX03 中村 亮 born 1996), not a match.
MIN_PLAUSIBLE_AGE = 14
MAX_PLAUSIBLE_AGE = 50


@dataclass
class Pre2014MatchResult:
    matched: list[dict[str, str]] = field(default_factory=list)
    ambiguous: list[dict[str, str]] = field(default_factory=list)
    unmatched: list[dict[str, str]] = field(default_factory=list)
    nickname_candidates: list[dict[str, str]] = field(default_factory=list)


def fold_name(value: str) -> str:
    """Normalize + apply kanji variant folds. The comparison key for both sides."""
    return normalize_text(value).translate(KANJI_VARIANT_FOLDS)


def is_katakana_only(value: str) -> bool:
    return bool(_KATAKANA_ONLY.fullmatch(normalize_text(value)))


def is_katakana_mononym(value: str) -> bool:
    """Single-token katakana names (ビスマルク, アレックス) — the registered-name style of
    most Brazilian-era foreign players. The same mononym recurs across unrelated people
    (archive 1999 ビスマルク is the Kashima Brazilian; SFIX03's ビスマルク is a defender
    born 2002), so these are never auto-matched, only queued for review."""
    normalized = normalize_text(value)
    return " " not in normalized and is_katakana_only(normalized)


def _birth_year(player: dict[str, str]) -> int | None:
    birth_date = player.get("birth_date", "")
    head = birth_date.split("/")[0]
    return int(head) if head.isdigit() else None


def _age_plausible(player: dict[str, str], season_year: int) -> bool:
    birth_year = _birth_year(player)
    if birth_year is None:
        return True
    return MIN_PLAUSIBLE_AGE <= season_year - birth_year <= MAX_PLAUSIBLE_AGE


def expand_name_aliases(name_ja: str) -> tuple[set[str], set[str]]:
    """Split an SFIX03 name into (full_name_aliases, nickname_aliases).

    Full-name aliases carry family+given and are safe to auto-match:
      黒崎 久志（比差支）    -> {黒崎 久志, 黒崎 比差支}
      岩﨑 知瑳（岩崎 知瑳）  -> {岩﨑 知瑳, 岩崎 知瑳}
      田渕（花垣） 龍二      -> {田渕 龍二, 花垣 龍二}
    Nickname aliases are single katakana tokens and are only ever review candidates:
      三都主 アレサンドロ（アレックス） -> nickname {アレックス}
    NFKC (inside normalize_text) folds full-width （） to ASCII () first, which also
    rescues the mixed-bracket names observed in SFIX03 (e.g. 髙山 和真（高山 和真)).
    """
    normalized = normalize_text(name_ja)
    full_aliases: set[str] = set()
    nicknames: set[str] = set()

    base = normalize_text(_PAREN_SEGMENT.sub(" ", normalized))
    if base:
        full_aliases.add(base)
    base_tokens = base.split()

    for match in _PAREN_SEGMENT.finditer(normalized):
        content = normalize_text(match.group(1))
        if not content:
            continue
        if " " in content:
            # Parenthesized full name (family + given), e.g. 岩﨑 知瑳（岩崎 知瑳）.
            full_aliases.add(content)
        elif is_katakana_only(content):
            nicknames.add(content)
        else:
            # Single-token alternate: replace the token the paren was attached to.
            token_index = len(normalized[: match.start()].rstrip().split()) - 1
            if 0 <= token_index < len(base_tokens):
                variant = base_tokens.copy()
                variant[token_index] = content
                full_aliases.add(" ".join(variant))

    return full_aliases, nicknames


@dataclass
class _UniverseIndex:
    exact: dict[str, list[dict[str, str]]]
    folded: dict[str, list[dict[str, str]]]
    alias: dict[str, list[dict[str, str]]]
    nickname: dict[str, list[dict[str, str]]]


def build_universe_index(players: list[dict[str, str]]) -> _UniverseIndex:
    index = _UniverseIndex(exact={}, folded={}, alias={}, nickname={})
    for player in players:
        full_aliases, nicknames = expand_name_aliases(player["name_ja"])
        base = normalize_text(_PAREN_SEGMENT.sub(" ", normalize_text(player["name_ja"])))
        index.exact.setdefault(base, []).append(player)
        index.folded.setdefault(fold_name(base), []).append(player)
        for alias in full_aliases - {base}:
            index.alias.setdefault(fold_name(alias), []).append(player)
        for nickname in nicknames:
            index.nickname.setdefault(fold_name(nickname), []).append(player)
    return index


def _lookup(
    index: _UniverseIndex, name: str
) -> tuple[list[dict[str, str]], str | None]:
    """Return (candidates, match_method) trying folded base names, then full-name aliases.

    Candidates always come from the folded index so that a variant-spelling sibling
    (universe holding both 楢﨑 X and 楢崎 X as different people) surfaces as ambiguous
    even when one of them matches the archive spelling exactly — with no birth date on the
    archive side, an exact hit is not evidence of which sibling played that season.
    """
    folded = fold_name(name)
    candidates = index.folded.get(folded, [])
    if candidates:
        exact_hit = bool(index.exact.get(normalize_text(name)))
        return candidates, MATCH_EXACT if exact_hit else MATCH_FOLDED
    candidates = index.alias.get(folded, [])
    if candidates:
        return candidates, MATCH_ALIAS
    return [], None


def match_pre2014_records(
    records: list[dict[str, str]], players: list[dict[str, str]]
) -> Pre2014MatchResult:
    """Match appearance rows (dicts from appearance_records_pre2014_*.csv) to universe rows.

    Rows whose name resolves to exactly one universe player are joined; names with 2+
    candidates go to `ambiguous`, names with none to `unmatched` (flagged katakana-only or
    not), and names that only hit a katakana nickname alias to `nickname_candidates`.
    """
    index = build_universe_index(players)
    result = Pre2014MatchResult()

    for record in records:
        name = record["player_name"]
        season_year = int(record["season_year"])
        candidates, match_method = _lookup(index, name)
        candidates = [c for c in candidates if _age_plausible(c, season_year)]

        if is_katakana_mononym(name):
            # Never auto-match mononyms; queue any name hit for review alongside
            # explicit nickname aliases.
            candidates = candidates or index.nickname.get(fold_name(name), [])
            if candidates:
                result.nickname_candidates.append(_diagnostic(record, candidates))
            else:
                result.unmatched.append(
                    {**_diagnostic(record, []), "katakana_only": "true"}
                )
            continue

        if len(candidates) == 1 and match_method is not None:
            result.matched.append(_join(record, candidates[0], match_method))
            continue
        if len(candidates) > 1:
            result.ambiguous.append(_diagnostic(record, candidates))
            continue
        nickname_candidates = [
            c
            for c in index.nickname.get(fold_name(name), [])
            if _age_plausible(c, season_year)
        ]
        if nickname_candidates:
            result.nickname_candidates.append(_diagnostic(record, nickname_candidates))
        else:
            result.unmatched.append(
                {
                    **_diagnostic(record, []),
                    "katakana_only": str(is_katakana_only(name)).lower(),
                }
            )
    return result


def _join(
    record: dict[str, str], player: dict[str, str], match_method: str
) -> dict[str, str]:
    return {
        **record,
        "source_player_id": player["source_player_id"],
        "universe_name_ja": player["name_ja"],
        "birth_date": player.get("birth_date", ""),
        "position": player.get("position", ""),
        "match_method": match_method,
    }


def _diagnostic(record: dict[str, str], candidates: list[dict[str, str]]) -> dict[str, str]:
    return {
        "season_year": record["season_year"],
        "competition_label": record["competition_label"],
        "team_name": record["team_name"],
        "player_name": record["player_name"],
        "candidate_player_ids": ";".join(
            candidate["source_player_id"] for candidate in candidates
        ),
        "candidate_names": ";".join(candidate["name_ja"] for candidate in candidates),
    }
