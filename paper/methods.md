# Methods（英文本体 + 和文要点）

> **この文書の読み方**: 各節は「**要点（和文）**」→ 英文ドラフト の順。
> 和文は訳ではなく、その節が何を主張しているか・なぜその設計かの要約。
> 投稿原稿には英文のみを使う。
>
> 数値の出所: `docs/research_plan_phase1b.md`（SAP v15）、
> `docs/phase1b_confirmatory_results_2026-08-14.md`、`docs/results_canonical.md`。
> **本文に書く数値は必ずこれらから引く**（原稿側で計算し直さない）。

---

## 2.1 Study design and reporting

> **要点**: 観察研究であること、事前に仕様を固定したこと、その固定が**外部から検証可能**である
> ことを最初に置く。個人研究なので「信じてくれ」ではなく「検証してくれ」と言える形にする。
> ここで **pre-registered とは書かない**——公的レジストリに登録していないため。
> 書けるのは「事前に指定し、版管理し、公開した」まで。この区別は査読で必ず突かれる。

This is an observational study of professional footballers' developmental pathways, reported
following STROBE. The analysis plan was written and version-controlled before the outcome data
were examined, and both the plan and every revision to it are public. We did not register the
protocol in a public trials registry; instead, the analysis plan, its revision history, and the
commit that fixed each version are available in the study repository [DOI], so that the sequence of
decisions can be audited independently. Where a specification changed, the change, its date, its
justification and whether the outcome had been seen at that point are recorded in a revision table
within the plan itself.

Two distinctions are used throughout. **Confirmatory** refers to the single pre-specified
hypothesis test; everything else is descriptive or exploratory and is labelled as such.
**Association** rather than effect is used for all estimates: the design does not support causal
interpretation, for reasons given in §2.9.

---

## 2.2 Setting, participants and eligibility

> **要点**: 標本は「J リーグ出場者」に条件付けられている。**育成人口全体ではない**——
> ここを曖昧にすると論文全体の主張が誇大になる。プロに到達しなかった選手は原理的に見えない。
> 出生年下限 1981 は「18歳到達=1999年」から来る観測可能性の制約であって恣意ではない。

Participants are Japanese players with at least one league appearance in the Japanese professional
leagues (J1, J2 or J3) between 1999 and 2025, identified in the J.League Data Site player register,
born in or after 1981.

Three points bound what this sample can answer. First, **the cohort is conditioned on having played
professionally**: players who left the development system before reaching a professional league are
not observable, so no statement about the probability that a given pathway *produces* a
professional is possible. Second, appearance is defined as league appearances greater than zero;
squad registration, cup matches, play-offs and satellite fixtures do not qualify. An earlier
version of this plan required 500 career minutes; that requirement was removed because it
conditions on a post-exposure career outcome and, as the earlier eras were collected under
different criteria, the condition itself correlated with era. Third, the 1981 lower bound is the
earliest birth year for which a career from the ordinary age of professional entry is broadly
observable (age 18 in 1999); we do not claim complete observation, since appearances at 17 or
younger before 1999 cannot be excluded.

For the confirmatory analysis, players must additionally have a completed 25-year horizon: the
season of their 25th year must have finished by 2025.

---

## 2.3 Era definition

> **要点**: 時代区分は**生年ベース**（育成年代で割り当てる）。デビュー年ベースにすると
> 「遅く芽が出た選手」が後の時代に流れ込んで曝露と outcome が混ざる。
> **政策効果の推定ではない**ことを明記する——2005年を参照して区切ってはいるが、
> リーグ構造・移籍市場・記事作成慣行の変化と分離できない。

Eras are assigned by birth year rather than by debut year, so that a player is placed in the era in
which they were *developed* rather than the era in which they happened to break through. A player
is assigned to the era containing the year they turned 15.

| Era | Turned 15 | Birth years |
|---|---|---|
| Era 1 | 2004 or earlier | 1981–1989 |
| Era 2 | 2005–2014 | 1990–1999 |
| Era 3 | 2015 or later | 2000– (excluded from the confirmatory analysis) |

