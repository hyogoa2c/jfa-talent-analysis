# National-Team Selection Source Pilot (2026-07-03)

## Method and sample

This pilot tests the two candidate sources flagged by
`docs/source_audit_national_team_selection.md` — Wikidata `P54` national-team statements and
Wikipedia's per-player `代表歴` infobox field/prose — against the **same 22-player sample** used in
`docs/pathway_source_pilot_2026-07-03.md`, so results are comparable player-for-player across both
outcome variables. The sample is stratified into a **notable group** (10 players, high career
J.League minutes 2014-2025) and an **obscure group** (12 players, fringe/backup players under 500
total career minutes across 2+ seasons), drawn mechanically, not cherry-picked.

Because the pathway pilot already identity-confirmed a Wikidata Q-id and birth date for all 22
players in this sample, this pilot reused those same Q-ids rather than re-searching by name, and
re-fetched each item page checking specifically for `P54` (member of sports team) statements
pointing to any Japan national-team item — not just the four confirmed in the audit
(Q170566 A team, Q1683280 U-23, Q3658577 U-20, Q3044339 U-17) but any other national-team-category
item encountered. Every one of the 22 birth dates matched the table below again on this refetch, so
no identity-collision risk applied. Separately, each player's `ja.wikipedia.org` article was fetched
and checked for the `代表歴` infobox field or any prose mentioning national-team selection (matching
the pathway pilot's per-player fetch approach, applied here to a different field). 矢田龍之介's known
Wikipedia mention (`U-22日本代表 Mirabror Usmanov Memorial Cup(2025年)`) was re-confirmed as part of
this normal process, not skipped.

As a side check on the audit's four confirmed national-team Q-ids, this pilot searched Wikidata
directly for the other youth categories named in the project's taxonomy. **Q23978196** ("Japan
national under-19 association football team") and **Q23978195** ("Japan national under-18 football
team") do exist as distinct items, but the U-18 item carries only 3 statements total (essentially
unpopulated — no roster of linked players), and no U-16 or U-15 team item exists on Wikidata at all
(a direct search returns zero results and offers to create one). This is consistent with this
pilot's finding, below, that no player in the sample had a `P54` statement for any category outside
A/U-23/U-20/U-17.

## Results table

