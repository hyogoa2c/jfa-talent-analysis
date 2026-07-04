from jfa_talent_analysis.sources.wikipedia import (
    build_wikipedia_queries,
    extract_pathway_context,
    parse_extract_response,
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


def test_parse_extract_response_returns_none_for_missing_page():
    data = {"query": {"pages": {"-1": {"ns": 0, "title": "存在しないページ", "missing": ""}}}}

    assert parse_extract_response(data) is None


def test_parse_extract_response_returns_extract_text():
    data = {"query": {"pages": {"123": {"pageid": 123, "extract": "本文テキスト"}}}}

    assert parse_extract_response(data) == "本文テキスト"


def test_extract_pathway_context_falls_back_to_whole_text_without_headings():
    text = "見出しのない本文だけの記事。"

    assert extract_pathway_context(text) == text


def test_extract_pathway_context_captures_flat_rireki_section():
    # Matches the real 伊藤遼哉 article structure: one flat 来歴 section holds everything,
    # followed by an unrelated 人物 section that should be excluded.
    text = (
        "伊藤 遼哉は東京都出身のプロサッカー選手。\n\n"
        "== 来歴 ==\n"
        "スイスに移住し、FCチューリッヒでプレー。その後バイエルン・ミュンヘンの下部組織に入団。\n\n"
        "== 人物 ==\n"
        "趣味は読書。"
    )

    context = extract_pathway_context(text)

    assert "バイエルン・ミュンヘン" in context
    assert "趣味は読書" not in context


def test_extract_pathway_context_includes_nested_subsection_under_matching_heading():
    # Matches the real 三笘薫 article structure: a level-3 筑波大学 subsection continues
    # the level-2 幼少期 section's pathway story, followed by an unrelated クラブ経歴
    # section (also level 2) covering pro-career details that should be excluded.
    text = (
        "三笘薫は日本のプロサッカー選手。\n\n"
        "== 幼少期 ==\n"
        "さぎぬまSCでプレーしたのち川崎フロンターレU-10に加入した。\n\n"
        "=== 筑波大学 ===\n"
        "スポーツ推薦で筑波大学体育専門学群へ進学。\n\n"
        "== クラブ経歴 ==\n\n"
        "=== 川崎フロンターレ ===\n"
        "2020年に川崎フロンターレに入団。プロとしてデビューした。"
    )

    context = extract_pathway_context(text)

    assert "川崎フロンターレU-10" in context
    assert "筑波大学体育専門学群" in context
    assert "プロとしてデビュー" not in context
