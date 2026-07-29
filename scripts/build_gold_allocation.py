"""Stratified allocation for the holdout gold (SAP §6b-2b).

The simulation fixes how many verified players each observed-pathway row needs;
this fixes which players they are and with what probability, which is what makes
the resulting confusion matrix weightable back to the population.

Two constraints shape it. The review requires over-sampling the strata where
misclassification actually lives -- the two procedures disagreeing, and any
direction that moves a player into or out of the reference category -- because a
proportional sample would spend almost everything on both_agree and estimate the
directions that matter from single figures. And §6b-2a puts the rows used to
build the rule into the development sample, so this allocation is a *fresh*
holdout rather than a top-up of the existing gold.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

MAIN_PATHWAYS = ("j_club_academy", "high_school", "university")
PER_ROW = 60  # SAP §6b-2c(ii), sensitivity envelope of simulate_gold_requirement.py

# Strata that carry the misclassification signal. Taken as a census up to this
# size: they are small, and estimating a direction-specific rate from a
# proportional slice of them is what the review objected to.
CRITICAL = ("disagree_academy", "disagree_other", "club_list_only", "prose_only")
CRITICAL_CAP = 25
HUMAN_REVIEWED_QUOTA = 10


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pooled", type=Path, default=Path("data/processed/pooled_player_outcomes_1999_2025.csv")
    )
    parser.add_argument(
        "--output", type=Path, default=Path("reports/generated/gold_allocation.md")
    )
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def stratum(row: dict[str, str]) -> str:
    """Which sampling stratum a labelled player belongs to.

    Disagreements are split by whether the reference category is involved, since
    that is the direction the review singled out: an error into or out of
    j_club_academy moves the baseline every other pathway is measured against.
    """
    source = row["pathway_category_source"]
    if source != "club_list_over_prose":
        return source
    if "j_club_academy" in (row["pathway_prose_category"], row["pathway_club_list_category"]):
        return "disagree_academy"
    return "disagree_other"


def allocate(population: Counter[str]) -> dict[str, int]:
    """How many to draw from each stratum within one observed-pathway row."""
    plan: dict[str, int] = {}
    remaining = PER_ROW
    for name in CRITICAL:
        size = population.get(name, 0)
        take = min(size, CRITICAL_CAP, remaining)
        if take:
            plan[name] = take
            remaining -= take
    reviewed = min(population.get("human_reviewed", 0), HUMAN_REVIEWED_QUOTA, remaining)
    if reviewed:
        plan["human_reviewed"] = reviewed
        remaining -= reviewed
    both = min(population.get("both_agree", 0), remaining)
    if both:
        plan["both_agree"] = both
        remaining -= both
    return plan


def main() -> None:
    args = parse_args()
    rows = [
        row
        for row in read_csv(args.pooled)
        if row["eligible_confirmatory"] == "1" and row["pathway_category"] in MAIN_PATHWAYS
    ]

    lines = [
        "# holdout gold の層化割付（SAP §6b-2b）",
        "",
        f"生成: `scripts/build_gold_allocation.py` / 1 行あたり {PER_ROW} 件",
        "",
        "**アウトカムは参照していない。** 層は曝露ラベルとその由来のみで定義される。",
        "",
        "## 設計",
        "",
        "- 行 = era × 観測経路（6 行）。1 行あたりの必要数は"
        " `simulate_gold_requirement.py` が決めた **60 件**（感度シナリオまで満たす水準）。",
        f"- **不一致・club_list_only・prose_only は最大 {CRITICAL_CAP} 件まで悉皆**。"
        "誤分類が実際に存在する層であり、比例配分すると方向別の率を数件から推定することになる"
        "（外部レビューが退けた設計）。",
        "- 不一致は**基準カテゴリが出入りする向き**（`disagree_academy`）を分けて扱う。",
        f"- `human_reviewed` は最大 {HUMAN_REVIEWED_QUOTA} 件（人手判定そのものの検証）。",
        "- 残りを `both_agree` から。",
        "- **抽出確率を層ごとに記録し、解析時にその逆数で母集団構成へ重み戻す。**",
        "",
        "> **これは既存 gold への上積みではない。** SAP §6b-2a により、規則の形成に用いた行"
        "（採用判断の 12 例、判定保留 5 行、v5 で判定した 115 行）は**開発標本**であり、"
        "独立性能評価の分母から除く。本割付は**新規の holdout** である。",
        "",
        "## 割付表",
        "",
        "| era | 観測経路 | 層 | 母集団 | 抽出数 | 抽出確率 |",
        "|---|---|---|---|---|---|",
    ]

    total = 0
    for era in ("era1", "era2"):
        for pathway in MAIN_PATHWAYS:
            population = Counter(
                stratum(row)
                for row in rows
                if row["era"] == era and row["pathway_category"] == pathway
            )
            plan = allocate(population)
            for name, take in sorted(plan.items(), key=lambda item: -item[1]):
                size = population[name]
                total += take
                lines.append(
                    f"| {era} | {pathway} | `{name}` | {size} | {take} | {take / size:.1%} |"
                )
            row_total = sum(plan.values())
            lines.append(
                f"| {era} | {pathway} | **小計** | {sum(population.values())} | "
                f"**{row_total}** | |"
            )
    lines += ["", f"**合計 {total} 件**（新規 holdout）。", ""]

    lines += [
        "## 収集の要件（SAP §6b-2a）",
        "",
        "- **outcome・両分類器の出力・最終採用ラベルのいずれも見ずに**、外部ソース",
        "  （クラブ公式・学校/大学・新聞・選手名鑑）で**二者独立判定**する。",
        "- 不一致は合議し、初回判定・最終判定・根拠 URL・判定者を保存する。",
        "- 層別抽出確率を**抽出前に固定して保存**する（本表がその記録）。",
        "- 検証不能・gold 判定不能も別カテゴリとして保存する（欠測として捨てない）。",
        "",
        "## 注記",
        "",
        "- `club_list_only` は適格標本に存在しない（該当行はすべてレビューを経て",
        "  `human_reviewed` になった）。層としては残すが割付は 0 件。",
        "- 悉皆にした層は抽出確率 100% なので重み戻しの分散寄与がない。逆に `both_agree` は",
        "  抽出率が低く、重みが大きい。",
        "- 収集後、実際の行構成で `simulate_gold_requirement.py` を再実行し、",
        "  停止規則を満たしたかを確認する（構成比を保つ仮定が崩れるため）。",
    ]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[lines.index("| era | 観測経路 | 層 | 母集団 | 抽出数 | 抽出確率 |") :]))
    print(f"\nwrote={args.output}")


if __name__ == "__main__":
    main()
