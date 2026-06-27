# J.League Data Site Source Audit

## Purpose

Identify which J.League Data Site pages can support Step 1: building the initial Japanese professional player universe.

## Candidate Pages

| Page ID | Label | Initial Assessment |
|---|---|---|
| `SFIX02` | 登録選手一覧 | Useful for current registered players by J1/J2/J3 and team. Team options appear to be dynamically populated. |
| `SFIX03` | 全選手一覧 | Best first candidate for all-player identity resolution. Has filters for last J.League team, nationality/origin, and position. |
| `SFPR01` | 選手出場記録 | Best candidate for season-level appearance records. Competition/team selectors appear to be dynamically populated. |

## Key Findings

### `SFIX03` All Players

The initial HTML contains:

- `last_belong_team` select with J.League club IDs.
- `national_origin` select with `0 = 日本` and `2 = 外国籍`.
- `field_position_type` select with `0 = GK`, `1 = DF`, `2 = MF`, `3 = FW`.
- Search endpoint hint: `/SFIX03/search`.

The page posts a form to `/SFIX03/search`. The JavaScript maps visible filter values to hidden fields:

| Visible field | Hidden field |
|---|---|
| `#team` | `team_year_id_ex` |
| `#nationalOrigin` | `national_origin_ex` |
| `#fieldPosition` | `field_position_type_ex` |

For the first player-universe PoC, test POSTing `national_origin_ex=0` to `/SFIX03/search`.

### `SFPR01` Player Appearance Records

The initial HTML contains:

- `competition_year` select.
- `competition_frame_id` select.
- `competition_id` select.
- `team_id` select.
- Search endpoint hints around `/SFPR01/`.

The page uses dynamic dependent selectors, so it needs a second audit pass after `SFIX03` is understood.

### `SFIX02` Registered Players

The initial HTML contains:

- League selector values: `1 = J1`, `2 = J2`, `3 = J3`.
- Endpoint hints: `/SFIX02/search`, `/SFIX02/searchTeams`.

This page may help validate current-season registered rosters, but it is not enough for 2005-onward historical player universe construction.

## Current Audit Script

Run:

```bash
uv run python scripts/audit_jleague_data_site.py
```

Default output:

```text
data/interim/source_audit/jleague_data_site_audit.json
```

The output is local-only and gitignored.

## Next PoC

Build a small script to test `SFIX03/search`:

1. POST a minimal search request for Japanese players.
2. Parse returned table rows.
3. Extract candidate fields:
   - source player ID if present.
   - player name.
   - last J.League team.
   - nationality/origin.
   - position.
   - profile/detail URL.
4. Save a small local sample to:

```text
data/interim/player_universe_sample.csv
```

Do not proceed to broad automated collection until the table fields and request behavior are confirmed.

## PoC Result

`SFIX03/search` POST succeeded with `national_origin_ex=0`.

Command:

```bash
uv run python scripts/poc_sfix03_player_universe.py --limit 100
```

Observed result:

- Parsed 7,162 Japanese player records.
- Wrote a 100-row local sample to `data/interim/player_universe_sample.csv`.
- The generated CSV is local-only and gitignored.

Extracted fields:

- `source_player_id`
- `name_ja`
- `name_en`
- `last_belong_team`
- `position`
- `birth_date`
- `height_cm`
- `weight_kg`
- `source_url`
- `retrieved_at`

This confirms that `SFIX03` can provide the base player identity universe. The next unresolved task is to connect these player IDs to season-level appearance records from `SFPR01`.

## `SFPR01` Appearance Record PoC

`SFPR01` uses dependent selectors:

1. `/SFPR01/createCompetitionFrames` with `competition_year`.
2. `/SFPR01/createCompetitions` with `competition_year` and `competition_frame_id`.
3. `/SFPR01/createTeams` with `competition_id`.

For 2014:

| League | competition_frame_id | competition_id |
|---|---:|---:|
| J1 | 1 | 372 |
| J2 | 2 | 373 |
| J3 | 3 | 380 |

`SFPR01/search` requires a team. Therefore appearance collection should run by:

```text
season x league x team
```

Command tested:

```bash
uv run python scripts/poc_sfpr01_appearance_records.py \
  --season 2014 \
  --league J1 \
  --team-id 1 \
  --team-name 鹿島 \
  --limit 100
```

Observed result:

- Parsed 31 player appearance records for 2014 J1 Kashima.
- Wrote local sample to `data/interim/appearance_records_sample.csv`.
- The generated CSV is local-only and gitignored.

