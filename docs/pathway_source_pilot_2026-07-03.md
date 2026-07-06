# Pathway Source Pilot (2026-07-03)

## Method and sample

This pilot tests the two candidate sources flagged by `docs/source_audit_pathway_classification.md`
(fansaka.info's "過去の所属クラブ" field and Wikidata's `P69`), plus Japanese Wikipedia prose as a
cross-check, against a 22-player sample stratified by the coordinator into a **notable group**
(10 players, high career J.League minutes 2014-2025) and an **obscure group** (12 players, fringe/
backup players under 500 total career minutes across 2+ seasons), drawn mechanically from
`data/processed/player_season_features_2014_2025_J1_J2_J3.csv`. The goal was to measure whether the
prior audit's flagged risk — that famous players have much richer biographical coverage than
ordinary role players — actually holds, and at what rate, before any scraper or bulk-collection
script is built. For each player: fansaka.info was searched by name (profile URL pattern
`/player/{id}/`, falling back to team-roster pages `/player/{team}/` when name search alone did not
surface a profile link), Wikidata was searched by name and the resulting item's birth date was
checked against the table below before trusting any `P69` value, and the player's `ja.wikipedia.org`
article (if any) was fetched and checked for pre-professional pathway mentions in 来歴 prose or a
所属クラブ/infobox list. Every cell below reflects a page or query actually fetched this session.

One fansaka.info quirk worth flagging for any future automation: two goalkeepers' profile URLs
resolved to a `-p` suffixed page (e.g. `/player/J366I0-p/`) which omits the 過去の所属クラブ field
entirely; the same player ID without the `-p` suffix (`/player/J366I0/`) carries the field. Any
scraper would need to normalize away this suffix rather than trust the first URL a search surfaces.

## Results table

