from jfa_talent_analysis.sources.wikipedia import (
    build_wikipedia_queries,
    parse_wikipedia_search_results,
    summarize_wikipedia_candidates,
)


def test_build_wikipedia_queries_adds_football_and_spacing_variants():
    assert build_wikipedia_queries("原 大智", "HARA Taichi") == [
        "原大智 サッカー",
        "原大智",
        "原 大智 サッカー",
        "原 大智",
        "HARA Taichi",
        "Hara Taichi",
    ]


def test_parse_wikipedia_search_results_builds_urls():
    results = parse_wikipedia_search_results(
        {
            "query": {
                "search": [
                    {
                        "title": "原大智",
                        "snippet": "日本のサッカー選手",
                    }
                ]
            }
        }
    )

    assert results[0].title == "原大智"
    assert results[0].url == "https://ja.wikipedia.org/wiki/%E5%8E%9F%E5%A4%A7%E6%99%BA"
    assert results[0].snippet == "日本のサッカー選手"


def test_summarize_wikipedia_candidates_joins_fields():
    results = parse_wikipedia_search_results(
        {
            "query": {
                "search": [
                    {"title": "原大智", "snippet": "日本のサッカー選手"},
                    {"title": "原大智 (野球)", "snippet": "別人"},
                ]
            }
        }
    )

    summary = summarize_wikipedia_candidates(results)

    assert summary["wikipedia_titles"] == "原大智|原大智 (野球)"
    assert "https://ja.wikipedia.org/wiki/%E5%8E%9F%E5%A4%A7%E6%99%BA" in summary[
        "wikipedia_urls"
    ]
