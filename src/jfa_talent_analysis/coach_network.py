from __future__ import annotations

import re
from dataclasses import dataclass

# University athletic-club suffixes stripped so "阪南大学サッカー部" (a player's raw
# Wikipedia club-history string) and "阪南大学" (the coach-tenure table's plain name)
# resolve to the same key.
CLUB_SUFFIXES = ("体育会サッカー部", "ア式蹴球部", "サッカー部", "蹴球部", "体育会蹴球部")

# A leading administrative-unit qualifier ("熊本県立", "静岡市立", "船橋市立", ...)
# followed by 立 is stripped from the FRONT of the name only — this is what lets
# "熊本県立大津高等学校" (player-side, prefecture-qualified) and "大津高等学校"
# (coach-tenure-side, bare) collide, and also what lets "船橋市立船橋高等学校" and
# "市立船橋高等学校" collide (the city name is optional in front of the qualifier,
# not just the qualifier itself). A short \S{1,6}? bounds how much can precede
# the 立 so this doesn't eat into an unrelated proper name — school names whose
# own name happens to end in one of these characters (e.g. 東京学芸大学) never
# have 立 immediately after within that window, so they're untouched.
ADMIN_PREFIX_RE = re.compile(r"^\S{0,6}?(?:都|道|府|県|市|区|町|村)立")

HIGH_SCHOOL_ABBREVIATIONS = ("高等学校", "高校")

# Leading fragments the club-history line parser occasionally leaves glued to an
# institution name ("2011 - 2013年度 鹿島アントラーズユース", "同年10月 京都サンガ…",
# "シーズン途中 -   ヴィッセル神戸 U-18", "：柏レイソルU-18") — each a real corpus case.
LEADING_JUNK_RE = re.compile(
    r"^(?:[：:‐\-\s]+|\d{4}(?:\s*-\s*\d{4})?年度?\s*|同年\d{0,2}月?\s*|シーズン途中\s*)+"
)

# "U18" / "U 18" → "U-18" so hyphenation variance can't split a team in two.
U_BRACKET_RE = re.compile(r"U\s?(\d{2})")

# Renamed / historically-named J-academy teams mapped onto the researched
# canonical name. Keys are written in POST-normalization form (spaces removed,
# U-18 hyphenated), values are names as they appear in the coach-tenure table.
# Only continuity-verified renames belong here (読売日本SCユース really is the
# team that became 東京ヴェルディユース); similarly-named but DIFFERENT clubs
# (ヴェルディS.S.相模原ユース, 札幌ジュニアFCユース, 千葉SCユース) must NOT be
# added. 読売日本SCユースS is the junior section (現・ヴェルディジュニア), not
# the U-18 team — also excluded.
ACADEMY_ALIASES = {
    "コンサドーレ札幌U-18": "北海道コンサドーレ札幌U-18",
    "コンサドーレ札幌ユースU-18": "北海道コンサドーレ札幌U-18",
    "東京ヴェルディ1969ユース": "東京ヴェルディユース",
    "ヴェルディ1969ユース": "東京ヴェルディユース",
    "ヴェルディユース": "東京ヴェルディユース",
    "読売日本SCユース": "東京ヴェルディユース",
    "浦和レッドダイヤモンズユース": "浦和レッズユース",
    "京都パープルサンガユース": "京都サンガF.C.U-18",
    "名古屋グランパスエイトU-18": "名古屋グランパスU-18",
    "名古屋グランパスエイトユース": "名古屋グランパスU-18",
    "柏レイソルユース": "柏レイソルU-18",
    "ヴィッセル神戸ユース": "ヴィッセル神戸U-18",
    "セレッソ大阪ユース": "セレッソ大阪U-18",
    "大宮アルディージャU-18": "大宮アルディージャユース",
    "ジェフユナイテッド千葉U-18": "ジェフユナイテッド市原・千葉U-18",
    "ジェフユナイテッド千葉ユース": "ジェフユナイテッド市原・千葉U-18",
    "ジェフユナイテッド市原ユース": "ジェフユナイテッド市原・千葉U-18",
    "ジェフユナイテッド市原・千葉ユース": "ジェフユナイテッド市原・千葉U-18",
    "サンフレッチェ広島F.Cユース": "サンフレッチェ広島ユース",
    "サンフレッチェ広島FCユース": "サンフレッチェ広島ユース",
}


