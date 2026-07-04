# National-Team Selection Source Audit

## Purpose

Evaluate sources that can populate `docs/data_collection_plan.md`'s `national_team_selections`
table (`selection_id`, `player_id`, `year`, `category`, `competition_or_match`, `source_url`,
`retrieved_at`, with `category` in `A / U23 / U20 / U19 / U18 / U17 / U16 / U15 / university /
other`) for the 2014-2025 J1/J2/J3 appearance cohort. This is the third outcome variable needed
alongside `moved_overseas` (`docs/source_audit_overseas_transfers.md`) and pathway classification
(`docs/source_audit_pathway_classification.md`), feeding the plan's
`selected_a_national_team`/`selected_youth_national_team` outcome features and
`first_a_national_team_age` timing feature.

The J.League Data Site's SFIX04 player profile page has already been confirmed (in the pathway
audit) to contain only professional-era club season/team history. This audit re-confirms that
finding for the whole site, not just SFIX04, and evaluates JFA's own site, Wikipedia, Wikidata,
RSSSF, and other candidates, at the same evidentiary standard as the two sibling audits: candidate
evidence is not a final label, and every claim below is backed by a page or query actually fetched
in this session (URLs included).

## Comparison Table

| Source | Expected use | Current assessment |
|---|---|---|
| JFA official site (jfa.jp) | Canonical per-competition/per-year squad announcements across all categories (A and U-23/U-21/U-20/U-19/U-18/U-17/U-16/U-15) | Structured and genuinely historical (year selectors spanning 2014-2026 confirmed on multiple category pages), but organized as a browsable-by-year-and-competition archive, not a player-name-searchable database — the same structural pattern the pathway audit found for JFA's academy pages. Per-match/tournament squad pages list name and position only, no caps, no club, no shirt number. Individual player bio pages carry no cap/goal counts at all. Good primary evidence for "player X was named to squad Y in year Z," expensive to reconstruct a full per-player history from because that requires crawling many year/competition pages. |
| Wikipedia — per-player infobox `代表歴` table | Per-player summary: category, year range, appearances, goals | Reliable and detailed for notable players (遠藤航 has a full breakdown: `2016 日本U-23 3(0)`, `2021 日本U-24（OA） 6(0)`, `2015-2026 日本 73(4)`). For a lesser-selected player the same section exists but is far thinner — 矢田龍之介's `代表歴` section is just prose naming one youth tournament (`U-22日本代表 Mirabror Usmanov Memorial Cup(2025年)`) with no cap count and no formal table row. Same notability gradient the pathway pilot already documented for pathway prose. |
| Wikipedia — per-tournament squad-list articles and category pages | Structured historical squad rosters by tournament edition; name-indexed alumni lists by category | Confirmed rich but tournament-scoped: `U-17サッカー日本代表` inlines full squad tables (player, birth date, tournament appearances/goals, club) for editions from 1993 to 2025; `U-20サッカー日本代表` does the same for FIFA U-20 World Cup editions (1979-2007+) but explicitly does **not** cover AFC U-20 Asian Cup qualifying squads, only aggregate results for those. `サッカー日本代表出場選手` is a genuine all-time master table for the **A team only** — 663 players, columns Name/Birth date/Height/Appearances/Goals/Position/Debut/Final appearance, current through a June 2026 match. No youth-category equivalent master table was found; youth coverage is per-tournament-edition, not a single flat table. |
| Wikidata `P54` (member of sports team) | Distinguish national-team stints (by category) from club stints, with dates and caps | **Good news, opposite of the pathway audit's `P54` finding for youth academies.** National teams are distinct, well-populated Wikidata items (`Q170566` A team, `Q1683280` U-23, `Q3658577` U-20, `Q3044339` U-17, confirmed via direct item lookups and `wbsearchentities`), and category-level stints appear as separate `P54` statements with `P580`/`P582` start/end dates and `P1350`/`P1351` match/goal-count qualifiers. Confirmed on 遠藤航 (`Q10526787`): four distinct dated statements — U-17 (2009-2010), U-20 (2012, 4 matches/0 goals), U-23 (2015-2016, 11/2), and senior (2015-present, 72/4 as of the item's last edit). Aggregate SPARQL counts of Japanese-nationality footballer items: 579 tagged to the A team (`Q170566`), 205 to U-20 (`Q3658577`), 107 to U-23 (`Q1683280`), 87 to U-17 (`Q3044339`) — all-era, not scoped to the 2014-2025 cohort. Coverage is uneven per player: 冨安健洋's item (`Q21286402`) shows only the senior-team stint (2018-present, 23 matches) with no U-23/U-20/U-17 entries at all, despite his youth career being well documented elsewhere — so a missing youth-category `P54` statement is not proof of no selection, the same caution the overseas-transfer audit applies to missing foreign-club `P54` hints. |
| RSSSF | Historical squad-by-squad match database | **Dead end for this project's window.** `rsssf.org/tablesj/jap-intres.html` covers only 1917 through October 2005 (page states "last updated 28 Jul 2011") and lists match dates/opponents/scores only — no lineups, no player names, A team only. No 2014-2025 coverage and no youth-category coverage found. |
| J.League Data Site | Check whether any page besides SFIX04 carries representative caps | **Confirmed absent, out of scope.** The homepage's full navigation (日程・結果/順位表/お知らせ/通算データ/出場記録/選手・監督・審判) has no 代表/国際 section or link. Consistent with SFIX04's known club-only scope; the site is a J.League domestic-competition product, not a source for this table. |
| Transfermarkt | Structured "international caps" field | **Exclusion carries over unchanged.** Already confirmed in the pathway audit that `transfermarkt.us/robots.txt` blanket-disallows Anthropic-affiliated crawlers (`ClaudeBot`, `Claude-SearchBot`, `anthropic-ai`). Not re-checked here; treat as excluded project-wide. |

