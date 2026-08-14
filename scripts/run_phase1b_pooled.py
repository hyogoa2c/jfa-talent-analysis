"""The pooled association between pathway and reaching J1 by 25 (SAP §12).

A separate estimand, not a sensitivity analysis for H1b-2: it asks what the
pathway gap looks like averaged over 1981-1999 births, with no era term at all.
§12 fixed the specification before H1b-2 ran, so nothing here was chosen after
seeing that result.

**This runs as exploratory.** H1b-2 was downgraded when Gate B fired
(`docs/phase1b_confirmatory_results_2026-08-14.md`), and the same measurement
error sits under these numbers. The pooled estimate is reported as a description
of the measured association, not as a confirmatory finding.

Run: uv run python scripts/run_phase1b_pooled.py
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

from jfa_talent_analysis import phase1b_confirmatory as pc

BIRTH_MIN, BIRTH_MAX = 1981, 1999
BOOT = 500
SEED = 20260718


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pooled", type=Path, default=Path("data/processed/pooled_player_outcomes_1999_2025.csv")
    )
    parser.add_argument(
        "--leagues", type=Path, default=Path("data/processed/career_league_seasons_1999_2025.csv")
    )
    parser.add_argument(
        "--output", type=Path, default=Path("reports/generated/phase1b_pooled.md")
    )
    parser.add_argument("--n-boot", type=int, default=BOOT)
    return parser.parse_args()


def head_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except Exception:
        return "unknown"


def build_pooled_frame(pooled: pd.DataFrame) -> pd.DataFrame:
    """§12-2: eligible, born 1981-1999, one of the three main pathways.

    Births from 2000 are excluded because a 25-year horizon cannot have
    completed for them -- the same rule §5 states, applied here rather than
    silently carried in through the era variable.
    """
    frame = pooled.copy()
    frame["birth_year"] = pd.to_numeric(frame["birth_year"], errors="coerce")
    frame = frame[
        (frame["eligible_confirmatory"].astype(str) == "1")
        & frame["birth_year"].between(BIRTH_MIN, BIRTH_MAX)
        & frame["pathway_category"].isin(pc.MAIN_PATHWAYS)
    ].copy()
    frame[pc.OUTCOME] = frame[pc.OUTCOME].astype(float)
    return frame.reset_index(drop=True)


def three_knots(birth_year: pd.Series) -> list[float]:
    """§12-2's three-knot RCS, placed at quantiles.

    §12 says three knots and cites §6's "five-year quantile" placement, which
    names four cut points. Three knots at the 20th, 50th and 80th percentiles is
    the reading that keeps the count §12 fixed while staying quantile-based; it
    is recorded here because the two clauses cannot both be taken literally.
    """
    return [float(v) for v in np.quantile(birth_year.to_numpy(float), [0.2, 0.5, 0.8])]


def pooled_risks(df: pd.DataFrame, formula: str) -> dict[str, float]:
    """G-computation over the whole pooled sample (§12-2 標準化対象)."""
    fit = pc._fit(df, formula)
    risks = {}
    for pathway in pc.MAIN_PATHWAYS:
        counterfactual = df.copy()
        counterfactual["pathway_category"] = pathway
        risks[pathway] = float(fit.predict(counterfactual).mean())
    return risks


def risk_differences(risks: dict[str, float]) -> dict[str, float]:
    return {p: risks[p] - risks[pc.BASE_PATHWAY] for p in pc.CONTRASTS}


def bootstrap(df: pd.DataFrame, formula: str, n_boot: int, seed: int) -> dict[str, tuple[float, float]]:
    rng = np.random.default_rng(seed)
    draws = {p: [] for p in pc.CONTRASTS}
    for _ in range(n_boot):
        sample = df.sample(n=len(df), replace=True, random_state=int(rng.integers(2**32)))
        try:
            values = risk_differences(pooled_risks(sample, formula))
        except Exception:
            continue
        for pathway, value in values.items():
            draws[pathway].append(value)
    return {
        pathway: (
            float(np.percentile(values, 2.5)),
            float(np.percentile(values, 97.5)),
        )
        for pathway, values in draws.items()
        if values
    }


def odds_ratios(df: pd.DataFrame, formula: str) -> dict[str, tuple[float, float, float]]:
    fit = pc._fit(df, formula)
    interval = fit.conf_int()
    out = {}
    for pathway in pc.CONTRASTS:
        term = [t for t in fit.params.index if pathway in t]
        if not term:
            continue
        key = term[0]
        out[pathway] = (
            float(np.exp(fit.params[key])),
            float(np.exp(interval.loc[key, 0])),
            float(np.exp(interval.loc[key, 1])),
        )
    return out


def main() -> None:
    args = parse_args()
    pooled = pd.read_csv(args.pooled, dtype=str, encoding="utf-8-sig")
    frame = build_pooled_frame(pooled)

    knots = three_knots(frame["birth_year"])
    spline = f"cr(birth_year, knots=[{', '.join(f'{k:.4f}' for k in knots)}])"
    main_formula = f"{pc.OUTCOME} ~ {pc.PATHWAY_TERM} + {spline}"

    risks = pooled_risks(frame, main_formula)
    differences = risk_differences(risks)
    interval = bootstrap(frame, main_formula, args.n_boot, SEED)
    ors = odds_ratios(frame, main_formula)

    lines = [
        "# Phase 1b プール解析（SAP §12・**探索的**）",
        "",
        f"コード版 `{head_commit()}` / 出生年 {BIRTH_MIN}–{BIRTH_MAX} / "
        f"ブートストラップ {args.n_boot} 回・seed {SEED}",
        "",
        "**探索的として実施する。** H1b-2 は Gate B の発火により確認的主張から降格しており",
        "（`docs/phase1b_confirmatory_results_2026-08-14.md`）、同じ測定誤差がこの推定の下にもある。",
        "**era 項は主仕様に入れない**（§12-2）。プール推定から era 別効果を逆算する記述はしない。",
        "",
        f"主仕様: `{main_formula}`",
        f"RCS ノット（3 点・分位）: {[round(k, 1) for k in knots]}",
        "",
        "## 1. 標本",
        "",
        f"プール標本 **{len(frame)} 名**（出生年 {int(frame['birth_year'].min())}–{int(frame['birth_year'].max())}）",
        "",
        "| 経路 | n | 割合 |",
        "|---|---|---|",
    ]
    counts = frame["pathway_category"].value_counts()
    for pathway in pc.MAIN_PATHWAYS:
        lines.append(f"| {pathway} | {counts.get(pathway, 0)} | {counts.get(pathway, 0) / len(frame):.1%} |")

    excluded = pooled[
        (pooled["eligible_confirmatory"].astype(str) == "1")
        & pd.to_numeric(pooled["birth_year"], errors="coerce").between(BIRTH_MIN, BIRTH_MAX)
        & (~pooled["pathway_category"].isin(pc.MAIN_PATHWAYS))
    ]
    lines += [
        "",
        f"**除外（unknown・3 経路外）: {len(excluded)} 名**",
        "",
        "| era | 除外数 |",
        "|---|---|",
    ]
    for era, count in excluded["era"].value_counts().sort_index().items():
        lines.append(f"| {era} | {count} |")

    lines += ["", "参入 season の分布（§12-3）", "", "| era | n | 参入 season 中央値 |", "|---|---|---|"]
    frame["first_observed_season"] = pd.to_numeric(frame["first_observed_season"], errors="coerce")
    for era, block in frame.groupby("era"):
        lines.append(f"| {era} | {len(block)} | {block['first_observed_season'].median():.0f} |")

    lines += [
        "",
        "## 2. 主報告: 標準化到達確率とリスク差",
        "",
        "| 経路 | 標準化到達確率 | リスク差（vs j_club_academy） | 95% 区間 | OR [95% CI] |",
        "|---|---|---|---|---|",
        f"| j_club_academy | {risks['j_club_academy']:.1%} | — | — | 1（基準） |",
    ]
    for pathway in pc.CONTRASTS:
        low, high = interval.get(pathway, (float("nan"), float("nan")))
        odds = ors.get(pathway, (float("nan"),) * 3)
        lines.append(
            f"| {pathway} | {risks[pathway]:.1%} | **{differences[pathway] * 100:.1f}pp** "
            f"| [{low * 100:.1f}, {high * 100:.1f}]pp | {odds[0]:.2f} [{odds[1]:.2f}, {odds[2]:.2f}] |"
        )

    # sensitivities
    lines += ["", "## 3. 感度（§12-2）", "", "| 感度 | n | " + " | ".join(f"{p} リスク差" for p in pc.CONTRASTS) + " |", "|---|---|---|---|"]

    def sensitivity(label: str, block: pd.DataFrame, formula: str | None = None) -> None:
        use = formula or main_formula
        try:
            values = risk_differences(pooled_risks(block, use))
            cells = " | ".join(f"{values[p] * 100:.1f}pp" for p in pc.CONTRASTS)
        except Exception as error:
            cells = f"推定できず: {error}"
        lines.append(f"| {label} | {len(block)} | {cells} |")

    sensitivity("線形出生年（主仕様は RCS）", frame, f"{pc.OUTCOME} ~ {pc.PATHWAY_TERM} + birth_year")
    sensitivity("born ≥ 1984", frame[frame["birth_year"] >= 1984])
    if args.leagues.exists():
        leagues = pd.read_csv(args.leagues, dtype=str, encoding="utf-8-sig")
        top = set(leagues[leagues["division"].isin(["J1", "J2"])]["source_player_id"])
        sensitivity("J1/J2 出場ありに限定", frame[frame["source_player_id"].isin(top)])
    else:
        lines.append("| J1/J2 限定 | — | リーグ表が無く実行できない |")
    for source, block in frame.groupby("pathway_category_source"):
        if len(block) >= 100:
            sensitivity(f"source = {source}", block)

    lines += [
        "",
        "## 4. 解釈上の制約（§12-3）",
        "",
        "- 対象は**リーグ出場者に条件付けられた集団**であり、育成人口全体への一般化はできない。",
        "- プール効果は era 別効果の**混合**であり、時代を通じた平均的関連としてのみ読む。",
        "- 1999–2004 年はリーグ構造が異なる（J3 不在）。J1/J2 限定感度と参入 season の分布を上に併記した。",
        "- **測定誤差は H1b-2 と同じものが乗っている。** Gate B が示したのは「実測の誤分類だけで",
        "  9pp 規模の era 差が動く」ことであり、プール推定でも同じ誤分類が働いている。",
        "  ここでの区間は**測定誤差を含まない**（統計的不確実性のみ）ことに注意する。",
        "",
    ]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"報告 -> {args.output}")
    print(f"  n = {len(frame)}")
    for pathway in pc.CONTRASTS:
        print(f"  リスク差 {pathway} = {differences[pathway] * 100:.1f}pp")


if __name__ == "__main__":
    main()
