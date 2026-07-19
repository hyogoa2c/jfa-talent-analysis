# Pre-2014 J.League Appearance Records: Source Audit

## Purpose

Support the "1999-2013 backfill" track flagged as a future extension in
`docs/research_plan_phase1.md` §12: build player-season appearance records for 1999-2013 from
the J.League Data Site's static legacy archive, so that a later study can attempt a 3-period
comparison (1999-2005 / 2005-2015 / 2015-2025) around the 2005 JFA 三位一体 turning point.
**Phase 1's observation window (2014-2025) and eligibility criteria (§3) are unchanged by this
work.** This audit and the accompanying collector are an independent, self-contained pilot;
nothing here is wired into the Phase 1 confirmatory analysis.

Identity resolution to `SFIX03` player IDs is explicitly **out of scope** for this pilot. Player
names on these pages are plain text with no player ID, profile link, or birth date — matching a
parsed row to a specific SFIX03 player will require name x team x year based resolution (an
extension of the existing `scripts/suggest_identity_overrides_from_profiles.py` approach), to be
done in a later stage once the parser itself is accepted.

## Source

- Index: `https://data.j-league.or.jp/SS/jpn/team/index.html`, titled 過去の試合記録 ("past match
  records"). Static HTML, declared `charset=Shift_JIS` in a `<meta>` tag; decodes correctly as
  `cp932`.
- The index page contains exactly **1,196** `<a href="....html">` links, all matching the fixed
  filename shape `<4-digit year><6-digit competition code>_<6-digit team code>_W0707_J.html`
  (the `W0707` segment is constant across every observed link). Per-year counts range from 56
  (2011) to 94 (2004), consistent with the "~1,200" estimate already in the SAP.
- Each link points to a single static Shift_JIS page: one team x competition-stage x year
  选手出場記録 (player appearance record) table, at the same base path
  (`https://data.j-league.or.jp/SS/jpn/team/`).

## Page Structure

Verified by fetching and inspecting 16 sample pages spanning 1999, 2005, and 2013 across every
distinct competition-code family present in the index (see "Competitions observed" below), plus
the confirmed Kashima 1999 J1 1st-stage example from the initial probe.

### Header block

Every page has this exact structural pattern (HTML, not just visual layout):

```html
<p align=right><FONT ...>1999/10/13更新</FONT></p>
<center><b><FONT ...>選手出場記録</FONT></b></center><br>
<P>
鹿島アントラーズ
</P>
<P>
１９９９Ｊリーグ　ディビジョン１　１ｓｔステージ
</P>
<P>
チーム成績(7位) 勝(6) 分(1) 敗(8) 得点(18) 失点(13) 得失点差(+5)
</P>
<table ...>
```

The `選手出場記録` bold marker is followed by exactly two `<P>` blocks that matter: **team name**,
then **competition label** (raw text). A third `<P>` block holds a team-level result summary
(win/draw/loss/goals, and rank for league competitions) that is not parsed by this pilot. The
parser (`AppearancePageParser` in the module below) locates team name and competition label by
finding the `選手出場記録` marker and taking the next two `<P>` blocks in document order, rather
than a fixed document-start index — this is robust to the update-date `<p>` that always precedes
the marker, and to any other incidental `<p>` elements.

### Player table

Below the header, a single `<table>` contains, in this row order:

1. 節 (matchday number) row
2. 日 (date) row
3. 対 (opponent) row
4. 会場 (venue) row
5. a row of single-character team match-result marks (○/●/△/□/■)
6. 合計 (team totals) row
7. **the column header row**: exactly `No | 選手 | 出場 | 時間 | 得点 | <per-matchday minutes...>`
8. one row per player: `No | name | total appearances | total minutes | total goals |
   <per-matchday marks...>`

Player rows are identified by the fixed 5-column header row content (`["No", "選手", "出場",
"時間", "得点"]`, exact string match, byte-identical across every one of the 16 sampled pages
including cup/playoff variants) followed by any row whose first cell is a bare integer.

**Per-matchday marks are intentionally not parsed** by this pilot (decision confirmed with the
task owner up front). They encode start (○), captain (○C), bench (SUB), substituted-on (▲*n*),
substituted-off (▽*n*), red card, etc. — a second, larger parsing effort with its own edge cases
(e.g. one sample page contained a bare `追加` "added" mark instead of a normal appearance mark).
Only the three total columns (出場/時間/得点) are extracted for this pilot.

## Ground truth verification

The task brief's stated ground truth was reproduced exactly from the raw byte stream (decoded
`cp932`) of `1999010001_000001_W0707_J.html` (鹿島アントラーズ, 1999 J1 1st stage):

