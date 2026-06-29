from __future__ import annotations

import json
import time
from dataclasses import dataclass
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


USER_AGENT = "jfa-talent-analysis/0.1 Wikipedia manual review helper"


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
    data: dict = {}
    for attempt in range(retries + 1):
        try:
            with urlopen(request, timeout=timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
            break
        except HTTPError as error:
            if error.code != 429 or attempt >= retries:
                raise
            retry_after = parse_retry_after(error.headers.get("Retry-After", ""))
            time.sleep(retry_after)
    return parse_wikipedia_search_results(data, language)


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


def parse_retry_after(value: str) -> float:
    try:
        return max(float(value), 1.0)
    except ValueError:
        return 5.0
