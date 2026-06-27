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

## Starting Point

- [Research session note](docs/research_session_2026-06-26_jfa_talent_development.md)