| source_player_id | name_ja | group | wikidata P54 result | wikipedia 代表歴 result | any_national_team_selection | categories found | confidence | notes |
|---|---|---|---|---|---|---|---|---|
| 7493 | 西川 周作 | notable | Q558890 confirmed (b. 18 June 1986). P54: Japan U-20 (2004-2005, 4/0), Japan U-23 (2007-2008, 8/0), Japan A team (2009-present, no end date). | 代表歴 table: 2005 U-20 4(0), 2008 U-23 3(0), 2009-2021 日本 31(0). | yes | A, U23, U20 | high | Sources agree on all three categories and roughly on years; minor count/year discrepancies (Wikidata's U-20 spans 2004-2005 vs Wikipedia's single year 2005; Wikidata's A team has no end date vs Wikipedia's 2009-2021/31 caps) are the kind of drift expected between an actively-edited item and a possibly-stale infobox snapshot. |
| 12090 | 鈴木 義宜 | notable | Q20038670 confirmed (b. 11 Sept 1992). P54: only one club stint (Oita Trinita), no national-team statement. | No `代表歴` field found; no national-team mention anywhere in the article. | no | — | high | Both sources agree on absence — a genuine "never selected" case among the notable group, not a data gap. |
| 11004 | 岩尾 憲 | notable | Q6387858 confirmed (b. 18 April 1988). P54: three club stints (Shonan Bellmare, Mito HollyHock, Tokushima Vortis), no national-team statement. | No `代表歴` field; no mention anywhere in the article. | no | — | high | Both sources agree on absence. |
| 12040 | 朴 一圭 | notable | Q18234493 confirmed (b. 22 Dec 1989). P54: one club stint (Yokohama F. Marinos), no national-team statement. | No `代表歴` field. Prose notes he acquired Japanese citizenship in November 2022 and expressed interest in joining the Japan national team — i.e. an aspiration, not a selection. | no | — | high | Both sources agree there is no confirmed selection as of the fetched content; the citizenship/aspiration note is a useful timing signal (he was not naturalized long enough, as of the article's content, to have been selected) but is not evidence of selection itself. |
| 11245 | 風間 宏希 | notable | Q6426618 confirmed (b. 19 June 1991). P54: two overseas amateur-club stints plus two domestic club stints (Kawasaki Frontale, Giravanz Kitakyushu), no national-team statement. | Dedicated `代表歴` section: 2006年 U-15日本代表, 2007年 U-16日本代表, 2008年 U-17日本代表, 2009年 U-18日本代表, 2010年 U-19日本代表 (no appearance/goal counts given for any). | yes | U15, U16, U17, U18, U19 | medium-high | Sharp disagreement: Wikidata shows zero national-team signal for a player Wikipedia documents across five consecutive youth categories. This is the single richest youth-selection record in the sample and it is entirely invisible to `P54`. |
| 10947 | 福森 晃斗 | notable | Q4701239 confirmed (b. 16 Dec 1992). P54: two club stints (Consadole Sapporo, Kawasaki Frontale), no national-team statement. | No `代表歴` field; no mention anywhere in the article. | no | — | high | Both sources agree on absence. |
| 11937 | 稲垣 祥 | notable | Q16264219 confirmed (b. 25 Dec 1991). P54: one club stint (Ventforet Kofu), no national-team statement. | `代表歴`: "2021- 日本 4 (3)" — A team since 2021, 4 caps, 3 goals (as of a July 2025 infobox snapshot). | yes | A | medium-high | Wikidata is silent despite a documented, dated, cap-and-goal-qualified senior call-up on Wikipedia — a second case (with 風間宏希 and 中谷進之介 below) where Wikidata's P54 completely misses a real selection Wikipedia records cleanly. |
| 8603 | 森重 真人 | notable | Q275841 confirmed (b. 21 May 1987). P54: two club stints (FC Tokyo, Oita Trinita) plus Japan U-23 (2008, 3/0) and Japan A team (2013-present, no end date; a 2015 AFC Asian Cup qualifier reference also attached). | `代表歴`: 2004 U-17サッカー日本代表, 2005-2007 日本 U-18/19/20 (3/0 aggregated), 2008 日本 U-23 (3/0), 2013-2017 日本 (41/2). | yes | U17, U18, U19, U20, U23, A | high | Best cross-source agreement in the sample: U-23 2008 (3 matches/0 goals) and the A-team start year (2013) match exactly across both sources. Wikipedia additionally documents U-17/U-18/U-19/U-20 stints entirely missing from Wikidata's `P54` — again the pattern of Wikidata capturing only a subset (here A + U-23) of a fuller Wikipedia-documented career. The 2005-2007 "U-18/19/20" aggregation on Wikipedia reflects the audit's flagged taxonomy caution that JFA renames the same age cohort by World Cup cycle year. |
| 11462 | 中谷 進之介 | notable | Q17226371 confirmed (b. 24 March 1996). P54: one club stint (Kashiwa Reysol), no national-team statement at all. | Rich `代表歴`: 2011 U-15 (8 apps), 2012 U-16 (9 apps), 2014 U-19 (10/1), 2015 U-22 (1 app), 2016 U-23 (1 app), 2021-2022 日本 (senior A, 5/0, debut noted as 31 March 2021 vs. Mongolia). | yes | U15, U16, U19, U22 (non-standard label), U23, A | high | The starkest Wikidata/Wikipedia gap in the whole sample: Wikidata's item has zero national-team `P54` statements — not even a hint — for a player with a six-category, dated, cap-counted Wikipedia record including full senior-team caps. If this pilot had relied on Wikidata alone, this player's entire national-team history (A team included) would have been recorded as "no selection," a false negative, not a true negative. |
| 11391 | 藤田 息吹 | notable | Q11624797 confirmed (b. 30 Jan 1991). P54: one club stint (Ehime FC), no national-team statement. | `代表歴`: U-19日本代表 — AFC U-19選手権2010; also 全日本大学選抜 (2010) and 関東大学選抜 (2011) (all-Japan and Kanto university select teams). | yes | U19, university | medium-high | Wikidata silent again. The university-select entries map onto the project's `university` category value in `national_team_selections`, distinct from a school-pathway `university` pathway_category — worth keeping the two uses of "university" clearly separated in any collection script. |
| 19210 | 大石 文弥 | obscure | Q28859185 confirmed (b. 2 April 1993). P54: four domestic club stints, no national-team statement. | No `代表歴` field; no mention anywhere. | no | — | high | Both sources agree on absence. |
| 32721 | 有田 恵人 | obscure | Q124982364 confirmed (b. 24 Jan 2002). P54: **Japan national under-17 football team (2018-2019)**, plus club stints (Kawasaki Frontale, Chuo University FC, Vegalta Sendai). | `代表歴`: "2018-2019 日本 U-17 1" — 1 appearance. | yes | U17 | high | The only case in the entire 22-player sample where both sources independently carry a national-team statement for an obscure/fringe player, and they agree exactly on category and year range. Direct counter-example to the notability-gradient hypothesis for this specific outcome variable. |
| 11338 | 山田 満夫 | obscure | Q11470519 confirmed (b. 26 May 1994). P54: one club stint (Matsumoto Yamaga FC), no national-team statement. | No `代表歴` field; no mention anywhere. | no | — | high | Both sources agree on absence. |
| 45208 | 矢田 龍之介 | obscure | Q130537520 confirmed (b. 30 Sept 2006). P54: one club stint (Shimizu S-Pulse, shirt number 45), no national-team statement. | `代表歴`: "U-22日本代表 — Mirabror Usmanov Memorial Cup(2025年)" — confirms the known sanity-check case; no appearance/goal count given. | yes | U22 (non-standard; nearest taxonomy fit is U-23 or "other") | medium | Confirms/expands the task's known sanity-check case: Wikipedia is the only source with signal, and the category itself ("U-22") is not one of the project's eight age-bracket values, echoing the audit's note that JFA's youth cohorts are sometimes labeled by an interim age relative to a World Cup cycle rather than a fixed bracket — a taxonomy mapping decision, not a data gap. |
| 39341 | 五十嵐 理人 | obscure | Q106543383 confirmed (b. 13 June 1999). P54: **no statements of any kind** (not even a club team) — the emptiest Wikidata item in the sample. | No `代表歴` field; no mention anywhere. | no | — | high | Both sources agree on absence, though the total absence of any P54 data here (not just national-team) suggests this item is simply thin, not specifically checked-and-negative. |
| 54752 | 高瀬 生聖 | obscure | Q125422882 confirmed (b. 6 July 2001). P54: two club stints (Tokoha University FC, Tegevajaro Miyazaki), no national-team statement. | No `代表歴` field. A separate `選抜暦` (selection history) section lists 2017 Kokutai (National Athletic Meet) Nara Prefecture youth selection and a 2023 Denso Cup East selection. | no | — | high | The `選抜暦` entries are prefectural/regional select-team honors, not JFA national-team call-ups, so they do not satisfy this table's category taxonomy (A/U23/.../university/other refers to Japan national teams, not inter-prefectural representative teams) — recorded as "no" rather than miscounted as a youth-category hit. |
| 29298 | 寺前 光太 | obscure | Q54867532 confirmed (b. 9 July 1995). P54: one club stint (Fukushima United FC), no national-team statement. | No `代表歴` field; no mention anywhere. | no | — | high | Both sources agree on absence. |
| 61018 | 遠藤 貴成 | obscure | Q130534950 confirmed (b. 19 Oct 2002). P54: one club stint (Yokohama FC, shirt number 39), no national-team statement. | No `代表歴` field; no mention anywhere. | no | — | high | Both sources agree on absence. |
| 45105 | 西村 遥己 | obscure | Q111113685 confirmed (b. 19 April 2003). P54: **no statements of any kind**, not even a club team. | No `代表歴` field, but prose states: "2021年にU-18日本代表候補に選出された" (selected as a U-18 Japan national-team **candidate** in 2021) — no appearance/goal count, and "候補" (candidate/nominee) does not confirm an actual squad call-up or match. | unclear | U18 (candidate-status only) | low-medium | The one genuinely ambiguous case in the sample: Wikipedia signals youth-national-team interest/candidacy but not confirmed selection, and Wikidata has zero corroborating or contradicting data (its item is otherwise empty). Recorded as "unclear" rather than yes or no, per the task's guidance. |
| 32375 | 小池 大喜 | obscure | Q62601593 confirmed (b. 8 Dec 1996). P54: one club stint (Blaublitz Akita), no national-team statement. | No `代表歴` field; no mention anywhere. | no | — | high | Both sources agree on absence. |
| 29318 | 伊藤 遼哉 | obscure | Q27917546 confirmed (b. 2 May 1998). P54: one club stint (Sagan Tosu), no national-team statement. | `代表歴`: U-16日本代表 — 第11回デルレナシオネス国際大会 (2014); U-17日本代表 — 第22回バーツラフ・イェゼック国際ユース大会 (2015). | yes | U16, U17 | medium-high | This is the pathway pilot's own taxonomy-gap player (entirely overseas club-academy pathway: Zurich, Bayern Munich, Schalke, Fortuna Düsseldorf youth) — yet he still received Japan youth national-team call-ups per Wikipedia, entirely missed by Wikidata. A useful cross-reference: pathway-classification difficulty and national-team-selection evidence are independent problems for this player, not correlated ones. |
| 32579 | 小島 圭巽 | obscure | Q73882401 confirmed (b. 21 June 2001). P54: **no statements of any kind**, not even a club team. | No `代表歴` field; no mention anywhere. | no | — | high | Both sources agree on absence. |

## Coverage summary

| Source | Notable group | Obscure group | Overall |
|---|---|---|---|
| Wikidata P54 (national-team statement found, identity-confirmed) | 2/10 (20%: 西川周作, 森重真人) | 1/12 (8%: 有田恵人) | 3/22 (14%) |
| Wikipedia (`代表歴` field or prose with a national-team mention, including the one "candidate"-only case) | 6/10 (60%) | 4/12 (33%, incl. 1 unclear) | 10/22 (45%) |
| Any confirmed national-team selection (yes) | 6/10 (60%) | 3/12 (25%) | 9/22 (41%) |
| Unclear (candidate/ambiguous signal only) | 0/10 | 1/12 (8%) | 1/22 (5%) |
| No evidence found (either source) | 4/10 (40%) | 8/12 (67%) | 12/22 (55%) |

Identity-collision risk was zero in this sample: every one of the 22 Wikidata Q-ids reused from the
pathway pilot re-confirmed the same birth date on this refetch, and every Wikipedia article fetched
resolved unambiguously to the correct player (no disambiguation needed).

## Conclusion

**The notability gradient shows up here too, but it looks like a true population effect, not a
source-coverage artifact — the opposite diagnosis from fansaka.info in the sibling pilot.** The
pathway pilot found fansaka.info's coverage collapsing from 100% (notable) to 33% (obscure) because
the *source itself* was harder to find fringe players in (needing team-roster crawls or reverse
lookups instead of a name search). Nothing analogous happened here: every Wikidata and Wikipedia
lookup in this pilot succeeded on the first attempt for every player, notable or obscure — the drop
from 60% (notable) to 25% (obscure) confirmed-selection rate is not a source-discoverability problem,
it is the expected shape of the real world. Players with enough ability to log the top-10 J.League
minutes in this cohort are simply more likely to have been called into a Japan youth or senior squad
at some point than fringe/backup players with under 500 career minutes — the outcome variable itself
is correlated with the stratification variable (career minutes), which is exactly the causal
relationship this project's research question wants to measure, not a data-collection defect to fix.
The 8/12 "no evidence found" obscure-group players are very likely true negatives (never selected),
not missing data, mirroring this pilot's confirmation of the audit's caution against reading a missing
statement as a certain non-selection while still landing on "genuinely never selected" as the most
probable explanation for most of them.

**Wikidata `P54`'s structural advantage (distinct, actively-maintained national-team items) does
not translate into good real-world coverage on this cohort — it under-performs Wikipedia by a wide
margin.** The audit's optimism about `P54` was about *data shape* (categories/dates/counts arrive
as clean qualifiers when present), and that shape held up in the three hits this pilot found
(西川周作, 森重真人, 有田恵人 all show exactly the kind of dated, count-qualified statement the audit
described). But *presence* is the real bottleneck: only 3 of 22 players (14%) had any national-team
`P54` statement at all, against 9 confirmed selections found through Wikipedia (41%) — meaning
Wikidata missed roughly two-thirds of the real selections this sample's Wikipedia articles document,
including a case (中谷進之介) with a full six-category history and confirmed senior-team caps that
`P54` shows nothing for. This is a materially worse miss rate than the pathway pilot found for `P69`
(55% overall, with the "reversed" obscure/notable pattern the pilot flagged as likely noise) — here
Wikidata is simply the weaker of the two structured sources, at every notability tier, for this
specific variable.

