"""Run the Phase 1 confirmatory analysis (docs/research_plan_phase1.md §6).

This is the pre-specified confirmatory pipeline: logistic regressions of the
three outcome tiers on final pre-professional pathway with natural-cubic-
spline birth-cohort adjustment, institution-cluster-robust standard errors as
the primary covariance, g-computation adjusted probabilities and pathway risk
differences with cluster-bootstrap CIs, and the five pre-specified sensitivity
analyses. Output is a markdown report plus coefficient/risk-difference CSVs in
reports/generated/ (gitignored).
"""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

from jfa_talent_analysis.confirmatory_analysis import (
    COHORT_SPLINE_TERM,
    MAIN_PATHWAYS,
    PATHWAY_TERM,
    FittedLogit,
    adjusted_pathway_probabilities,
    bootstrap_risk_differences,
    build_analysis_frame,
    fit_logit,
    odds_ratio_table,
    risk_differences,
)
from jfa_talent_analysis.pathway_multiplicity import STAGES, build_multipath_rows

F_PRIMARY = f"reached_j1 ~ {PATHWAY_TERM} + {COHORT_SPLINE_TERM}"
F_PRIMARY_YOUTH = f"{F_PRIMARY} + youth_selected"
F_OVERSEAS = f"overseas_yes ~ {PATHWAY_TERM} + {COHORT_SPLINE_TERM}"
F_OVERSEAS_YOUTH = f"{F_OVERSEAS} + youth_selected"
F_OVERSEAS_SEQUENTIAL = f"{F_OVERSEAS_YOUTH} + reached_j1"
F_A_TEAM = f"a_team_selected ~ {PATHWAY_TERM} + {COHORT_SPLINE_TERM}"
F_A_TEAM_YOUTH = f"{F_A_TEAM} + youth_selected"

REPORT_TERMS = ("pathway_category", "youth_selected", "reached_j1", "position_mode")
FALSE_NEGATIVE_RATE = 0.022  # JFA spot-check (docs/jfa_national_team_spot_check_2026-07-08.md)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--outcomes", type=Path, default=Path("data/processed/player_pathway_outcomes.csv")
    )
    parser.add_argument(
        "--stints",
        type=Path,
        default=Path("data/interim/coach_network/player_institution_stints.csv"),
    )
    parser.add_argument(
        "--features",
        type=Path,
        default=Path("data/processed/player_season_features_2014_2025_J1_J2_J3.csv"),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("reports/generated"))
    parser.add_argument("--n-boot", type=int, default=500)
    parser.add_argument("--n-bias-reps", type=int, default=200)
    parser.add_argument("--seed", type=int, default=20260718)
    return parser.parse_args()


def fmt_or(row: pd.Series) -> str:
    return f"{row['odds_ratio']:.2f} [{row['ci_low']:.2f}, {row['ci_high']:.2f}]"


def short_term(term: str) -> str:
    if "pathway_category" in term and "[T." in term:
        return "pathway=" + term.split("[T.")[1].rstrip("]")
    if "position_mode" in term and "[T." in term:
        return "position=" + term.split("[T.")[1].rstrip("]")
    return term


def or_section(fits: list[FittedLogit]) -> list[str]:
    lines = [
        "| model | term | OR [95% CI] | p | n | SE type |",
        "|---|---|---|---|---|---|",
    ]
    for fit in fits:
        table = odds_ratio_table(fit)
        mask = table["term"].apply(lambda t: any(key in t for key in REPORT_TERMS))
        for _, row in table[mask].iterrows():
            cov = fit.cov_type
            if fit.n_clusters:
                cov = f"cluster ({fit.n_clusters})"
            lines.append(
                f"| {fit.label} | {short_term(row['term'])} | {fmt_or(row)} | "
                f"{row['p_value']:.4f} | {fit.n} | {cov} |"
            )
    lines.append("")
    return lines


