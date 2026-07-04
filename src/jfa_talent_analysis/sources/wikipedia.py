from __future__ import annotations

import json
import re
from dataclasses import dataclass
from urllib.parse import quote, urlencode
from urllib.request import Request

from jfa_talent_analysis.sources.retry import request_with_retry

USER_AGENT = "jfa-talent-analysis/0.1 Wikipedia manual review helper"

# Section headings that most often carry pre-professional pathway prose, per the
# pilot in docs/pathway_source_pilot_2026-07-03.md (heading conventions vary a lot
# between articles: some use a single flat 来歴, others split 幼少期/high-school/
# university subsections apart from a separate クラブ経歴 pro-career section).
PRE_PRO_SECTION_HEADINGS = {
    "来歴",
    "経歴",
    "幼少期",
    "少年時代",
    "生い立ち",
    "プロ入りまで",
    "高校時代",
    "大学時代",
    "アマチュア時代",
}

SECTION_HEADER_RE = re.compile(r"^(={2,4})\s*(.+?)\s*\1\s*$", re.MULTILINE)


@dataclass(frozen=True)
class WikipediaSearchResult:
    title: str
    url: str
    snippet: str


def build_wikipedia_queries(name_ja: str, name_en: str) -> list[str]:
    queries: list[str] = []
    normalized_ja = " ".join(name_ja.split())
    if normalized_ja:
        no_space_ja = normalized_ja.replace(" ", "")
        queries.append(f"{no_space_ja} サッカー")
        queries.append(no_space_ja)
        if no_space_ja != normalized_ja:
            queries.append(f"{normalized_ja} サッカー")
            queries.append(normalized_ja)
    normalized_en = " ".join(name_en.split())
    if normalized_en:
        queries.append(normalized_en)
        title_en = normalized_en.title()
        if title_en != normalized_en:
            queries.append(title_en)
    return list(dict.fromkeys(queries))


def fetch_wikipedia_candidates(
    name_ja: str,
    name_en: str,
    *,
    language: str = "ja",
    per_query_limit: int = 3,
    max_results: int = 5,
    timeout: int = 30,
) -> list[WikipediaSearchResult]:
    results: list[WikipediaSearchResult] = []
    seen_titles: set[str] = set()
    for query in build_wikipedia_queries(name_ja, name_en):
        for result in search_wikipedia(query, language, per_query_limit, timeout):
            if result.title in seen_titles:
                continue
            seen_titles.add(result.title)
            results.append(result)
            if len(results) >= max_results:
                return results
    return results


def search_wikipedia(
    query: str,
    language: str = "ja",
    limit: int = 3,
    timeout: int = 30,
    retries: int = 2,
) -> list[WikipediaSearchResult]:
    endpoint = f"https://{language}.wikipedia.org/w/api.php"
    payload = urlencode(
        {
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": query,
            "srlimit": str(limit),
            "utf8": "1",
        }
    )
    request = Request(
        f"{endpoint}?{payload}",
        headers={
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    _, _, content = request_with_retry(request, timeout=timeout, retries=retries)
    return parse_wikipedia_search_results(json.loads(content), language)


def parse_wikipedia_search_results(
    data: dict,
    language: str = "ja",
) -> list[WikipediaSearchResult]:
    return [
        WikipediaSearchResult(
            title=row.get("title", ""),
            url=build_wikipedia_url(row.get("title", ""), language),
            snippet=row.get("snippet", ""),
        )
        for row in data.get("query", {}).get("search", [])
        if row.get("title")
    ]


def summarize_wikipedia_candidates(results: list[WikipediaSearchResult]) -> dict[str, str]:
    return {
        "wikipedia_titles": "|".join(result.title for result in results),
        "wikipedia_urls": "|".join(result.url for result in results),
    }


def build_wikipedia_url(title: str, language: str = "ja") -> str:
    return f"https://{language}.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"


def fetch_wikipedia_extract(
    title: str,
    *,
    language: str = "ja",
    timeout: int = 30,
    retries: int = 2,
) -> str | None:
    """Fetch the full plaintext extract of a Wikipedia article, or None if it doesn't exist."""
    endpoint = f"https://{language}.wikipedia.org/w/api.php"
    payload = urlencode(
        {
            "action": "query",
            "format": "json",
            "prop": "extracts",
            "exlimit": "1",
            "explaintext": "1",
            "redirects": "1",
            "titles": title,
        }
    )
    request = Request(
        f"{endpoint}?{payload}",
        headers={
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    _, _, content = request_with_retry(request, timeout=timeout, retries=retries)
    return parse_extract_response(json.loads(content))


def parse_extract_response(data: dict) -> str | None:
    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        if "missing" in page:
            return None
        extract = page.get("extract")
        return extract if extract else None
    return None


def extract_pathway_context(extract_text: str) -> str:
    """Return prose from sections most likely to describe the pre-professional pathway.

    Includes subsections nested under a matching heading (e.g. a "筑波大学" subsection
    under "幼少期"), since a matching section commonly continues in a deeper subsection
    rather than repeating the same heading text. Falls back to the whole article extract
    when no matching heading is found at all, since heading conventions vary too much
    between articles to guarantee a match (see docs/pathway_source_pilot_2026-07-03.md).
    This returns candidate research text for a human/semi-automated reviewer to read and
    classify — it does not itself infer a pathway_category.
    """
    matches = list(SECTION_HEADER_RE.finditer(extract_text))
    if not matches:
        return extract_text.strip()

    collected: list[str] = []
    active = False
    active_depth = 0
    for index, match in enumerate(matches):
        depth = len(match.group(1))
        heading = match.group(2)
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(extract_text)

        if heading in PRE_PRO_SECTION_HEADINGS:
            active = True
            active_depth = depth
        elif active and depth <= active_depth:
            active = False

        if active:
            collected.append(extract_text[start:end].strip())

    return "\n\n".join(collected) if collected else extract_text.strip()
