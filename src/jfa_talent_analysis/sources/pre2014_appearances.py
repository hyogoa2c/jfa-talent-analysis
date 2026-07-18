"""Parser for the J.League Data Site pre-2014 static appearance-record archive.

Source: https://data.j-league.or.jp/SS/jpn/team/index.html ("過去の試合記録"), a static
Shift_JIS (cp932) HTML archive covering 1999-2013 season x team x competition pages. See
docs/source_audit_pre2014_appearances.md for the full page-format and anomaly writeup, and
docs/research_plan_phase1.md §12 for how this backfill track fits the Phase 1 plan.

This module intentionally does NOT resolve players to SFIX03 identities and does NOT classify
competition_label into league vs. cup categories — both are out of scope for the collector
pilot and are left as raw text for a later stage to redo without re-scraping.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import asdict, dataclass, fields
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request

from jfa_talent_analysis.sources.retry import request_with_retry

BASE_URL = "https://data.j-league.or.jp/SS/jpn/team/"
INDEX_URL = urljoin(BASE_URL, "index.html")
ENCODING = "cp932"
USER_AGENT = "jfa-talent-analysis/0.1 pre2014-appearance-collector (research contact: hyg.a2c@gmail.com)"

# Every index link observed follows this exact shape, e.g. "1999010001_000001_W0707_J.html":
# <4-digit year><6-digit competition code>_<6-digit team code>_W0707_J.html
INDEX_LINK_PATTERN = re.compile(r"^(\d{4})\d{6}_\d{6}_\w+_J\.html$")

# The bold "選手出場記録" page marker precedes the two <P> blocks we care about (team name,
# then competition label). See docs/source_audit_pre2014_appearances.md "Header structure".
HEADER_MARKER = "選手出場記録"

# The player table header row is always exactly these five cells, followed by variable-length
# per-matchday columns that this module does not parse (see audit doc "Per-matchday marks").
APPEARANCE_HEADER_ROW = ["No", "選手", "出場", "時間", "得点"]


@dataclass
class IndexLink:
    year: int
    filename: str
    url: str
    link_text: str


@dataclass
class AppearanceRecord:
    season_year: int
    competition_label: str
    team_name: str
    player_no: str
    player_name: str
    appearances: int | None
    minutes: int | None
    goals: int | None
    source_url: str
    retrieved_at: str


def normalize_text(value: str) -> str:
    """Collapse whitespace (including U+3000 ideographic space) and fold full-width
    digits/Latin letters to half-width via NFKC. Used for header text, names, and numbers."""
    return " ".join(unicodedata.normalize("NFKC", value).split())


def parse_int(value: str) -> int | None:
    cleaned = normalize_text(value).replace(",", "")
    if not cleaned or not cleaned.lstrip("-").isdigit():
        return None
    return int(cleaned)


class IndexLinkParser(HTMLParser):
    """Collects (href, link_text) for every <a href="...html"> on the index page."""

    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._current_href: str | None = None
        self._current_text: list[str] = []

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            attrs = dict(attrs_list)
            href = attrs.get("href")
            if href and href.endswith(".html"):
                self._current_href = href
                self._current_text = []

    def handle_data(self, data: str) -> None:
        if self._current_href is not None:
            self._current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._current_href is not None:
            self.links.append((self._current_href, normalize_text("".join(self._current_text))))
            self._current_href = None
            self._current_text = []


def parse_index(html: str, *, base_url: str = BASE_URL) -> list[IndexLink]:
    """Parse the archive index into (year, url) pairs, skipping any href that doesn't match
    the observed pre-2014 filename shape (defensive: the index also carries unrelated nav
    links elsewhere on data.j-league.or.jp templates)."""
    parser = IndexLinkParser()
    parser.feed(html)
    links: list[IndexLink] = []
    for href, text in parser.links:
        match = INDEX_LINK_PATTERN.match(href)
        if not match:
            continue
        links.append(
            IndexLink(
                year=int(match.group(1)),
                filename=href,
                url=urljoin(base_url, href),
                link_text=text,
            )
        )
    return links


class AppearancePageParser(HTMLParser):
    """Extracts the header <P> blocks (team name, competition label, ...) in document order
    plus every <table> as a list of rows of cell text. See docs/source_audit_pre2014_appearances.md
    "Header structure" for why team name / competition label are the first two <P> blocks
    that follow the "選手出場記録" marker rather than fixed indices from document start."""

    def __init__(self) -> None:
        super().__init__()
        self.p_blocks: list[str] = []
        self.header_p_index: int | None = None
        self.tables: list[list[list[str]]] = []
        self._in_p = False
        self._p_parts: list[str] = []
        self._current_table: list[list[str]] | None = None
        self._current_row: list[str] | None = None
        self._current_cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        if tag == "p":
            self._in_p = True
            self._p_parts = []
        elif tag == "table":
            self._current_table = []
        elif tag == "tr" and self._current_table is not None:
            self._current_row = []
        elif tag in {"td", "th"} and self._current_row is not None:
            self._current_cell = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "p" and self._in_p:
            self.p_blocks.append(normalize_text("".join(self._p_parts)))
            self._in_p = False
        elif tag in {"td", "th"} and self._current_cell is not None and self._current_row is not None:
            self._current_row.append(normalize_text("".join(self._current_cell)))
            self._current_cell = None
        elif tag == "tr" and self._current_row is not None and self._current_table is not None:
            self._current_table.append(self._current_row)
            self._current_row = None
        elif tag == "table" and self._current_table is not None:
            self.tables.append(self._current_table)
            self._current_table = None

    def handle_data(self, data: str) -> None:
        if self._current_cell is not None:
            self._current_cell.append(data)
        elif self._in_p:
            self._p_parts.append(data)
        elif self.header_p_index is None and HEADER_MARKER in data:
            self.header_p_index = len(self.p_blocks)


def find_appearance_header_row_index(table: list[list[str]]) -> int | None:
    for index, row in enumerate(table):
        if row[:5] == APPEARANCE_HEADER_ROW:
            return index
    return None


def parse_appearance_page(
    html: str,
    *,
    season_year: int,
    source_url: str,
    retrieved_at: str | None = None,
) -> list[AppearanceRecord]:
    """Parse one team x competition-stage x year page into per-player total rows.

    Only the No/選手/出場/時間/得点 total columns are extracted; per-matchday mark columns
    (先発○, キャプテンC, ベンチSUB, etc.) are intentionally skipped for this pilot (see
    docs/source_audit_pre2014_appearances.md "Per-matchday marks"). Totals are already the
    full competition-stage cumulative values even on paginated pages (verified against the
    matching "_1_" first-page file for a multi-page 2005/2013 case), so no pagination
    following is needed.
    """
    parser = AppearancePageParser()
    parser.feed(html)
    retrieved = retrieved_at or datetime.now(UTC).isoformat()

    if parser.header_p_index is None or len(parser.p_blocks) < parser.header_p_index + 2:
        raise ValueError(f"could not locate team/competition header block in {source_url}")

    team_name = parser.p_blocks[parser.header_p_index]
    competition_label = parser.p_blocks[parser.header_p_index + 1]

    if not parser.tables:
        return []

    table = max(parser.tables, key=len)
    header_index = find_appearance_header_row_index(table)
    if header_index is None:
        return []

    records: list[AppearanceRecord] = []
    for row in table[header_index + 1 :]:
        if len(row) < 5 or not row[0].isdigit():
            continue
        records.append(
            AppearanceRecord(
                season_year=season_year,
                competition_label=competition_label,
                team_name=team_name,
                player_no=row[0],
                player_name=row[1],
                appearances=parse_int(row[2]),
                minutes=parse_int(row[3]),
                goals=parse_int(row[4]),
                source_url=source_url,
                retrieved_at=retrieved,
            )
        )
    return records


def fetch_index_html(timeout: int = 30) -> str:
    request = Request(INDEX_URL, headers={"User-Agent": USER_AGENT})
    _, _, html = request_with_retry(request, timeout=timeout, encoding=ENCODING)
    return html


def fetch_page_html(url: str, timeout: int = 30) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    _, _, html = request_with_retry(request, timeout=timeout, encoding=ENCODING)
    return html


APPEARANCE_RECORD_FIELDNAMES = [f.name for f in fields(AppearanceRecord)]


def write_appearance_records_csv(path: Path, records: list[AppearanceRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=APPEARANCE_RECORD_FIELDNAMES)
        writer.writeheader()
        for record in records:
            writer.writerow(asdict(record))