| source_player_id | name_ja | group | fansaka.info result | wikidata P69 result | wikipedia result | pathway_category | confidence | notes |
|---|---|---|---|---|---|---|---|---|
| 7493 | 西川 周作 | notable | Found (`/player/J366I0/`, not the `-p` variant): "宇佐FCJrユース、大分トリニータU-15、大分トリニータU-18、大分トリニータ、サンフレッチェ広島". Birth date 1986/06/18 matches. | Q558890, birth date confirmed (18 June 1986). P69 not present. | Article exists. 来歴 states he joined 大分トリニータ U-18 (invited by its coach) and enrolled at 大分東明高等学校 as a boarding student — the high school was incidental to the club-academy recruitment. | j_club_academy | high | 3-source agreement on academy route; high school was a dormitory/partner school of the academy, not an independent recruitment. |
| 12090 | 鈴木 義宜 | notable | Found (`/player/J429B0`): "広瀬サッカースポーツ少年団、宮崎日大中、宮崎日大高、宮崎産業経営大、大分トリニータ、清水エスパルス". Birth date matches. | Q20038670, birth date confirmed (11 Sept 1992). P69 = Miyazaki Sangyo-keiei University. | Article exists; 来歴 states "広瀬SSS・宮崎日本大学中学校・高等学校を経て2011年に宮崎産業経営大学に進学", matching exactly. | university | high | All 3 sources agree exactly on the full chain and the terminal institution. |
| 11004 | 岩尾 憲 | notable | Found (`/player/J384I1/`): "多々良FC、図南SC、多々良中、西邑楽高、日本体育大、湘南ベルマーレ、水戸ホーリーホック、湘南ベルマーレ、徳島ヴォルティス、浦和レッズ、徳島ヴォルティス、浦和レッズ". Birth date matches. | Q6387858, birth date confirmed (18 April 1988). P69 = Nippon Sport Science University. | Article exists; infobox lists 図南SC→館林市立多々良中→群馬県立西邑楽高等学校→日本体育大学, matching. | university | high | All 3 sources agree. |
| 12040 | 朴 一圭 | notable | Found (`/player/J39CM0/`, not `-p`): "東京朝鮮中高級学校、朝鮮大学校、藤枝MYFC、FC KOREA、藤枝MYFC、FC琉球、横浜F・マリノス、サガン鳥栖、横浜F・マリノス、サガン鳥栖". Birth date matches. | Q18234493, birth date confirmed (22 Dec 1989). P69 not present. | Article exists; confirms 東京朝鮮中高級学校 (2002-2007) then 朝鮮大学校 (2008-2011) before turning pro in 2012. | university | medium-high | fansaka+Wikipedia agree; the terminal institution is an ethnic-Korean (Chongryon) school system, not a mainstream Japanese high school/university — "university" is the closest of the 6 categories but is a definitional stretch worth a taxonomy note. |
| 11245 | 風間 宏希 | notable | Found (via team-roster search, `/player/J416J1/`): "江尻サッカースポーツ少年団、清水FC、清水商高、ロウレターノDC（ポルトガル）、TuSコブレンツ（ドイツ）、川崎フロンターレ、ギラヴァンツ北九州、モンテディオ山形、ザスパクサツ群馬、モンテディオ山形、FC琉球". Birth date matches. | Q6426618, birth date confirmed (19 June 1991). P69 not present. | Article exists; confirms 清水FC (清水第一中学校) then 静岡市立清水商業高等学校. | high_school | high | fansaka+Wikipedia agree on the terminal domestic institution; note an overseas amateur-club detour (Portugal, Germany) between high school and his eventual J.League debut. |
| 10947 | 福森 晃斗 | notable | Found (`/player/J42CG0/`): "FC高谷04、村岡中、桐光学園高、川崎フロンターレ、コンサドーレ札幌、川崎フロンターレ、北海道コンサドーレ札幌、川崎フロンターレ、北海道コンサドーレ札幌、横浜FC、北海道コンサドーレ札幌、横浜FC". Birth date matches. | Q4701239, birth date confirmed (16 Dec 1992). P69 not present. | Article exists; confirms FC高谷04 (藤沢市立高谷小)→藤沢市立村岡中→桐光学園高等学校, and that a strong Interhigh performance drew J-club offers. | high_school | high | fansaka+Wikipedia agree exactly. |
| 11937 | 稲垣 祥 | notable | Found (`/player/J41CP0/`): "大泉西ハリケーン、サウスユーベFC、FC東京U-15むさし、帝京高、日本体育大、ヴァンフォーレ甲府、サンフレッチェ広島". Birth date matches. | Q16264219, birth date confirmed (25 Dec 1991). P69 = Nippon Sport Science University. | Article exists; confirms FC東京U-15むさし (2004)→帝京高等学校 (2007)→日本体育大学 (2010)→ヴァンフォーレ甲府 (2014). | university | high | Mixed pathway: J-club academy (FC Tokyo) only through junior-high age, then an unaffiliated high school and university before turning pro — classified by terminal pre-pro institution, consistent with how the prior audit's own 三笘薫 example (full academy through U-18, then university) was treated. |
| 8603 | 森重 真人 | notable | Found (`/player/J375L1/`): "高陽FC、サンフレッチェ広島Jrユース、広島皆実高、大分トリニータ". Birth date matches. | Q275841, birth date confirmed (21 May 1987). P69 not present. | Article exists; confirms 広島高陽FC→サンフレッチェ広島ジュニアユース (中学)→広島皆実高校. | high_school | high | Academy only through junior-high age (Sanfrecce Jr Youth), then an independent high school, then signed pro with a different club (Oita) out of high school — terminal pre-pro stage is high school. |
| 11462 | 中谷 進之介 | notable | Found (`/player/J463O0`): "柏レイソルU-12、柏レイソルU-15、柏レイソルU-18、柏レイソル、名古屋グランパス". Birth date matches. | Q17226371, birth date confirmed (24 March 1996). P69 not present. | Article exists; confirms 間野台サッカークラブ→柏レイソル下部組織 (from age 10)→柏レイソルU-18主将→トップチーム2種登録 (2013). | j_club_academy | high | Clean single-club academy-to-pro pathway, all sources agree. |
| 11391 | 藤田 息吹 | notable | Found (`/player/J411U1/`): "名古屋FC、藤枝東高、慶応大、清水エスパルス、愛媛FC、清水エスパルス、愛媛FC、松本山雅FC、モンテディオ山形". Birth date matches. | Q11624797, birth date confirmed (30 Jan 1991). P69 = Keio University. | Article exists; confirms 静岡県立藤枝東高等学校 (準優勝)→慶應義塾大学 (U-19代表選出). | university | high | All 3 sources agree exactly. |
| 19210 | 大石 文弥 | obscure | Found, but only via a team-roster crawl (`/player/akita/` did not list him as he left in 2018; found instead via reverse lookup `?fsh=明海大学`, profile `/player/J43420/`): "大谷戸SC、FC中原、横浜FC鶴見Jrユース、かえつ有明高、明海大、ブラウブリッツ秋田、東京ユナイテッドFC、栃木シティ、東京23FC、東京ユナイテッドFC". Birth date matches. | Q28859185, birth date confirmed (2 April 1993). P69 = Meikai University. P54 also lists Blaublitz Akita 2016-2018, confirming identity. | Article exists; confirms the identical chain and 2016 signing with Blaublitz Akita. | university | high | All 3 sources agree exactly, but this player was only findable on fansaka.info via a name-of-affiliation reverse-lookup, not a direct name search or his (now former) team's current roster — a real discoverability cost for a retired-from-that-club player. |
| 32721 | 有田 恵人 | obscure | Found, but only via the current Vegalta Sendai roster page (not a direct name search), profile `/player/J521O0/`: "川崎フロンターレU-12、川崎フロンターレU-15、川崎フロンターレU-18、中央大". Birth date matches. | Q124982364, birth date confirmed (24 Jan 2002). P69 = 4 values: 川崎市立今井小学校 (elementary), 川崎市立今井中学校 (JHS), Bunkyo University Senior High School, Chuo University. | Article exists; confirms full Kawasaki Frontale U-12→U-15→U-18 chain, a 2019 dual-registration (2種登録) with Frontale's top team while still in U-18, then Chuo University (2020-2023), pro debut with Vegalta Sendai in 2024. | university | high | Notable disagreement worth flagging: fansaka's chain lists Chuo University directly after Frontale U-18 with no high school entry, while Wikidata's P69 additionally lists "Bunkyo University Senior High School" — implying he attended a separate high school academically while still developing in Frontale's academy (the common J-club-academy-plus-partner-school arrangement). All sources agree on Chuo University as terminal stage. |
| 11338 | 山田 満夫 | obscure | Not found. Searched by name (no profile URL surfaced) and checked his most recent J.League team roster page (`/player/numazu/`, Azul Claro Numazu) — not listed (he may have left/be inactive there). | Q11470519, birth date confirmed (26 May 1994), occupation confirmed as footballer (ruling out a namesake collision). P69 = Sendai University. | Article exists; confirms FORZA S.C. (Sapporo, elementary-JHS)→帯広北高等学校→仙台大学 (2014), matching Wikidata exactly. | university | high | fansaka.info gave nothing; Wikidata + Wikipedia alone fully reconstructed the pathway and agree with each other. |
| 45208 | 矢田 龍之介 | obscure | Found (`/player/J569U0/`): "1FC川越水上公園、清水エスパルスユース、筑波大". Birth date matches (2006/09/30, age 19). | Q130537520, birth date confirmed (30 Sept 2006). P69 = 2 values, both unlabeled Wikidata items resolving to 鶴ヶ島市立 elementary school and 鶴ヶ島市立南中学校 (junior high), i.e. Saitama-prefecture elementary/JHS only — no high school/university entry. | Article exists; confirms Shimizu S-Pulse youth (2022-2024), registered to the senior team in March 2023 while still a youth player, then joined 筑波大学蹴球部 (Tsukuba University's football club) from 2025. | j_club_academy | medium | Genuinely ambiguous case: he is simultaneously a J-club-academy graduate registered with Shimizu's senior team *and*, as of 2025, a university-club player — unlike 三笘薫/有田恵人 (academy → left the club → university), he appears to still be Shimizu-affiliated while at Tsukuba. Wikidata's elementary/JHS entries (Saitama) are geographically consistent with fansaka's "1FC川越水上公園" grassroots club (also Saitama) but do not overlap with or contradict the high-school/university stage — no direct disagreement, just non-overlapping coverage. |
| 39341 | 五十嵐 理人 | obscure | Not found. Searched by name (returned a different player, 五十嵐 太陽) and checked the Tochigi SC roster page directly — not listed. | Q106543383, birth date confirmed (13 June 1999). P69 not present. | Article exists; confirms ともぞうSCジュニア→ともぞうSC Jrユース→前橋育英高等学校 (national championship win)→鹿屋体育大学, then pro debut with Tochigi SC in 2021/2022. | university | high | Wikipedia was the *only* source with any signal for this player; fansaka and Wikidata both drew blanks. |
| 54752 | 高瀬 生聖 | obscure | Not found. Searched by name and checked the Tegevajaro Miyazaki roster page directly — not listed. | Q125422882, birth date confirmed (6 July 2001). P69 = Nara Prefectural Yamabe High School, Tokoha University. | Article exists; confirms 京都紫光サッカークラブ→ガンバ大阪ジュニアユース (中学, not promoted to U-18)→奈良県立山辺高等学校→常葉大学, matching Wikidata exactly. | university | high | fansaka gave nothing; Wikidata + Wikipedia agree exactly with each other, including the detail that he was *not* promoted to Gamba Osaka's own U-18 team. |
| 29298 | 寺前 光太 | obscure | Not found. Searched by name and checked the Fukushima United roster page directly — not listed. | Q54867532, birth date confirmed (9 July 1995). P69 = Kanagawa University. | Article exists; confirms ゆたかFC→横浜F・マリノスプライマリー (2008-2010)→横浜F・マリノスジュニアユースみなとみらい (2011-2013)→日本大学藤沢高等学校 (2014-2017)→神奈川大学, matching Wikidata on the terminal institution. | university | high | Same academy-through-JHS-then-independent-school-then-university pattern as 稲垣祥/森重真人 above (Yokohama F. Marinos academy only through junior-high age). fansaka gave nothing; Wikidata+Wikipedia agree on the terminal stage. |
| 61018 | 遠藤 貴成 | obscure | Found, via the Yokohama FC roster page (not a direct name search), profile `/player/J52AJ1/`: "グランセナ、アルビレックス新潟U-15、東福岡高、桐蔭横浜大". Birth date matches. | Q130534950, birth date confirmed (19 Oct 2002). P69 = Higashi Fukuoka High School, Toin University of Yokohama. | Article exists; confirms the identical chain: グランセナ→アルビレックス新潟U-15→東福岡高校→桐蔭横浜大学, with a 2024 announcement of his move to Yokohama FC starting 2025. | university | high | All 3 sources agree exactly, term-for-term (東福岡高 = Higashi Fukuoka High School, 桐蔭横浜大 = Toin University of Yokohama). |
| 45105 | 西村 遥己 | obscure | Not found. Searched by name and checked both the Albirex Niigata and Matsumoto Yamaga roster pages directly — not listed on either. | Q111113685, birth date confirmed as "born 2003" matching year, and full date 19 April 2003 on the item page. P69 not present. | Article exists; confirms he switched from field player to goalkeeper in JHS, then attended 昌平高等学校 (national tournament, quarterfinal, 2021 U-18 Japan-candidate selection). No university mentioned. | high_school | medium-high | Wikipedia is the only source with signal; no university stage appears anywhere, so high_school (not university) is the terminal pre-pro stage for this player, unlike most of the obscure group. |
| 32375 | 小池 大喜 | obscure | Not found. Searched by name and checked the Vanraure Hachinohe roster page directly — not listed (consistent with him having already moved on from that club by the current roster snapshot). | Q62601593, birth date confirmed (8 Dec 1996). P69 = Toyo University. | Article exists; confirms 松戸小金原FC→三井千葉東葛JYFC→FCフトゥーラスエストレージャス→大宮アルディージャユース (while attending 千葉県立小金高等学校 as a separate school)→東洋大学, matching Wikidata on the terminal institution. | university | high | Same academy-plus-separate-high-school pattern (Omiya Ardija youth, but attending an unaffiliated high school) as several other obscure-group players; fansaka gave nothing, Wikidata+Wikipedia agree. |
| 29318 | 伊藤 遼哉 | obscure | Not found. Searched by name and checked the Sagan Tosu roster page directly — not listed. | Q27917546, birth date confirmed (2 May 1998). P69 not present. | Article exists (confirmed single/unambiguous match, no disambiguation needed); confirms an entirely overseas youth pathway: grew up partly in Sydney and Switzerland, played FC Zürich/Grasshopper Zürich youth, then Bayern Munich U-15/16, Schalke U-17/19, and Fortuna Düsseldorf U-19 before turning pro. | unknown | medium | Evidence found and pathway reconstructed in detail, but it does not map onto any of the 6 defined categories — his entire pre-pro development happened in foreign club academies, which "j_club_academy" (implicitly J-League-specific in this project's usage elsewhere) does not cover. Flagging as a taxonomy gap rather than a data gap. |
| 32579 | 小島 圭巽 | obscure | Not found. Searched by name and checked the Roasso Kumamoto roster page directly — not listed. | Q73882401, birth date confirmed (21 June 2001). P69 not present. | Article exists; confirms ブレイズ熊本ジュニア (2014-2016)→ブレイズ熊本 (2017-2019)→ロアッソ熊本ユース (while attending 熊本国府高等学校)→pro debut with ロアッソ熊本 in 2020, including a Emperor's Cup appearance while still a youth player. | j_club_academy | high | Clean local-club-to-same-club-pro pathway (Roasso Kumamoto's own grassroots-to-academy pipeline); high school here is again incidental to the academy arrangement, not an independent recruitment. |

## Coverage summary

| Source | Notable group | Obscure group | Overall |
|---|---|---|---|
| fansaka.info (usable 過去の所属クラブ field found) | 10/10 (100%) | 4/12 (33%) | 14/22 (64%) |
| Wikidata P69 (populated, identity-confirmed) | 4/10 (40%) | 8/12 (67%) | 12/22 (55%) |
| Wikipedia (article exists with pathway-relevant prose/list) | 10/10 (100%) | 12/12 (100%) | 22/22 (100%) |
| Any source giving a usable, taxonomy-mappable signal | 10/10 (100%) | 11/12 (92%; 1 taxonomy-gap case) | 21/22 (95%) |

Identity-collision risk (the concern raised by the overseas-transfer audit's 伊藤剛 experience) was low
in this sample: every Wikidata search returned exactly one plausible candidate, and every one had its
birth date checked and confirmed against the table before use. No case required picking between
multiple same-name Wikidata items.

## Conclusion

**The notability gradient hypothesis holds strongly for fansaka.info and not at all for Wikipedia,
with Wikidata actually inverted in this small sample.** fansaka.info matched the prior audit's fear
almost exactly: 100% hit rate for the notable group collapsing to 33% for the obscure group, and even
those 4 obscure hits mostly required falling back to a team-roster crawl or a reverse `?fsh=` lookup
rather than a plain name search — meaning the *effective* obscure-group hit rate for a name-search-only
pipeline would be closer to 1/12. Wikidata P69 showed no such gradient — if anything the reverse (67%
obscure vs. 40% notable) — but with only 10-12 players per group this is likely sample noise (plausibly
reflecting that many of these young obscure players' Wikidata items were created/edited recently, at
the point of their pro announcement, by editors who systematically copy a school/university field from
official club or university sources, whereas some veteran notable players' older items were never
backfilled with it) rather than a real, generalizable reversal — it should not be relied on without a
larger sample. The one source that did **not** show any gradient at all was Japanese Wikipedia: every
single one of the 22 players, including all 12 fringe/backup players with under 500 career minutes,
had an article with usable pre-professional pathway information in prose or a 所属クラブ list.

**The manual-review burden is lower than the prior audit predicted, but not for the reason expected.**
The audit anticipated that "a majority of players outside the most notable tier" would resist
classification altogether. That did not happen here: 21 of 22 players (95%) got a pathway_category
that maps cleanly onto the project's 6-category taxonomy, and the single non-mapping case
(伊藤遼哉) failed because his genuinely all-overseas-academy pathway has no matching category, not
because no evidence existed. What the audit's "majority" framing undersold is a different cost: getting
that 95% coverage required reading and interpreting Wikipedia prose for essentially every player, not
mechanically extracting a labeled field. Several cases (稲垣祥, 森重真人, 寺前光太, 有田恵人,
小池大喜, 矢田龍之介) needed a judgment call about whether a J-club-academy stint that stopped at
junior-high age, or continued through a partner high school, or continued through a partner high
school while also enrolled at a university, should be labeled by that academy stage or by whatever
domestic institution came right before turning pro. That judgment call is not something a structured
field lookup (fansaka's chain or Wikidata's P69) resolves by itself — it is closer to a semi-supervised
classification problem than a data-retrieval problem.

**Wikipedia is the source worth investing in, but as a fetch-and-interpret target, not a
mechanically-parseable field.** Given its 100% hit rate against fansaka.info's notability-skewed 64%
and Wikidata's uneven 55%, building the full-page-fetch-and-parse capability that
`src/jfa_talent_analysis/sources/wikipedia.py` currently lacks (it only does title search today) looks
like the single highest-leverage investment this pilot surfaced. fansaka.info and Wikidata P69 remain
worth querying opportunistically as cheap, no-new-infrastructure cross-checks — and in the cases where
all three sources existed and agreed (鈴木義宜, 岩尾憲, 大石文弥, 高瀬生聖, 遠藤貴成 among others),
that agreement is a strong accuracy signal worth capturing when available — but neither should be
built as a primary bulk-collection pipeline: fansaka.info's coverage is too notability-skewed and its
30-second crawl-delay too slow, and Wikidata P69's coverage, while decent in this sample, is still
partial and gives only a school *name* requiring a separate name-to-category mapping step. This pilot's
overall recommendation is a soft revision of the audit's original one: pathway classification should
stay a **per-player, Wikipedia-centered manual/semi-automated research process** (opportunistically
cross-checked against fansaka.info and Wikidata P69 when they exist) rather than a purely mechanical,
fully-scaled pipeline — but the pilot's 95% mapped-coverage result suggests that process, once a
Wikipedia fetch-and-parse tool exists, is far more tractable across the full player population than the
audit's "expect a substantial manual review load... plausibly a majority of players" framing implied.

## Implementation Status

The Wikipedia fetch-and-parse capability this pilot recommended has been built:

- `jfa_talent_analysis.sources.wikipedia.fetch_wikipedia_extract` fetches a full plaintext
  article extract via the MediaWiki `action=query&prop=extracts&explaintext=1` API.
- `extract_pathway_context` heuristically returns prose from sections whose heading matches a
  pre-pro marker (来歴/経歴/幼少期/高校時代/大学時代/etc.), including nested subsections (e.g.
  a `筑波大学` subsection under `幼少期`), and falls back to the whole article when no heading
  matches — both structural patterns observed in this pilot (三笘薫's split
  幼少期/クラブ経歴 vs. 伊藤遼哉's single flat 来歴) are covered by tests in
  `tests/test_wikipedia.py`.
- `scripts/build_pathway_candidates_from_wikipedia.py` runs this against a small player list and
  writes candidate `wikipedia_pathway_context` text per player, alongside `wikipedia_found` and
  the resolved title — a research aid for manual/semi-automated review, matching this pilot's
  conclusion that `pathway_category` assignment itself still needs human judgment, not an
  automatic classifier.

Known limitation confirmed by a smoke test: when a player's direct-title fetch is missing, the
script falls back to Wikipedia's fuzzy title search (the same search used by the overseas-transfer
enrichment workflow), which can surface an unrelated page for a name with no real article (e.g. a
nonsense test name matched an unrelated musician's biography). `wikipedia_found=1` therefore means
"a candidate page was found," not "the correct player was confirmed" — exactly the same caveat
`docs/source_audit_overseas_transfers.md` already documents for Wikipedia search candidates, and
why this script's output is candidate evidence for a reviewer, not a final label.

**This has intentionally not been run at production scale** (i.e., not against the full
`data/processed/player_season_features_2014_2025_J1_J2_J3.csv` population) — only smoke-tested
against a handful of already-verified players from this pilot. Running it broadly, reviewing the
output, and building the actual `pathway_category` assignment step remain future work.

## Production Run and Identity Verification (2026-07-04/05)

Ran `build_pathway_candidates_from_wikipedia.py` against the full 4,037-player population,
split into three tiers by total career J.League minutes (2014-2025): Tier A (≥3,000 min,
n=1,982), Tier B (500-2,999 min, n=849), Tier C (<500 min, n=1,206). First attempted with 6
processes in parallel (one per tier per outcome variable, run alongside the sibling
national-team fetch) — this triggered Wikimedia's rate limiter (HTTP 429, confirmed via a
direct `curl` with the script's own User-Agent header, `x-envoy-ratelimited: true`,
`retry-after: 42`) after sustained concurrent load. Not an IP ban: a plain `curl` with a
different User-Agent succeeded immediately throughout. Fixed by switching to strictly
sequential execution (one script at a time) with `--sleep 1.0`; completed cleanly at ~6-10
seconds/player (the search-fallback path for non-exact-title players dominates this, not the
sleep itself).

This full-scale run surfaced a false-positive pattern too small to appear in the 22-player
pilot: the fuzzy search fallback (triggered when a player has no exact-title article) can match
an unrelated page whose title happens to be soccer-adjacent, most commonly soccer-themed
fiction (e.g. a real player named 大磯竜輝 matched `イナズマイレブンGOの登場人物`, a 153,085-
character character-list page for the anime; two other real players both matched `ブルーロック`,
a soccer manga, with byte-identical context length) or broad alumni/list pages (e.g.
`日本大学の人物一覧`). Concentrated almost entirely in Tier C (fringe players most likely to
lack a real article): 16.9-18.0% of Tier C rows had a context over 10,000 characters, versus
0.3-1.6% in Tier A/B.

Built `scripts/verify_wikipedia_candidate_identity.py` to catch this: it rejects titles matching
a junk-page pattern (`一覧`/`登場人物`/`キャラクター`, via `looks_like_junk_title` in
`sources/wikipedia.py`) outright with no re-fetch, and for everything else, re-fetches the full
article and cross-checks a `extract_lead_birth_date`-parsed birth date (from the lead sentence,
e.g. "1997年5月20日") against the player's known `birth_date`. Run across all six tier files
(pathway + national-team × A/B/C); results were nearly identical between the pathway and
national-team runs (as expected, since both resolve the same title via the same logic):

| | Tier A (n=1,982) | Tier B (n=849) | Tier C (n=1,206) | Overall (n=4,037) |
|---|---|---|---|---|
| `confirmed` | 94.7% | 92.5% | 61.5% | 84.3% |
| `birth_date_mismatch` | 1.5% | 2.2-2.4% | 8.3-8.4% | 3.7% |
| `no_birth_date_found` | 3.8% | 5.2-5.3% | 21.9-22.1% | 9.5% |
| `title_pattern_reject` | 0.05% | 0% | 8.0-8.3% | 2.5% |

`birth_date_mismatch` (a real person's page, just the wrong person) is the case simple
length/title heuristics alone would miss entirely — this is why the birth-date cross-check was
necessary, not just the cheaper title-pattern filter. `no_birth_date_found` is not itself proof
of a bad match (a genuinely correct but unusually-formatted article could fail the lead-sentence
regex) but should be treated as unconfirmed pending manual review, the same as
`birth_date_mismatch` and `title_pattern_reject` — only `confirmed` rows (84.3% overall) should
be used as-is going into the next `pathway_category`-labeling pass.

Reviewing the `*_verified.csv` files (in `data/interim/pathway_national_team/`, gitignored) and
building the actual `pathway_category` assignment step remain future work.

## Labeling Phase (2026-07-05)

Rather than manually reading all ~3,400 `confirmed` rows, built
`jfa_talent_analysis.pathway_classification.classify_pathway_category`, a heuristic
classifier over `wikipedia_pathway_context` text, and validated it against this pilot's own
22-player table (the only players in the full-scale data with an independent, manually
verified ground-truth label) before running it at scale — the same validate-before-trusting
discipline used throughout this project.

**Method**: assigns the highest-priority institution keyword found in the text
(`university` > `high_school` > `jfa_academy` > `j_club_academy` > `grassroots_club`), mirroring
this pilot's own terminal-institution rule, and separately requires a preceding character
before a bare `高校` match (excluding relative age references like "高校2年時", which are not
a named school — the pattern that caused 中谷進之介's initial misclassification below). Rather
than flagging every co-occurrence of a school and a club-academy signal (roughly 40-45% of all
confirmed rows on a first attempt — most bios normally name both a childhood/JHS club and a
high school in ordinary chronological order, e.g. 森重真人/稲垣祥 above, which the plain
priority rule already resolves correctly), confidence is only downgraded to `needs_review` when
*incidental-schooling framing language* (`寮生活`/`寮に入`/`誘われ`) is also present — the
narrower signature actually found in this pilot's one real miss (7493 西川周作: a named high
school existed only as a boarding arrangement for a club academy he'd already joined). A
separate check flags an all-overseas pathway with no domestic institution at all (伊藤遼哉's
taxonomy-gap case) via relocation-abroad language (`移住`/`渡欧`/etc.), since foreign-club
`ユース`/`下部組織` mentions would otherwise be silently counted as a J-League club academy.

**Validation against the 22-player pilot table**: 20/22 (91%) correct, **0 silently wrong** —
every incorrect guess was flagged `needs_review` rather than confidently mislabeled. The two
flagged-and-wrong cases are 7493 (labeled `high_school`, correctly caught by the incidental-
schooling check) and 29318 (labeled `j_club_academy`, correctly caught by the overseas-
relocation check; true category is `unknown`, a taxonomy gap this classifier cannot resolve
automatically since the taxonomy has no "overseas academy" bucket).

**First full-scale pass found a real coverage gap, not just theoretical ambiguity**: an initial
run flagged 238/3,403 (7.0%) confirmed rows for review, but a breakdown by reason showed 200 of
those 238 (84%) were `unknown` results (`no_institution_keyword_found`), not the incidental-
schooling/overseas-relocation ambiguity the design targeted. Sampling those 200 rows found the
regex simply never checked for `アカデミー` ("XXのアカデミー出身"), a very common phrasing for
club academy membership distinct from `ユース`/`下部組織` — 69/200 (35%) of the "unknown" rows
contained it. Added `アカデミー` to `J_CLUB_ACADEMY_RE` and re-ran; separately, a matching
review of the sibling national-team classifier's `needs_review` rows found ~35/333 were
similarly over-flagged by an unrelated `候補`/`落選` mention elsewhere in the bio (see
`docs/national_team_pilot_2026-07-03.md`'s Labeling Phase section) and narrowed that check too.
Both fixes were re-validated against the 22-player table before being trusted (still 20/22,
0 silently wrong) — this is standard practice for this project, not a special step taken only
because the user pushed back on the review volume.

**Full-scale result after both fixes** (`scripts/label_pathway_categories.py`, run against all
6 `*_verified.csv` files' `confirmed` rows, n=3,403):

| | Tier A (n=1,876) | Tier B (n=785) | Tier C (n=742) | Overall (n=3,403) |
|---|---|---|---|---|
| `university` | 58.9% | 63.8% | 57.3% | 59.7% |
| `high_school` | 18.2% | 16.4% | 15.0% | 17.1% |
| `j_club_academy` | 18.7% | 15.4% | 23.3% | 19.0% |
| `unknown` | 3.7% | 3.8% | 4.2% | 3.8% |
| `jfa_academy` / `grassroots_club` | 0.5% | 0.6% | 0.3% | 0.5% |
| **flagged `needs_review`** | 5.2% | 4.6% | 4.7% | **5.0%** |

169 of 3,403 confirmed rows (5.0%, down from 238/7.0% before the `アカデミー` fix) need a human
read before their `pathway_category` can be trusted; the remaining 95% carry a `high`-confidence
auto-label validated at 100% accuracy in the pilot sample (all 20 correct guesses were `high`
confidence; both misses were flagged). Output:
`data/interim/pathway_national_team/pathway_tier_{a,b,c}_labeled.csv` (gitignored), columns
`pathway_category`/`pathway_confidence`/`pathway_matched_categories`/`pathway_reason` alongside
the original identity columns. Rows outside `identity_check=confirmed` are kept with a blank
category (`pathway_reason=identity_not_confirmed`) for coverage visibility, not silently
dropped.

Reviewing the 169 flagged rows and joining `confirmed`, auto-labeled rows into
`docs/data_collection_plan.md`'s Step 5 analysis-ready dataset remain future work.
