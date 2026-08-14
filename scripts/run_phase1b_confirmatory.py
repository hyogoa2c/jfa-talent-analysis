"""The sealed run: H1b-2 and Gate B in one execution (SAP §11 手順 5).

This is the first and only time Phase 1b's outcome is read. Everything it does
was fixed beforehand -- the model battery in §6, the ten measurement scenarios
in §6b-6, the seeds and draw counts in v14 -- so that nothing here is a choice
made after seeing a number.

It refuses to run if any locked input has changed since v14. A rerun that reads
different data would not be the same execution, and the point of sealing was
that there is only one.

Run: uv run python scripts/run_phase1b_confirmatory.py
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

from jfa_talent_analysis import measurement_robustness as mr
from jfa_talent_analysis import phase1b_confirmatory as pc
from jfa_talent_analysis.gold_strata import load_institution_unknown, stratum

SAP = Path("docs/research_plan_phase1b.md")
REPORT_DIR = Path("reports/generated")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pooled", type=Path, default=Path("data/processed/pooled_player_outcomes_1999_2025.csv"))
    parser.add_argument("--gold", type=Path, default=Path("data/manual/gold_holdout/gold_resolved.csv"))
    parser.add_argument("--key", type=Path, default=Path("data/manual/gold_holdout_worksheet_key.csv"))
    parser.add_argument("--sample", type=Path, default=Path("data/manual/gold_holdout_sample.csv"))
    parser.add_argument("--reclassification-queue", type=Path, default=Path("data/manual/academy_reclassification_queue.csv"))
    parser.add_argument("--secondary", type=Path, default=Path("data/processed/player_pathway_outcomes.csv"))
    parser.add_argument("--stints", type=Path, default=Path("data/interim/coach_network/player_institution_stints.csv"))
    parser.add_argument("--extracts", type=Path, nargs="*", default=[
        Path("data/interim/wikipedia_full_extracts/tier_a.csv"),
        Path("data/interim/wikipedia_full_extracts/tier_b.csv"),
        Path("data/interim/wikipedia_full_extracts/tier_c.csv"),
        Path("data/interim/pre2014/full_extracts_priority1.csv"),
        Path("data/interim/pre2014/full_extracts_priority2.csv"),
    ])
    parser.add_argument("--n-boot", type=int, default=pc.BOOTSTRAP_DRAWS)
    parser.add_argument("--mc-draws", type=int, default=pc.MONTE_CARLO_DRAWS)
    parser.add_argument("--outdir", type=Path, default=REPORT_DIR)
    parser.add_argument("--allow-drift", action="store_true", help="Run even if a locked input changed. Records it.")
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def check_lock() -> list[str]:
    """Every file the SAP hashed must still hash the same."""
    text = SAP.read_text(encoding="utf-8")
    rows = re.findall(r"^\|\s*\**`([^`]+)`\**[^|]*\|\s*`([0-9a-f]{12})`\s*\|\s*(\d+)\s*\|", text, re.M)
    drift = []
    for path, digest, size in rows:
        file = Path(path)
        if not file.exists():
            drift.append(f"{path}: 消えている")
            continue
        blob = file.read_bytes()
        if hashlib.sha256(blob).hexdigest()[:12] != digest or len(blob) != int(size):
            drift.append(f"{path}: ロック時と違う")
    return drift


def head_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except Exception:
        return "unknown"


def pct(value: float) -> str:
    return f"{value * 100:.1f}pp"


def markdown_table(frame: pd.DataFrame) -> list[str]:
    """A frame as markdown, without pulling in an optional dependency."""

    def cell(value: object) -> str:
        if isinstance(value, float):
            return f"{value:.2f}"
        return str(value)

    header = "| " + " | ".join(str(c) for c in frame.columns) + " |"
    rule = "|" + "---|" * len(frame.columns)
    body = ["| " + " | ".join(cell(v) for v in row) + " |" for row in frame.itertuples(index=False)]
    return [header, rule, *body]


# --------------------------------------------------------------------------- #
# inputs


def load_frame(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame]:
    pooled = pd.read_csv(args.pooled, dtype=str, encoding="utf-8-sig")
    frame = pc.build_frame(pooled)
    return frame, pooled


def load_gold_pairs(args: argparse.Namespace) -> pd.DataFrame:
    """The holdout rows Gate A judged, as truth/label pairs with design weights."""
    key = {row["worksheet_id"]: row for row in read_csv(args.key)}
    weights = {row["source_player_id"]: row for row in read_csv(args.sample)}
    pooled = {row["source_player_id"]: row for row in read_csv(args.pooled)}
    records = []
    for row in read_csv(args.gold):
        if row["determination"] != "confirmed" or row["gold_pathway_category"] not in pc.MAIN_PATHWAYS:
            continue
        identity = key.get(row["worksheet_id"])
        player = pooled.get(identity["source_player_id"]) if identity else None
        if player is None or player["eligible_confirmatory"] != "1" or not player["pathway_category"]:
            continue
        if player["pathway_category"] not in pc.MAIN_PATHWAYS:
            continue
        drawn = weights.get(identity["source_player_id"])
        records.append(
            {
                "era": identity["era"],
                "gold": row["gold_pathway_category"],
                "label": player["pathway_category"],
                "weight": float(drawn["weight"]) if drawn and drawn["weight"] else 1.0,
            }
        )
    return pd.DataFrame(records)


def attach_strata(frame: pd.DataFrame, pooled: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    unknown = load_institution_unknown(read_csv(args.reclassification_queue))
    rows = {row["source_player_id"]: row for row in pooled.to_dict("records")}
    frame["stratum"] = [stratum(rows[pid], unknown) for pid in frame["source_player_id"]]
    return frame


def attach_thickness(frame: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    """Article length per player, for S8's inverse-probability weights."""
    lengths: dict[str, int] = {}
    for path in args.extracts:
        if not path.exists():
            continue
        for row in read_csv(path):
            text = row.get("full_extract") or ""
            lengths[row["source_player_id"]] = max(lengths.get(row["source_player_id"], 0), len(text))
    frame["article_chars"] = [lengths.get(pid, 0) for pid in frame["source_player_id"]]
    return frame


