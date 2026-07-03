from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.parse import urljoin
from urllib.request import Request
import csv
import json
import re

from jfa_talent_analysis.sources.retry import request_with_retry


BASE_URL = "https://data.j-league.or.jp/"
DEFAULT_PAGES = ("SFIX02", "SFIX03", "SFPR01")
USER_AGENT = "jfa-talent-analysis/0.1 source-audit"
SFIX03_SEARCH_URL = urljoin(BASE_URL, "SFIX03/search")
SFIX04_INDEX_URL = urljoin(BASE_URL, "SFIX04/index")
SFPR01_SEARCH_URL = urljoin(BASE_URL, "SFPR01/search")


@dataclass
class SelectOption:
    value: str | None
    text: str


@dataclass
class SelectSummary:
    name: str | None
    id: str | None
    options_count: int
    sample_options: list[SelectOption] = field(default_factory=list)


@dataclass
class InputSummary:
    name: str | None
    id: str | None
    input_type: str | None
    value: str | None


@dataclass
class LinkSummary:
    href: str
    text: str


@dataclass
class ScriptSummary:
    src: str


@dataclass
class TableSummary:
    headers: list[str]
    row_count: int


@dataclass
class PlayerUniverseRecord:
    source_player_id: str
    name_ja: str
    name_en: str
    last_belong_team: str
    position: str
    birth_date: str
    height_cm: int | None
    weight_kg: int | None
    source_url: str
    retrieved_at: str


@dataclass
class PlayerSeasonHistoryRecord:
    source_player_id: str
    season: str
    team_name: str
    league: str
    appearances: int | None
    goals: int | None
    source_url: str
    retrieved_at: str


@dataclass
class CompetitionOption:
    display_name: str
    display_name_en: str | None
    select_value: str
    parent_value: str | None


@dataclass
class AppearanceRecord:
    season: str
    competition_frame_id: str
    competition_id: str
    league: str
    team_id: str
    team_name: str
    shirt_number: str
    name_ja: str
    appearances: int | None
    minutes: int | None
    goals: int | None
    source_url: str
    retrieved_at: str


@dataclass
class PageAudit:
    page_id: str
    url: str
    status: int | None
    content_type: str | None
    retrieved_at: str
    title: str
    inputs: list[InputSummary]
    selects: list[SelectSummary]
    links: list[LinkSummary]
    scripts: list[ScriptSummary]
    tables: list[TableSummary]
    endpoint_hints: list[str]
    error: str | None = None


class DataSiteParser(HTMLParser):
    def __init__(self, base_url: str, max_options_per_select: int = 20) -> None:
        super().__init__()
        self.base_url = base_url
        self.max_options_per_select = max_options_per_select
        self.title_parts: list[str] = []
        self.inputs: list[InputSummary] = []
        self.selects: list[SelectSummary] = []
        self.links: list[LinkSummary] = []
        self.scripts: list[ScriptSummary] = []
        self.tables: list[TableSummary] = []

        self._in_title = False
        self._current_link: dict[str, Any] | None = None
        self._current_select: dict[str, Any] | None = None
        self._current_option: dict[str, Any] | None = None
        self._current_table: dict[str, Any] | None = None
        self._current_cell: dict[str, Any] | None = None

    @property
    def title(self) -> str:
        return " ".join(" ".join(self.title_parts).split())

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        attrs = dict(attrs_list)
        if tag == "title":
            self._in_title = True
        elif tag == "input":
            self.inputs.append(
                InputSummary(
                    name=attrs.get("name"),
                    id=attrs.get("id"),
                    input_type=attrs.get("type"),
                    value=attrs.get("value"),
                )
            )
        elif tag == "select":
            self._current_select = {
                "name": attrs.get("name"),
                "id": attrs.get("id"),
                "options_count": 0,
                "sample_options": [],
            }
        elif tag == "option" and self._current_select is not None:
            self._current_option = {"value": attrs.get("value"), "text_parts": []}
        elif tag == "a" and attrs.get("href"):
            self._current_link = {"href": urljoin(self.base_url, attrs["href"]), "text_parts": []}
        elif tag == "script" and attrs.get("src"):
            self.scripts.append(ScriptSummary(src=urljoin(self.base_url, attrs["src"])))
        elif tag == "table":
            self._current_table = {"headers": [], "row_count": 0, "in_row": False}
        elif tag == "tr" and self._current_table is not None:
            self._current_table["in_row"] = True
            self._current_table["row_count"] += 1
        elif tag in {"th", "td"} and self._current_table is not None:
            self._current_cell = {"tag": tag, "text_parts": []}

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        elif tag == "option" and self._current_option is not None and self._current_select is not None:
            text = normalize_text(" ".join(self._current_option["text_parts"]))
            self._current_select["options_count"] += 1
            if len(self._current_select["sample_options"]) < self.max_options_per_select:
                self._current_select["sample_options"].append(
                    SelectOption(value=self._current_option["value"], text=text)
                )
            self._current_option = None
        elif tag == "select" and self._current_select is not None:
            self.selects.append(
                SelectSummary(
                    name=self._current_select["name"],
                    id=self._current_select["id"],
                    options_count=self._current_select["options_count"],
                    sample_options=self._current_select["sample_options"],
                )
            )
            self._current_select = None
        elif tag == "a" and self._current_link is not None:
            text = normalize_text(" ".join(self._current_link["text_parts"]))
            self.links.append(LinkSummary(href=self._current_link["href"], text=text))
            self._current_link = None
        elif tag in {"th", "td"} and self._current_cell is not None and self._current_table is not None:
            text = normalize_text(" ".join(self._current_cell["text_parts"]))
            if self._current_cell["tag"] == "th" and text:
                self._current_table["headers"].append(text)
            self._current_cell = None
        elif tag == "table" and self._current_table is not None:
            row_count = max(0, self._current_table["row_count"] - 1)
            self.tables.append(
                TableSummary(
                    headers=self._current_table["headers"],
                    row_count=row_count,
                )
            )
            self._current_table = None

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title_parts.append(data)
        if self._current_option is not None:
            self._current_option["text_parts"].append(data)
        if self._current_link is not None:
            self._current_link["text_parts"].append(data)
        if self._current_cell is not None:
            self._current_cell["text_parts"].append(data)