The 2005 boundary references a national development policy, but **this study does not estimate the
effect of that policy**. The boundary cannot be separated from concurrent changes in league
structure, scouting, the transfer market, the school system, or the conventions of the web sources
from which the exposure is measured. Results are therefore stated as differences in association
between birth cohorts defined with reference to a policy period, never as policy effects.

Era 3 is excluded from the confirmatory analysis because the 25-year horizon has not completed for
those births; treating an incomplete horizon as a zero would manufacture an era difference.

---

## 2.4 Outcome

> **要点**: 25歳までの J1 到達。年単位データなので誕生日による最大1年のずれは規則で吸収する。
> 副次アウトカム（海外移籍・代表）は**追跡期間が時代間で非対称**なので記述のみ。

The primary outcome is **reaching J1 by age 25**: at least one J1 league appearance in a season
satisfying `season − birth year ≤ 25`. Because the appearance data are annual, this rule tolerates
up to one year of displacement from a player's birthday, applied identically in both eras.

The outcome combines the integrated career table with a backfill from Japanese Wikipedia debut
records; the number of players where the two sources disagree is reported directly rather than
resolved silently.

Secondary outcomes (ever moving abroad, ever selected for a national team) are reported
descriptively only. They are *ever* indicators with no selection or transfer year available, so no
fixed horizon can be imposed, and the observation window is longer for the earlier era. Comparing
them across eras would confound the outcome with follow-up length, so no test is performed.

---

## 2.5 Exposure measurement

> **要点**: ここが本研究の中核。曝露＝「プロ入り**直前**に在籍した育成機関」を3カテゴリに。
> 測定は Wikipedia の**散文**と**所属クラブ欄**という2つの独立手順＋人手レビューの複合規則。
> なぜ複合にしたか: 散文だけだと機関名の連結（「柏レイソルU-18（柏中央高→…）」）で高校に倒れる。
> **この複合規則自体が検証対象**であって、正しさを仮定していない。

The exposure is the **last developmental institution attended before entering senior football**,
classified into three categories: club academy (`j_club_academy`), high school, and university.
Institutions outside these three (JFA Academy, vocational colleges, adult-age teams) and players
whose institution could not be identified are retained as separate categories and excluded from the
three-way comparison rather than forced into it.

The exposure is measured by a **composite rule** combining two procedures that read different parts
of the same Japanese Wikipedia article, plus human review:

1. **Prose extraction.** A classifier reads the biographical narrative sections and assigns a
   category by priority (university > high school > academy), with guards for cases the narrative
   describes ambiguously.
2. **Club-history derivation.** The article's structured club-history list is chronological, so the
   pathway is the last developmental institution appearing immediately before the first
   *senior-club entry* — defined as the first non-developmental, dated club joined at age 16 or
   above. Amateur, regional and overseas clubs all qualify as senior entries. Second-team
   registrations and special-designation entries do not.
3. **Human review.** Rows where the two procedures disagree, or where either flags a specific
   ambiguity, are routed to manual adjudication with the reviewer's rationale recorded.

The composite rule exists because neither procedure dominates. Prose is stronger on sequence;
the club-history list is stronger on institution names — where a youth team and its partner high
school are concatenated into one string, prose-only extraction resolves to the school. **The object
validated in §2.7 is the composite rule as a whole**, not either procedure.

A club academy is defined with reference to a **date-stamped register of league membership**, so
that a club's youth team counts as a professional academy only for the years in which the club was
actually a league member; youth teams of non-member clubs are held in a separate category. This
definition was applied retrospectively to the earlier published analysis, so that the same players
are not measured two different ways across the two studies.

---

## 2.6 Gold-standard validation sample

> **要点**: 妥当性を測るには「正解」が要る。**開発に使った例で性能を測ってはいけない**ので、
> 独立 holdout を凍結してから判定した。層化抽出で「誤ると効きやすい層」を過剰抽出し、
> 解析時は抽出確率の逆数で母集団に戻す。**判定者には最終ラベルも層名も見せない**
> （層名は「不一致行である」ことを漏らすため）。