| Player | 出場 (appearances) | 時間 (minutes) | 得点 (goals) |
|---|---:|---:|---:|
| 名良橋　晃 | 5 | 464 | 0 |
| 古川　昌明 | 0 | 0 | 0 |

Both rows are included verbatim (trimmed HTML, same byte encoding) in the committed test
fixture `tests/fixtures/pre2014_appearance_sample_1999_kashima_j1_1st.html`.

## Encoding and full-width text

- All pages decode correctly with `cp932` (a superset of Shift_JIS that Python's codec registry
  handles natively; no external dependency needed).
- Competition labels, team-summary lines, and some numeric-looking cells use full-width forms:
  full-width digits (`２００５`, U+FF10-FF19), full-width Latin letters (`ｓｔ`, U+FF41 range),
  and the ideographic space U+3000 as a word/date separator (e.g. `’99Ｊリーグ　ヤマザキナビスコカップ`).
  Player names also use U+3000 between surname and given name (`名良橋　晃`).
- Player-row numeric cells (出場/時間/得点) are **already half-width ASCII digits**, so no
  full-width folding is needed there — but large minute totals use a half-width comma thousands
  separator (`3,342`), which must be stripped before `int()`.
- The parser normalizes all header/name/label text with `unicodedata.normalize("NFKC", ...)`
  followed by whitespace collapsing, which folds full-width digits/Latin letters to half-width
  and converts U+3000 to a regular space in one step (verified: `'２００５Ｊリーグ　ディビジョン１　１ｓｔステージ'`
  → `'2005Jリーグ ディビジョン1 1stステージ'`).

## Pagination anomaly (important finding, changes collector design)

For team-seasons with enough matchdays that the per-matchday columns don't fit one page (all
observed J1-from-2005-onward pages at 18 teams/34 matchdays, and larger J2 seasons), the site
splits the table across multiple files sharing the same team+competition prefix:
`<prefix>_1_W0707_J.html` (page 1), `<prefix>_2_W0707_J.html` (page 2 if 3+ pages), and finally
`<prefix>_W0707_J.html` **with no numeric infix** for the last page. **The index page links only
to the last-page file** (no numeric infix) — page 1 (and page 2, if present) are reachable only
via an in-page `[1頁]` link, not from the index.

This matters because it determines whether the collector needs to chase pagination links. It was
checked explicitly:

- `2005010001_000001_W0707_J.html` (Kashima, 2005 J1, single stage, 34 matchdays → 2 pages):
  player 名良橋　晃 shows **11 / 552 / 0** on *both* the `_1_` first-page file and the no-infix
  last-page file that the index links to.
- `2013020003_000014_W0707_J.html` (Consadole Sapporo, 2013 J2, 42 matchdays → 3 pages): player
  曵地　裕哉 shows **4 / 360 / 0** on *both* the `_1_` first-page file and the no-infix third-page
  file; the full 35-row player roster is identical (same names, same totals) across both files
  — only the per-matchday mark columns differ by date range.

**Conclusion: the 出場/時間/得点 total columns are always the full competition-stage cumulative
totals, even on a page that only shows a subset of matchday columns.** The collector therefore
only needs to fetch the single URL the index links to per (year, team, competition) — chasing
`[1頁]`/`[2頁]` links is unnecessary for totals-only extraction. This was verified on 2 multi-page
cases (2-page and 3-page); it is not exhaustively verified across all ~1,196 pages, so a future
full crawl should spot-check a larger sample of paginated pages before trusting this at scale.

## Competitions observed

Sixteen pages were sampled (1999/2005/2013 × every distinct 6-digit competition-code family
present in the index). Competition labels are kept as **raw text** in the parser output —
classification into league vs. cup vs. other is deliberately left to a later stage, since (a) it
touches the Phase 1 SAP's confirmatory-analysis boundary and (b) the label format itself is not
fully consistent (see anomaly below), so getting the classification right deserves its own pass
without re-scraping.