class Sfix03PlayerListParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.player_ids: list[str] = []
        self.tables: list[list[list[str]]] = []
        self._current_table: list[list[str]] | None = None
        self._current_row: list[str] | None = None
        self._current_cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        attrs = dict(attrs_list)
        if tag == "input" and attrs.get("name") == "playerIdList" and attrs.get("value"):
            self.player_ids.append(attrs["value"])
        elif tag == "table":
            self._current_table = []
        elif tag == "tr" and self._current_table is not None:
            self._current_row = []
        elif tag in {"th", "td"} and self._current_row is not None:
            self._current_cell = []

    def handle_data(self, data: str) -> None:
        if self._current_cell is not None:
            self._current_cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"th", "td"} and self._current_cell is not None and self._current_row is not None:
            self._current_row.append(normalize_text(" ".join(self._current_cell)))
            self._current_cell = None
        elif tag == "tr" and self._current_row is not None and self._current_table is not None:
            self._current_table.append(self._current_row)
            self._current_row = None
        elif tag == "table" and self._current_table is not None:
            self.tables.append(self._current_table)
            self._current_table = None


def normalize_text(value: str) -> str:
    return " ".join(value.split())


def page_url(page_id: str) -> str:
    return urljoin(BASE_URL, f"{page_id}/")


def fetch_url(url: str, timeout: int = 30) -> tuple[int, str | None, str]:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    return request_with_retry(request, timeout=timeout)


