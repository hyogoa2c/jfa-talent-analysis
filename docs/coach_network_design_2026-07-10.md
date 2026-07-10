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

## Analytical cautions carried forward

- What the primary linkage measures is "was at institution X while coach Y was head coach" —
  exposure, not interaction intensity.
- Coach effects are confounded with institution effects (prestige, facilities, selection);
  identification leverage comes from coaches who moved BETWEEN institutions (coach fixed
  effects), which is exactly what the network representation surfaces.
- The selection-effect lesson from the player analysis (youth_selected controls) applies
  here doubly: strong institutions attract both strong players and strong coaches.