Extracted fields:

- `season`
- `competition_frame_id`
- `competition_id`
- `league`
- `team_id`
- `team_name`
- `shirt_number`
- `name_ja`
- `appearances`
- `minutes`
- `goals`
- `source_url`
- `retrieved_at`

Important limitation:

- `SFPR01` does not expose player IDs in the appearance table.
- It includes both Japanese and foreign players.
- Joining to the Japanese player universe will require identity resolution using `name_ja`, team, season, and possibly additional profile/detail pages.

This is still useful for Phase 1 because it provides season-level outcome variables once identity resolution is handled.

## SFPR01 Season Availability Audit

Season/league metadata can be audited with:

```bash
uv run python scripts/audit_sfpr01_season_availability.py \
  --start-season 2005 \
  --end-season 2016
```

Observed result from the 2005-2016 audit:

| Season range | SFPR01 J1/J2 availability | Notes |
|---|---|---|
| 2005-2013 | Not available via current `createCompetitionFrames` flow | J1/J2 expected frame IDs were not returned. Backfill needs a separate source-availability audit or another source. |
| 2014 | Available | J1, J2, and J3 each have one competition. |
| 2015-2016 | Available | J1 has two competitions (`1st` and `2nd` stages); J2 and J3 each have one competition. |

Implication:

- The current automated SFPR01 pipeline should expand first across 2014 onward.
- The 2005-2013 target period should be treated as a separate backfill problem instead of being forced through the current SFPR01 collector.

## 2014-2016 Identity Disambiguation Pass

Ambiguous Japanese names in the 2014-2016 joined sample were checked against `SFIX04`
player detail pages. The detail page contains season/team history, so ambiguous rows can be
resolved when exactly one candidate has a matching season and team.

Helper command:

```bash
uv run python scripts/suggest_identity_overrides_from_profiles.py \
  --appearance data/interim/appearance_records_2014_J1_J2_J3.csv \
  --appearance data/interim/appearance_records_2015_J1_J2_J3.csv \
  --appearance data/interim/appearance_records_2016_J1_J2_J3.csv \
  --ambiguous data/interim/ambiguous_appearance_names_2014_J1_J2_J3.csv \
  --ambiguous data/interim/ambiguous_appearance_names_2015_J1_J2_J3.csv \
  --ambiguous data/interim/ambiguous_appearance_names_2016_J1_J2_J3.csv
```

Accepted overrides are stored in:

```text
data/manual/player_identity_overrides.csv
```

Observed improvement after applying SFIX04-backed overrides:

| Season | Matched rows before | Matched rows after | Ambiguous names before | Ambiguous names after |
|---|---:|---:|---:|---:|
| 2014 | 1,355 | 1,364 | 10 | 2 |
| 2015 | 1,746 | 1,756 | 9 | 3 |
| 2016 | 1,899 | 1,913 | 10 | 0 |

Remaining ambiguous rows in 2014-2015 were zero-appearance roster rows, so they were left
unresolved for now. The primary analysis population should distinguish true appearance rows
from registered-but-zero-appearance rows.

## 2014 J1 Season-League Sample

Collector tested:

```bash
uv run python scripts/collect_appearance_records_sample.py \
  --season 2014 \
  --league J1 \
  --sleep 0.5 \
  --output data/interim/appearance_records_2014_J1.csv
```

Observed result:

- Collected 555 appearance rows.
- Covered all 18 J1 clubs in 2014.
- Output is local-only and gitignored.

Simple name match against the `SFIX03` Japanese player universe:

```bash
uv run python scripts/poc_sfix03_player_universe.py \
  --limit 10000 \
  --output data/interim/player_universe_sample.csv

uv run python scripts/analyze_name_match_sample.py \
  --players data/interim/player_universe_sample.csv \
  --appearances data/interim/appearance_records_2014_J1.csv
```

Observed result:

| Metric | Value |
|---|---:|
| appearance rows | 555 |
| unique appearance names | 547 |
| Japanese player universe names | 7,129 |
| matched unique names | 460 |
| simple name match rate | 0.841 |

The unmatched sample is dominated by foreign players, which is expected because `SFPR01` returns all players while the `SFIX03` universe sample is filtered to Japanese players.

Implication:

- Name-based matching is good enough for a first-pass Japanese-player filter.
- A later identity resolution layer is still required for duplicate names, name changes, and ambiguous records.

## Joined 2014 J1 Japanese-Player Sample

Join script:

```bash
uv run python scripts/build_joined_appearance_sample.py \
  --players data/interim/player_universe_sample.csv \
  --appearances data/interim/appearance_records_2014_J1.csv
```

Summary script:

```bash
uv run python scripts/summarize_joined_appearance_sample.py
```

Observed result:

| Metric | Value |
|---|---:|
| appearance rows | 555 |
| automatically matched rows | 463 |
| unique matched players | 457 |
| unmatched unique names | 87 |
| ambiguous unique names | 3 |
| total matched minutes | 510,526 |
| total matched goals | 557 |

The three ambiguous names in the 2014 J1 sample are:

- 吉川 健太
- 松田 陸
- 田中 達也

These names have multiple candidates in the `SFIX03` player universe. They should be resolved using season, team, position, birth date, and profile history. If automatic resolution remains uncertain, manual mapping is acceptable.

Current identity-resolution policy:

1. Auto-match exact normalized Japanese names with one `SFIX03` candidate.
2. Exclude unmatched names from the Japanese-player output for now.
3. Write unmatched names to `data/interim/unmatched_appearance_names_2014_J1.csv`.
4. Write ambiguous names to `data/interim/ambiguous_appearance_names_2014_J1.csv`.
5. Add a manual override table later for ambiguous or high-value records.

This produces a usable first-pass Japanese-player season outcome dataset while making unresolved identity issues explicit.

## 2014 J1/J2/J3 Combined Sample

Unified build script:

```bash
uv run python scripts/build_season_dataset.py --season 2014 --sleep 0.5
```

This runs:

1. `SFIX03` Japanese player universe collection.
2. `SFPR01` appearance collection by league and team.
3. League CSV combination.
4. Japanese-player identity join.
5. Summary output.

Multi-league collection script:

```bash
uv run python scripts/collect_appearance_records_multi_league_sample.py \
  --season 2014 \
  --sleep 0.5
```

Combine league CSVs:

```bash
uv run python scripts/combine_csv_files.py \
  data/interim/appearance_records_2014_J1.csv \
  data/interim/appearance_records_2014_J2.csv \
  data/interim/appearance_records_2014_J3.csv \
  --output data/interim/appearance_records_2014_J1_J2_J3.csv
```

Observed raw collection:

| League | Teams | Rows |
|---|---:|---:|
| J1 | 18 | 555 |
| J2 | 22 | 714 |
| J3 | 11 regular clubs parsed | 293 |
| Combined | 51 regular clubs parsed | 1,562 |

Note: 2014 J3 includes `J-22` in the team selector. `J-22` was a temporary U-22 selection team composed of players registered with other J1/J2 clubs, not a regular club team. It existed only for a limited period and is excluded from the primary analysis because club affiliation, team-level development investment, and appearance opportunity are not comparable with regular J.League clubs.

Join to `SFIX03` Japanese-player universe:

```bash
uv run python scripts/build_joined_appearance_sample.py \
  --players data/interim/player_universe_sample.csv \
  --appearances data/interim/appearance_records_2014_J1_J2_J3.csv \
  --output data/processed/appearance_records_2014_J1_J2_J3_japanese_matched.csv \
  --unmatched-output data/interim/unmatched_appearance_names_2014_J1_J2_J3.csv \
  --ambiguous-output data/interim/ambiguous_appearance_names_2014_J1_J2_J3.csv
```

Observed joined result:

| Metric | Value |
|---|---:|
| appearance rows | 1,562 |
| automatically matched rows | 1,355 |
| unique matched players | 1,306 |
| unmatched unique names | 184 |
| ambiguous unique names | 10 |
| total matched minutes | 1,656,822 |
| total matched goals | 1,894 |

This confirms that the 2014-onward collection pipeline is feasible across J1/J2/J3, with the following known gaps:

- `J-22` is excluded from primary analysis.
- ambiguous Japanese names.
- foreign players intentionally excluded after joining to the Japanese player universe.
- 2013 and earlier data lives behind a separate legacy site link and needs a separate audit.

## Manual Identity Overrides

Ambiguous name resolution can be handled with a small manual override table:

```text
data/manual/player_identity_overrides.csv
```

Schema:

| Column | Description |
|---|---|
| `season` | Season year |
| `league` | League label |
| `team_name` | Team name in appearance record |
| `name_ja` | Japanese player name in appearance record |
| `source_player_id` | Chosen `SFIX03` player ID |
| `note` | Rationale or source note |

The file is intentionally committed as an empty template. Future manual resolutions should be explicit and reviewable.