| Filename competition code | Sample raw label(s) observed | What it appears to be |
|---|---|---|
| `010001` | `１９９９Ｊリーグ　ディビジョン１　１ｓｔステージ`, `２００５Ｊリーグ　ディビジョン１`, `２０１３Ｊリーグ　ディビジョン１` | **J1 league.** 1999-2004: two-stage season (`１ｓｔ`/`２ｎｄステージ` suffix, see `010002` below). 2005-2013: single-stage season, no stage suffix. 16 teams 1999-2004, 18 teams 2005-2013 — matches known J1 club-count history. |
| `010002` | `１９９９Ｊリーグ　ディビジョン１　２ｎｄステージ` | **J1 league, 2nd stage.** Only appears 1999-2004 (two-stage era). |
| `010004` | `１９９９Ｊリーグ　サントリーチャンピオンシップ` | **J1 championship series** (stage-winners playoff, two-legged), only appears in 1999-2001 and 2004 — years when the 1st/2nd stage winners differed. Not a regular-season league page. |
| `020003` | `１９９９Ｊリーグ　ディビジョン２` | **J2 league.** Team count grows from 10 (1999) to 22 (2013), matching known J2 expansion history. |
| `002006` | `’９９Ｊリーグ　ヤマザキナビスコカップ`, `２００５Ｊリーグヤマザキナビスコカップ 予選リーグ`, `２０１３Ｊリーグヤマザキナビスコカップ　決勝トーナメント` | **J.League (Yamazaki Nabisco) Cup.** Not a league competition — should be excluded from any J1/J2 appearance-count analysis. Label format for this competition is the least consistent (see anomaly below). |
| `002000` | `２００５Ｊリーグヤマザキナビスコカップ 予選リーグ`, `２０１３Ｊリーグヤマザキナビスコカップ 予選リーグ` | Also **Nabisco Cup group stage** — appears to be a second, parallel code family for the same cup competition in different years (raw text is what disambiguates, not the filename code, consistent with the "do not guess from filename" instruction). |
| `100001` | `２００５Ｊサテライトリーグ　Ａグループ` | **Satellite/reserve league**, *not* first-team competition — this exists only 2000-2009 per the index (disappears after 2009, plausibly when the satellite-league system was discontinued/restructured). `100002`-`100006` follow the same 2000s-only pattern in the index counts and are presumed to be the same satellite league's other groups (B/C/D/...), but only `100001` was directly fetched this pass — flagged for confirmation in a later, more thorough sample rather than guessed here. |
| `903001` | `２００５Ｊ１・Ｊ２入れ替え戦` | Sampled via `2005903001_000011_W0707_J.html`: **J1/J2 promotion-relegation playoff**, two-legged, 2004-2008 only per the index. Not a regular league page. |
| `803001` | `２０１３Ｊ１昇格プレーオフ` | **J1 promotion playoff** (introduced 2012, replacing/supplementing the older `903001` playoff format — `903001` and `803001` do not overlap in the index's year coverage). |
| `904001` | `２０１３Ｊ２・ＪＦＬ入れ替え戦` | **J2/JFL promotion-relegation playoff.** |

**Practical takeaway for a later league/cup classification pass:** the safest signal is
substring matching on the raw `competition_label`: `ディビジョン１` (optionally with `１ｓｔステージ`/
`２ｎｄステージ`) → J1 league; `ディビジョン２` → J2 league; anything containing `ナビスコ`,
`チャンピオンシップ`, `入れ替え戦`, `昇格プレーオフ`, or `サテライト` → not a regular league competition
and should be excluded from J1/J2 appearance-count analysis.

## Anomalies

1. **Abbreviated year format on early cup pages.** Most competition labels use a full 4-digit
   year (`１９９９Ｊリーグ...`), but the 1999 Nabisco Cup page uses an abbreviated apostrophe-year
   form instead: `’９９Ｊリーグ　ヤマザキナビスコカップ` (`'99` rather than `1999`). Since
   `season_year` is taken from the *filename*, not parsed out of the label text, this does not
   affect the collector's `season_year` field — but it means the raw `competition_label` column
   cannot be assumed to always start with a parseable 4-digit year, which matters for any later
   automated classification step working from the label text.
2. **Filename competition codes are not reliable classifiers.** As shown above, the `002006` and
   `002000` code families both turned out to be the Nabisco Cup in different years, and codes
   like `903001`/`803001` are two non-overlapping playoff formats across different eras rather
   than one stable competition. The task brief's instruction to derive competition identity from
   each page's own header text (not the filename) is confirmed necessary, not just cautious.
3. **Overtime/extra-time matchday minutes.** The per-matchday minutes-header row for regular
   1999 J1 matches is usually `90`, but some matchdays show `101`, `111`, `120`, etc. — golden
   goal / sudden-death overtime, which J.League used prior to allowing draws. This does not
   affect player-row totals (which are pre-aggregated by the source) but is worth flagging for
   anyone later wanting to reconstruct per-match minutes from the skipped per-matchday columns.
4. **No player IDs, links, or birth dates anywhere on these pages** — confirmed across all 16
   sampled pages, not just the original probe page. Identity resolution to SFIX03 is a fully
   separate, later effort (see "Purpose" above).
5. Zero-appearance parsed rows are common and expected (229 of 1,635 rows, 14%, in the 1999
   pilot) — these are registered-but-unused squad members, not a parsing failure. The ground
   truth case (古川　昌明, 0/0/0) is exactly this pattern.

## Parser module

`src/jfa_talent_analysis/sources/pre2014_appearances.py` — pure functions:

- `parse_index(html) -> list[IndexLink]` (`year`, `filename`, `url`, `link_text`)
- `parse_appearance_page(html, *, season_year, source_url) -> list[AppearanceRecord]`
  (`season_year`, `competition_label` [raw, NFKC-normalized], `team_name`, `player_no`,
  `player_name`, `appearances`, `minutes`, `goals`, `source_url`, `retrieved_at`)
- `normalize_text`, `parse_int` helpers (full-width folding, comma stripping)

Plus thin I/O wrappers (`fetch_index_html`, `fetch_page_html`, using `cp932` decoding via a new
optional `encoding` parameter added to the shared `request_with_retry` helper in
`src/jfa_talent_analysis/sources/retry.py`) and `write_appearance_records_csv`.

Tests: `tests/test_pre2014_appearances.py`, using two small committed cp932 fixtures under
`tests/fixtures/` (`pre2014_appearance_index_sample.html`, trimmed real index excerpt;
`pre2014_appearance_sample_1999_kashima_j1_1st.html`, trimmed real Kashima 1999 J1 1st-stage
page including the 名良橋　晃 5/464/0 and 古川　昌明 0/0/0 ground-truth rows). All tests pass
(`uv run pytest`), and `uv run ruff check .` is clean.

## Collector script and pilot run

`scripts/collect_pre2014_appearance_records.py` — sequential fetch only, `--sleep` (default
1.0s, applied only to live fetches, not cache hits), `--start-year`/`--end-year`,
`--limit-pages` (smoke-test cap), `--output-dir` (default `data/interim/pre2014/`, gitignored).
Resume-safe: raw HTML is cached to `<output-dir>/html_cache/<filename>` (and the index to
`<output-dir>/html_cache/index.html`); a page already on disk is read from cache and not
re-fetched or re-slept-on. Output is one CSV per season year,
`appearance_records_pre2014_<year>.csv`; pages that fail to parse (missing header block, empty
player table) are logged to `<output-dir>/collection_failures.csv` instead of aborting the run.

**Pilot run (1999 only, full year, no `--limit-pages`):**

```bash
uv run python scripts/collect_pre2014_appearance_records.py \
  --start-year 1999 --end-year 1999 --sleep 1.0 --output-dir data/interim/pre2014
```

Result: 70/70 pages fetched (matches the index's 1999 count exactly), **0 failures**, wrote
`data/interim/pre2014/appearance_records_pre2014_1999.csv`.

| Metric | Value |
|---|---:|
| Rows | 1,635 |
| Distinct teams | 26 (16 J1 + 10 J2, matching known 1999 club counts) |
| Distinct competition labels | 5 (J1 1st stage, J1 2nd stage, J1 championship series, J2, Nabisco Cup) |
| Zero-appearance rows | 229 (14%) |
| Rows with unparseable numeric fields | 0 |

Spot-checks against raw cached HTML (all exact matches, byte-level):

| Page | Player | Reported (出場/時間/得点) | Raw HTML | Match |
|---|---|---|---|---|
| `1999010001_000001` (Kashima, J1 1st stage) | 名良橋　晃 | 5 / 464 / 0 | `5` / `464` / `0` | Yes (task ground truth) |
| `1999002006_000001` (Kashima, Nabisco Cup) | 名良橋　晃 | 7 / 665 / 1 | `7` / `665` / `1` | Yes |
| `1999010002_000001` (Kashima, J1 2nd stage) | 名良橋　晃 | 10 / 894 / 2 | `10` / `894` / `2` | Yes |
| `1999010004_000007` (Shimizu, Championship Series) | 真田　雅則 | 2 / 197 / 0 | `2` / `197` / `0` | Yes |
| `1999020003_000014` (Sapporo, J2) | 佐藤　洋平 | 35 / 3,342 / 0 | `35` / `3,342` / `0` | Yes (comma-thousands parsed correctly) |

No parsing anomalies or unhandled page-format variants were encountered in the 1999 pilot; all
70 pages parsed with a non-empty player table via the same header-row detection logic.

## Full crawl (2026-07-18)

The full 1999-2013 crawl completed with **1,196/1,196 index pages fetched and parsed, 0
failures** (`--sleep 1.0`, sequential; the 1999 pilot's 70 pages were reused from cache).
Output: 15 per-year CSVs under `data/interim/pre2014/`, **31,274 player-competition rows**
total (per-year row counts 1,313-2,384; the 2010-2011 dip mirrors the index's own per-year
page counts, not a collection gap).

The pagination cumulative-totals assumption ("Pagination anomaly" above) was re-verified at
scale: of 385 paginated team-seasons found in the crawled cache, a seeded random sample of
15 (spanning 2000-2013, J1 and J2) was checked player-by-player against the corresponding
`_1_` first-page file — **all 15 rosters identical in (出場, 時間, 得点), 0 mismatches**
(17 verified cases cumulative including the pilot's 2).

## Identity resolution to SFIX03 (name x team x year)

`src/jfa_talent_analysis/pre2014_identity.py` +
`scripts/match_pre2014_appearances_to_sfix03.py` join the crawled rows to the SFIX03
Japanese player universe (7,162 players, `data/interim/player_universe_sample.csv`) by
name. Design points, each forced by an observed failure mode:

- **Kanji variant folding** applied to both sides (楢崎/楢﨑, 髙/高, 澤/沢, 將/将, 藪/薮,
  已/己, ...). The 斎/齋 and 斉/齊 families are kept separate (distinct characters, not
  old/new forms).
- **Registered-name alias expansion** of SFIX03 parenthesized forms: given-name change
  (黒崎 久志（比差支）), family-name change (田渕（花垣） 龍二), full alternate spelling
  (岩﨑 知瑳（岩崎 知瑳）), and mixed-width brackets (髙山 和真（高山 和真)).
- **Katakana mononyms are never auto-matched** (review queue only): SFIX03's ビスマルク is
  a defender born 2002, not the 1999-2003 Kashima/Kobe Brazilian of the same registered
  name. Same for nickname aliases like 三都主 アレサンドロ（アレックス）.
- **Age-plausibility filter** (14 ≤ season − birth_year ≤ 50): a same-name universe player
  born too late/early for the season is a different person (archive 2004 FC東京 中村 亮 vs
  SFIX03 中村 亮 born 1996) and is dropped from the candidate set. The bounds clear both
  森本貴幸 (debut at 15) and 三浦知良 (J2 at 46 in 2013). After matching, 0 of the matched
  rows violate the window.
- **Variant-spelling siblings force ambiguity even on an exact hit**: with no birth date on
  the archive side, an exact spelling match is not evidence of which same-name (after
  folding) universe player played that season.

**Full-run result (all 15 years, 31,274 rows):**

| Bucket | Rows | Share |
|---|---:|---:|
| Matched to a unique `source_player_id` | 26,777 (2,310 distinct players) | 85.6% |
| — exact_name / folded_name / alias_name | 26,587 / 140 / 50 | |
| Ambiguous (2+ candidates → SFIX04 queue) | 87 | 0.3% |
| Katakana-mononym / nickname review queue | 92 | 0.3% |
| Unmatched, katakana-only (non-Japanese players; outside the SFIX03 Japanese universe by construction) | 3,226 | 10.3% |
| Unmatched, other | 1,092 | 3.5% |

The "unmatched, other" bucket decomposes almost entirely into (a) Korean/Chinese-kanji
foreign players (柳 想鐵, 洪 明甫, 崔 龍洙, 朴 智星, ...) — correctly outside the Japanese
universe, (b) satellite-league-only rows, and (c) registered-but-never-played squad members
with 0 appearances, who have no SFIX03 page. In the 1999 deep-dive, **every unmatched
Japanese-name row with appearances > 0 was resolved** by a fold/alias fix (小川 雅已/雅己
was the last); at full scale, non-katakana unmatched rows with appearances > 0 outside the
satellite league are 301, dominated by the Korean-player names above.

Outputs (all under `data/interim/pre2014/`, gitignored):
`matched_appearance_records_pre2014.csv` (row-level join with `source_player_id`,
`match_method`, `birth_date`), plus deduplicated diagnostics
`pre2014_ambiguous_names.csv`, `pre2014_nickname_candidates.csv`,
`pre2014_unmatched_names.csv` (with `katakana_only` flag).

### SFIX04 season-history disambiguation (2026-07-19)

`scripts/resolve_pre2014_identities_from_sfix04.py` resolves the ambiguous + nickname
queues against SFIX04 season/team histories (30 candidate profiles fetched once, cached to
`sfix04_cache/`; decision rule mirrors `suggest_identity_overrides_from_profiles.py`: a
candidate is accepted only when it is the *only* one whose history covers that season at
that club). Archive full club names are mapped to SFIX04 short names by
`sfix04_team_matches` (substring rule + explicit aliases for letter abbreviations and era
renames: F東京/G大阪/横浜FM, 市原↔千葉 2005, 平塚↔湘南 2000, 草津↔群馬 2013, V川崎/東京V).

Result: **62/104 queue entries resolved**, feeding 110 rows back into the matcher via
`--resolutions` (`match_method=sfix04_history`) → **matched total 26,887/31,274 (86.0%),
2,317 distinct players, still 0 age-window violations**. Spot-checked against SFIX04
directly: 三都主 アレサンドロ resolved as アレックス only for 清水 1999-2001 (his actual
club-seasons), 田中 マルクス闘莉王 as トゥーリオ only for 広島 2001-2002 — while the same
mononyms at 大分/甲府/大宮/柏 etc. were correctly rejected as different (foreign) players
(`none_matched`), exactly the false-positive class the mononym guard exists for.

Remaining queues after this pass: **8 ambiguous rows (4 player-seasons: 田中雄大 川崎
2011-12, 田中達也 熊本 2012, 松田陸 FC東京 2013, 鈴木翼 山形 2013)** — SFIX04 lists no
season row for either candidate, consistent with 特別指定/registered-only stints — and 61
nickname rows that are correctly-rejected foreign mononyms. Both are inert unless a later
analysis needs those specific rows.

Remaining follow-up for this track: competition_label classification (league vs. cup vs.
playoff/satellite) before any analysis use.

## Explicitly out of scope for this pilot (flagged, not solved)

- **Identity resolution** (name x team x year → SFIX03 `source_player_id`) — see "Purpose".
- **Competition classification** (league vs. cup vs. playoff/satellite as a structured column) —
  raw label text is preserved so this can be redone without re-scraping; see "Competitions
  observed" for the substring-matching approach a later pass could start from.
- **Per-matchday marks** (start/bench/sub/card) — totals only, by design; see "Player table".
- **Full-scale pagination verification** — the cumulative-totals finding is verified on 2 cases,
  not exhaustively; a full 1999-2013 crawl should re-check a larger paginated-page sample before
  the parser is treated as fully trustworthy at scale.
- **The full 1999-2013 crawl itself** — this pilot deliberately collected 1999 only. Running the
  full range is a later stage for another agent once the parser is accepted (per task brief).