def rd_section(
    label: str,
    fit: FittedLogit,
    df: pd.DataFrame,
    n_boot: int,
    seed: int,
    cluster_col: str | None,
) -> tuple[list[str], pd.DataFrame]:
    probabilities = adjusted_pathway_probabilities(fit, df)
    rds = risk_differences(probabilities)
    ci = bootstrap_risk_differences(
        df, fit.formula, cluster_col=cluster_col, n_boot=n_boot, seed=seed
    )
    lines = [
        f"調整済み予測確率（g-computation, {label}）: "
        + ", ".join(f"{level} {probabilities[level]:.3f}" for level in MAIN_PATHWAYS),
        "",
        "| pathway | risk difference vs j_club_academy | bootstrap 95% CI |",
        "|---|---|---|",
    ]
    records = []
    for _, row in ci.iterrows():
        level = row["pathway"]
        lines.append(
            f"| {level} | {rds[level]:+.3f} | "
            f"[{row['rd_ci_low']:+.3f}, {row['rd_ci_high']:+.3f}] "
            f"({row['n_boot_ok']}/{row['n_boot_ok'] + row['n_boot_failed']} reps) |"
        )
        records.append(
            {
                "model": label,
                "pathway": level,
                "adjusted_probability": probabilities[level],
                "risk_difference": rds[level],
                "rd_ci_low": row["rd_ci_low"],
                "rd_ci_high": row["rd_ci_high"],
            }
        )
    records.append(
        {
            "model": label,
            "pathway": "j_club_academy",
            "adjusted_probability": probabilities["j_club_academy"],
            "risk_difference": 0.0,
            "rd_ci_low": np.nan,
            "rd_ci_high": np.nan,
        }
    )
    lines.append("")
    return lines, pd.DataFrame(records)


def university_or(fit: FittedLogit) -> float:
    table = odds_ratio_table(fit)
    return float(table[table["term"].str.contains("university")]["odds_ratio"].iloc[0])