Validity was assessed against an independently constructed gold standard, held out from the data
used to develop the composite rule. **539 players** were drawn by stratified sampling before any
rating began; the sample, its strata, the population size of each stratum and the sampling
probabilities were frozen and hashed in advance (SHA-256 recorded in the analysis plan).

Strata cross **era × agreement pattern × observed pathway**. Strata where a single
misclassification would move the estimate most — rows where the two procedures disagree, rows
derived from the club history alone, and rows where the academy category is entered or left — were
deliberately over-sampled and are weighted back to the population by the inverse sampling
probability at analysis. Rows that could not be verified are retained as an explicit category
rather than dropped as missing.

Raters received a **blinded worksheet** containing only player name, romanised name, birth date,
first and last observed season, and senior clubs. They did not see either classifier's output, the
final label, or the stratum name — the stratum name alone would reveal that a row was a
disagreement.

**Rating protocol.** Two raters from different model families rated independently (Claude Sonnet as
rater A; Codex as rater B), each given web search and retrieval tools and no access to the study
repository — which serves both cost and blinding, since a rater with file access could read the
labels it is meant to check. For each player a rater recorded the category, the institution's
formal name, a determination (confirmed / indeterminate / unreachable), a source URL, a **verbatim
quotation** supporting the verdict, and the source type. Paraphrase was not accepted. Sources that
cannot carry a verdict alone were enumerated in advance — Wikipedia and its mirrors (the
measurement target itself), aggregators without citations, personal blogs and social media,
user-edited databases — and a row resting only on such a source is `indeterminate`. Search was
capped at five external queries per player, beyond which the row is `indeterminate`; an
indeterminate rate is information, whereas a verdict resting on weak evidence is not.

**Allocation of double rating.** Rating all 539 rows twice proved infeasible within budget after a
30-player pilot measured the cost. The allocation was therefore fixed before continuing: the
strata where one error moves the estimate most (150 rows) and a seeded 15% reliability subsample of
the rest (54 rows) were double-rated; the remaining 305 were rated once, with the two raters
balanced within each stratum so that neither rater's habits fall entirely on one kind of row. A
pre-specified reversion rule stated that if the two raters, both confirming, disagreed on category
in more than 5% of the reliability subsample, the single-rated rows would be re-rated in
duplicate.

**Adjudication.** All disagreements, plus a seeded 10% spot check of *agreements*, were adjudicated
by the author against the same evidentiary standard. The spot check exists because agreement
between two language models is not independent evidence: both query the same Japanese-language web
and can converge on the same error. Across 17 spot-checked rows the adjudicator upheld both raters
in every case.

**A directional rater error found by this design.** The reliability subsample produced two
disagreements, both the same shape: rater A filed players who went academy → university →
professional under the academy, when the rule ("last institution before senior entry") gives
university. In both rows rater A's own free-text note named the university it had skipped. Rater B
made no such error. Since the reversion threshold was not crossed (2 of 49 = 4.1%), single rating
continued — but because such rows *state their own contradiction*, a screen was added: any
single-rated row labelled academy or high school whose quotation or note mentions a university that
is neither the recorded institution nor a university-affiliated high school is sent to the other
rater for a second opinion. The screen is a request for a second reading, never a verdict. It is
reported with its yield in §3.

---

## 2.7 Gate A: measurement equivalence, assessed before the outcome

> **要点**: 2段階ゲートの1段目。**アウトカムを見ずに**測定の妥当性だけで先に進めるか決める。
> 4条件を事前に決めてあり、1つでも該当したら確認的解釈をしない。
> 特に条件2（silent-wrong の era 差）は「誰も気づかないまま誤っているラベル」の時代差で、
> **これが時代間で違うと、時代差そのものが測定のアーティファクトになりうる**。

Gate A asks whether the exposure is measured equivalently enough across eras for an era comparison
to mean anything. Every quantity it uses is a function of the gold label and the pipeline label
only, so **Gate A is settled while the outcome remains unexamined**.

