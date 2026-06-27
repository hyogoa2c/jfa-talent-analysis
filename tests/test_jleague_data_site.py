from jfa_talent_analysis.sources.jleague_data_site import DataSiteParser, find_endpoint_hints


def test_parser_extracts_selects_links_and_tables():
    html = """
    <html>
      <head><title>Sample</title></head>
      <body>
        <a href="/SFIX03/">全選手一覧</a>
        <select name="national_origin" id="nationalOrigin">
          <option value="">▼</option>
          <option value="0">日本</option>
        </select>
        <table>
          <tr><th>選手名</th><th>所属</th></tr>
          <tr><td>田中 太郎</td><td>札幌</td></tr>
        </table>
      </body>
    </html>
    """

    parser = DataSiteParser(base_url="https://data.j-league.or.jp/SFIX01/")
    parser.feed(html)

    assert parser.title == "Sample"
    assert parser.links[0].href == "https://data.j-league.or.jp/SFIX03/"
    assert parser.links[0].text == "全選手一覧"
    assert parser.selects[0].name == "national_origin"
    assert parser.selects[0].sample_options[1].value == "0"
    assert parser.selects[0].sample_options[1].text == "日本"
    assert parser.tables[0].headers == ["選手名", "所属"]
    assert parser.tables[0].row_count == 1


def test_find_endpoint_hints_extracts_sf_paths():
    html = """<script>var path = "/SFPR01/search";</script><a href="/SFIX03/">x</a>"""

    hints = find_endpoint_hints(html)

    assert "/SFIX03/" in hints
    assert "/SFPR01/search" in hints
