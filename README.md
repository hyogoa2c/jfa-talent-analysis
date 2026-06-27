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

## Starting Point

- [Research session note](docs/research_session_2026-06-26_jfa_talent_development.md)