def post_form(url: str, form: dict[str, str], timeout: int = 30) -> tuple[int, str | None, str]:
    data = urlencode(form).encode()
    request = Request(
        url,
        data=data,
        headers={
            "User-Agent": USER_AGENT,
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    return request_with_retry(request, timeout=timeout)


def post_json(path: str, form: dict[str, str], timeout: int = 30) -> dict[str, Any]:
    _, _, content = post_form(urljoin(BASE_URL, path), form, timeout=timeout)
    return json.loads(content)


def sfix03_japanese_players_form() -> dict[str, str]:
    return {
        "team_year_id_ex": "",
        "national_origin_ex": "0",
        "field_position_type_ex": "",
        "selectedTeamName": "（指定なし）",
        "selectedNationalOriginName": "日本",
        "selectedFieldPositionTypeName": "（指定なし）",
        "selectedJLeaguePlayerTypeNmae": "すべて",
        "selectedpalyerName": "",
        "selectedbrithPalce": "",
        "selectedplayerNameFirstAlphabet": "（指定なし）",
        "last_belong_team": "",
        "national_origin": "0",
        "field_position_type": "",
        "j_league_current_belong_player_type": "3",
        "palyer_name": "",
        "brith_palce": "",
        "player_name_first_alphabet": "",
    }


def fetch_sfix03_japanese_players() -> str:
    _, _, html = post_form(SFIX03_SEARCH_URL, sfix03_japanese_players_form())
    return html


def sfix04_player_url(source_player_id: str) -> str:
    return f"{SFIX04_INDEX_URL}?{urlencode({'player_id': source_player_id})}"


def fetch_sfix04_player_profile(source_player_id: str) -> str:
    _, _, html = fetch_url(sfix04_player_url(source_player_id))
    return html


def parse_height_weight(value: str) -> tuple[int | None, int | None]:
    if not value or "/" not in value:
        return None, None
    height, weight = value.split("/", 1)
    return parse_int(height), parse_int(weight)


def parse_int(value: str) -> int | None:
    value = value.strip().replace(",", "")
    if not value or not value.isdigit():
        return None
    return int(value)


def parse_sfix03_player_universe(
    html: str, retrieved_at: str | None = None
) -> list[PlayerUniverseRecord]:
    parser = Sfix03PlayerListParser()
    parser.feed(html)
    retrieved = retrieved_at or datetime.now(UTC).isoformat()

    if not parser.tables:
        return []

    player_table = max(parser.tables, key=len)
    data_rows = [row for row in player_table if len(row) == 6 and row[0] != "全てチェック クリア"]

    records: list[PlayerUniverseRecord] = []
    for player_id, row in zip(parser.player_ids, data_rows, strict=False):
        height_cm, weight_kg = parse_height_weight(row[5])
        records.append(
            PlayerUniverseRecord(
                source_player_id=player_id,
                name_ja=row[0],
                name_en=row[1],
                last_belong_team=row[2],
                position=row[3],
                birth_date=row[4],
                height_cm=height_cm,
                weight_kg=weight_kg,
                source_url=SFIX03_SEARCH_URL,
                retrieved_at=retrieved,
            )
        )
    return records


def parse_sfix04_player_season_history(
    html: str,
    *,
    source_player_id: str,
    source_url: str | None = None,
    retrieved_at: str | None = None,
) -> list[PlayerSeasonHistoryRecord]:
    parser = Sfix03PlayerListParser()
    parser.feed(html)
    retrieved = retrieved_at or datetime.now(UTC).isoformat()
    records: list[PlayerSeasonHistoryRecord] = []
    for table in parser.tables:
        header_index = find_player_history_header_index(table)
        if header_index is None:
            continue
        for row in table[header_index + 2 :]:
            if len(row) < 6 or not row[0].isdigit():
                continue
            records.append(
                PlayerSeasonHistoryRecord(
                    source_player_id=source_player_id,
                    season=row[0],
                    team_name=row[1],
                    league=row[2],
                    appearances=parse_int(row[3]),
                    goals=parse_int(row[4]),
                    source_url=source_url or sfix04_player_url(source_player_id),
                    retrieved_at=retrieved,
                )
            )
    return records


def find_player_history_header_index(table: list[list[str]]) -> int | None:
    for index, row in enumerate(table):
        if len(row) >= 3 and row[:3] == ["シーズン", "チーム", "リーグ"]:
            return index
    return None


def write_player_universe_sample(
    path: Path, records: list[PlayerUniverseRecord], limit: int
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(PlayerUniverseRecord.__dataclass_fields__.keys())
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for record in records[:limit]:
            writer.writerow(asdict(record))


def create_competition_frames(season: str) -> list[CompetitionOption]:
    payload = post_json(
        "SFPR01/createCompetitionFrames",
        {"competition_year": season, "selectFlag": "true"},
    )
    return options_from_payload(payload.get("competitionFrameList") or [])


def create_competitions(season: str, competition_frame_id: str) -> list[CompetitionOption]:
    payload = post_json(
        "SFPR01/createCompetitions",
        {
            "competition_year": season,
            "competition_frame_id": competition_frame_id,
            "selectFlag": "true",
        },
    )
    return options_from_payload(payload.get("competitionList") or [])


def create_teams(competition_id: str) -> list[CompetitionOption]:
    payload = post_json(
        "SFPR01/createTeams",
        {"competition_id": competition_id, "selectFlag": "true"},
    )
    return options_from_payload(payload.get("teamList") or [])


def options_from_payload(items: list[dict[str, Any]]) -> list[CompetitionOption]:
    output: list[CompetitionOption] = []
    for item in items:
        output.append(
            CompetitionOption(
                display_name=str(item.get("displayName") or ""),
                display_name_en=item.get("displayNameEn"),
                select_value=str(item.get("selectValue") or ""),
                parent_value=str(item["parentValue"]) if item.get("parentValue") is not None else None,
            )
        )
    return output


def sfpr01_search_form(
    *,
    season: str,
    competition_frame_id: str,
    competition_id: str,
    team_id: str,
    league: str,
    team_name: str,
) -> dict[str, str]:
    return {
        "competition_year_ex": season,
        "competition_frame_id_ex": competition_frame_id,
        "competition_id_ex": competition_id,
        "team_id_ex": team_id,
        "selectedCompetitionName": league,
        "selectedCompetitionSubName": "",
        "selectedCompetitionYear": season,
        "selectedTeamName": team_name,
        "dataSize": "1",
        "pageStartNo": "0",
        "competition_year": season,
        "competition_frame_id": competition_frame_id,
        "competition_id": competition_id,
        "team_id": team_id,
    }


def fetch_sfpr01_appearance_records(
    *,
    season: str,
    competition_frame_id: str,
    competition_id: str,
    team_id: str,
    league: str,
    team_name: str,
) -> str:
    _, _, html = fetch_url(
        sfpr01_search_url(
            season=season,
            competition_frame_id=competition_frame_id,
            competition_id=competition_id,
            team_id=team_id,
            league=league,
            team_name=team_name,
        )
    )
    return html


def sfpr01_search_url(
    *,
    season: str,
    competition_frame_id: str,
    competition_id: str,
    team_id: str,
    league: str,
    team_name: str,
) -> str:
    query = urlencode(
        sfpr01_search_form(
            season=season,
            competition_frame_id=competition_frame_id,
            competition_id=competition_id,
            team_id=team_id,
            league=league,
            team_name=team_name,
        )
    )
    return f"{SFPR01_SEARCH_URL}?{query}"


def parse_sfpr01_appearance_records(
    html: str,
    *,
    season: str,
    competition_frame_id: str,
    competition_id: str,
    league: str,
    team_id: str,
    team_name: str,
    source_url: str | None = None,
    retrieved_at: str | None = None,
) -> list[AppearanceRecord]:
    parser = Sfix03PlayerListParser()
    parser.feed(html)
    retrieved = retrieved_at or datetime.now(UTC).isoformat()
    if not parser.tables:
        return []

    table = max(parser.tables, key=len)
    header_index = find_appearance_header_index(table)
    if header_index is None:
        return []

    records: list[AppearanceRecord] = []
    for row in table[header_index + 1 :]:
        if len(row) < 5 or not row[0] or not row[0].isdigit():
            continue
        records.append(
            AppearanceRecord(
                season=season,
                competition_frame_id=competition_frame_id,
                competition_id=competition_id,
                league=league,
                team_id=team_id,
                team_name=team_name,
                shirt_number=row[0],
                name_ja=row[1],
                appearances=parse_int(row[2]),
                minutes=parse_int(row[3]),
                goals=parse_int(row[4]),
                source_url=source_url or SFPR01_SEARCH_URL,
                retrieved_at=retrieved,
            )
        )
    return records


def find_appearance_header_index(table: list[list[str]]) -> int | None:
    for index, row in enumerate(table):
        if len(row) >= 5 and row[:5] == ["No.", "選手", "出場", "時間", "得点"]:
            return index
    return None


def write_appearance_sample(path: Path, records: list[AppearanceRecord], limit: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(AppearanceRecord.__dataclass_fields__.keys())
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for record in records[:limit]:
            writer.writerow(asdict(record))


def find_endpoint_hints(html: str) -> list[str]:
    patterns = [
        r"/SF[A-Z0-9_/?=&.-]+",
        r"/[^\"']*(?:ajax|Ajax|api|Api|search|Search)[^\"']*",
    ]
    hints: set[str] = set()
    for pattern in patterns:
        for match in re.finditer(pattern, html):
            value = match.group(0).strip()
            if len(value) <= 200:
                hints.add(value)
    return sorted(hints)


def audit_page(page_id: str) -> PageAudit:
    url = page_url(page_id)
    retrieved_at = datetime.now(UTC).isoformat()
    try:
        status, content_type, html = fetch_url(url)
        parser = DataSiteParser(base_url=url)
        parser.feed(html)
        return PageAudit(
            page_id=page_id,
            url=url,
            status=status,
            content_type=content_type,
            retrieved_at=retrieved_at,
            title=parser.title,
            inputs=parser.inputs,
            selects=parser.selects,
            links=dedupe_links(parser.links),
            scripts=parser.scripts,
            tables=parser.tables,
            endpoint_hints=find_endpoint_hints(html),
        )
    except Exception as exc:
        return PageAudit(
            page_id=page_id,
            url=url,
            status=None,
            content_type=None,
            retrieved_at=retrieved_at,
            title="",
            inputs=[],
            selects=[],
            links=[],
            scripts=[],
            tables=[],
            endpoint_hints=[],
            error=f"{type(exc).__name__}: {exc}",
        )


def dedupe_links(links: list[LinkSummary]) -> list[LinkSummary]:
    seen: set[tuple[str, str]] = set()
    output: list[LinkSummary] = []
    for link in links:
        key = (link.href, link.text)
        if key in seen:
            continue
        seen.add(key)
        output.append(link)
    return output


def audit_pages(page_ids: list[str]) -> dict[str, Any]:
    return {
        "source": "J.League Data Site",
        "base_url": BASE_URL,
        "generated_at": datetime.now(UTC).isoformat(),
        "pages": [asdict(audit_page(page_id)) for page_id in page_ids],
    }


def write_audit(path: Path, page_ids: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    report = audit_pages(page_ids)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
