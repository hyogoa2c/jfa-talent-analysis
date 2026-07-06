# JFA Talent Analysis

Research repository for quantitative analysis of Japanese football talent-development pathways, coach networks, and player career outcomes.

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
- `label_pathway_categories.py` - apply the `pathway_category` heuristic classifier to identity-confirmed candidates; 93.0% high-confidence, 7.0% flagged for manual review at full scale (2026-07-05)

National-team selection research (see [the national-team pilot](docs/national_team_pilot_2026-07-03.md)):

- `build_national_team_candidates_from_wikipedia.py` - fetch candidate national-team selection text from Wikipedia for manual/semi-automated review; run at full population scale 2026-07-04/05
- `label_national_team_selections.py` - apply the `any_national_team_selection`/category heuristic classifier to identity-confirmed candidates; 90.2% high-confidence, 9.8% flagged for manual review at full scale (2026-07-05)

## Starting Point

- [Research session note](docs/research_session_2026-06-26_jfa_talent_development.md)
- [Data collection plan](docs/data_collection_plan.md)
- [Overseas transfer source audit and review runbook](docs/source_audit_overseas_transfers.md)