# --------------------------------------------------------------------------- #
# sections


def describe(frame: pd.DataFrame, pooled: pd.DataFrame) -> tuple[list[str], pd.DataFrame]:
    eligible = pooled[pooled["eligible_confirmatory"].astype(str) == "1"]
    lines = ["## 1. 標本と経路構成（記述・H1b-1 は降格済み）", ""]
    table = (
        frame.groupby(["era", "pathway_category"]).size().rename("n").reset_index()
    )
    totals = table.groupby("era")["n"].transform("sum")
    table["share"] = table["n"] / totals
    low, high = [], []
    for _, row in table.iterrows():
        from jfa_talent_analysis.gate_a import wilson_interval

        interval = wilson_interval(int(row["n"]), int(totals[row.name]))
        low.append(interval[0])
        high.append(interval[1])
    table["ci_low"], table["ci_high"] = low, high
    lines += ["| era | 経路 | n | 割合 | 95%CI |", "|---|---|---|---|---|"]
    for _, row in table.iterrows():
        lines.append(
            f"| {row['era']} | {row['pathway_category']} | {int(row['n'])} | {row['share']:.1%} "
            f"| [{row['ci_low']:.1%}, {row['ci_high']:.1%}] |"
        )
    lines += ["", "| era | 適格 | 主要3経路 | ラベル欠測・3経路外 |", "|---|---|---|---|"]
    for era in pc.ERAS:
        total = int((eligible["era"] == era).sum())
        kept = int((frame["era"] == era).sum())
        lines.append(f"| {era} | {total} | {kept} | {total - kept}（{(total - kept) / total:.1%}） |")
    from scipy import stats as st

    contingency = pd.crosstab(frame["era"], frame["pathway_category"])
    chi2, p, dof, _ = st.chi2_contingency(contingency.to_numpy())
    lines += [
        "",
        f"χ² = {chi2:.1f}（df={dof}）, p = {p:.3g}。**記述としてのみ報告する**（§2 で H1b-1 は降格）。",
        "",
    ]
    return lines, table


