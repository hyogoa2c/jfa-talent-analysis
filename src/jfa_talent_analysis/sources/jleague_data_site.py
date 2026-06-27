from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin
from urllib.request import Request, urlopen
import json
import re


BASE_URL = "https://data.j-league.or.jp/"
DEFAULT_PAGES = ("SFIX02", "SFIX03", "SFPR01")
USER_AGENT = "jfa-talent-analysis/0.1 source-audit"


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


def normalize_text(value: str) -> str:
    return " ".join(value.split())


def page_url(page_id: str) -> str:
    return urljoin(BASE_URL, f"{page_id}/")


def fetch_url(url: str, timeout: int = 30) -> tuple[int, str | None, str]:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        content = response.read().decode("utf-8", errors="replace")
        return response.status, response.headers.get("content-type"), content


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
