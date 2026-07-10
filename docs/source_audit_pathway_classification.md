# Pathway Classification Source Audit

## Purpose

Evaluate sources that can reconstruct each player's pre-professional development pathway
(`j_club_academy` / `high_school` / `university` / `jfa_academy` / `grassroots_club` / `unknown`,
per `docs/data_collection_plan.md`) for the J.League appearance cohort.

The J.League Data Site's SFIX04 player profile page
(`https://data.j-league.or.jp/SFIX04/index?player_id={id}`) has already been confirmed to contain
only professional-era season/team history (年度別成績). It has no youth club, high school,
university, or JFA academy information. Pathway data must come from other sources, evaluated here
with the same evidentiary standard as `docs/source_audit_overseas_transfers.md`: candidate
evidence is not a final label, and every claim below is backed by a page or query actually
fetched in this session (URLs included).

## Comparison Table

| Source | Expected use | Current assessment |
|---|---|---|
| Japanese Wikipedia (来歴 prose + infobox) | Human-readable pre-pro chronology, sometimes a structured クラブ経歴/ユース table | Reliable and detailed for internationally notable players (confirmed for 3/3 sampled). Coverage for ordinary J2/J3 role players is unverified and likely much thinner. Requires full-page fetch + parsing; current `src/jfa_talent_analysis/sources/wikipedia.py` only does title search, not page content. |
| Wikidata `P69` (educated at) | Structured school/university name per player | Populated for 1 of 4 sampled players, with full elementary→university chain when present. Aggregate query: ~41% of Japanese-nationality footballer items (3,807 / 9,294) have any `P69` value, but this is a country-wide, all-era, all-gender count, not the specific J1/J2/J3 2014-2025 cohort. Gives a school *name*, not a pathway *category* — still needs a name→category mapping step. |
| Wikidata `P54` (member of sports team) | Distinguish youth/academy stints from senior stints | **Dead end for this purpose.** In all 4 sampled players, no youth-team-specific item (e.g. "Kawasaki Frontale U-18") is distinct from the senior club item; pre-pro stints are absent from `P54` except where the pre-pro entity is itself a fully modeled club (Tsukuba University's football club, in one case). |
| JFA official academy pages (jfa.jp) | Canonical JFA academy alumni list | Structured, but at cohort/institution level, not player-name level. The practical name-level alumni list is the Wikipedia category page, not the JFA site itself. |
| High-school tournament databases (koko-soccer.com, soccermagazine.jp, shindeme.com) | Digitized squad lists joinable to player names | No single source is both player-level and broadly browsable. koko-soccer.com has structured per-player pages but unconfirmed full-site browse/search; soccermagazine.jp publishes structured squad-list articles per tournament edition/school (including 前登録チーム) but requires a large per-year/per-school crawl; shindeme.com is school-level only (no player names) — dead end for player join. |
| University league sites/databases (JUFA関東, soccer-db.net) | Structured roster database | Official league sites (JUFA関東) are match/standings-oriented, not rosters. soccer-db.net has team/player URL patterns but the fetched competition page did not expose full rosters directly; would require per-team-per-year crawling at a similar scale problem as high school. |
| J-club official academy alumni pages | Per-club structured graduate list | Highly inconsistent across clubs. Kashima Antlers publishes a genuinely structured all-time promoted-players table (rare, best-in-class). Kawasaki Frontale's official academy page exposed no equivalent in what was fetched; the practical Frontale alumni source found was a fan blog, not an official page. Gamba Osaka's official pages show only current squad members. Treat as opportunistic, per-club supplementation only. |
| Transfermarkt | Structured youth-clubs field | **Excluded.** `transfermarkt.us/robots.txt` explicitly disallows `ClaudeBot`, `Claude-SearchBot`, and `anthropic-ai` (blanket `Disallow: /`). This is an unambiguous compliance signal specific to Anthropic-affiliated tooling; do not scrape, confirming and sharpening the existing caution flag in `docs/data_collection_plan.md`. |
| fansaka.info ("ファンタジーサッカー研究室", newly discovered) | Structured, ordered, multi-stage pre-pro pathway chain per player | Most promising single find of this audit. Player pages list a full ordered "過去の所属クラブ" chain spanning grassroots club → academy age-groups → high school/university → pro club in one field. No explicit terms-of-use/license/data-source page found; `robots.txt` sets no `Disallow` but does set `Crawl-delay: 30`. Coverage scope (does it include players who retired before the site's current tracking window?) is unconfirmed. Treat as unverified, Wikipedia-tier accuracy until cross-checked. |

## 1. Japanese Wikipedia Prose and Infobox

Fetched three full player articles, chosen to sample different apparent pathways:

- **松木玖生 (Matsuki Kuryu, high-school pathway)** —
  `https://ja.wikipedia.org/wiki/松木玖生`. The 来歴 prose states plainly:
  "2019年、青森山田高等学校に進学し、1年次から全国高等学校サッカー選手権大会に出場" (enrolled at
  Aomori Yamada High School in 2019, appeared in the national tournament from year one). A
  separate structured 所属クラブ list at the end of the article also names a pre-high-school
  grassroots club, "室蘭大沢FC". Pathway data appears in both prose and a structured list.

- **三笘薫 (Mitoma Kaoru, academy + university pathway)** —
  `https://ja.wikipedia.org/wiki/三笘薫`. Prose states "高校卒業まで川崎の下部組織に所属"
  (stayed in Kawasaki's youth system through high school), and a dedicated "### 筑波大学"
  subsection covers his university years. The infobox additionally lists distinct, dated rows:
  "2013-2015: 川崎フロンターレU-18" and "2016-2019: 筑波大学蹴球部", both preceding his 2020
  professional debut row. This is the richest of the three examples: prose, subsection headers,
  and a dated structured table all agree.

- **久保建英 (Kubo Takefusa, academy pathway with an overseas academy leg)** —
  `https://ja.wikipedia.org/wiki/久保建英`. Prose: "2011年8月、FCバルセロナのカンテラ（ラ・マシア）
  入団テストに日本人で初めて合格。川崎フロンターレアカデミーから移籍をしスペインに渡る" and
  "2015年3月に日本へ帰国してFC東京の下部組織に入団した". The infobox ユース table lists dated rows:
  2010-2011 川崎フロンターレU-10, 2011-2015 FCバルセロナ, 2015 FC東京U-15むさし,
  2016-2017 FC東京U-18.

All three cases are internationally notable players with unusually well-maintained articles. This
is a real limitation of the sample: it does not establish how much detail exists for an ordinary
J2/J3 player who never reached a national team or a marquee high school/university program.
Expect a strong notability gradient — the more famous the player, the more likely a structured
ユース/クラブ経歴 table exists; the least notable players may have short articles or none at all.

Infrastructure note: `src/jfa_talent_analysis/sources/wikipedia.py` currently implements only
`action=query&list=search` (title/snippet search), used by the overseas-transfer manual-review
enrichment step. It does not fetch or parse article content or infobox tables. Any pathway
extraction from Wikipedia would need a new full-page-fetch-and-parse component (e.g. via the
MediaWiki API's `action=parse` or REST `page/html` endpoint) that does not currently exist.

Terms/robots: `ja.wikipedia.org/robots.txt` allows generic crawlers to access article pages
(`Disallow` rules target `Special:` and backend `/w/` paths, not `/wiki/` articles); it blocks
known aggressive scraping tools (MJ12bot, wget, HTTrack) by name but not a well-behaved,
rate-limited crawler. Consistent with the existing search-only usage already in this repo.

## 2. Wikidata Structured Properties

Checked four players' Wikidata items directly, chosen to span pathway types:

| Player | Item | `P69` (educated at) | `P54` youth/academy distinction |
|---|---|---|---|
| 原口元気 (Haraguchi Genki) | `Q982163` | Not populated | None — only senior Urawa/Hertha/etc. |
| 遠藤航 (Endo Wataru) | `Q10526787` | Not populated | None — only senior Shonan/Urawa/etc. |
| 板倉滉 (Itakura Ko) | `Q20038711` | Not populated | None — Kawasaki Frontale listed only as senior team (2015-2018) |
| 三笘薫 (Mitoma Kaoru) | `Q44395063` | **Populated**: 川崎市立鷺沼小学校 (2003-2009), 川崎市立有馬中学校 (2010-2013), 橘学苑高等学校 (2013-2016), 筑波大学 (2016-2020) | Only entry resembling a pre-pro stint is "University of Tsukuba Football Club" (2016-2019), because that club is itself a distinct Wikidata item; no distinct item exists for "Kawasaki Frontale U-18" |

`P54` is a dead end for pre-pro pathway signal on its own: in every sampled case, senior pro clubs
are recorded, but youth/academy years are absent from `P54` unless the pre-pro team happens to
also be a separately modeled Wikidata item (as with a university's football club).

`P69` is a real signal where populated, but coverage looks uneven and skewed toward players whose
biography is unusually thorough (Mitoma's page traces back to elementary school). A direct SPARQL
aggregate query against the public endpoint:

```text
https://query.wikidata.org/sparql?query=SELECT (COUNT(DISTINCT ?person) AS ?count) WHERE {
  ?person wdt:P106 wd:Q937857 .   # occupation: association football player
  ?person wdt:P27 wd:Q17 .        # country of citizenship: Japan
}
```

returned **9,294** matching items. Adding `?person wdt:P69 ?school .` narrowed this to **3,807**
(~41%). This is a coverage ceiling estimate only — it spans all eras, all competition levels, and
both genders, not specifically the 2014-2025 J1/J2/J3 cohort this project tracks, and a populated
`P69` value is a school *name*, not yet a `pathway_category` (a separate high-school-list /
university-list / academy-list mapping step would still be required to turn "橘学苑高等学校" into
`high_school`).

The Wikidata Query Service endpoint (`query.wikidata.org/sparql`) is a public API intended for this
kind of aggregate query; no terms-of-use concern beyond Wikidata's general reuse (CC0) license and
normal rate-limiting courtesy.

## 3. JFA Official Academy Alumni

Fetched `https://www.jfa.jp/youth_development/jfa_academy/fukushima/course.html` (卒校生進路,
JFA Academy Fukushima). This page organizes graduate destinations by **graduation cohort and
gender**, not by individual name: e.g. "2023年度卒校（13期生）" lists destination institutions
such as "愛知学院大学、大阪体育大学、鹿屋体育大学、順天堂大学" and club destinations including
"VfBシュツットガルトU21（ドイツ）", without naming which graduate went where. JFA Academy Sakai
has an equivalent page (`.../sakai/course.html`, confirmed to exist via its navigation menu) that
is presumably structured the same way.

This means the official JFA page is useful only as **confirmatory context** (e.g. "this academy's
2023 cohort included students who reached a German U21 team"), not as a name-indexed alumni
roster. The practical name-level alumni list is Wikipedia's
`Category:JFAアカデミー福島出身の人物` (confirmed to contain 81 pages/entries), which is a
byproduct of Wikipedia's category system rather than anything JFA publishes directly. Any
`jfa_academy` flag built from this source would in practice be built by joining player names
against that Wikipedia category (or an equivalent category if one exists for Sakai), with the
official JFA page used only to sanity-check cohort-level claims.

## 4. High-School Football (高校サッカー) Databases

No single structured, player-level, broadly browsable database was found.

- **koko-soccer.com** (高校サッカードットコム) has genuinely structured per-player pages, e.g.
  `https://koko-soccer.com/player/2495` (松木玖生, 青森山田) with discrete fields: school,
  prefecture, graduation year, height, weight, position, dominant foot, birth date, and even a
  named middle school. URLs follow a `/player/{id}` pattern and team pages follow `/team/{code}`.
  However, whether the site can be systematically browsed/searched by school+year at scale (as
  opposed to being discovered player-by-player via search) was not confirmed in this session, and
  its scope appears oriented toward notable prospects (Premier League/Takamado Cup caliber)
  rather than a full national census of every squad player at every school.
- **soccermagazine.jp** publishes structured national-tournament squad-list articles per edition,
  e.g. `https://soccermagazine.jp/_st/s16780960` (第102回, all 48 schools), each with
  "背番号／ポジション／選手名（＆カナ）／学年／前登録チーム" — importantly including 前登録チーム
  (feeder club before high school), which would let a `grassroots_club → high_school` transition
  be reconstructed for tournament squad members. But this is one article per tournament edition
  covering only the ~48 schools that reach the national stage that year, with the article itself
  organized as 48 linked school-card pages rather than one flat table — a real but narrow slice
  (national-tournament squads only, not prefectural-qualifier-only players, and only from the
  years an aggregator chose to publish this format).
- **shindeme.com** (`https://www.shindeme.com/sports/t0032/tokyo/`) is **school-level only**:
  which schools appeared in which tournament round/year and their result, with no player names at
  all. This is a dead end for player-level pathway joins, though it could still be useful as a
  reference table of school-participation-years if a school-level feature were ever wanted.

## 5. University Football League Databases

Similarly no ready-made player-level database. The official league association site
(`https://www.jufa-kanto.jp/`, JUFA関東) is match-schedule and standings oriented. A third-party
aggregator, **Soccer D.B.** (`https://soccer-db.net/competition/index/1065/2024`, 2024 関東大学
サッカーリーグ1部), has team pages (`/competition/team/{comp_id}/{year}/{team_id}`) and player
pages (`/player/index/{id}`), and covers awards/standings/results at the league level, but the
competition-level page fetched did not itself expose full team rosters — reaching player-level
data would require crawling one team page per team per year, the same scale problem as the
high-school tournament sources. University affiliation therefore currently looks discoverable
mainly through Wikipedia prose (as in the 三笘薫 example above, which names 筑波大学 explicitly and
even quotes his graduation thesis topic) or through the fansaka.info pathway chain described below,
not through a structured university-football database.

## 6. J-Club Official Academy Alumni Pages

Spot-checked three clubs known for strong academies:

- **鹿島アントラーズ (Kashima Antlers)** —
  `https://www.antlers.co.jp/academy/all-time-players.html` is a genuinely structured, dated
  table titled 昇格選手一覧 (all-time promoted players), with columns for promotion year, player
  name, position, and the specific academy category path (e.g. "2015 鈴木優磨 FW 鹿島ジュニア
  鹿島ジュニアユース 鹿島ユース"), spanning 1995-2026. This is exactly the kind of source the
  pathway table needs, and it is a rare best-in-class example among club sites.
- **川崎フロンターレ (Kawasaki Frontale)** — the official academy profile page
  (`https://www.frontale.co.jp/academy/profile/index.html`) did not expose an equivalent alumni
  table in what was fetched (only a page title was retrievable, suggesting a JS-rendered or
  deeper-linked structure not visible to a simple fetch). The practical alumni-tracking resource
  found for this club was a fan-run blog, `kawasakisodachi.net` ("川崎そだち"), which posts
  informal monthly round-ups of academy-origin players active in J.League — useful as a lead
  generator, not as an authoritative structured source.
- **ガンバ大阪 (Gamba Osaka)** — official pages (`gamba-osaka.net/c/academy/member_youth.html`,
  `.../member_junioryouth.html`) show only **current** squad members, with no equivalent
  historical alumni list found.

Conclusion: club academy alumni pages are too inconsistent to use as a general, scalable method.
Kashima's page is worth using opportunistically; most other clubs would need per-club, ad hoc
handling, or reliance on third-party aggregation instead (see fansaka.info below).

## 7. Other Sources Found During Research

### Transfermarkt — confirmed exclusion

`https://www.transfermarkt.com` itself could not even be fetched by this session's tooling.
`https://www.transfermarkt.us/robots.txt` was fetchable and explicitly lists
`User-agent: ClaudeBot`, `Claude-SearchBot`, and `anthropic-ai` each with a blanket `Disallow: /`,
alongside blocks for GPTBot, ChatGPT-User, and PerplexityBot. This is a concrete, unambiguous
compliance signal: Transfermarkt's own robots.txt disallows Anthropic-affiliated crawling
specifically. Combined with the existing caution flag in `docs/data_collection_plan.md`
("Treat carefully; scraping and redistribution may be restricted"), this source should be
excluded outright for this project's tooling, not just deprioritized. (General web knowledge
suggests Transfermarkt profile pages do carry a structured "Youth clubs" sidebar field, but this
could not be verified in-session and is now moot given the robots.txt exclusion.)

### fansaka.info — new candidate, most promising single find

Discovered via search results for official club academy alumni. `https://www.fansaka.info/` is a
fan-run "ファンタジーサッカー研究室" (Fantasy Soccer Laboratory) fantasy-football stats site for
J-League. Two things make it stand out for pathway classification:

1. **Reverse-index by origin**, via a `?fsh=<name>` URL parameter that already works for
   grassroots clubs, academies, high schools, and universities alike, e.g.:
   - `https://www.fansaka.info/player/?fsh=青森山田高` (high school)
   - `https://www.fansaka.info/player/?fsh=川崎フロンターレU-18` (academy age-group, returned 97
     players for Kashima's equivalent query)
   - `https://www.fansaka.info/player/?fsh=筑波大` (university)
   - `https://www.fansaka.info/player/?fsh=三菱養和調布SS` (grassroots club)
   This means the site's own data model already carries something close to `pathway_category`
   granularity per affiliation, not just a single flat "origin" tag.

2. **Full ordered per-player pathway chains** on individual profile pages, e.g.
   `https://www.fansaka.info/player/J475K1/` (三笘薫) lists under "過去の所属クラブ" (past
   affiliated clubs): "さぎぬまSC、川崎フロンターレU-12、川崎フロンターレU-15、
   川崎フロンターレU-18、筑波大、川崎フロンターレ" — one field spanning grassroots club through
   both academy age-groups and university before the pro club. This is richer, single-fetch
   pathway detail than any other source checked, including Wikipedia's infobox tables, and it
   would directly support the plan's `pathway_count`/`pathway_diversity` derived features since
   multiple stages are already enumerated in sequence.

Caveats, all confirmed in-session:

- No terms-of-use, license, or data-source/methodology page was found. The homepage and help
  index (`/help/`) show only a blanket "Copyright (c) 2026 Fantasy Soccer Laboratory. All Rights
  Reserved." notice — no explicit permission or prohibition on scraping/reuse.
- `robots.txt` sets no `Disallow` paths but does set `Crawl-delay: 30`, meaning any automated
  collection must run at 30+ seconds per request — slow by design, and a real throughput
  constraint for any bulk pull.
- Coverage scope for players who retired or left J.League before the site's current tracking
  window is unconfirmed; the site is framed as a fantasy-football tool, which suggests an
  active/recent-roster bias that could leave gaps for older parts of the 2014-2025 cohort.
- As a fan-maintained site with no visible sourcing methodology, treat its accuracy as unverified
  per-player, same epistemic tier as Wikipedia — a candidate-evidence source, not a final label
  source, until spot-checked against Wikipedia/official profiles.

## Recommendation

No single source combines high coverage, high per-player detail, and low manual-review burden.
The realistic picture, most-to-least promising:

1. **fansaka.info** is the standout new find: its per-player "過去の所属クラブ" chain already
   approximates the multi-stage pathway model this project wants (grassroots → academy stages →
   high school/university → pro), in one field, for one fetch. It should be the first pilot
   target, but only after (a) trying to locate an actual about/contact/terms page beyond the
   blanket copyright notice already found, given the compliance checklist in
   `docs/data_collection_plan.md` requires checking terms of use before building a scraper, and
   (b) respecting the confirmed 30-second crawl-delay, which caps how much can be collected
   quickly.
2. **Wikidata `P69`** is a cheap, already-query-able secondary structured check (no new scraping
   infrastructure needed — the query endpoint is a public API), useful to corroborate or fill
   gaps from fansaka.info, but with real limitations: uneven coverage even at the whole-population
   level (~41%), a school *name* rather than a *pathway category* (still needs a name→category
   lookup), and confirmed-useless `P54` for detecting youth/academy stints specifically.
3. **Wikipedia prose/infobox** remains the best manual-review fallback and cross-check source
   (as it already is for the overseas-transfer audit), but building an automated extractor is new
   work (`wikipedia.py` currently only supports title search, not page content), and its detail
   level in the three examples fetched here is inflated by picking internationally notable
   players; expect much thinner coverage for the bulk of ordinary J2/J3 players.
4. **JFA academy, high-school tournament, and university-league sources** are not usable as
   scalable, name-indexed, automatable sources in their official/primary form. Their practical
   value is indirect: JFA academy alumni are better found via Wikipedia's category pages than
   JFA's own cohort-level course pages; high-school/university affiliation is better found via
   Wikipedia prose or fansaka.info than via any tournament or league database checked, all of
   which are either school-level-only (shindeme.com), fragmented per tournament-edition/per-team
   (soccermagazine.jp, soccer-db.net), or of unconfirmed browse/search scale (koko-soccer.com).
5. **Club academy alumni pages** should be used opportunistically (Kashima's structured
   all-time-players table is genuinely useful) but not relied on as a general method — most clubs
   checked (Frontale, Gamba) do not publish an equivalent.
6. **Transfermarkt is excluded**, confirmed by its own robots.txt blocking Anthropic-affiliated
   crawlers by name.

Given that even the strongest source (fansaka.info) has unverified terms, an unconfirmed
historical-coverage boundary, and no visible sourcing methodology, expect a **substantial manual
review load** — plausibly a majority of players outside the most notable tier — until the pilot
below establishes real coverage numbers. This mirrors the overseas-transfer audit's experience,
where a well-structured source (Wikidata `P54`) still left ~15-17% of candidates in manual review
even with good coverage; pathway classification has no source yet demonstrated to have Wikidata
`P54`'s combination of coverage and structure, so a higher manual-review rate should be the
working assumption, not a surprise.

**Next concrete step:** before writing any collection code, (a) look for an about/contact page on
fansaka.info beyond what was found in this session and, if one exists, check whether it says
anything about scraping or reuse; (b) pilot manual (not automated) lookups of the fansaka.info
`?fsh=` pathway chain plus a Wikidata `P69` check for a small sample (20-30 players) drawn from
the players already resolved in `data/processed/player_season_features_2014_2025_J1_J2_J3.csv`,
deliberately including both nationally notable and obscure/role-player names to test the
notability-coverage gradient flagged above; then cross-check that sample's fansaka.info/Wikidata
results against Wikipedia prose the same way the overseas-transfer audit's Wikipedia enrichment
pass was used as a manual-review aid rather than an automatic label. Only after that pilot
produces real coverage/accuracy numbers should any scraper or bulk-collection script be
considered, and only for whichever source(s) the pilot shows are both permitted and reliable
enough to reduce, rather than merely relocate, the manual review burden.
