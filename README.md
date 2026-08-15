# JFA Talent Analysis

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21944859.svg)](https://doi.org/10.5281/zenodo.21944859)

Archived at Zenodo — concept DOI [10.5281/zenodo.21944859](https://doi.org/10.5281/zenodo.21944859)
(resolves to the latest version). Code is MIT; data and documents CC BY 4.0 (see `LICENSE-DATA`,
which also states what the licence does not reach).

Research repository for quantitative analysis of Japanese football talent-development pathways, coach networks, and player career outcomes.

## Research Status (2026-07-18)

- **Canonical results live in [docs/results_canonical.md](docs/results_canonical.md)** — when any
  other document (including this README) disagrees with it, the canonical document wins.
- The Phase 1 research plan and pre-specified analysis plan are in
  [docs/research_plan_phase1.md](docs/research_plan_phase1.md); the external mid-study review
  that motivated them is [docs/review_results.md](docs/review_results.md).
- Scope note: this is an exploratory observational study of **final pre-professional pathway vs.
  career outcomes among players observed in J1/J2/J3 (2014-2025)** — not a causal evaluation of
  the Japanese development system, and not generalizable to the full development population.
- The coach-effect claim "permutation p=0.001" is **retracted** (attribution artifact); the
  current result is non-detection (p≈0.30). Coach research is frozen pending better data
  (see the retraction notice in [docs/coach_effect_inference_2026-07-16.md](docs/coach_effect_inference_2026-07-16.md)).

## Project Layout

- `docs/` - research notes and study design documents
- `src/jfa_talent_analysis/` - reusable Python package code
- `scripts/` - one-off data collection and processing scripts
- `notebooks/` - exploratory notebooks
- `data/` - local data workspace; raw/interim/processed outputs are gitignored
- `reports/` - generated analysis outputs; generated report files are gitignored
- `tests/` - automated tests

## Development

This project uses `uv`.

```bash
uv sync
uv run pytest
uv run ruff check .
```

Run the package entry point:

```bash
uv run jfa-talent-analysis
```

Build the local 2014 J1/J2/J3 season sample:

```bash
uv run python scripts/build_season_dataset.py --season 2014 --sleep 0.5
```

This writes local, gitignored CSV files under `data/interim/` and `data/processed/`.

Build player-season analytical features from the joined Japanese appearance sample:

```bash
uv run python scripts/build_player_season_features.py
```

The feature output includes midseason age, total minutes, J1 minutes, U21/U23 cumulative
minutes within the input data, and first observed J1 season.

Plan and run a small multi-season collection:

```bash
uv run python scripts/build_multi_season_dataset.py --start-season 2014 --end-season 2016 --dry-run
uv run python scripts/build_multi_season_dataset.py --start-season 2014 --end-season 2016 --limit-teams 1 --sleep 0.5
```

The multi-season driver writes a diagnostics CSV with per-season appearance rows, matched
rows, match rate, unmatched names, ambiguous names, league count, and team count. J3 is
automatically excluded before 2014.

Build player-season features after multi-season collection:

```bash
uv run python scripts/build_multi_season_features.py --start-season 2014 --end-season 2016
```

Suggest identity overrides for ambiguous same-name players using SFIX04 profile histories:

```bash
uv run python scripts/suggest_identity_overrides_from_profiles.py --appearance data/interim/appearance_records_2014_J1_J2_J3.csv --ambiguous data/interim/ambiguous_appearance_names_2014_J1_J2_J3.csv
```

The ambiguous diagnostics include the unresolved appearance context, so zero-appearance
roster rows can be distinguished from true unresolved appearance rows.

Build observed J.League reappearance candidates after a multi-year gap:

```bash
uv run python scripts/build_reappearance_candidates.py --target-start-season 2023 --target-end-season 2025
```

This is a gap-based candidate list, not proof of overseas transfer.

## Scripts

Source audits (run before building collectors):

- `audit_jleague_data_site.py` - audit J.League Data Site pages before building collectors
- `audit_sfpr01_season_availability.py` - audit SFPR01 season/league competition availability
- `audit_wikidata_reappearance_candidates.py` - audit Wikidata coverage for reappearance candidates

Collection:

- `poc_sfix03_player_universe.py` - sample Japanese players from SFIX03/search
- `poc_sfpr01_appearance_records.py` - sample appearance records for one team from SFPR01
- `collect_appearance_records_sample.py` - collect a season-league sample of SFPR01 appearance records
- `collect_appearance_records_multi_league_sample.py` - collect a small multi-league sample
- `build_season_dataset.py` - build one season end to end (universe, collection, join, diagnostics)
- `build_multi_season_dataset.py` - run the season builder over a year range with diagnostics
- `combine_csv_files.py` - combine CSV files with identical headers

Joining and identity resolution:

- `build_joined_appearance_sample.py` - join SFPR01 appearances to the SFIX03 player universe
- `analyze_name_match_sample.py` - analyze simple name-match rates between the two sources
- `summarize_joined_appearance_sample.py` - summarize a joined appearance sample
- `suggest_identity_overrides_from_profiles.py` - suggest identity overrides for ambiguous names from SFIX04 histories

Features:

- `build_player_season_features.py` - build player-season features from one joined season
- `build_multi_season_features.py` - combine joined seasons and build features over the window

Overseas review workflow (see [the overseas transfer source audit](docs/source_audit_overseas_transfers.md) for the full runbook):

- `build_reappearance_candidates.py` - flag players reappearing after a multi-season gap
- `build_overseas_manual_review_queue.py` - build the manual review queue from a Wikidata audit
- `enrich_manual_review_queue_with_wikipedia.py` - add Wikipedia search candidates to the queue
- `validate_overseas_manual_review_queue.py` - validate manual review entries before committing
- `build_overseas_transfer_outcomes.py` - materialize a moved_overseas outcome table from queue decisions

Pathway classification research (see [the pathway source pilot](docs/pathway_source_pilot_2026-07-03.md)):

- `build_pathway_candidates_from_wikipedia.py` - fetch candidate pre-professional pathway text from Wikipedia for manual/semi-automated review; run at full population scale 2026-07-04/05
- `verify_wikipedia_candidate_identity.py` - cross-check a candidate CSV's matched Wikipedia title against known player birth_date, rejecting junk-page titles outright; 84.3% confirmed overall at full scale
- `label_pathway_categories.py` - apply the `pathway_category` heuristic classifier to identity-confirmed candidates; 95.0% high-confidence, 5.0% flagged for manual review at full scale (2026-07-05)

National-team selection research (see [the national-team pilot](docs/national_team_pilot_2026-07-03.md)):

- `build_national_team_candidates_from_wikipedia.py` - fetch candidate national-team selection text from Wikipedia for manual/semi-automated review; run at full population scale 2026-07-04/05
- `label_national_team_selections.py` - apply the `any_national_team_selection`/category heuristic classifier to identity-confirmed candidates; 91.3% high-confidence, 8.7% flagged for manual review at full scale (2026-07-05)
- `build_pathway_review_queue.py` / `build_national_team_review_queue.py` - build human review queues from needs_review rows, joining back Wikipedia context text; see `docs/pathway_national_team_review_instructions_2026-07-05.md`
- The "no evidence" label's false-negative rate was spot-checked against JFA/club primary sources on a 45-player stratified sample: 2.2% strict (see [the JFA spot-check](docs/jfa_national_team_spot_check_2026-07-08.md))

Wikipedia full-extract corpus and derived evidence (see [the revision proposal](docs/data_collection_revision_proposal_2026-07-07.md)):

- `fetch_full_wikipedia_extracts.py` - cache full plaintext extracts for all identity-confirmed players (resume-safe; trimmed contexts lack the 出場歴 lines)
- `extract_j1_debuts_from_wikipedia.py` - parse J.League/J1 debut lines and validate against SFPR01 in-window ground truth; this cross-validation exposed and fixed a features bug where zero-appearance J1 roster registrations counted as reaching J1 (24% of reached_j1=1 rows)
- `label_overseas_stints.py` - classify senior-career foreign-club stints from career prose, extending moved_overseas beyond the 33-player manual queue; all 196 needs_review rows human-reviewed 2026-07-09 (see [the review record](docs/overseas_needs_review_2026-07-09.md), which also documents a "中国" (China vs. the domestic Chugoku regional league) classifier bug found and fixed mid-review

Exploratory modeling (docs/data_collection_plan.md's "Later Modeling"):

- `exploratory_modeling.py` - Random Forest vs logistic comparison on pre-career features (permutation importance + partial dependence in place of SHAP, whose numba dependency lacks Python 3.13 support); headline finding: with the current features/sample/settings RF shows no clear predictive improvement over logistic (not proof that nonlinear structure is absent), and the overseas outcome's birth-year effect is non-monotonic (a 1990-1997 birth-cohort peak the linear models miss)

Step 5 analysis-ready dataset (docs/data_collection_plan.md):

- `build_player_pathway_outcomes.py` - join collapsed player-season features with resolved pathway_category, any_national_team_selection, and moved_overseas outcomes into `data/processed/player_pathway_outcomes.csv`, one row per player (4,037 rows). Resolution prefers a human review queue's `reviewed_*` value over the classifier's auto-label; `pathway_category_source`/`national_team_selection_source` record which applied (`human_reviewed` / `auto_high_confidence` / `identity_not_confirmed`). `moved_overseas` (manual-queue column) covers only the narrow 2023-2025 reappearance-gap queue (33 players); the analysis outcome is `moved_overseas_final` (career-wide Wikipedia classifier + human review, 3,408/4,037 players).

## Starting Point

- [Canonical results](docs/results_canonical.md) and [Phase 1 research plan / SAP](docs/research_plan_phase1.md)
- [Research session note](docs/research_session_2026-06-26_jfa_talent_development.md)
- [Data collection plan](docs/data_collection_plan.md) (historical; the observation window and eligibility now live in the Phase 1 plan)
- [Overseas transfer source audit and review runbook](docs/source_audit_overseas_transfers.md)