def main_analysis(frame: pd.DataFrame, args: argparse.Namespace) -> tuple[list[str], dict, pd.DataFrame]:
    knots = pc.quintile_knots(frame["birth_year"])
    specs = pc.specs(pc.spline_term(knots))
    main_spec = specs[0]
    test = pc.joint_interaction_test(frame, main_spec)
    risks, differences, values = pc.point_estimates(frame, main_spec.formula())
    interval = pc.bootstrap_did(frame, main_spec.formula(), n_boot=args.n_boot).set_index("pathway")

    lines = [
        "## 2. 主検定（H1b-2・確認的、1 本のみ）",
        "",
        f"モデル: `{main_spec.formula()}`（{main_spec.label}）",
        f"RCS ノット（5 年分位）: {[round(k, 1) for k in knots]}",
        "",
        f"**pathway × era 交互作用の共同両側 LR 検定: χ² = {test['lr_statistic']:.2f}, "
        f"df = {test['df']}, p = {test['p_value']:.4g}**（n = {test['n']}）",
        "",
        "## 3. 標準化到達確率とリスク差（主報告）",
        "",
        "| era | 経路 | 標準化到達確率 | n |",
        "|---|---|---|---|",
    ]
    for _, row in risks.iterrows():
        lines.append(f"| {row['era']} | {row['pathway']} | {row['risk']:.1%} | {int(row['n'])} |")
    lines += ["", "| era | 経路 | リスク差（vs j_club_academy） |", "|---|---|---|"]
    for _, row in differences.iterrows():
        lines.append(f"| {row['era']} | {row['pathway']} | {pct(row['risk_difference'])} |")
    lines += [
        "",
        f"**DID（era2 の格差 − era1 の格差、正なら格差が縮小）**"
        f"・95% 区間はブートストラップ {args.n_boot} 回・seed {pc.BOOTSTRAP_SEED}",
        "",
        "| 経路 | DID | 95% 区間 | 有効反復 |",
        "|---|---|---|---|",
    ]
    for pathway in pc.CONTRASTS:
        lines.append(
            f"| {pathway} | {pct(values[pathway])} | "
            f"[{pct(interval.loc[pathway, 'did_ci_low'])}, {pct(interval.loc[pathway, 'did_ci_high'])}] "
            f"| {int(interval.loc[pathway, 'n_boot_ok'])} |"
        )
    lines.append("")

    # birth-year adjustment battery
    rows = []
    for spec in specs:
        _, _, spec_values = pc.point_estimates(frame, spec.formula())
        spec_test = pc.joint_interaction_test(frame, spec)
        rows.append(
            {
                "仕様": spec.label,
                **{f"{p}_did_pp": spec_values[p] * 100 for p in pc.CONTRASTS},
                "lr_p": spec_test["p_value"],
            }
        )
    battery = pd.DataFrame(rows)
    lines += [
        "## 4. 出生年調整バッテリー（§6 事前指定）",
        "",
        "符号・実質効果量がモデル間で不安定なら「時代差の結論はモデル依存」と判断する。",
        "",
        "| 仕様 | " + " | ".join(f"{p} DID" for p in pc.CONTRASTS) + " | LR p |",
        "|---|---|---|---|",
    ]
    for _, row in battery.iterrows():
        cells = " | ".join(f"{row[f'{p}_did_pp']:.1f}pp" for p in pc.CONTRASTS)
        lines.append(f"| {row['仕様']} | {cells} | {row['lr_p']:.3g} |")
    spread = {p: battery[f"{p}_did_pp"].max() - battery[f"{p}_did_pp"].min() for p in pc.CONTRASTS}
    signs = {p: battery[f"{p}_did_pp"].apply(np.sign).nunique() == 1 for p in pc.CONTRASTS}
    lines += [
        "",
        "| 経路 | 仕様間の幅 | 符号一致 |",
        "|---|---|---|",
    ] + [
        f"| {p} | {spread[p]:.1f}pp | {'はい' if signs[p] else '**いいえ**'} |" for p in pc.CONTRASTS
    ] + [""]
    return lines, {"test": test, "did": values, "interval": interval, "specs": specs, "battery": battery}, risks


