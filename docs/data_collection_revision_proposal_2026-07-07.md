# Data Collection Revision Proposal (2026-07-07)

Written after running the Initial Analysis Targets from `docs/data_collection_plan.md`
(`scripts/analyze_pathway_outcomes.py`, output in `reports/generated/initial_analysis_report.md`,
gitignored — rerun the script to regenerate it). Three gaps surfaced, ranked by how much they
threaten the validity of results already produced versus how much they block results not yet
attempted.

## 1. [High priority, DONE 2026-07-08] `reached_j1` and `first_j1_age` are unreliable for cohorts likely to have debuted before 2014

**This is a new finding from running the regression/survival analysis, not something the earlier
audits caught**, though it is a direct consequence of the already-documented "SFPR01 has no
appearance-record data before 2014" limitation (`docs/data_collection_plan.md`'s Data Quality
Risks table) — what's new here is quantifying *which players* that gap actually silently affects
and *how much*.

**Evidence.** `age_at_first_observed` (the player's age in their first season appearing in this
project's 2014-2025 SFPR01 collection) by birth cohort:

| birth cohort | median age at first observation | % first observed at age ≥22 |
|---|---|---|
| `<1990` | 28 | 100% |
| `1990-1994` | 23 | 84.6% |
| `1995-1999` | 22 | 56.7% |
| `2000-2004` | 20 | 41.5% |
| `2005+` | 18 | 0% |

Typical J-League pro debut age is roughly 18-20. A player first observed at age 23-28 was almost
certainly already several seasons into their career when this dataset's window opens in 2014 —
if their J1 debut happened before 2014, this dataset has no way to see it. `reached_j1` for such a
player defaults to `0` (never reached J1 *within the observed window*) even if they debuted in J1
in, say, 2010 and this dataset only observes them later, e.g. in a J2/J3 stint. The same problem
contaminates `first_j1_age` in the other direction for players who *are* marked `reached_j1=1`
but whose true debut predates the window: the recorded `first_j1_age` is really "age at first
observed J1 appearance within 2014-2025," which could be a *return* to J1, not the actual debut —
inflating the apparent debut age for exactly the older cohorts.

**Consequence for the analysis just run.** The `<1990` and `1990-1994` cohorts (1,467 of 3,266
players in the regression sample, 44.9%) carry this risk most heavily. `docs/data_collection_plan.md`
already restricts its own "primary analytical cohort" to players born 1990 or later specifically
to sidestep pre-2014-history problems, but the evidence above shows that boundary alone doesn't
fully solve it — 84.6% of the 1990-1994 slice is still at risk. The birth_year control in the
logistic regressions partially absorbs a *smooth* age-related trend, but this is a *structural*
cohort-specific data gap, not a smooth trend, so it isn't fully corrected by that control.

**Proposed fixes, in order of preference:**

1. **Backfill pre-2014 J1 debut year via Wikipedia**, reusing this project's now-proven
   audit → pilot → fetch-tool → identity-verify → heuristic-classify → human-review pattern
   (see `docs/pathway_source_pilot_2026-07-03.md`/`docs/national_team_pilot_2026-07-03.md`).
   Japanese Wikipedia biographies routinely state a player's J1 (or "J1のリーグ戦" /
   "トップチーム") debut year in prose (e.g. "2009年、J1初出場"), the same kind of prose this
   project's classifiers already parse for pathway/national-team evidence. A pilot on a small
   stratified sample of the `<1990`/`1990-1994` cohorts (say 20-25 players, mirroring the
   22-player pilots already run) would show whether Wikipedia coverage is good enough to backfill
   `reached_j1`/`first_j1_age` for this specific population before committing to full-scale
   collection.
2. **Restrict `reached_j1`-based modeling to cohorts largely immune to this gap** (roughly
   `2000-2004` and `2005+`, where a majority were first observed near typical debut age) as an
   interim measure while (1) is pursued, explicitly re-running the regression/survival analysis
   on that restricted sample and comparing coefficients to the full-population version already
   produced — if they're similar, the full-population result is probably safe to keep using; if
   they diverge, that confirms the bias is material.
3. Wikidata's `P54` club-history statements (with `P580`/`P582` start/end date qualifiers) could
   answer the narrower question "did this player ever play for a J1-tier club, and when" faster
   than a full Wikipedia read — but both prior pilots found Wikidata's coverage/completeness
   noticeably worse than Wikipedia's for this project's cohort, so treat this as a fast
   supplementary cross-check rather than the primary source, consistent with this project's
   established Wikipedia-first pattern.

**Resolved 2026-07-08.** Fetched full Wikipedia extracts for all 3,403 confirmed players,
parsed "Jリーグ初出場" debut lines (`debut_extraction.py`), and validated against SFPR01
in-window ground truth: 97.3% agreement (321/330) on debuts SFPR01 could also see, confirming
the extractor before trusting its 340 pre-2014 backfill values. This work also surfaced a
**separate, larger bug**: `first_j1_season_by_player` was counting zero-appearance J1 roster
registrations (bench-only, 特別指定/2種登録 players) as "reaching J1" — 24.2% of all
`reached_j1=1` players (443/1,834) had zero career J1 minutes. Fixed in `features.py`
(appearances>0, falling back to minutes>0). `reached_j1_final` now combines the corrected
SFPR01 signal with the Wikipedia backfill; a sensitivity rerun restricted to `birth_year>=2000`
(largely immune to the original truncation risk) shows consistent coefficients with the
full-population regression (university odds ratio 0.31→0.28 for J1 attainment, 0.24→0.24 for
national-team selection), so the truncation problem does not appear to flip the substantive
findings, though the roster-only fix did shift the raw rates materially (see the regenerated
`reports/generated/initial_analysis_report.md`).