**Wikipedia is the more useful primary source for this table too, echoing the pathway pilot's
conclusion, but with a smaller coverage gap over Wikidata than it had over fansaka.info, and a real
manual-judgment cost.** 45% of players had some Wikipedia national-team signal versus Wikidata's 14%,
and the confirmed-yes rate (41% overall) tracks almost entirely with Wikipedia's coverage rather than
Wikidata's. But unlike the pathway pilot's 100%-flat Wikipedia hit rate for pre-pro pathway prose,
national-team selection prose is genuinely uneven by player, not just by notability tier — it is
absent for most players in both groups (12/22 "no evidence," the majority result), which is expected
and appropriate given most J-League players are never selected, not a coverage failure to fix.
Where Wikipedia does carry a signal, format varies from a clean multi-row table with caps and goals
(遠藤航-style, seen partially in 西川周作/森重真人/中谷進之介) down to a single unlabeled tournament
name with no year or count (矢田龍之介, echoed by 伊藤遼哉's and 藤田息吹's tournament-named-only
entries) — a reviewer has to read and interpret prose rather than mechanically parse a field, the
same cost the pathway pilot found for pre-pro context.

**The manual-review burden looks light enough to scale soon for a Wikipedia-then-Wikidata-cross-check
pass, but not light enough to skip human review of "no evidence" cases before labeling them true
negatives.** Every one of the 22 rows in this pilot's table was resolvable to a clear yes/no in a
single fetch pair per player, with only one genuinely ambiguous case (西村遥己's "U-18候補"/candidate
wording) requiring a judgment call rather than a mechanical read — a much lower ambiguity rate than
the pathway pilot's pathway-stage judgment calls (six players needed a "which stage counts as
terminal" decision there). That said, this pilot did not touch the JFA per-occasion squad pages the
audit flagged as the highest-credibility but most labor-intensive source, and this sample never
needed them: no case here was left genuinely unresolved by Wikidata+Wikipedia together (西村遥己's
"unclear" status is a real ambiguity in the *source text itself*, not a case JFA squad pages would
obviously resolve without directly checking whether he appears on the specific 2021 U-18 squad
announcement, which was out of scope for this pilot). The practical implication for the audit's
recommendation: **a Wikidata-first pipeline (as the audit's phrasing "P54 is the strongest first
pilot target" implied) would be the wrong design for this variable** — Wikidata should be queried as
a fast, cheap corroboration check (as it did for 森重真人 and 有田恵人, where its data shape earns
its keep), but Wikipedia has to be the primary fetch-and-read source, exactly mirroring the pathway
pilot's revised recommendation for that variable. Building the `national_team_selections` table can
likely proceed at moderate scale on Wikidata + Wikipedia alone without JFA squad-page crawling as a
prerequisite, with the caveat that the "no evidence found" majority (55% here) should be spot-checked
against JFA's per-occasion pages for a subsample before being trusted at full population scale, since
this pilot's sample size (22) is too small to rule out a meaningful false-negative rate among the
"no" players the way it could confidently classify the "yes" players it did find.

## Implementation Status

The Wikipedia fetch tool for this variable has been built, reusing the pathway tool's
infrastructure:

- `extract_sections_by_heading` in `jfa_talent_analysis.sources.wikipedia` was factored out of
  `extract_pathway_context` as a shared, heading-set-parameterized helper.
- `extract_national_team_context` applies it against a `NATIONAL_TEAM_SECTION_HEADINGS` set
  (`代表歴`, `代表経歴`, `日本代表`) — both real heading spellings confirmed in this pilot
  (中谷進之介 uses `代表歴` with nested `出場大会`/`試合数` subsections; 遠藤航 uses a flat
  `代表経歴`). Confirmed by direct fetch that the per-category caps/goals **infobox** field this
  pilot also read (via a rendered-page tool, not the plaintext extract API) is NOT captured by
  this function — only prose sections are. The `代表歴`/`代表経歴` prose sections turned out to
  carry the same substantive detail as the infobox in both checked cases, including 中谷進之介's
  full six-category history, so this gap did not cost real coverage in this pilot's spot checks,
  but it means a future reviewer should not expect exact cap/goal numbers to always be present in
  this tool's output the way the infobox sometimes states them.
- `resolve_wikipedia_title_and_extract` was factored out of the pathway script into
  `jfa_talent_analysis.sources.wikipedia` as a shared title-resolution helper (direct no-space
  title first, then fuzzy search fallback), now used by both
  `scripts/build_pathway_candidates_from_wikipedia.py` and the new
  `scripts/build_national_team_candidates_from_wikipedia.py`.
- Tests in `tests/test_wikipedia.py` cover both real heading patterns found in this pilot.
- Smoke-tested against 中谷進之介 (rich case, correctly extracted), 大石文弥 (no evidence case,
  correctly falls back to the whole article since no matching heading exists), and a nonexistent
  name (correctly falls through to fuzzy search, which surfaces an unrelated page — the same known
  limitation already documented for the pathway tool).

**This has intentionally not been run at production scale.** Running it against the full player
population, cross-checking against Wikidata P54, and building the actual
`national_team_selections` table remain future work — as does the JFA per-occasion squad-page
spot-check this pilot recommends before trusting "no evidence" rows at scale.

## Production Run and Identity Verification (2026-07-04/05)

Run at full population scale (4,037 players, same three career-minutes tiers as the sibling
pathway run) alongside `build_pathway_candidates_from_wikipedia.py` — see
`docs/pathway_source_pilot_2026-07-03.md`'s "Production Run and Identity Verification" section
for the full account of what happened (an initial 6-way-parallel attempt hit Wikimedia's rate
limiter, HTTP 429, fixed by switching to sequential execution) and the false-positive pattern
discovered at scale (the search fallback matching soccer-themed fiction or alumni-list pages for
players with no real article, concentrated in Tier C). That account and the
`verify_wikipedia_candidate_identity.py` tool apply identically here, since both scripts share
the same `resolve_wikipedia_title_and_extract` title-resolution logic — the two runs' identity
results were consistent to within 1-2 rows per tier (a birth-date lead sentence occasionally
fails to parse on one run's fresh re-fetch of the exact same page but not the other's, likely a
transient rendering/whitespace difference between requests, not a systematic issue). Same
headline numbers apply: 84.3% `confirmed` overall (94.7% Tier A, 92.5% Tier B, 61.5% Tier C),
with the remainder needing manual review before being trusted as either a real "candidate found"
or a genuine "no evidence" case.

Reviewing the `national_team_tier_*_verified.csv` files (gitignored,
`data/interim/pathway_national_team/`) and building the actual `national_team_selections` table
remain future work.

## Labeling Phase (2026-07-05)

Built `jfa_talent_analysis.national_team_classification.classify_national_team_selection`,
a heuristic classifier over `wikipedia_national_team_context` text, following the same
validate-against-the-pilot-table-before-scaling discipline as the sibling pathway classifier
(see `docs/pathway_source_pilot_2026-07-03.md`'s Labeling Phase section for the shared
methodology and reasoning).

**Method**: splits context into sentences/lines and, per sentence, looks for a `U-NN`
bracket (mapped to a standard category when `NN` is in `{15,16,17,18,19,20,23}`, else
`other`, per `docs/data_collection_plan.md`'s schema), a `大学選抜` mention (→ `university`),
or a bare `日本代表`/`A代表`/`国際Aマッチ` line (→ `A`). Two corrections proved necessary
after the first pass against the pilot table: (1) a bare `U-NN` only counts if `代表` appears
in the *same sentence* — otherwise it is usually a club's own youth age-group team (e.g.
"`U-18`には昇格せず", 高瀬生聖/遠藤貴成's false-positive pattern, both silently miscounted as
`yes` before this fix); (2) any sentence containing negation language (`落選`/`選外`/`メンバー
から外れ`/etc.) is excluded entirely, since Wikipedia prose narrates confirmed selections and
near-misses in the same paragraph (中谷進之介's "`2013 FIFA U-17ワールドカップのメンバーから
は落選した`"). `候補`(candidate-only) language yields `unclear` rather than `yes` (西村遥己's
case), and any negation or candidate wording anywhere in the context downgrades confidence to
`needs_review` — the `categories` list stays best-effort even when `any_national_team_selection`
is high-confidence, since dense narrative prose can still miss or misattribute an individual
bracket.

**Validation against the 22-player pilot table**: 21/22 (95%) correct on
`any_national_team_selection`; the one mismatch (29298 寺前光太, classifier says `unclear`
where the pilot's table says `no`) is arguably a correction of an oversight in the original
pilot's manual read — its context contains "`全日本大学選抜候補に選出される`" (a real
candidate-only mention analogous to 45105's already-`unclear` case), which the pilot's own
"no mention anywhere" note did not account for — and it is flagged `needs_review` either way.

**First full-scale pass over-flagged on unrelated negation/candidate mentions**: an initial run
flagged 333/3,403 (9.8%) rows, but checking whether the negation/candidate word actually
co-occurred with a selection-relevant token found ~35 rows were flagged solely because an
unrelated `候補`/`落選`/etc. word appeared *elsewhere* in the bio — e.g. 福森直也's "`ガンバ
大阪ジュニアユースのセレクションを受けるが落選`" describes missing a *club academy* trial, not
a national-team decision, yet it tripped the review flag for his entire row. Narrowed both
`NEGATION_RE` and `CANDIDATE_RE` to only count when the same sentence also contains `代表` or
`大学選抜`, re-validated against the 22-player table (still 21/22, same single arguable
mismatch), and re-ran.

**Full-scale result after the fix** (`scripts/label_national_team_selections.py`, run against
all 6 `*_verified.csv` files' `confirmed` rows, n=3,403 — the same population as the pathway
labeling pass):

| | Tier A (n=1,876) | Tier B (n=785) | Tier C (n=742) | Overall (n=3,403) |
|---|---|---|---|---|
| `yes` | 53.1% | 34.5% | 23.3% | 42.3% |
| `no` | 44.0% | 63.8% | 74.1% | 55.1% |
| `unclear` | 2.9% | 1.7% | 2.6% | 2.6% |
| **flagged `needs_review`** | 10.5% | 6.2% | 6.6% | **8.7%** |

The `yes`-rate gradient across tiers (53% → 35% → 23%) reproduces this pilot's own finding
that the notability/selection correlation is a real population effect, not a source-coverage
artifact — reassuring at 3,403 players rather than 22, and unchanged by the review-flag fix
(only confidence changed, not any row's `any_national_team_selection`/`categories` value).
91.3% of confirmed rows carry a `high`-confidence auto-label; the remaining 295 rows (down from
333 before the fix) need a human read, still concentrated more in Tier A (richer, longer prose
with more negation/candidate language to parse) than Tier B/C. Output:
`data/interim/pathway_national_team/national_team_tier_{a,b,c}_labeled.csv` (gitignored),
columns `any_national_team_selection`/`national_team_categories`/`national_team_confidence`/
`national_team_reason`. As with the pathway table, non-`confirmed`
identity rows are kept with a blank result rather than dropped.

This pilot's own recommendation to spot-check the "no evidence found" majority against JFA
per-occasion squad pages before trusting it at full population scale remains outstanding —
the `no` rows here are still Wikipedia-absence-based, not JFA-corroborated. Reviewing the 295
flagged rows and the JFA spot-check both remain future work, alongside joining these labels
into `docs/data_collection_plan.md`'s Step 5 analysis-ready dataset.
