# Data Collection Plan

## Purpose

Build the minimum viable dataset needed to test whether Japanese football player-development pathways are associated with player career outcomes.

The first phase deliberately excludes coach-network analysis. Coach data will be added after the player-pathway and outcome dataset is stable.

## Phase 1 Research Question

Do development pathways for Japanese professional football players explain differences in post-debut growth speed, top-league attainment, overseas transfers, and national-team selection?

## Scope

Primary population:

- Japanese-nationality players who appeared in official J1, J2, or J3 matches from 2005 onward.

Primary analytical cohort:

- Players born in 1990 or later, or players who were U-15 or younger in 2005.

Sensitivity cohorts:

- Players born in 1985 or later.
- Players born in 1995 or later.
- Players born in 2000 or later.

## Collection Principles

1. Start with structured, source-attributed records.
2. Keep raw data separate from normalized data.
3. Store source URLs and retrieval dates for every record.
4. Preserve conflicting source claims instead of overwriting them.
5. Avoid scraping sites before checking their terms and robots policy.
6. Prefer official or stable sources for canonical identifiers.

## Directory Layout

```text
data/
  raw/         # downloaded or manually captured source data; gitignored
  interim/     # cleaned but not final normalized data; gitignored
  processed/   # analysis-ready datasets; gitignored
```

The `data/` workspace is local-only. Generated datasets should not be committed unless they are small, redistributable, and legally safe.

## Core Tables

### players

One row per person.

| Column | Description |
|---|---|
| player_id | Internal stable identifier |
| canonical_name | Normalized player name |
| name_ja | Japanese name if available |
| name_en | English/romaji name if available |
| birth_date | Date of birth |
| nationality | Nationality |
| position | Primary position |
| height_cm | Optional |
| dominant_foot | Optional |
| source_url | Source URL for canonical profile |
| retrieved_at | Retrieval date |

### teams

One row per club, school, university, academy, national team, or overseas team.

| Column | Description |
|---|---|
| team_id | Internal stable identifier |
| canonical_name | Normalized team name |
| team_type | pro_club / youth_academy / high_school / university / grassroots_club / jfa_academy / national_team / overseas_club |
| country | Country |
| prefecture | Japanese prefecture if applicable |
| source_url | Source URL |
| retrieved_at | Retrieval date |

### player_team_stints

One row per player-team period.

| Column | Description |
|---|---|
| stint_id | Internal stable identifier |
| player_id | Player identifier |
| team_id | Team identifier |
| from_year | Start year |
| to_year | End year |
| age_category | U12 / U15 / U18 / university / senior / unknown |
| pathway_category | j_club_academy / high_school / university / jfa_academy / grassroots_club / pro / overseas / unknown |
| evidence_text | Short source-backed note |
| source_url | Source URL |
| retrieved_at | Retrieval date |
| confidence | high / medium / low |

### appearances_by_season

One row per player-season-club-league.

| Column | Description |
|---|---|
| player_id | Player identifier |
| season | Season year |
| team_id | Club identifier |
| league | J1 / J2 / J3 / other |
| appearances | Match appearances |
| starts | Starts if available |
| minutes | Minutes played if available |
| goals | Goals if available |
| age_in_season | Age during season |
| source_url | Source URL |
| retrieved_at | Retrieval date |

### national_team_selections

One row per player national-team selection event or squad listing.

| Column | Description |
|---|---|
| selection_id | Internal stable identifier |
| player_id | Player identifier |
| year | Selection year |
| category | A / U23 / U20 / U19 / U18 / U17 / U16 / U15 / university / other |
| competition_or_match | Competition, camp, or match name |
| source_url | Source URL |
| retrieved_at | Retrieval date |

### transfers

One row per transfer or loan move when available.

| Column | Description |
|---|---|
| transfer_id | Internal stable identifier |
| player_id | Player identifier |
| from_team_id | Source team |
| to_team_id | Destination team |
| year | Transfer year |
| transfer_type | permanent / loan / return / free / unknown |
| destination_country | Country of destination team |
| fee | Fee if available and legally usable |
| source_url | Source URL |
| retrieved_at | Retrieval date |

## Derived Features

### Pathway Features

| Feature | Description |
|---|---|
| primary_pathway | Main pathway before first pro appearance |
| has_j_club_academy | J-club academy experience |
| has_high_school | High-school football experience |
| has_university | University football experience |
| has_jfa_academy | JFA academy experience |
| pathway_count | Number of distinct pathway categories |
| pathway_diversity | Simple diversity score across pathway categories |