## 1. JFA Official Site (jfa.jp)

### Structure: browsable, not searchable

`https://www.jfa.jp/samuraiblue/` is a news/fixtures hub for the current senior squad, with no
historical squad browser on the page itself, but its "選手・スタッフ" link
(`https://www.jfa.jp/samuraiblue_2026/member/`) exposes a year dropdown running
**2026, 2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016, 2015, 2014**, plus age-category
tabs including "SAMURAI BLUE," "U-24," "U-23," and other youth levels. `jfa.jp/samuraiblue_2014/`
independently exists and resolves to 2014-era content (キリンチャレンジカップ2014, 2014 FIFA World
Cup Brazil, preparation for the 2015 Asian Cup), confirming the year-scoped archive genuinely goes
back to the start of this project's collection window rather than just labeling a single current
page differently. `jfa.jp/samuraiblue_2014/member/` itself displays one aggregate roster titled
"選手(2014年招集)・スタッフ" (players called up in 2014) rather than a list of that year's
individual competition announcements.

A second, finer-grained structure exists alongside the year-aggregate pages: per-occasion squad
announcement pages, one per match/tournament/camp, e.g.:

- `https://www.jfa.jp/samuraiblue/asiancup2023/member.html` (AFC Asian Cup Qatar 2023)
- `https://www.jfa.jp/samuraiblue/20231017/member.html` (Kirin Challenge Cup 2023)
- `https://www.jfa.jp/samuraiblue/20230909/member.html`, `20230912/member.html`,
  `20231013/member.html` (other 2023 friendlies)
- `https://www.jfa.jp/samuraiblue/worldcup_2022/2nd_q/20210330/member.html` (WC qualifying)

Fetching `asiancup2023/member.html` directly confirmed the page is plain (non-JS-dependent) HTML,
organized into GK/DF/MF-FW/STAFF sections, each entry a name pair (e.g. "板倉　滉 ITAKURA Kou") with
a hyperlink to the player's individual profile page, and no other fields — **no shirt number, no
club affiliation, no cap count, no goal count on the squad page itself.** Each occasion's URL
segment (e.g. `asiancup2023`, `20231017`) is itself a natural fit for the plan's
`competition_or_match` field.

The full category list confirmed present under `jfa.jp/national_team/` includes men's U-23, U-21,
U-19, U-18, U-17, U-16, U-15, women's NADESHIKO JAPAN plus U-20/U-17/U-16/U-15, futsal, beach
soccer, and eSports national teams — each with its own year-scoped `member/` landing page (e.g.
`u19_2026/member/`, confirmed to carry the same 2014-2026 year dropdown as the senior team page).
Fetching `u19_2026/member/` directly showed the landing page does not print a flat roster at all;
instead it lists that year's upcoming activities (e.g. "International friendly match, March 23-31,
Uzbekistan," "Maurice Revello Tournament, May 28-June 15, France") each with its own
"招集メンバーはこちら" link to a per-occasion squad page, mirroring the senior-team pattern above.

### Player profile pages carry no cap counts

