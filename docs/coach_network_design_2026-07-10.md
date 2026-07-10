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

## Pilot in progress

A 15-institution pilot (5 universities / 5 high schools / 5 J-club academies, drawn from the
head of the concentration distribution) is testing whether 2000-2025 head-coach timelines
are reconstructable per institution type, written incrementally to
`data/interim/coach_network/institution_coach_pilot.md`. Scale-up decisions (how many
institutions, which types first) wait on its results, per this project's standard
audit→pilot→tool→verify sequence.

## Analytical cautions carried forward

- What the primary linkage measures is "was at institution X while coach Y was head coach" —
  exposure, not interaction intensity.
- Coach effects are confounded with institution effects (prestige, facilities, selection);
  identification leverage comes from coaches who moved BETWEEN institutions (coach fixed
  effects), which is exactly what the network representation surfaces.
- The selection-effect lesson from the player analysis (youth_selected controls) applies
  here doubly: strong institutions attract both strong players and strong coaches.
