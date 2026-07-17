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

## Plan 2 addendum (same day): the lineage graph

`scripts/build_coach_lineage.py` matches each verified coach article's own playing stints
against the 86 researched institutions' tenure timelines: **27 mentored_by edges** (coach A
played under researched coach B — years overlapping), 74 alumni edges, 16 mover edges.
Interactive visualization published as a Claude artifact (coach_lineage_network.html).

- Largest confirmed lineage: **坂本康博 (大阪体育大学, 1973–2017) → 黒田剛・島田貴裕・松尾元太**;
  his grand-students (players attributed to those three) reached J1 at 64% (n=22).
- Other multi-student mentors: 小嶺忠敏 (国見), 大澤英雄 (国士舘), 桐田英樹 (東京学芸大),
  志波芳則 (東福岡).
- Players whose primary coach is **in-lineage** (his own developer is in our tenure table)
  reached J1 at **71% vs 41%** in the mature cohort — but n=17, in-lineage coaches skew
  toward strong institutions, and edge coverage is era-biased (a missing edge means "tenure
  table doesn't reach that era", not "no relationship"). Suggestive, not established.
- The 国見 unnamed-figurehead row is now excluded as a gap placeholder everywhere
  (`is_gap_placeholder`), removing 3 spurious mentor edges and one fake coach from the
  exposure join.

## Era-gap deepening result (2026-07-17)

Targeted pre-2015 gap-filling at the 5 highest-loss researched academies (柏/マリノス/ジェフ/
浦和/ヴェルディ, 150 gap players) recovered 19 tenure rows (14 named coaches). Canonical
table now 359 rows. J-youth primary-coach coverage 52% → **57%**. Highlights: 柏レイソルU-18
1993-2020 nearly fully reconstructed via a specialist fan archive cross-verified against
coach bios (also corrected 下平隆宏's tenure to 2010-2015 and contradicted the pilot's
"no U-18 tenure" note on 吉田達磨); ヴェルディ 2015-16 closed by official club releases.
ジェフ was stopped mid-research by user decision (one in-flight unverified lead: 神戸清雄 =
ユース監督 1996, no source captured — manual follow-up candidate). マリノス 2004-2016 (13y)
and ヴェルディ 1997-2007 are documented as structurally unresolvable online.

The significance-test core did NOT grow (still 528 players / 24 units): recovered players
split across many short-tenured coaches, so no new unit crossed the 10-player floor — the
known J-academy attribution-fragmentation problem, now measured. The p=0.001 result is
unchanged. The 14 new era-fill coaches have no attribute rows yet (Phase-C table); flagged
as follow-up.

## Era-fill coach attributes complete — attribute coverage now 100% (2026-07-17)

The era-fill follow-up is closed. Per-entity research (Sonnet subagent, 12 coaches — the
"14" in the previous section double-counted 下平隆宏 who already had a row, and the combined
布部/永井 transition row) filled every missing Phase-C attribute row:
`era_fill_coach_attributes.csv`, merged into `coach_attributes.csv` (255 → 267 rows).
Coordinator independently re-verified 3 load-bearing rows against the coaches' Wikipedia
bios (堀孝史 1991 selection with 0 caps; 布部陽功 name + Jan-Mar 2016 U-18 tenure;
濱吉正則 "選手経験は特になく" + Slovenia 3rd division) — all exact matches.

- **Every player with an identifiable primary development coach (2,047) now joins to an
  attribute row (100%, previously the era-fill coaches were missing).**
- Two data corrections fell out of the identity work: the Tassiy table's 布部洋一 is a
  misspelling of **布部陽功** (own bio: U-18 監督 Jan-Mar 2016 before moving to the top
  team), and 永井俊太's tenure extends to **2016-2017** (own bio) — the combined transition
  row was split into two properly-sourced rows.
- Attribute findings: 9/12 played professionally, 6/12 top flight (安達亮 and 筒井紀章 held
  J1 registrations with zero recorded appearances — counted as no), 4/12 overseas
  (吉田達磨 Singapore, 布部陽功 Brazil, 藤吉信次 China, 濱吉正則 Slovenia amateur), and
  堀孝史 is the only full-national-team selection (1991, 0 caps — same convention as the
  existing 倉又寿雄 row).
- **Conclusions unchanged** after rerunning the full pipeline: J1 permutation p=0.001
  (LR 47.1/13df), national-team permutation p=0.31 (χ² p≈0.05 remains anti-conservative),
  own_national_team still flat, any-pro-experience still weakly positive.
- **Lineage graph grew 117 → 130 edges** (mentored_by 27 → 31): the era-fill tenures +
  new playing histories mechanically connected 柴田慎吾 ← 佐々木直人 (柏U-18 2003), and
  安達亮/永井俊太 ← 布啓一郎 (市立船橋) — 布啓一郎 becomes a multi-mentee mentor.

## ジェフ lead verified + CRITICAL data-quality finding (2026-07-17)

The era-fill batch's in-flight ジェフ lead is now closed: **神戸清雄 = ジェフユナイテッド市原
ユース監督 1996** (single year), confirmed by INAC神戸's official 2024 appointment release
carrying his verbatim self-reported career history (1995 サテライト監督兼トップコーチ →
**1996 ユース監督** → 1997 トップコーチ兼サテライト). His Wikipedia lumps 1994-1996 as
"コーチ", but its cited source (J.League Data Site staff_id=208) was fetched directly and has
no year-by-year youth roles — the club release is the higher-resolution source. Tenure row +
attribute row (本田技研 JSL1部 1984-1990, 60 games; 1989 FIFA futsal World Championship
squad — futsal, so own_national_team=no) added; canonical 360 rows, attributes 268.
One real join gained: 山本英臣 (JEF youth 1996-1998) correctly attributes to 神戸清雄.

**The 1996 row exposed a serious pre-existing attribution artifact.** Yearless player stints
(no from/to year in the club-history line) join EVERY tenure at their institution
(`years_overlap` open-bound semantics — by design), and `select_primary_dev_coach` then
breaks the all-equal tie by *first-seen order in the canonical file*. Adding a 1996 tenure
made this visible: 2010s JEF players "joined" a 1996 coach. Quantified over all 2,048
primary attributions: **47% rest on real year overlap, 9% yearless with a single candidate,
44% (900 players) yearless with 2+ candidates — i.e. an arbitrary deterministic pick**,
concentrated in universities (639/900), exactly where the significance-test core lives.
The planned birth-year imputation (design doc: HS 15-18, univ 18-22) was never implemented
in this join path.

**Sensitivity test — the headline p=0.001 does not survive.** Dropping the 900 arbitrary
attributions collapses the identifiable core from 528 players / 24 units / 11 institutions
to **83 / 4 / 2**, and the J1 coach-FE test there is null (LR 1.1/2df, permutation p=0.37).
This does not *refute* the coach effect (the reduced test is nearly powerless) but it shows
the previous core was mostly built on contaminated assignments. Worse, yearlessness is
plausibly notability-correlated (obscure players have thinner Wikipedia club lines), so
piling yearless players onto the first-listed coach can inflate the observed FE statistic
in a way the within-cell permutation does not replicate. **The p=0.001 claim is suspended
pending re-attribution via birth-year imputation.**
