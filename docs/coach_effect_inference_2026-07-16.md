# Do development coaches matter? A significance test (2026-07-16)

Follow-up to `docs/coach_network_design_2026-07-10.md`'s Phase C, which established that a
coach's own elite playing pedigree does NOT explain player outcomes, while leaving open
whether the observed coach-to-coach differences (明治's 栗田 83% vs 井澤 40% J1 rate, the
FC東京U-18 20pp spread) are real individual-coach effects or just era/sampling noise. This
analysis (`scripts/test_coach_effect_significance.py`) answers that question.

## Design

- Unit: **coach-at-institution** (a mover coach counts once per institution), keeping coach
  effects strictly nested inside institution effects.
- Sample: players with a primary development coach and a known birth year, restricted to
  coach-units with ≥10 players at institutions with ≥2 such units (the only slice where
  "coach vs institution" is even identifiable) → **527 players, 24 coach-units, 11
  institutions**.
- Test 1 — likelihood-ratio: logit `outcome ~ coach-unit + cohort` vs
  `outcome ~ institution + cohort`.
- Test 2 — **permutation** (the honest one for small/separated cells): shuffle coach labels
  within institution × birth-cohort cells (preserving both margins), 1,000 draws, count how
  often the shuffled LR beats the observed.

## Results

| outcome | LR (13 df) | χ² p | permutation p | verdict |
|---|---|---|---|---|
| reached_j1_ever | 46.8 | <0.0001 | **0.001** | **coach effects are real** |
| any_national_team_selection | 22.3 | 0.051 | 0.355 | not distinguishable from noise |

**Which coach a player developed under predicts J1 attainment beyond what the institution
and the player's birth cohort explain — at p=0.001 under the permutation null.** For
national-team selection the χ²'s borderline 0.05 evaporates under permutation (0.35): a
useful illustration of why the permutation test was worth running — the asymptotic χ² is
anticonservative at these cell sizes.

## Adjusted value-added (observed − institution+cohort expectation), J1 outcome

Top: 中央大学×佐藤健 (+45pp, n=10), 明治大学×栗田大輔 (+26pp, n=29), 桐蔭横浜大学×安武亨
(+24pp), 法政大学×長山一也 (+22pp). Bottom: 明治大学×井澤千秋 (−18pp, n=48), 中央大学×山口芳忠
(−16pp), 仙台大学×中屋敷眞 (−11pp). The Phase C 栗田/井澤 contrast survives cohort adjustment.

## What this does and does not establish

- Establishes: within the same institution, controlling birth cohort, players under some
  coaches reached J1 at rates that cannot plausibly be sampling noise. Combined with Phase C
  (pedigree ≠ development skill), the original research question's answer is now:
  **development-stage coaching involvement is associated with real, individual-coach-level
  differences in player outcomes, and those differences are not explained by the coach's own
  playing background.**
- Does NOT establish causation or the mechanism: a coach fixed effect bundles development
  skill with **recruiting skill** (a coach who attracts stronger 15-year-olds shows the same
  signature) and any unobserved institution-era shocks that coincide with coaching changes
  (facility upgrades, league reorganization). Separating development from selection would
  need entry-quality measures (e.g. youth-selection status at entry — itself partially
  post-treatment) or roster-level entry data we don't have.
- The identifiable core is small (527 of 1,974 attributed players) and university-heavy;
  J-academy units mostly fell below the 10-player floor because primary-coach attribution
  splits academy players across many short-tenured coaches.