def main() -> None:
    args = parse_args()
    outcomes = pd.read_csv(args.outcomes, dtype=str)
    stints = pd.read_csv(args.stints, dtype=str).fillna("")
    features = pd.read_csv(args.features, dtype=str)
    df = build_analysis_frame(outcomes, stints, features)

    lines = [
        "# Phase 1 Confirmatory Analysis Report",
        "",
        f"Generated: {dt.date.today().isoformat()} | SAP: docs/research_plan_phase1.md §6 "
        f"| seed={args.seed}, n_boot={args.n_boot}, n_bias_reps={args.n_bias_reps}",
        "",
        "本レポートの推定値は SAP コミット後の確認的分析。用語は SAP §8 に従い、"
        "すべて「関連」であって因果効果ではない。",
        "",
        "## 1. 対象者フロー",
        "",
    ]

    total = len(df)
    unident = int((df["pathway_category_source"] == "identity_not_confirmed").sum())
    classified = total - unident
    unknown = int((df["pathway_category"] == "unknown").sum())
    jfa = int((df["pathway_category"] == "jfa_academy").sum())
    grassroots = int((df["pathway_category"] == "grassroots_club").sum())
    base = df[df["in_main_pathways"] & df["birth_year"].notna() & df["reached_j1"].notna()].copy()
    lines += [
        f"- 全同定済み日本人選手: {total}",
        f"- 本人同定不能: {unident} → 経路分類対象 {classified}",
        f"- pathway unknown: {unknown} / jfa_academy: {jfa} / grassroots_club: {grassroots}",
        f"- 主要3経路の主分析標本: {len(base)} "
        f"({base['pathway_category'].value_counts().to_dict()})",
        f"- 機関クラスター同定済み（主SE用）: {int(base['final_institution'].notna().sum())} "
        f"/ クラスター数 {base['final_institution'].nunique()}",
        "",
        "SAP §4 の事前固定値: 4,037 / 634 / 3,403 / 117 / 11 / 9 / 3,266。上と一致しない場合は"
        "逸脱として SAP に追記すること。",
        "",
    ]

    clustered = base[base["final_institution"].notna()].copy()

    # ---- Primary outcome ----
    m_primary = fit_logit(clustered, F_PRIMARY, "J1到達・主（機関クラスターSE）", "final_institution")
    m_primary_full = fit_logit(base, F_PRIMARY, "J1到達・全標本（通常SE）")
    m_primary_youth = fit_logit(
        clustered, F_PRIMARY_YOUTH, "J1到達＋youth_selected調整", "final_institution"
    )
    lines += ["## 2. 主アウトカム: J1到達", ""]
    lines += or_section([m_primary, m_primary_full, m_primary_youth])
    rd_frames = []
    for label, fit in [("J1到達・主", m_primary), ("J1到達＋youth調整", m_primary_youth)]:
        section, frame = rd_section(
            label, fit, clustered, args.n_boot, args.seed, "final_institution"
        )
        lines += section
        rd_frames.append(frame)

    # ---- Secondary outcomes ----
    overseas = clustered[clustered["overseas_labeled"]].copy()
    overseas_full = base[base["overseas_labeled"]].copy()
    nt = clustered[clustered["nt_labeled"]].copy()
    nt_full = base[base["nt_labeled"]].copy()
    m_overseas = fit_logit(overseas, F_OVERSEAS, "海外移籍・主（クラスターSE）", "final_institution")
    m_overseas_full = fit_logit(overseas_full, F_OVERSEAS, "海外移籍・全標本（通常SE）")
    m_overseas_youth = fit_logit(
        overseas, F_OVERSEAS_YOUTH, "海外移籍＋youth調整", "final_institution"
    )
    m_overseas_seq = fit_logit(
        overseas, F_OVERSEAS_SEQUENTIAL, "海外移籍・逐次調整（+reached_j1）", "final_institution"
    )
    m_a_team = fit_logit(nt, F_A_TEAM, "A代表・主（クラスターSE）", "final_institution")
    m_a_team_full = fit_logit(nt_full, F_A_TEAM, "A代表・全標本（通常SE）")
    m_a_team_youth = fit_logit(nt, F_A_TEAM_YOUTH, "A代表＋youth調整", "final_institution")

    lines += ["## 3. 副アウトカム: 海外移籍・A代表", ""]
    lines += or_section(
        [m_overseas, m_overseas_full, m_overseas_youth, m_a_team, m_a_team_full, m_a_team_youth]
    )
    for label, fit, frame_df in [
        ("海外移籍・主", m_overseas, overseas),
        ("A代表・主", m_a_team, nt),
    ]:
        section, frame = rd_section(
            label, fit, frame_df, args.n_boot, args.seed, "final_institution"
        )
        lines += section
        rd_frames.append(frame)

    lines += [
        "## 4. 逐次調整モデル（海外移籍のみ・媒介分析ではない）",
        "",
        "J1到達を追加調整した後に残る経路と海外移籍の関連（SAP §8: 「J1到達調整後の残存関連」）。",
        "",
    ]
    lines += or_section([m_overseas_seq])

    # ---- Sensitivity analyses ----
    lines += ["## 5. 事前指定の感度分析", ""]

    lines += ["### 5.1 出生年下限制限", ""]
    sens_rows = [f"- 基準（全出生年, n={m_primary.n}）: university OR {university_or(m_primary):.2f}"]
    for floor in (1995, 2000):
        subset = clustered[clustered["birth_year"] >= floor]
        fit = fit_logit(subset, F_PRIMARY, f"J1到達・出生年≥{floor}", "final_institution")
        sens_rows.append(f"- 出生年≥{floor} (n={fit.n}): university OR {university_or(fit):.2f}")
    lines += sens_rows + [""]

    lines += ["### 5.2 pathway_category_source による分類誤り感度", ""]
    reviewed = base[base["pathway_category_source"] == "human_reviewed"]
    auto_only = clustered[clustered["pathway_category_source"] == "auto_high_confidence"]
    fit_reviewed = fit_logit(reviewed, F_PRIMARY, "J1到達・human_reviewedのみ（通常SE）")
    fit_auto = fit_logit(
        auto_only, F_PRIMARY, "J1到達・auto_high_confidenceのみ", "final_institution"
    )
    lines += [
        f"- human_reviewed のみ (n={fit_reviewed.n}): "
        f"university OR {university_or(fit_reviewed):.2f}"
        f"（基準 {university_or(m_primary):.2f}。n が小さく点推定のみ参考値——"
        "human_reviewed は分類器が要レビューと判定した難例の集合であり、"
        "ここでの一致は分類誤りが主結果を駆動していないことの弱い傍証）",
        f"- auto_high_confidence のみ (n={fit_auto.n}): "
        f"university OR {university_or(fit_auto):.2f}",
        "",
    ]

    lines += [
        "### 5.3 代表歴「該当なし」偽陰性 2.2% の確率的バイアス分析",
        "",
        f"any_national_team_selection='no' の選手の youth_selected を確率 {FALSE_NEGATIVE_RATE} "
        f"で 1 に反転させて youth 調整付き J1 モデルを再推定（{args.n_bias_reps} 回、"
        "通常SEの点推定のみ）。アウトカム側（A代表）の偽陰性はさらに低率のため"
        "モデル化しない（A代表の見逃しは youth 選出の見逃しより稀）。",
        "",
    ]
    rng = np.random.default_rng(args.seed)
    bias_ors = []
    no_mask = clustered["any_national_team_selection"] == "no"
    for _ in range(args.n_bias_reps):
        perturbed = clustered.copy()
        flips = no_mask & (rng.random(len(perturbed)) < FALSE_NEGATIVE_RATE)
        perturbed.loc[flips, "youth_selected"] = 1
        fit = fit_logit(perturbed, F_PRIMARY_YOUTH, "bias")
        bias_ors.append(university_or(fit))
    bias_arr = np.asarray(bias_ors)
    lines += [
        f"- youth調整モデルの university OR: 中央値 {np.median(bias_arr):.3f} "
        f"[2.5–97.5 パーセンタイル {np.percentile(bias_arr, 2.5):.3f}, "
        f"{np.percentile(bias_arr, 97.5):.3f}]（無摂動 {university_or(m_primary_youth):.3f}）",
        "",
    ]

    lines += ["### 5.4 同定不能 634 名の欠測機構評価と IPW 再推定", ""]
    comp = df.groupby("identified").agg(
        n=("source_player_id", "count"),
        birth_year_mean=("birth_year", "mean"),
        tier_a=("minutes_tier", lambda s: (s == "A").mean()),
        tier_c=("minutes_tier", lambda s: (s == "C").mean()),
    )
    for identified, row in comp.iterrows():
        label = "同定済み" if identified == 1 else "同定不能"
        lines.append(
            f"- {label}: n={int(row['n'])}, 平均出生年 {row['birth_year_mean']:.1f}, "
            f"Tier A率 {row['tier_a']:.1%}, Tier C率 {row['tier_c']:.1%}"
        )
    ident_df = df[df["birth_year"].notna()].copy()
    ident_model = fit_logit(
        ident_df,
        f"identified ~ {COHORT_SPLINE_TERM} + np.log1p(career_minutes_num)",
        "同定確率モデル（IPW用）",
    ).result
    base_ipw = base.copy()
    base_ipw["ipw"] = 1.0 / ident_model.predict(base_ipw)
    glm = smf.glm(
        F_PRIMARY,
        data=base_ipw,
        family=sm.families.Binomial(),
        var_weights=base_ipw["ipw"],
    ).fit()
    uni_ipw = float(
        np.exp(glm.params[[i for i in glm.params.index if "university" in i][0]])
    )
    lines += [
        f"- IPW 再推定（点推定のみ・SEは重み付けを反映しない）: university OR {uni_ipw:.2f}"
        f"（基準 {university_or(m_primary_full):.2f}）",
        "",
    ]

    lines += ["### 5.5 機関クラスター SE の有無比較（同一標本）", ""]
    m_nocluster = fit_logit(clustered, F_PRIMARY, "J1到達・クラスター標本・通常SE")
    lines += or_section([m_primary, m_nocluster])

    lines += ["### 5.6 ポジション調整（感度共変量・サブグループ解析はしない）", ""]
    positioned = clustered[clustered["position_mode"].notna()].copy()
    m_position = fit_logit(
        positioned,
        f"{F_PRIMARY} + C(position_mode)",
        "J1到達＋position_mode調整",
        "final_institution",
    )
    lines += or_section([m_position])

    # ---- Multipath descriptives ----
    lines += ["## 6. 多段階経路の記述（SAP §7・探索）", ""]
    multipath = build_multipath_rows(stints)
    merged = base.merge(multipath, on="source_player_id", how="left")
    lines += [
        f"- 最終段階年代の在籍が観測された選手: {len(multipath)}",
        "- has_* 率: "
        + ", ".join(
            f"{stage} {multipath[f'has_{stage}'].mean():.1%}" for stage in STAGES
        ),
        "- pathway_count 分布: "
        + ", ".join(
            f"{count}段階 {n}名"
            for count, n in multipath["pathway_count"].value_counts().sort_index().items()
        ),
        "- 主分析標本内で複数段階経験（pathway_count≥2）: "
        f"{int((merged['pathway_count'] >= 2).sum())} 名 "
        f"({(merged['pathway_count'] >= 2).mean():.1%})",
        "- 上位系列: "
        + "; ".join(
            f"{sequence} ({n})"
            for sequence, n in multipath["pathway_sequence"].value_counts().head(6).items()
        ),
        "",
    ]

    # ---- Outputs ----
    args.output_dir.mkdir(parents=True, exist_ok=True)
    all_fits = [
        m_primary,
        m_primary_full,
        m_primary_youth,
        m_overseas,
        m_overseas_full,
        m_overseas_youth,
        m_overseas_seq,
        m_a_team,
        m_a_team_full,
        m_a_team_youth,
        fit_reviewed,
        m_nocluster,
        m_position,
    ]
    pd.concat([odds_ratio_table(fit) for fit in all_fits]).to_csv(
        args.output_dir / "phase1_confirmatory_model_coefficients.csv", index=False
    )
    pd.concat(rd_frames).to_csv(
        args.output_dir / "phase1_confirmatory_risk_differences.csv", index=False
    )
    report_path = args.output_dir / "phase1_confirmatory_report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {report_path}")


if __name__ == "__main__":
    main()