### Career Timing Features

| Feature | Description |
|---|---|
| pro_debut_age | Age at first senior pro appearance |
| first_j1_age | Age at first J1 appearance |
| first_overseas_age | Age at first overseas move |
| first_a_national_team_age | Age at first A national team selection |
| u21_minutes | Total senior-league minutes before age 21 |
| u23_minutes | Total senior-league minutes before age 23 |

### Outcome Features

| Feature | Description |
|---|---|
| reached_j1 | Whether player reached J1 |
| established_j1 | Whether player exceeded a minutes threshold in J1 |
| moved_overseas | Whether player moved to an overseas club |
| moved_to_europe | Whether player moved to a European club |
| selected_a_national_team | Whether player was selected for the senior national team |
| selected_youth_national_team | Whether player was selected for a youth national team |

## Source Candidates

### Highest Priority

| Source | Expected Use | Notes |
|---|---|---|
| J.League official data/profile pages | Player profiles, appearances, club history | Check availability by season and usage restrictions |
| JFA official pages | National-team selections, youth teams, academy context | Prefer for national-team records |
| Club official profiles | Player career histories and academy affiliations | Useful for pathway classification |

### Secondary Sources

| Source | Expected Use | Notes |
|---|---|---|
| Wikipedia / Wikidata | Player identity resolution and career history hints | Must verify against better sources |
| Soccerway / WorldFootball.net | Appearance and transfer cross-checks | Terms must be checked |
| Transfermarkt | Market value, transfer movement, overseas move hints | Treat carefully; scraping and redistribution may be restricted |

### Manual Research Sources

| Source | Expected Use | Notes |
|---|---|---|
| High-school and university team pages | Youth pathway records | Often incomplete and inconsistent |
| News articles/interviews | Early pathway and coach references | Use source attribution and confidence scoring |
| JFA academy pages | JFA academy alumni and program records | Likely useful for a specific pathway flag |

## Collection Order

### Step 1: Player Universe

Create the initial list of Japanese players with J1/J2/J3 appearances from 2005 onward.

Output:

```text
data/interim/player_universe.csv
```

Minimum fields:

- canonical_name
- birth_date
- nationality
- first_observed_season
- first_observed_league
- first_observed_club
- source_url

### Step 2: Season Outcomes

Collect appearances by season for the player universe.

Output:

```text
data/interim/appearances_by_season.csv
```

Minimum fields:

- player
- season
- club
- league
- appearances
- minutes if available

Current implementation status:

- `scripts/build_season_dataset.py` builds a local 2014 J1/J2/J3 sample from J.League Data Site.
- `scripts/build_multi_season_dataset.py` runs the season builder over a year range and writes per-season diagnostics.
- `scripts/build_player_season_features.py` derives player-season analytical features from the joined Japanese-player appearance sample.
- `scripts/build_multi_season_features.py` combines joined season files over a year range and builds player-season features from the combined observation window.
- `scripts/suggest_identity_overrides_from_profiles.py` uses SFIX04 season/team histories to suggest manual identity overrides for ambiguous same-name players.
- Ambiguous diagnostics are written at unresolved appearance-context level, including season, league, team, shirt number, appearances, minutes, and goals.
- `scripts/build_reappearance_candidates.py` flags players who reappear in a target window after an observed J.League appearance gap. This is useful for candidate discovery, but it is not proof of overseas transfer.
- The collection script supports multiple competitions inside one league frame, which is needed for 2015 and 2016 J1 two-stage seasons.
- A 2014-2025 SFPR01 availability audit confirmed the J1/J2/J3 frames contain only league
  competitions (one per season, plus the 2015/2016 J1 1st/2nd stages). Playoff and
  championship matches live in other frames, so league minutes are not double-counted;
  the 2015/2016 championship matches are simply outside the collected league totals.