Four stopping conditions were specified in advance. The confirmatory analysis does not proceed if
any is met:

1. the between-era difference in pathway determination rate exceeds 10 percentage points;
2. the between-era difference in **silent-wrong rate** exceeds 5 points, where silent-wrong is a
   final label that disagrees with gold *and was never flagged for human review* — a row a reviewer
   adjudicated is not silent even when it is wrong, because the failure mode of concern is the
   pipeline being confidently mistaken;
3. for any era and any of the three pathways, the Wilson 95% lower bound of sensitivity or positive
   predictive value falls below 80%, or the cell is too small to judge;
4. any required review remains incomplete.

A cell too small to reach the bound even at 100% agreement is reported as **undetermined**, and a
cell with enough rows that failed is reported as a **failure**; an earlier version of the report
conflated the two, which hides an inaccurate label behind a statement about sample size.

---

## 2.8 Gate B: measurement robustness, assessed after estimation

> **要点**: 2段階目。「測定が正確か」ではなく **「実測された誤差で、主張しようとしている
> 大きさの差が作れてしまわないか」**。許容差3ppは Phase 1 の既報格差 −26.3pp の約1割で、
> **アウトカムを見る前に固定した**。gold の不確実性を Dirichlet で推定へ伝播させる。

Gate B asks a different question from Gate A: not whether the label is accurate, but whether the
labelling error **that gold actually measured** could manufacture the era difference being
reported.

The **measurement-robustness tolerance is 3 percentage points on the difference-in-differences
scale**, fixed before the outcome was examined. It is not a minimal important difference in the
clinical sense; it is approximately one tenth of the university-pathway gap already published from
the earlier study (−26.3 points). The statement it encodes is: *if measurement error alone can
produce an era difference the size of a tenth of the known pathway gap, then the claim that the gap
changed over time is not established.* A 5-point threshold is reported alongside as a threshold
sensitivity, not as a second criterion.

**Misclassification model.** For each era, the gold sample gives counts of the true pathway within
each observed label. A Dirichlet posterior (gold counts weighted to the population, plus a Jeffreys
prior, scaled so that the posterior's spread reflects the number of rows actually verified rather
than the population they represent) is drawn 2,000 times; on each draw every player's pathway is
redrawn from P(true | observed) for their era and the entire analysis refitted. This propagates the
verification sample's own uncertainty into the final estimate rather than treating the gold
proportions as known.

Ten scenarios were specified in advance, spanning the measured rates (S1), a common rate across
eras (S2), stress multipliers on the earlier era (S3) and on the direction that empties the
reference category (S4), a pessimistic flat error on hard strata (S5), extreme reallocations of
uncategorised rows (S6), restriction to human-reviewed rows (S7), inverse-probability weighting on
article length (S8), and re-analysis under each single labelling procedure (S9, S10). S9 and S10
are diagnostics, **not substitutes for validation**: since the older procedure is the one suspected
of error, agreement with it would not establish that the newer one is right.

Four stopping conditions apply to the **envelope of all scenarios**, not to any single convenient
one: a sign change; a difference from the main estimate of at least the tolerance; an envelope
containing both zero and an important effect of the opposite sign; or a tipping point within a
plausible misclassification range. **Overlap of confidence intervals is explicitly not a
criterion**, since its operating characteristics depend on sample size.

---

## 2.9 Statistical analysis

> **要点**: 主検定は**1本だけ**（多重比較を作らない）。報告尺度はオッズ比ではなく
> **リスク差**——ゲートも許容差も「pp」で定義してあるので尺度を揃える。
> 出生年調整は4仕様を事前指定し、**符号と効果量が仕様間で不安定なら結論はモデル依存と判断**する。

The single confirmatory test is a **two-sided joint likelihood-ratio test of the pathway × era
interaction** in

```
reached_j1_by_age25 ~ pathway * era + within-era birth year
```

with club academy as the reference and birth year centred on each era's own median. No other test
is confirmatory.