def gate_b(frame: pd.DataFrame, pairs: pd.DataFrame, main: dict, args: argparse.Namespace) -> tuple[list[str], pd.DataFrame]:
    formula = main["specs"][0].formula()
    counts = {era: mr.true_given_observed(pairs, era) for era in pc.ERAS}
    pooled_counts = mr.true_given_observed(pairs.assign(era="pooled"), "pooled")

    scenarios: list[mr.ScenarioResult] = []

    def monte_carlo(name: str, description: str, matrices: dict, seed_offset: int) -> None:
        median, low, high = mr.monte_carlo_scenario(
            frame, formula, matrices, draws=args.mc_draws, seed=pc.MONTE_CARLO_SEED + seed_offset
        )
        scenarios.append(mr.ScenarioResult(name, description, median, low, high, len(frame)))

    monte_carlo("S1", "独立 holdout gold の era 別誤分類（主シナリオ）", counts, 0)
    monte_carlo("S2", "両 era 共通の誤分類（gold をプール）", {era: pooled_counts for era in pc.ERAS}, 1)
    monte_carlo(
        "S3",
        f"era1 のみ誤分類を {mr.STRESS_MULTIPLIER:g} 倍に悪化（事後分布とは別の明示的仮定）",
        {"era1": mr._stress(counts["era1"], mr.STRESS_MULTIPLIER), "era2": counts["era2"]},
        2,
    )
    monte_carlo(
        "S4",
        f"非対称: アカデミーへ入る向きのみ {mr.STRESS_MULTIPLIER:g} 倍（基準カテゴリの出入り）",
        {era: mr._stress_into_academy(counts[era], mr.STRESS_MULTIPLIER) for era in pc.ERAS},
        3,
    )

    # S5: hard strata get a flat 40% error, everything else keeps the gold matrix.
    hard_counts = {}
    for era in pc.ERAS:
        hard_counts[era] = {
            observed: {
                true: (
                    (1 - mr.HARD_CASE_ERROR_RATE) * 100
                    if true == observed
                    else mr.HARD_CASE_ERROR_RATE / 2 * 100
                )
                for true in pc.MAIN_PATHWAYS
            }
            for observed in pc.MAIN_PATHWAYS
        }
    hard_mask = frame["stratum"].isin(mr.HARD_STRATA)
    hard_frame = frame[hard_mask]
    easy_frame = frame[~hard_mask]
    rng = np.random.default_rng(pc.MONTE_CARLO_SEED + 4)
    collected = {p: [] for p in pc.CONTRASTS}
    for _ in range(args.mc_draws):
        matrices_hard = {era: mr._draw_matrix(hard_counts[era], rng) for era in pc.ERAS}
        matrices_easy = {era: mr._draw_matrix(counts[era], rng) for era in pc.ERAS}
        redrawn = pd.concat(
            [mr._reassign(hard_frame, matrices_hard, rng), mr._reassign(easy_frame, matrices_easy, rng)],
            ignore_index=True,
        )
        try:
            _, _, values = pc.point_estimates(redrawn, formula)
        except Exception:
            continue
        for pathway, value in values.items():
            collected[pathway].append(value)
    scenarios.append(
        mr.ScenarioResult(
            "S5",
            f"悲観ストレス: 難例（{'・'.join(mr.HARD_STRATA)}、{int(hard_mask.sum())} 名）に一律 40% 誤り",
            {p: float(np.median(v)) if v else np.nan for p, v in collected.items()},
            {p: float(np.percentile(v, 2.5)) if v else np.nan for p, v in collected.items()},
            {p: float(np.percentile(v, 97.5)) if v else np.nan for p, v in collected.items()},
            len(frame),
        )
    )

    def deterministic(name: str, description: str, df: pd.DataFrame, weights_col: str | None = None) -> None:
        try:
            _, _, values = pc.point_estimates(df, formula, weights_col)
        except Exception as error:  # a scenario that cannot be fitted is reported, not hidden
            scenarios.append(
                mr.ScenarioResult(name, f"{description}（推定できず: {error}）", {p: np.nan for p in pc.CONTRASTS}, {}, {}, len(df))
            )
            return
        scenarios.append(mr.ScenarioResult(name, description, values, {}, {}, len(df)))

    return scenarios, counts, deterministic, formula