- J3 is automatically excluded before 2014 in the multi-season driver.
- Current derived features are based only on seasons included in the input file, so first-observed season, first-J1 season, and cumulative U21/U23 minutes are observation-window measures until multi-season collection is run.
- A full 2005-2013 SFPR01 availability audit (`scripts/audit_sfpr01_season_availability.py
  --start-season 2005 --end-season 2013`) confirmed zero competition frames for every season
  and league in that range, not just 2013. This was cross-checked directly against the SFPR01
  search page's own season `<select>` dropdown, whose options span only 2014 through the
  current season (plus youth/special entries) — 2005-2013 are not offered as choices at all.
  This is a hard boundary of the SFPR01 endpoint's dataset, not a request-format or
  collection-code issue: **SFPR01 has no appearance-record data before 2014.** 2005-2013
  backfill for the primary population (defined above as players active from 2005 onward)
  therefore requires an entirely different source (e.g. archived league records, JFA/club
  official histories, or third-party databases from the candidate list in
  `docs/source_audit_overseas_transfers.md`, subject to the same terms-of-use checks), not
  further collection from this source. Until that source is identified, treat 2014 as the
  practical start of the appearance/outcome-feature observation window and the 2005-2013
  portion of the primary population definition as aspirational rather than currently
  collectible.
- 2020-2022 collection is available through SFPR01, but should be treated as a COVID-period block because league/team counts differ from surrounding seasons.

### Step 3: Pathway Classification

Classify each player into pre-professional pathway categories.

Output:

```text
data/interim/player_pathways.csv
```

### Overseas Transfers and Returnees

The current J.League Data Site pipeline can flag observed J.League reappearance after a
multi-season gap, but this is only a candidate signal for overseas transfer or overseas
return. It can also reflect JFL, regional leagues, injury periods, college contexts, loans,
or other unobserved domestic stints.

Before treating overseas transfer or overseas-return status as an outcome variable, add a
separate source audit for transfer and career-history sources. Candidate source categories:

- JFA/J.League and club official announcements.
- Club profile career histories.
- Wikidata/Wikipedia as identity and career-history hints.
- Transfermarkt, Soccerway, WorldFootball.net, or other football databases, subject to
  terms-of-use and redistribution constraints.
- News articles for individual overseas moves and returns.

Near-term use:

- Keep `scripts/build_reappearance_candidates.py` as a discovery tool.
- Do not label reappearance candidates as overseas returnees without source-backed transfer
  evidence.

Start with simple categories:

- `j_club_academy`
- `high_school`
- `university`
- `jfa_academy`
- `grassroots_club`
- `unknown`

### Step 4: National-Team Selection

Collect A national-team and youth national-team selection records.

Output:

```text
data/interim/national_team_selections.csv
```

### Step 5: Analysis-Ready Dataset

Join the tables and create derived features.

Output:

```text
data/processed/player_pathway_outcomes.csv
```

## Initial Analysis Targets

### Descriptive Analysis

- Distribution of primary pathway by birth cohort.
- J1 attainment rate by primary pathway.
- Overseas move rate by primary pathway.
- National-team selection rate by primary pathway.
- Median pro debut age by primary pathway.

### Modeling

- Logistic regression for J1 attainment.
- Logistic regression for overseas move.
- Logistic regression for national-team selection.
- Survival analysis for time to J1 debut.
- Survival analysis for time to overseas move.

### Later Modeling

- Random Forest or XGBoost for exploratory prediction.
- SHAP analysis to inspect feature contributions.
- Network metrics after coach data is added.

## Data Quality Risks

| Risk | Mitigation |
|---|---|
| Name ambiguity | Maintain aliases and date-of-birth matching |
| Team name changes | Use stable internal team IDs |
| Missing minutes data | Keep appearances as fallback |
| Incomplete youth histories | Store confidence and source coverage |
| Conflicting pathway claims | Preserve source-specific claims, resolve only in processed layer |
| Site terms restrictions | Document source permissions before automated scraping |
| No SFPR01 appearance data before 2014 (confirmed) | Treat 2014 as the practical collection start; source a separate 2005-2013 provider before extending the primary population's start year in analysis |

## Terms and Compliance Checklist

Before building a scraper for a source:

- Read the source terms of use.
- Check `robots.txt`.
- Prefer official APIs or downloadable datasets if available.
- Rate-limit requests.
- Store only fields required for research.
- Do not commit raw scraped data if redistribution rights are unclear.
- Keep source URLs and retrieval dates.

## Phase 2: Coach Network Extension

After Phase 1 is stable, add coach records.

Additional tables:

- `coaches`
- `coach_team_stints`
- `player_coach_exposures`

Initial network metrics:

- coach degree centrality
- coach betweenness centrality
- number of future pro players coached
- number of future national-team players coached
- bridge score across academy/high-school/university/pro pathways

Phase 2 should use graph storage only after the relational schema is stable. A property graph such as Neo4j is a good fit once relationship data becomes large enough to justify it.