def normalize_institution_name(name: str) -> str:
    """Canonical join key for an institution name, absorbing the known sources
    of spelling variance between coach-tenure tables (hand-researched, plain
    names) and player_institution_stints.csv (raw Wikipedia club-history
    strings): university club-suffixes, high-school 高校/高等学校 abbreviation,
    and a leading prefecture/city administrative qualifier.

    Deliberately NOT a general-purpose fuzzy matcher: it only strips patterns
    confirmed safe against the current ~86-institution coach-tenure roster (see
    tests). Adding new institutions later should re-verify no unintended
    collisions arise (e.g. two different schools sharing an administrative
    prefix once stripped)."""
    normalized = LEADING_JUNK_RE.sub("", name)
    normalized = normalized.replace(" ", "").replace("　", "")
    normalized = U_BRACKET_RE.sub(r"U-\1", normalized)
    for suffix in CLUB_SUFFIXES:
        if normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)]
            break
    if normalized.endswith("高校") and not normalized.endswith("高等学校"):
        normalized = normalized[: -len("高校")] + "高等学校"
    match = ADMIN_PREFIX_RE.match(normalized)
    if match:
        normalized = normalized[match.end() :]
    return ACADEMY_ALIASES.get(normalized, normalized)


@dataclass(frozen=True)
class CoachTenure:
    institution: str
    coach_name: str
    role_type: str
    from_year: int | None
    to_year: int | None
    source_urls: str
    confidence: str
    notes: str
    source_batch: str


def parse_year(value: str) -> int | None:
    return int(value) if value else None


def load_coach_tenure_row(row: dict[str, str], source_batch: str) -> CoachTenure:
    return CoachTenure(
        institution=row["institution"],
        coach_name=row["coach_name"],
        role_type=row["role_type"],
        from_year=parse_year(row["from_year"]),
        to_year=parse_year(row["to_year"]),
        source_urls=row["source_urls"],
        confidence=row["confidence"],
        notes=row["notes"],
        source_batch=source_batch,
    )


def is_gap_placeholder(coach_name: str, role_type: str) -> bool:
    """A coach-tenure row documenting an UNKNOWN coach during a gap period
    (see docs/coach_network_design_2026-07-10.md's "Gaps are the ABSENCE of
    rows... never guessed" rule) — some batches instead wrote an explicit
    coach_name="不明" row to make the gap and its dated bounds visible. These
    must never be joined as a real coach exposure (a player wasn't "coached
    by 不明" — several different people happen to share that placeholder
    name across institutions, which would silently merge them). 氏名不詳
    covers the 国見 figurehead-監督 row: a real but unnamed person, equally
    unusable as an identifiable coach."""
    return (
        coach_name.startswith("不明")
        or "氏名不詳" in coach_name
        or role_type == "その他(記載)"
    )


def years_overlap(
    a_from: int | None, a_to: int | None, b_from: int | None, b_to: int | None
) -> bool:
    """True if two [from, to] year ranges overlap, treating a missing bound as
    open-ended (a missing from_year as "always already started", a missing
    to_year as "still ongoing"). A range with both bounds missing overlaps
    everything, matching how a yearless player stint (see club_history_
    extraction's yearless childhood-club case) can't be excluded by year."""
    if a_from is not None and b_to is not None and a_from > b_to:
        return False
    if a_to is not None and b_from is not None and a_to < b_from:
        return False
    return True
