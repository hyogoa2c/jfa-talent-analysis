from jfa_talent_analysis.sources.jleague_data_site import (
    DataSiteParser,
    find_endpoint_hints,
    parse_height_weight,
    parse_sfix03_player_universe,
)


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


def test_parse_height_weight():
    assert parse_height_weight("169/67") == (169, 67)
    assert parse_height_weight("") == (None, None)
    assert parse_height_weight("-/-") == (None, None)


def test_parse_sfix03_player_universe():
    html = """
    <html><body>
      <input type="checkbox" name="playerIdList" value="173" id="0">
      <input type="checkbox" name="playerIdList" value="6825" id="1">
      <table>
        <tr>
          <th>全てチェック クリア</th><th>選手名（英語）</th><th>最終所属</th>
          <th>ポジション</th><th>生年月日</th><th>身長/体重</th>
        </tr>
        <tr>
          <td>阿井 達也</td><td>Tatsuya AI</td><td>甲府</td>
          <td>MF</td><td>1968/04/17</td><td>169/67</td>
        </tr>
        <tr>
          <td>相川 進也</td><td>Shinya AIKAWA</td><td>岐阜</td>
          <td>FW</td><td>1983/07/26</td><td>179/74</td>
        </tr>
      </table>
    </body></html>
    """

    records = parse_sfix03_player_universe(html, retrieved_at="2026-06-26T00:00:00+00:00")

    assert len(records) == 2
    assert records[0].source_player_id == "173"
    assert records[0].name_ja == "阿井 達也"
    assert records[0].height_cm == 169
    assert records[0].weight_kg == 67
    assert records[1].source_player_id == "6825"
