"""Youth-career fields from the ja.wikipedia {{サッカー選手}} infobox.

The plaintext extract API cannot return infobox content, so everything built on
it -- the prose classifier and the 所属クラブ list parser alike -- has never seen
these fields. They hold what both of those procedures most often lack: the years
the player was actually in an academy, as a structured parameter rather than
prose to be inferred from.

    | ユースクラブ1 = {{Flagicon|JPN}} [[柏レイソル]]ユース| ユース年1 = 1993-1995

This module only reads them. Whether they may *label* a pathway is a measurement
decision with the same requirements SAP §1b-3 had to meet -- a coverage census,
gold validation, and a check that adoption is not era-differential -- and a
30-player probe already puts era-1 at 100% against era-2's 77%, so that question
is open, not settled. What the fields are used for today is narrower: evidence
for the human adjudication of academy rows already flagged as boundary cases.
"""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass

API = "https://ja.wikipedia.org/w/api.php"
USER_AGENT = "jfa-talent-analysis/0.1 (research; contact hyg.a2c@gmail.com)"

# Parameters may share a line, so a value runs to the next "|" -- but templates
# and wikilinks contain their own pipes ({{Flagicon|JPN}}, [[a|b]]), so they have
# to be consumed whole or the value is truncated at the first one.
_VALUE = r"(?:\{\{[^{}]*\}\}|\[\[[^\]]*\]\]|[^|\n}])*"
YOUTH_CLUB_RE = re.compile(rf"\|\s*ユースクラブ(\d*)\s*=\s*({_VALUE})")
YOUTH_YEARS_RE = re.compile(rf"\|\s*ユース年(\d*)\s*=\s*({_VALUE})")
TEMPLATE_RE = re.compile(r"\{\{[^{}]*\}\}")
LINK_RE = re.compile(r"\[\[(?:[^\]|]*\|)?([^\]|]*)\]\]")
REF_RE = re.compile(r"<ref[^>]*>.*?</ref>|<ref[^>]*/>", re.S)
YEAR_RANGE_RE = re.compile(r"(\d{4})\s*[-–—〜~]?\s*(\d{4})?")


@dataclass(frozen=True)
class YouthEntry:
    index: str
    club: str
    years: str
    from_year: int | None
    to_year: int | None


def clean_value(value: str) -> str:
    """Strip flag templates, wikilinks and refs, keeping the display text."""
    text = REF_RE.sub("", value)
    text = TEMPLATE_RE.sub("", text)
    text = LINK_RE.sub(r"\1", text)
    return text.replace("'''", "").strip()


def parse_year_range(value: str) -> tuple[int | None, int | None]:
    """"1993-1995" -> (1993, 1995); "2023-" -> (2023, None); "2016-????" -> (2016, None)."""
    match = YEAR_RANGE_RE.search(value)
    if not match:
        return (None, None)
    start = int(match.group(1))
    end = int(match.group(2)) if match.group(2) else None
    return (start, end)


def parse_youth_entries(wikitext: str) -> list[YouthEntry]:
    """Youth clubs and their years, in infobox order.

    Clubs and years are separate numbered parameters, so they are matched by
    index rather than by position: an article can carry a club with no years, or
    years for only some clubs, and pairing them positionally would silently
    attach one club's years to another.
    """
    years = {index: clean_value(value) for index, value in YOUTH_YEARS_RE.findall(wikitext)}
    entries = []
    for index, raw_club in YOUTH_CLUB_RE.findall(wikitext):
        club = clean_value(raw_club)
        if not club:
            continue
        span = years.get(index, "")
        start, end = parse_year_range(span)
        entries.append(YouthEntry(index or "1", club, span, start, end))
    return entries


def fetch_wikitext(title: str, *, timeout: int = 30) -> str:
    """Raw wikitext for an article, or "" when the page has no revision."""
    query = urllib.parse.urlencode(
        {
            "action": "query",
            "format": "json",
            "prop": "revisions",
            "rvprop": "content",
            "rvslots": "main",
            "titles": title,
            "formatversion": "2",
        }
    )
    request = urllib.request.Request(f"{API}?{query}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        page = json.load(response)["query"]["pages"][0]
    if "revisions" not in page:
        return ""
    return page["revisions"][0]["slots"]["main"]["content"]
