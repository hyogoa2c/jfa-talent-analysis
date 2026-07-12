# Coach Network Dataset Design (2026-07-10)

Phase 2 of `docs/data_collection_plan.md` (deferred until the player-outcome dataset
stabilized, which it did with PR #2). Research question: 育成段階での指導者関与の効果 — do
development-stage coaches/instructors explain differences in player career outcomes?

## Feasibility findings (from the cached corpus, zero new fetches)

1. **Player→institution linkage is essentially solved**: 97.3% of the 3,403 cached player
   extracts carry a structured 所属クラブ list with year ranges; parsing them
   (`club_history_extraction.py`) recovers 96% of the 22-player pilot's manually-verified
   institution chains (27,073 stint rows, 9,068 youth-flagged).
2. **Institutions are head-concentrated**: the top ~100 institution strings account for
   roughly half of all youth-institution mentions (流通経済大学 101, FC東京U-18 102,
   明治大学 94, 国士舘大学 82 …), so an institution×era→coach table over the head
   institutions covers a large share of the population without per-player coach research.
3. **Direct coach mentions in player prose are sparse but precise**: 9.1% of players have a
   監督/コーチ mention in the same sentence as a youth institution; ~1% have an explicit
   guidance narrative (誘われ/指導を受け/コンバート…), e.g. 西川周作←皇甫官・吉坂圭介,
   長澤和輝←源平貴久. Useful for validation and case studies, not population coverage.

## Two-layer linkage design

```
[Primary]   player →(所属クラブ rows, dated)→ institution × stint years
                                     ↓ JOIN on institution + year overlap
            institution × era →(new research)→ head coach at the time
[Secondary] direct player-prose coach mentions (~300 pairs) → validation / case studies
```

Year gaps in player stints (dated coverage is 44-49% for HS/university/U-18 rows) are filled
by **age-based imputation**: Japanese school years are rigid (high school = age 15-18,
university = 18-22, U-15/U-18 analogous), so `birth_date` pins the stint years for
school-type institutions with high confidence.

Institution-name normalization is a known pre-join task (前橋育英高校 vs 前橋育英高等学校,
spacing variants like "アルビレックス新潟 U-15").

## Coach attribute table: the coach's own pathway (added 2026-07-10 per user)

Beyond linking players to coaches, each coach's own background is an analytical variable —
did the coach play in J1? play abroad? hold an S級 license? User framing: likely low
priority and sparse, but the design should accommodate it from the start.

**Key reuse insight: coaches are mostly ex-players, so the existing player-article toolchain
applies nearly unchanged** once coach names are known:

| coach attribute | tool reused | new work needed |
|---|---|---|
| playing-career stints | `club_history_extraction.py` (所属クラブ) | none |
| played in J1 (+ years) | `debut_extraction.py` (出場歴 lines) | none |
| played overseas | `overseas_classification.py` | none |
| identity verification | `verify_wikipedia_candidate_identity.py` pattern (birth date) | none |
| coaching career timeline | — | new: 指導歴/監督歴 section parsing |
| S級ライセンス etc. | — | new: license-mention extraction (prose pattern) |

Planned columns (populated when the coach roster exists):
`coach_id, name_ja, wikipedia_title, birth_year, played_j1, j1_debut_year, played_overseas,
coaching_stints(institution, from_year, to_year, role), s_license_mentioned, identity_check`.

Expected coverage honestly stated: Wikipedia articles exist reliably for famous youth
coaches (名将 tier: 黒田剛, 山田耕介, 中野雄二…) and for any coach who had a notable playing
career — precisely the coaches of the head institutions this design prioritizes. Long-tail
institution coaches will often lack articles; those get institution-level linkage only.

### Build reality (2026-07-11): auto-resolution is ~60% reliable, needs a research pass

`scripts/build_coach_attribute_candidates.py` auto-fetched Wikipedia extracts and parsed the
所属クラブ (own playing career) list for all 195 named coaches. Findings that shaped the
approach:
- The prose-based `overseas_classification` is too NOISY on coach articles (a coach's article
  is dominated by their coaching career and the players they developed — 黒田剛's 18k-char
  article false-positived as "played overseas" off text about his players). The reliable
  overseas/top-flight signal is the parsed CLUB LIST (are any of the coach's own clubs
  foreign / top-flight), not prose classification.
- Title auto-resolution (name → article) is only ~60% reliable: ~76 of 195 grabbed the WRONG
  page (date pages like "5月7日", club pages like "福岡大学サッカー部", even a comedian for
  南健司). So the attribute build is NOT fully automatic — it needs a per-coach research pass
  (delegated to a Sonnet subagent) that confirms the correct article using the coach's
  institution + era as identity anchors, with the ~120 trustworthy auto-resolutions (title
  contains the coach name; 72 with clean club lists) as a fast-path scaffold.
- Top-flight definition fixed: **J1 (1993+) OR JSL Division 1 (pre-1993 top flight)** — many
  of these coaches played in the 1970s-80s, so JSL-D1 experience counts as top-flight; the
  literal-J1 debut extractor alone would undercount the older generation.

Output: `data/interim/coach_network/coach_attributes.csv` (played_professionally,
played_top_flight, played_overseas, own_national_team, top_flight_era, ...).

### J-youth coverage gap quantified (2026-07-11) — motivates the J-academy scale-up

Once the player↔coach exposure was built, the coverage-by-pathway funnel exposed a large,
non-random gap. Of the full outcome population, the share of players with an identified
primary development coach is: **university 71%, high school 39%, but J-club-academy only 18%**
(535 of 653 J-youth-pathway players have NO development-coach data, because only 5 academies
were researched). Since j_club_academy is the pathway most central to the original research
question ("育成段階での指導者関与の効果"), analyzing coach effects on the current data alone
would effectively measure "university coach effects." This motivated a J-youth U-18 scale-up
batch (15 new academies: 東京ヴェルディ, 京都, 清水, 鹿島, 大分, 神戸, 浦和, 広島, 鳥栖,
横浜FC, 札幌, 大宮, 川崎, 千葉, 名古屋 — top-15 by distinct J-youth players, adding ~244
players of coverage), run in parallel with the coach-attribute build. J-academies remain the
hardest tier (~51% pilot coverage, unstable JFA-archive URLs), so expect lower yield here.

## Pilot results (completed 2026-07-10)

See `docs/institution_coach_pilot_2026-07-10.md` for the full 15-institution report
(coordinator-verified). Headline numbers — average 2000-2025 coverage by type:

| type | fully (≥90%) | mostly | poorly (<60%) | avg coverage |
|---|---|---|---|---|
| high schools | 5/5 | 0 | 0 | **~99%** |
| universities | 2/5 | 2/5 | 1/5 | ~74% |
| J-club academies | 1/5 | 1/5 | 3/5 | ~51% |

High schools inverted the pilot's expectation (名将 culture = coach biographies chain
cleanly); J-academies are the hard category as predicted, except FC東京U-18 (~95%, a
purpose-built 歴代監督 Wikipedia table). Method discoveries worth building into any scaled
run: (1) chain through COACHES' biographies rather than institution articles; (2) check
official per-season staff pages first for universities (法政's `hoseifc.com/club/season/
YYYY/` pattern); (3) archived JFA Premier League year-specific team pages are the best
J-academy source but have unstable URL slots across years (a real crawling cost); (4) the
schema needs a `role_type` field (総監督/ディレクター vs on-field 監督 duality confirmed at
multiple institutions); (5) store tenures as April-start seasons and treat ±1-year source
disagreements as expected noise.

## Coach-tenure table schema (fixed 2026-07-11, scale-up phase)

`institution,coach_name,role_type,from_year,to_year,source_urls,confidence,notes`

- `from_year`/`to_year`: season starting April of that year; empty `to_year` = currently
  serving. Non-consecutive stints by the same coach are separate rows (real case: 島田貴裕
  held ガンバ大阪ユース監督 in three separate periods).
- `role_type`: 監督 / 総監督 / アカデミーダイレクター兼監督 / ヘッドコーチ etc. — concurrent
  director-vs-field-coach rows may OVERLAP in years by design (法政大学, セレッソ大阪U-18).
- `confidence`: high / medium-high / medium / low. ±1-year cross-source disagreements are
  noted in `notes`, with the better-sourced year in the year columns.
- Gaps are the ABSENCE of rows (documented in the accompanying notes files), never guessed.

Files under `data/interim/coach_network/` (gitignored):
`pilot_coach_tenures.csv` (the 15 pilot institutions converted, 65 rows) and
`hs_batchN_coach_tenures.csv` + `hs_batchN_notes.md` per scaled batch.

Scale-up targets (fixed 2026-07-11): top-30 high schools by distinct-player count after
alias normalization (市立船橋高=船橋市立船橋高 merged ranks #6+#11), minus the 5 piloted →
25 new schools in 3 subagent batches (10/10/5). Top-40 schools cover ~48% of the 1,835
players with any high-school stint; the 462-school long tail is deliberately deferred.

### High-school scale-up: completed (2026-07-11)

All 30 target high schools done — 5 pilot + 25 across 3 batches (10/10/5). 148 tenure rows
total (pilot 65 + batch1 40 + batch2 30 + batch3 13). Per-batch source coverage improved
batch-over-batch (~79% → ~87% → ~91%), likely because later batches happened to draw more
famous/well-documented programs rather than a genuine method improvement. Files:
`hs_batch{1,2,3}_coach_tenures.csv` + matching `_notes.md`, gitignored under
`data/interim/coach_network/`.

New structural patterns found beyond the pilot's director/field-coach duality and
founder-emeritus patterns:
- **Figurehead-監督** (国見高等学校): a football-inexperienced teacher installed as nominal
  監督 solely to satisfy 全国高等学校体育連盟 eligibility rules, while real authority sits
  with a 総監督.
- **Celebrity hire** (昌平高等学校・玉田圭司): an ex-pro parachuted into a head-coach role
  with zero prior high-school coaching experience, won a title in one season, then left.
- **Scandal-driven dismissal** (千葉県立八千代高等学校・岡本一洋): mid-tenure firing for a
  conduct incident; the coach's full name had to be sourced from unofficial blog
  identification since the original news reporting anonymized him.
- **Cross-institution advisor edges**: the same person appears as head coach at one
  institution and an informal outside advisor at another (古沼貞雄: 帝京高等学校's longtime
  coach also advises 矢板中央高等学校) — a real network edge beyond simple employment.
- **Unresolved title-vs-authority gap** (静岡県立藤枝東高等学校, 2022-2023): a coach moved to
  a "ヘッドオブコーチング" title with no named 監督 successor found in any source — recorded
  as a genuine gap, not guessed.
- Coverage does not track institutional fame uniformly: 藤枝東 (長谷部誠's alma mater, one of
  the most historically prestigious programs in the dataset) still only reached ~70%,
  because press coverage clusters around its single most decorated coach rather than the
  full timeline.

### University scale-up targets (fixed 2026-07-11)

Same method as the high-school target list: normalize institution-name suffixes
(`サッカー部`/`体育会サッカー部`/`蹴球部`/`ア式蹴球部`/`体育会蹴球部`) on
`player_institution_stints.csv` rows containing `大学` (excluding rows that are actually
high schools with "大学" embedded in their proper name, e.g. 流通経済大学付属柏高等学校),
rank by distinct-player count, and take the top 35 minus the 5 already piloted
(流通経済大学/明治大学/国士舘大学/法政大学/筑波大学) → 30 new universities. Top-35
universities cover 1,554 of 1,951 distinct players with any university stint (80%).

30 new targets in 3 batches of 10/10/10, by rank (corrected 2026-07-11 — an earlier draft
of this section said "25 new, 10/10/5" but the batch lists below were always 30/10-10-10;
this line now matches what was actually run):
- **Batch 1**: 福岡大学, 早稲田大学, 桐蔭横浜大学, 阪南大学, 駒澤大学, 中央大学, 関西大学,
  順天堂大学, 東洋大学, 専修大学
- **Batch 2**: 大阪体育大学, 日本体育大学, 立命館大学, 関西学院大学, 鹿屋体育大学,
  関東学院大学, びわこ成蹊スポーツ大学, 神奈川大学, 立正大学, 東海学園大学
- **Batch 3**: 仙台大学, 中京大学, 京都産業大学, 大阪学院大学, 東京国際大学, 産業能率大学,
  東京学芸大学, 拓殖大学, 東海大学, 日本大学

Expect lower coverage than the high-school batches: the pilot already found universities
medium-cost/medium-yield (~74% average across the 5 piloted programs, vs. high schools'
~99%), driven by sparser official per-season staff pages for less prominent programs and by
university coaching staff overlapping with employment at the university's broader athletic
department (making searches noisier than the single-sport-focused high-school case).

### University scale-up: completed (2026-07-11)

All 35 target universities done — 5 pilot + 30 across 3 batches (10/10/10). 177 tenure rows
total (pilot 65 + uni_batch1 39 + uni_batch2 39 + uni_batch3 34 — pilot total includes non-
university institutions too; the 30 new universities alone contributed 112 rows). Batch
coverage: batch1 ~86%, batch2 ~66% (~84% excluding two weak outliers), batch3 ~70% (~84%
excluding two weak outliers). Files: `uni_batch{1,2,3}_coach_tenures.csv` + matching
`_notes.md`, gitignored under `data/interim/coach_network/`.

Key finding across all three batches: **coverage is not predicted by institutional
prominence.** Several nationally-successful, currently-prominent programs (立命館大学 ~10%,
京都産業大学 ~19%, 東京学芸大学 ~8%) had almost no searchable pre-2020s coaching history,
while some far less famous programs reached ~100%. The actual driver appears to be whether
any individual — an OB association, a famous alumnus with their own Wikipedia page, or a
diligent team-site maintainer — happened to informally document the program's history; team
prominence and documentation effort are only weakly correlated.

New structural patterns beyond the high-school phase:
- **部長** (faculty administrative advisor) and **副部長兼GM** as university-specific
  `role_type` values, distinct from the high-school phase's pure 監督/総監督/ヘッドコーチ set.
- **Corporate/J-club dispatch model**: some university programs are staffed via a formal
  partnership with a J-league club (関東学院大学↔横浜F・マリノス, 産業能率大学↔湘南ベルマーレ),
  producing high coach turnover instead of the "franchise coach" pattern that otherwise
  dominates both the high-school and university phases.
- **Longest single tenure found in the project**: 拓殖大学's 玉井朗, a professor-coach with
  33+ consecutive years in the role.
- **University-vs-affiliated-school name confusion** is a distinct disambiguation-risk
  category from simple similarly-named-university confusion (e.g. an affiliated high
  school's own site can look like the university's official athletic-department site);
  caught by cross-checking league names (大学/インカレ vs 高校/高円宮杯 references).
- Coach-network edges directly linking pilot, high-school, and university layers were
  found repeatedly (e.g. 池上礼一: 明治大学[pilot]→立教大学→立命館大学[batch2]; 加茂周:
  関西学院大学[batch2]↔大阪学院大学[batch3]; 専修大学[batch1]'s 源平貴久 named as a direct
  mentor in J1/national-team player 長澤和輝's own Wikipedia prose) — an early, encouraging
  signal for the eventual network analysis.

## Analytical cautions carried forward

- What the primary linkage measures is "was at institution X while coach Y was head coach" —
  exposure, not interaction intensity.
- Coach effects are confounded with institution effects (prestige, facilities, selection);
  identification leverage comes from coaches who moved BETWEEN institutions (coach fixed
  effects), which is exactly what the network representation surfaces.
- The selection-effect lesson from the player analysis (youth_selected controls) applies
  here doubly: strong institutions attract both strong players and strong coaches.

## Phase C findings (2026-07-11/12): does a coach's own playing pedigree matter?

Full pipeline built and run end-to-end: 340 coach-tenure rows across 86 institutions
(pilot + HS×3 + university×3 + J-youth×1) → player↔coach exposure join → per-player
"primary development coach" (head coach at the terminal pathway-stage institution, greatest
stint×tenure overlap; 1,974 players) → each coach's OWN playing attributes researched from
Wikipedia (`coach_attributes.csv`, 255 coaches: played_professionally / played_top_flight =
J1 or JSL-D1 / played_overseas / own_national_team). Analysis in
`scripts/analyze_coach_pathway_effects.py`, run on all cohorts and a censoring-controlled
mature cohort (birth 1988-1998).

**Key confound found and controlled — right-censoring.** Ex-top-flight coaches start their
tenures later (median 2013 vs 2011) and coach later-born players (median birth 1997 vs 1995)
who have had fewer years to reach J1. The naive comparison therefore understates elite-coach
outcomes; restricting to the mature cohort removes most of the artifact.

**Headline (mature cohort, censoring-controlled):**
- A coach having *any professional playing career* has a modest POSITIVE association with
  player outcomes — reached_j1 45% vs 41%, and national-team selection **50% vs 39%**.
- But having been *elite specifically* adds nothing on top: `own_national_team` (the coach
  was himself an international) is FLAT across every outcome (J1 42% vs 43%, NT 46% vs 45%).
  `played_top_flight` is flat on J1 (43% vs 42%) though positive on producing NT players
  (51% vs 40%).
- `played_overseas` is (weakly, n=49) NEGATIVE — but small-n and confounded; not reliable.

**Within-institution top_flight comparison stays negative (明治 −35%, 法政 −25%) — but the
cause is illuminating, not systematic.** Drilling in: at 明治大学 the two highest-yield
development coaches are 栗田大輔 (83% J1) and 神川明彦 (71% J1) — both celebrated
university-football developers who never played professionally — versus 井澤千秋 (40% J1, an
ex-JSL-D1 player coaching an earlier cohort). Same shape at 法政. So the "negative" is not
"elite background hurts"; it is that **development skill is an individual-coach property
orthogonal to the coach's own playing pedigree** — non-player coaches like 栗田/神川 are
living proof that great developers need not have been great players.

**Bottom line for the original research question:** development-stage coaches clearly vary in
their players' outcomes (the FC東京U-18 20pp within-academy J1 spread, the Meiji coach
contrasts), but a coach's OWN elite playing background does NOT explain that variation — at
most, having played professionally at all carries a weak positive signal for producing
national-team players. The signal that matters is individual coaching quality, which this
pedigree variable does not capture. All results remain descriptive/exploratory: era- and
coach-identity confounding is controlled only bluntly (birth-cohort restriction), not via a
full model with coach/institution/cohort fixed effects.