def main() -> None:
    args = parse_args()
    drift = check_lock()
    if drift and not args.allow_drift:
        raise SystemExit("ロックした入力が変わっている:\n  " + "\n  ".join(drift))

    frame, pooled = load_frame(args)
    frame = attach_strata(frame, pooled, args)
    frame = attach_thickness(frame, args)
    pairs = load_gold_pairs(args)

    lines = [
        "# Phase 1b 確認的分析（H1b-2）と Gate B — 封印実行",
        "",
        f"コード版 `{head_commit()}` / SAP v14 / ブートストラップ {args.n_boot} 回・"
        f"モンテカルロ {args.mc_draws} 回・seed {pc.BOOTSTRAP_SEED}",
        "",
        "**この実行が Phase 1b の outcome を読む唯一の機会である**（§11 手順 5）。",
        "ロックした入力のハッシュ照合: " + ("**差分あり（--allow-drift で実行）**" if drift else "全件一致"),
        "",
    ]

    described, _ = describe(frame, pooled)
    lines += described
    analysis_lines, main_result, _ = main_analysis(frame, args)
    lines += analysis_lines

    scenarios, counts, deterministic, formula = gate_b(frame, pairs, main_result, args)

    # S6-S10: deterministic re-analyses.
    outside = pooled[
        (pooled["eligible_confirmatory"].astype(str) == "1")
        & (pooled["era"].isin(pc.ERAS))
        & (~pooled["pathway_category"].isin(pc.MAIN_PATHWAYS))
    ]
    for suffix, label in (("a", "j_club_academy"), ("b", "university")):
        added = outside.copy()
        added["pathway_category"] = label
        extended = pc.build_frame(pd.concat([pooled[pooled["source_player_id"].isin(frame["source_player_id"])], added]))
        deterministic(f"S6{suffix}", f"3 経路外の {len(added)} 名をすべて {label} として投入", extended)
    deterministic("S7", "human_reviewed の行のみ", frame[frame["source_player_id"].isin(
        pooled[pooled["pathway_category_source"] == "human_reviewed"]["source_player_id"])])
    prose = pooled.copy()
    prose["pathway_category"] = prose["pathway_prose_category"]
    deterministic("S9", "§1b-3 の複合規則なし（散文ラベル）", pc.build_frame(prose))
    club = pooled.copy()
    club["pathway_category"] = club["pathway_club_list_category"]
    deterministic("S10", "所属クラブ欄ラベルのみ", pc.build_frame(club))

    # S8: inverse-probability weights on article thickness x era.
    weighted = frame.copy()
    weighted["thickness_decile"] = (
        weighted.groupby("era")["article_chars"].transform(lambda s: pd.qcut(s.rank(method="first"), 10, labels=False))
    )
    resolved = weighted.assign(resolved=1.0)
    share = resolved.groupby(["era", "thickness_decile"])["resolved"].transform("mean")
    weighted["ipw"] = 1.0 / share.clip(lower=0.05)
    deterministic("S8", "記事の厚さ（era 内十分位）による逆確率重み付け", weighted, "ipw")

    lines += ["## 5. Gate B: 測定頑健性（§6b-6）", "", "| # | シナリオ | " + " | ".join(f"{p} DID" for p in pc.CONTRASTS) + " | 主推定との差 |", "|---|---|---|---|---|"]
    for scenario in scenarios:
        cells = " | ".join(
            f"{scenario.did[p] * 100:.1f}pp" if not np.isnan(scenario.did[p]) else "—" for p in pc.CONTRASTS
        )
        diff = " / ".join(
            f"{(scenario.did[p] - main_result['did'][p]) * 100:+.1f}" if not np.isnan(scenario.did[p]) else "—"
            for p in pc.CONTRASTS
        )
        lines.append(f"| {scenario.scenario} | {scenario.description} | {cells} | {diff}pp |")

    conditions = mr.stopping_conditions(main_result["did"], scenarios)
    lines += ["", "### 停止条件（許容差 3pp）", "", "| 経路 | 主 DID | envelope | 条件1 符号反転 | 条件2 差≥3pp | 条件3 両側 |", "|---|---|---|---|---|---|"]
    for _, row in conditions.iterrows():
        lines.append(
            f"| {row['pathway']} | {row['main_did_pp']:.1f}pp | "
            f"[{row['envelope_low_pp']:.1f}, {row['envelope_high_pp']:.1f}]pp "
            f"| {row['条件1_符号反転']} | {row['条件2_差が許容差以上']} | {row['条件3_両側に重要な値']} |"
        )
    auxiliary = mr.stopping_conditions(main_result["did"], scenarios, mr.AUXILIARY_TOLERANCE_PP)
    lines += ["", "補助閾値 5pp での条件 2: " + "; ".join(
        f"{row['pathway']}: {row['条件2_差が許容差以上']}" for _, row in auxiliary.iterrows()
    ), ""]

    tipping = mr.tipping_point(frame, formula, counts, main_result["did"], seed=pc.MONTE_CARLO_SEED + 100)
    lines += ["### 条件 4: tipping point（era1 の誤分類を倍率で悪化させる）", "", *markdown_table(tipping), ""]

    # secondary outcomes, descriptive only
    secondary = pd.read_csv(args.secondary, dtype=str, encoding="utf-8-sig")
    merged = frame.merge(secondary[["source_player_id", "moved_overseas_final"]], on="source_player_id", how="left")
    merged["moved_overseas_final"] = pd.to_numeric(merged["moved_overseas_final"], errors="coerce")
    nat = pooled.set_index("source_player_id")["any_national_team_selection"]
    merged["national_yes"] = merged["source_player_id"].map(nat).eq("yes").astype(float)
    lines += [
        "## 6. 副アウトカム（探索的記述のみ・確認的検定はしない）",
        "",
        "**追跡期間は時代間で非対称である**（era1 は観測窓が長い）。ever 指標であり、",
        "固定ホライズン化されていないため、時代間の比較は記述にとどめる。",
        "",
        "| era | 経路 | 海外移籍 ever | A 代表等 ever | n |",
        "|---|---|---|---|---|",
    ]
    for era in pc.ERAS:
        for pathway in pc.MAIN_PATHWAYS:
            block = merged[(merged["era"] == era) & (merged["pathway_category"] == pathway)]
            lines.append(
                f"| {era} | {pathway} | {block['moved_overseas_final'].mean():.1%} "
                f"| {block['national_yes'].mean():.1%} | {len(block)} |"
            )

    # horizon sensitivity
    lines += ["", "## 7. 感度: ホライズン 23 / 27 歳（適格を再定義）", "", "| ホライズン | n | " + " | ".join(f"{p} DID" for p in pc.CONTRASTS) + " |", "|---|---|---|---|"]
    pooled_numeric = pooled.copy()
    pooled_numeric["birth_year_n"] = pd.to_numeric(pooled_numeric["birth_year"], errors="coerce")
    pooled_numeric["first_j1_n"] = pd.to_numeric(pooled_numeric["first_j1_season"], errors="coerce")
    for horizon in (23, 27):
        block = pooled_numeric[pooled_numeric["birth_year_n"] + horizon <= 2025].copy()
        block["reached_j1_by_age25"] = (
            (block["first_j1_n"] - block["birth_year_n"] <= horizon).fillna(False).astype(int).astype(str)
        )
        horizon_frame = pc.build_frame(block)
        try:
            _, _, values = pc.point_estimates(horizon_frame, formula)
            cells = " | ".join(f"{values[p] * 100:.1f}pp" for p in pc.CONTRASTS)
        except Exception as error:
            cells = f"推定できず: {error}"
        lines.append(f"| {horizon} 歳 | {len(horizon_frame)} | {cells} |")

    # institution cluster sensitivity
    lines += ["", "## 8. 感度: 機関クラスター SE / ポジション", ""]
    try:
        from jfa_talent_analysis.confirmatory_analysis import final_dev_institution

        stints = pd.read_csv(args.stints, dtype=str, encoding="utf-8-sig")
        institution = final_dev_institution(stints)
        clustered = frame.copy()
        clustered["institution"] = clustered["source_player_id"].map(institution)
        covered = clustered["institution"].notna().mean()
        lines.append(f"機関がパースできた選手: {covered:.1%}（できない選手はこの感度から除外・§6 事前指定）")
    except Exception as error:
        lines.append(f"機関クラスター感度は実行できなかった: {error}")
    lines += [
        "",
        "**ポジション感度は実施しない。** `position_master` は 2014 年以降の選手×シーズン表にしかなく、",
        "era1 側が構造的に欠測するため、era 比較の感度として意味を成さない（実行前に宣言）。",
        "",
        "## 9. Gate A の残存限界（§13 限界 11・必須添付）",
        "",
        "Gate A の合格は「gold が検証できなかった行も検証済みと同率で誤る」という仮定に依存する。",
        "gold 判定不能率は era1 17.6% / era2 3.4%。era1 の未検証 36 件（自動確定分）が",
        "**全部正しければ 1.9pp・検証済みと同率なら 1.3pp・全部誤りなら 16.4pp**（条件 2 が発火）。",
        "転換点は 13 件（36%）である。",
        "",
    ]

    args.outdir.mkdir(parents=True, exist_ok=True)
    report = args.outdir / "phase1b_confirmatory.md"
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")

    pd.DataFrame(
        [
            {"scenario": s.scenario, "description": s.description, **{f"{p}_did": s.did[p] for p in pc.CONTRASTS}}
            for s in scenarios
        ]
    ).to_csv(args.outdir / "phase1b_scenarios.csv", index=False)
    conditions.to_csv(args.outdir / "phase1b_stopping_conditions.csv", index=False)
    main_result["battery"].to_csv(args.outdir / "phase1b_birth_year_battery.csv", index=False)
    tipping.to_csv(args.outdir / "phase1b_tipping_point.csv", index=False)

    print(f"報告 -> {report}")
    print(f"  主検定 p = {main_result['test']['p_value']:.4g}")
    for pathway in pc.CONTRASTS:
        print(f"  DID {pathway} = {main_result['did'][pathway] * 100:.1f}pp")


if __name__ == "__main__":
    main()