The primary reporting scale is the **risk difference**, obtained by g-computation: each era's
counterfactual risk under each pathway is averaged over that era's own players, and the pathway gap
is contrasted against the academy reference. The quantity of interest is the **difference between
those gaps across eras (DID)**. Standardising within era rather than over the pooled sample follows
from the estimand: the comparison is between each era's internal gap. Confidence intervals come
from a player-level bootstrap resampled within era (500 resamples, seed fixed in advance). Odds
ratios are reported alongside but are not the basis of any conclusion, since the gates and the
tolerance are defined in percentage points and odds ratios are not collapsible.

Four birth-year adjustments were pre-specified as a battery: unadjusted, within-era centred linear
(primary), era-specific linear, and a restricted cubic spline with knots at five-year quantiles.
**If sign or magnitude is unstable across them, the conclusion is judged model-dependent.**

The pooled association across 1981–1999 births is a **separate estimand**, specified before the
confirmatory analysis ran and containing no era term; results from it are not used to infer
era-specific effects.

---

## 2.10 Order of operations and blinding

> **要点**: 「いつ何を見たか」を書く。ここを曖昧にすると事前指定の意味が消える。
> **正直に書くべき箇所**: Phase 1 の再実行で era2 の98.3%を占める重複標本の outcome を見ている。
> 「完全非閲覧」とは書けない。

The order of operations was fixed in advance and each step closed with a commit: implement the
exposure definition; collect and adjudicate the gold sample; judge Gate A; lock the inputs; run the
confirmatory analysis and Gate B **in a single sealed execution**; then run the pooled estimand.

The sealed run refuses to start unless every hashed input still matches the locked version, and it
was rehearsed end-to-end on fabricated data of the same shape before being run on the real data —
a rehearsal that caught a crash in the final table, which would otherwise have discarded the run
after the outcome had already been read.

**Disclosure of prior outcome exposure.** Blinding was not complete and is not claimed to be. When
the exposure definition was revised, the earlier study's confirmatory analysis was re-run to record
the impact, and that sample overlaps this one substantially — **98.3% of era 2 and 63.0% of era 1**.
Outcome-linked results were therefore seen for the majority of era 2 before this analysis was
specified, though not for the era comparison itself, which is the quantity tested here.

**Software and materials.** Analysis in Python (statsmodels, pandas, numpy, scipy). Code, the
analysis plan with its full revision history, the adjudicated gold labels and the per-rater
evidence — source URL and verbatim quotation for each verdict — are deposited at [DOI]. Raw
appearance records are not redistributed, as the source's terms prohibit reproduction; the
collection scripts are provided so they can be re-derived.

**Use of language models.** Two language models were used as *measurement instruments* — as
independent raters against a written protocol, with their verdicts, evidence and disagreements
recorded and adjudicated — not to generate or interpret results. Model identities, the rating
prompt, inter-rater agreement, indeterminate rates and the one systematic rater error the design
detected are reported in §3.

**Ethics.** This study analysed published records of professional footballers, who are public
figures. No participants were recruited, no private or sensitive personal information was used, and
no de-identification was applied — nor would it be meaningful, since birth year and club history
identify a player immediately. Ethical approval was not required.

---

## 未確定・要検討（原稿化の前に潰す）

1. **[DOI]** — Zenodo 寄託後に確定。2 箇所（§2.1・§2.10）。
2. **STROBE 準拠と書くか** — チェックリストを実際に埋めてから決める。埋めずに書かない。
3. **§2.6 の rater 記述の粒度** — モデル版まで書くか（`claude -p --model sonnet` /
   `codex exec -m gpt-5.6-sol`）。再現性のためには書くべきだが、モデルは更新されるため
   「この版で実行した」という記録以上の意味は持たない旨を添える必要がある。
4. **Phase 1 との関係の記述位置** — Methods（§2.10 の閲覧範囲）と Discussion のどちらで
   「独立再現ではない」と述べるか。両方に散らすと薄まる。
5. **和文投稿の可能性を残すか** — 残すなら本 Methods の和訳を別途作る（今は要点のみ）。