`https://www.jfa.jp/samuraiblue/member/itakura_kou.html` (板倉滉's official profile) was fetched
directly and confirmed to contain only a prose bio and photo gallery — no caps, no goals, no
appearance history, no youth-team history with dates. This forecloses using JFA's own player pages
as a per-player summary source; any per-player history has to be assembled by finding and reading
every relevant occasion page instead.

### robots.txt

`https://www.jfa.jp/robots.txt` was fetched and contains only two rules: a blanket `Disallow: /`
for `MJ12bot` and a narrow `Disallow: /nadeshikohiroba/` for `Applebot`. No rule targets Anthropic
or generic well-behaved crawlers, so this is not a compliance blocker (in contrast to
Transfermarkt), but the underlying scale problem remains: reconstructing one player's full
national-team history requires locating every relevant year/category/occasion page that player
appeared on, which is a real crawl, not a lookup.

## 2. Wikipedia

### 2a. Per-player infobox `代表歴` table

`https://ja.wikipedia.org/wiki/遠藤航` was fetched directly. Its infobox contains a `代表歴`
(national-team history) table with exactly these rows:

```
2016      日本 U-23        3 (0)
2021      日本 U-24（OA）  6 (0)
2015-2026 日本              73 (4)
```

This is a clean, dated, per-category breakdown with appearances and goals in one field per row —
structurally the richest single Wikipedia field found for this outcome, directly mappable to
`category`/`year`/an implied appearance count.

By contrast, `https://ja.wikipedia.org/wiki/矢田龍之介` (a fringe/backup player from the pathway
pilot's obscure sample) has a `代表歴` section, but it is unformatted prose naming only one
tournament with no year range and no appearance/goal count: `"U-22日本代表 Mirabror Usmanov
Memorial Cup(2025年)"`. This confirms the same notability gradient the pathway pilot found for
pre-pro pathway prose: the field exists across the notability spectrum, but its structure
(table-with-numbers vs. bare tournament name) degrades for less-selected players, so an extraction
script would need to handle both a structured-table case and a free-text fallback.

### 2b. Category pages

`https://ja.wikipedia.org/wiki/Category:サッカー日本代表選手` (686 pages) is the A-team alumni
category, organized alphabetically by kana with two subcategories: a women's-team parallel category
(`サッカー日本女子代表選手`, 256 pages) and a by-tournament category
(`サッカー日本代表選手_(大会別)`). Fetching that by-tournament category directly showed seven
sub-subcategories: `AFCアジアカップ日本代表選手` (170 pages), `アジア競技大会サッカー日本代表選手`
(316), `オリンピックサッカー日本代表選手` (283), `FIFAコンフェデレーションズカップ日本代表選手`
(89), `FIFA女子ワールドカップ日本代表選手` (107), `ユニバーシアードサッカー日本代表選手` (326),
`FIFAワールドカップ日本代表選手` (122). **No distinct category-page structure for U-23/U-20/U-19/
U-17/etc. national teams was found** — a targeted search for youth-specific category pages
(`"U-17日本代表選手"`, `"U-20日本代表選手"`, `"U-23日本代表選手"`) returned only the team articles
themselves, not alumni categories analogous to the A team's. Youth-category alumni are only
discoverable through the per-tournament squad articles described next, or through the Olympic
squad category above (which is U-23-eligible but Olympic-specific, not a general U-23 alumni list).

### 2c. Per-tournament squad-list articles

`https://ja.wikipedia.org/wiki/U-17サッカー日本代表` was fetched directly and confirmed to contain
inline squad-list subsections for numerous tournament editions from 1993 to 2025 (e.g. "1993年日本
大会," "1995年エクアドル大会," "2007年韓国大会," "2011年メキシコ大会," "2013年UAE大会," "2017年
インド大会"), each formatted with columns for shirt number, position, player name, birth
date/age, tournament appearances, goals, and club at the time — genuinely structured, player-level,
squad-scoped data.

`https://ja.wikipedia.org/wiki/U-20サッカー日本代表` was fetched directly and shows the same
pattern for FIFA U-20 World Cup editions (1979 Japan, 1995 Qatar, 1997 Malaysia, 1999 Nigeria, 2001
Argentina, 2003 UAE, 2005 Netherlands, 2007 Canada with full player-level detail; 2009/2011 shown as
lineup diagrams only) but **explicitly does not include equivalent player-level rosters for AFC U-20
Asian Cup qualifying tournaments** — those only get an aggregate results table (host year, round,
W/D/L, goals), no player names. This is an important coverage gap: the article documents the
pinnacle FIFA event well but not the more frequent continental qualifiers a youth international
would actually have appeared in.

An important structural/taxonomy nuance surfaced by search results while looking for youth-category
Wikidata items: JFA's youth national teams are commonly **renamed by World Cup cycle year rather
than being permanently fixed age brackets** — e.g. the same squad progression is called the U-17
team, then renamed U-16 the year before a U-17 World Cup, then U-15 the year before that; similarly
the U-20 team is renamed U-19, then U-18, in the run-up to a U-20 World Cup cycle. This means a
`category` value like "U-18" recorded for a given year is cycle-relative, not necessarily the
player's exact chronological age bracket that year — a taxonomy caution worth carrying into any
extraction/labeling step, in the same spirit as the pathway audit's taxonomy-gap flag for an
all-overseas-academy player who didn't map onto any of the six pathway categories.

### 2d. All-time master table (A team only)

`https://ja.wikipedia.org/wiki/サッカー日本代表出場選手` was fetched directly and confirmed to be
exactly the kind of master reference table this project would want, but for the **A team only**:
663 players total, current through a late-June-2026 match, with columns Name / Birth date / Height
/ Appearances / Goals / Position / Debut / Final appearance. Sample rows quoted verbatim:

```
塩貝健人 | 2005-03-26 (21歳) | 180cm | 3   | 0  | FW | 2026年3月28日 | 2026年6月14日
後藤啓介 | 2005-06-03 (21歳) | 191cm | 5   | 0  | FW | 2025年11月14日 | 2026年6月20日
吉田麻也 | 1988-08-24 (37歳) | 189cm | 127 | 12 | DF | 2010年1月6日   | 2026年5月31日
```

No youth-category equivalent of this single flat table was found in this session; youth coverage
remains scattered across the per-tournament-edition articles in 2c.

## 3. Wikidata `P54`

Three players' items were checked directly, chosen (per the task) to span profiles: a long-time A
team regular (遠藤航), a high-profile defender with a shorter/less-detailed youth trail on Wikidata
(冨安健洋), plus aggregate SPARQL counts across the whole Japanese-footballer population.

- **遠藤航 (`Q10526787`)** — `P54` carries four distinct national-team statements, confirmed via a
  direct item fetch: **Japan national under-17 team** (2009-2010), **Japan national under-20 team**
  (2012, 4 matches/0 goals), **Japan national under-23 team** (2015-2016, 11 matches/2 goals), and
  **Japan men's national football team** (2015-present, 72 matches/4 goals, last updated 18 November
  2025). Each is qualified with distinct start/end dates and match/goal counts, exactly the shape
  the pathway audit found missing for club-academy youth stints — national teams behave completely
  differently from club-academy teams on Wikidata because national teams (at every age level) are
  themselves modeled as distinct, actively maintained items, whereas "Kawasaki Frontale U-18" is
  not.
- **冨安健洋 (`Q21286402`)** — `P54` shows a full club history (Avispa Fukuoka, Sint-Truidense,
  Bologna, Arsenal, Ajax) plus exactly **one** national-team statement: Japan men's national
  football team, starting 2018, 23 matches recorded, no end date. **No U-23/U-20/U-17/etc. entries
  appear at all**, despite Tomiyasu having a documented youth-international career — this is the
  key caution for this source: a populated A-team `P54` entry does not guarantee youth-category
  entries are also populated for the same player, so absence of a youth-category `P54` statement
  cannot be read as "never selected."
- **Item identification**: the correct Wikidata Q-ids for the relevant team items were confirmed via
  `wbsearchentities` and direct item fetches: **Q170566** ("Japan men's national football team," A
  team), **Q1683280** (U-23), **Q3658577** (U-20), **Q3044339** (U-17). (An earlier attempt to read
  qualifiers via the raw `Special:EntityData` JSON endpoint produced garbled, incorrect output from
  the fetch tool's summarization step — cross-checked and discarded once `Q4512` resolved to VfB
  Stuttgart rather than any Japan national team; the human-readable item-page fetches above are the
  reliable source for this audit, not that JSON-parsing attempt.)
- **Aggregate coverage**: a SPARQL query against the public endpoint
  (`?person wdt:P106 wd:Q937857 . ?person wdt:P27 wd:Q17 . ?person wdt:P54 <team> .`) returned **579**
  Japanese-nationality footballer items tagged to the A team (`Q170566`), **205** to U-20
  (`Q3658577`), **107** to U-23 (`Q1683280`), and **87** to U-17 (`Q3044339`). These are all-era,
  whole-population counts (not scoped to the 2014-2025 J1/J2/J3 cohort), directly analogous to the
  pathway audit's ~41% `P69` coverage-ceiling estimate — a useful order-of-magnitude signal, not a
  cohort-specific number.

`P54`'s CC0 licensing and public SPARQL endpoint carry the same no-terms-of-use-concern status
already established in the pathway and overseas-transfer audits.

## 4. RSSSF

`https://www.rsssf.org/tablesj/jap-intres.html` was fetched directly. It is explicitly an A-team-only
results archive (the page's own text notes "517 International A-Matches" as of a June 2007 count),
lists matches as `date / venue / time / opponent / score / competition` with **no player names** in
the main table (a sample row: `"04.08.1936 Berlin GER 18:00 Sweden 3-2 W XI. Olympic Games"`), and
states it was last updated 28 July 2011, with coverage running only from 1917 through October 2005.
This is a hard dead end for the project's 2014-2025 window regardless of category: too old, no
lineups, and A-team-only even within its covered years. No further RSSSF page was found or checked
for youth categories, since the base coverage-period problem already rules the source out for this
project.

## 5. J.League Data Site

`https://data.j-league.or.jp/` was fetched directly. Its full top-level navigation is
日程・結果 (Schedule & Results) / 順位表 (Standings) / お知らせ (Announcements) / 通算データ
(Overall Data) / 出場記録 (Appearance Records) / 選手・監督・審判 (Players, Managers, Referees) —
no link or section referencing 代表 (national team) or 国際 (international) anywhere. This confirms,
at the whole-site level rather than just for SFIX04, that the J.League Data Site is not a viable
source for this table; it is a domestic-league-only product.

## 6. Other Sources

No new promising source (analogous to the pathway audit's fansaka.info discovery) turned up during
this session's searches. Transfermarkt's project-wide exclusion (confirmed in the pathway audit via
its robots.txt blocking Anthropic-affiliated crawlers by name) was not re-checked here but carries
over unchanged; a Transfermarkt profile's "international caps" sidebar field would in any case be
subject to the same exclusion as its "Youth clubs" field.

## Recommendation

**Wikidata `P54` is the strongest first pilot target for this table**, for the same structural
reason it worked well for the overseas-transfer audit and poorly for the pathway audit: unlike
club-academy youth teams, Japan's national teams at every age level are themselves distinct,
actively maintained Wikidata items, so `P54` naturally carries category, start/end dates, and
match/goal qualifiers in one query-able field — no name→category mapping step is needed the way
`P69` school names required one in the pathway audit. Expected split:

- **Likely automatable**: for players with a populated Wikidata item, extracting `category` +
  `year` (from `P580`/`P582`) + rough appearance count (`P1350`) directly from `P54` national-team
  statements, the same way `scripts/audit_wikidata_reappearance_candidates.py` already reads foreign
  `P54` stints. This should reconstruct A-team selection well (579 Japanese players tagged
  all-era) and youth-team selection less completely (87-205 tagged per category checked,
  all-era), with the same caveat as 冨安健洋's case: a missing youth-category statement is not
  proof of no selection, only proof the item wasn't (yet) populated with it.
- **Manual review / cross-check tier**: Wikipedia's per-player `代表歴` infobox field (rich for
  notable players like 遠藤航, thin free text for fringe players like 矢田龍之介) and the
  per-tournament squad-list articles (U-17/U-20 team pages, the A-team master table) are strong
  corroboration sources but are structurally uneven — tournament articles cover only the
  headline event per cycle (e.g. FIFA U-20 World Cup, not AFC U-20 Asian Cup qualifiers) — and
  should be used the way the overseas-transfer audit uses Wikipedia: candidate evidence and
  manual-review aid, not a primary bulk source.
- **JFA's own site** is the highest-credibility source per individual claim but the most
  labor-intensive to use at scale: it is genuinely a 2014-2026 archive (confirmed via year selectors
  and a live `samuraiblue_2014/` page), but organized by year/category/competition, not by player
  name, and per-competition squad pages carry no cap counts — so it is best reserved for verifying
  specific Wikidata-flagged selections (analogous to how club official profiles are used in the
  overseas-transfer audit) rather than for broad initial collection.
- **RSSSF and the J.League Data Site are confirmed dead ends** for this table and need no further
  investigation; Transfermarkt remains excluded project-wide.

**Single next concrete step**: before writing any collection code, run a small manual pilot (in the
same style as `docs/pathway_source_pilot_2026-07-03.md`) of 15-20 players stratified by notability
and by whether they are known to have any national-team selection, checking Wikidata `P54`
national-team statements against Wikipedia's `代表歴` field and, for a few cases, the relevant JFA
per-year member page, to measure real coverage/agreement rates for this specific cohort before
building any `national_team_selections`-building script — mirroring how the pathway pilot's 22-player
sample, not the audit's abstract source list alone, produced the real coverage numbers that shaped
the pathway recommendation.