## 2. [High priority, DONE 2026-07-08] `moved_overseas` covers 0.8% of the population, and not randomly

`data/processed/player_pathway_outcomes.csv` has a resolved `moved_overseas` value for only 33 of
4,037 players. All 33 come from `overseas_transfer_outcomes_2023_2025_gap2.csv`, itself built from
a manual review queue of players who were *already flagged* as plausible overseas movers by an
observed 2023-2025 J.League reappearance-after-gap pattern
(`docs/source_audit_overseas_transfers.md`'s original scope). This is a selected candidate set,
not a sample of the full population — a player who moved overseas before 2023, or who moved
without ever reappearing in J.League data afterward, is invisible to this queue by construction.
`reports/generated/initial_analysis_report.md`'s "Overseas Move: Not Modeled" section already
declines to fit a regression on this subset for exactly this reason (any pathway association found
would reflect who gets flagged as a reappearance candidate, not who actually moves abroad).

**Proposed fix:** extend the same Wikipedia-based pipeline already built and validated for pathway
and national-team selection to the full 4,037-player population for overseas transfer specifically
— an audit already exists (`docs/source_audit_overseas_transfers.md`) and the
`enrich_manual_review_queue_with_wikipedia.py` groundwork is already in place; what's missing is
running fetch + identity-verify + a heuristic classifier (e.g. detecting foreign league/club names
in a player's career-history prose, the same kind of pattern the pathway classifier already
detects for foreign academy relocation) at full population scale, the same way pathway and
national-team selection were scaled in this project's last working session. This is the single
largest remaining gap in outcome-variable coverage: two of the three Phase 1 research-question
outcomes (`reached_j1`, `any_national_team_selection`) now have population-scale coverage;
`moved_overseas` does not.

**Resolved 2026-07-08.** Built `overseas_classification.py`, a heuristic classifier over
Wikipedia career prose (foreign league/country+division/club-move patterns, with guards against
parents' relocations, short study-abroad stints, youth academies abroad, other players' moves,
and failed trials) — validated 32/32 with 0 silently wrong against the pathway/national-team
pilot's golden set, and cross-checked against the existing 33-player manually-reviewed queue
(agreement on all but definitional differences, e.g. a player who moved abroad outside the
originally-reviewed gap window). `moved_overseas_final` now covers 3,408 of 4,037 players
(84.4%), preferring the original manual review where present. This is a heuristic classifier's
output, not yet subject to the same needs_review human-review pass pathway/national-team
selection received — the logistic regression added to the analysis report treats it as
informative but less authoritative pending that review.

## 3. [Medium priority, DONE 2026-07-08] National-team "no evidence" rows were never spot-checked against JFA

`docs/national_team_pilot_2026-07-03.md` explicitly recommended spot-checking a sample of the "no
national-team evidence found" majority against JFA's per-occasion squad-announcement pages before
trusting it as a true-negative at scale, since Wikipedia's absence of a `代表歴`/`代表経歴` section
is suggestive but not conclusive. That spot-check was never run — `any_national_team_selection=no`
currently covers 1,968 of 3,403 confirmed players (57.8%) on Wikipedia-absence evidence alone.

**Proposed fix:** draw a stratified random sample (e.g. 15-20 players per tier, ~45-60 total) of
`no`-labeled players and check them against `jfa.jp`'s per-year/per-competition squad archive
pages (confirmed browsable by year 2014-2026 in the original audit). This is a bounded, one-time
verification cost that would give a concrete false-negative rate estimate for the `no` label,
rather than leaving it as an open caveat indefinitely.

**Executed 2026-07-08** (see `docs/jfa_national_team_spot_check_2026-07-08.md`): 45-player
stratified sample, strict false-negative rate **2.2%** (1/45; 8.9% including candidate-camp-only
call-ups), concentrated in the low-minutes tier. The one confirmed miss and one of the three
candidate cases were absent from the players' own Wikipedia articles entirely (found only via
club press releases) — quantifying the Wikipedia-absence method's blind spot for brief
youth-level call-ups. The `no` label is usable at scale with this documented error rate.

## Not a collection gap, but an interpretation caveat worth carrying forward

The `2005+` birth cohort's pathway distribution (71.3% `j_club_academy`, only 7.7% `university`,
per the descriptive table) is not evidence of a generational shift toward club academies — this
cohort is mostly still too young to have reached university age, so `university`-pathway members
of this cohort are systematically under-represented simply because most haven't gotten there yet
(right-censoring, not a data gap). Any claim about pathway trends over time should exclude or
heavily caveat the `2005+` cohort until it matures in future data collection.

## Suggested sequencing

1 (threatens the validity of the J1-attainment results already produced) → 2 (the largest fully
missing outcome, blocking a third of the Phase 1 research question) → 3 (refines an
already-mostly-usable variable rather than fixing something broken). All three follow the same
audit → pilot → tool → verify → classify → human-review pattern this project has now run twice
successfully; no new methodology needs to be invented, only applied to new populations/questions.
