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
