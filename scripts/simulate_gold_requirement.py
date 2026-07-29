"""Find the gold size at which Gate B's DID comparison becomes decidable.

Answers the question the review said "100 per era" had not answered: how many
verified players per row are needed before the uncertainty the gold sample puts
into the corrected DID is finer than the tolerance it is being compared against.

Outcome-free with respect to Phase 1b. Pathway composition comes from the
exposure labels; outcome risks are assumed, from Phase 1's published values in
the primary run and from hypothetical ranges in the sensitivity.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from jfa_talent_analysis.gold_requirement import (
    MAIN_PATHWAYS,
    EraInputs,
    half_width,
    simulate,
)

# SAP §6b-6. The correction has to be pinned down more finely than the movement
# Gate B is asked to detect, or the gate answers a question about sample size.
TOLERANCE_PP = 3.0

# Phase 1's published adjusted probabilities for J1 attainment by pathway
# (docs/results_canonical.md, 2026-07-28 re-run). Used as the primary design
# input; Phase 1b's own risks cannot be looked at.
PHASE1_RISKS = {"j_club_academy": 0.595, "high_school": 0.522, "university": 0.315}

# Sensitivity: risk levels bracketing the published ones, run as whole-scenario
# shifts so the requirement is not read off a single assumed value.
RISK_SCENARIOS = {
    "phase1_published": PHASE1_RISKS,
    "compressed_gap": {"j_club_academy": 0.50, "high_school": 0.47, "university": 0.40},
    "wide_gap": {"j_club_academy": 0.70, "high_school": 0.60, "university": 0.25},
    "low_risk": {"j_club_academy": 0.35, "high_school": 0.30, "university": 0.18},
}

GOLD_SETS = (
    (Path("data/manual/goldsets/goldset_era1_gold_labels.csv"), "era1"),
    (Path("data/manual/goldsets/goldset_era2_gold_labels.csv"), "era2"),
)
POOLED = Path("data/processed/pooled_player_outcomes_1999_2025.csv")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--draws", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20260718)
    parser.add_argument(
        "--output", type=Path, default=Path("reports/generated/gold_requirement.md")
    )
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def load_inputs() -> tuple[dict[str, dict[str, int]], dict[str, dict[str, dict[str, int]]]]:
    """Observed pathway counts and gold confusion counts, per era. No outcomes read."""
    pooled = {row["source_player_id"]: row for row in read_csv(POOLED)}
    counts: dict[str, dict[str, int]] = {}
    for era in ("era1", "era2"):
        counts[era] = {
            pathway: sum(
                1
                for row in pooled.values()
                if row["eligible_confirmatory"] == "1"
                and row["era"] == era
                and row["pathway_category"] == pathway
            )
            for pathway in MAIN_PATHWAYS
        }

    confusion: dict[str, dict[str, dict[str, int]]] = {}
    for path, era in GOLD_SETS:
        table = {o: dict.fromkeys(MAIN_PATHWAYS, 0) for o in MAIN_PATHWAYS}
        for row in read_csv(path):
            if row["determination"] != "confirmed":
                continue
            true = row["gold_pathway_category"]
            player = pooled.get(row["source_player_id"])
            if true not in MAIN_PATHWAYS or player is None:
                continue
            observed = player["pathway_category"]
            if observed in MAIN_PATHWAYS:
                table[observed][true] += 1
        confusion[era] = table
    return counts, confusion


def main() -> None:
    args = parse_args()
    counts, confusion = load_inputs()

    lines = [
        "# 追加 gold の必要数（SAP §6b-2c(ii) の精度ベース停止規則）",
        "",
        f"生成: `scripts/simulate_gold_requirement.py` / seed={args.seed} / draws={args.draws}",
        "",
        "**Phase 1b のアウトカムは参照していない。** 経路構成は曝露ラベル由来、",
        "アウトカムリスクは仮定（主 = Phase 1 既報値、感度 = 仮想シナリオ）。",
        "",
        "## 判定規則",
        "",
        f"Gate B は「感度推定と主推定の DID 差が {TOLERANCE_PP:.0f}pp 以上か」を問う。",
        "その比較が意味を持つのは、**DID 補正そのものの不確実性が tolerance より細かいとき**",
        "だけである。したがって停止規則は:",
        "",
        f"> **補正後 DID の 95% 区間の半幅 < {TOLERANCE_PP:.0f}pp**",
        "",
        "半幅が tolerance を超えている限り、Gate B の答えは測定の悪さではなく",
        "**検証した人数の少なさ**で決まる。",
        "",
        "## 現在の gold（観測 O 行 × 真 T 列）",
        "",
    ]
    for era in ("era1", "era2"):
        lines += [f"**{era}**（適格標本の経路構成: " + ", ".join(
            f"{p} {counts[era][p]}" for p in MAIN_PATHWAYS
        ) + "）", "", "| 観測＼真 | " + " | ".join(MAIN_PATHWAYS) + " | 行計 |", "|---|---|---|---|---|"]
        for observed in MAIN_PATHWAYS:
            row = confusion[era][observed]
            lines.append(
                f"| {observed} | "
                + " | ".join(str(row[t]) for t in MAIN_PATHWAYS)
                + f" | {sum(row.values())} |"
            )
        lines.append("")

    lines += [
        "## 1 行あたり検証数と DID 分解能",
        "",
        "行 = 観測経路。`現状` は上表そのもの。以降は各行をその件数まで増やした場合",
        "（行の構成比は保ったまま精度だけ上がる、という設計計算上の仮定）。",
        "",
        "| 1 行あたり検証数 | " + " | ".join(RISK_SCENARIOS) + " |",
        "|---|" + "---|" * len(RISK_SCENARIOS),
    ]

    sizes: list[int | None] = [None, 20, 30, 40, 50, 60, 80, 100]
    results: dict[int | None, dict[str, float]] = {}
    for per_cell in sizes:
        row_out = []
        results[per_cell] = {}
        for name, risks in RISK_SCENARIOS.items():
            era1 = EraInputs(counts["era1"], confusion["era1"], risks)
            era2 = EraInputs(counts["era2"], confusion["era2"], risks)
            values = simulate(
                era1, era2, per_cell=per_cell, draws=args.draws, seed=args.seed
            )
            width = half_width(values)
            results[per_cell][name] = width
            mark = "" if width < TOLERANCE_PP else " ×"
            row_out.append(f"{width:.1f}pp{mark}")
        label = "現状" if per_cell is None else str(per_cell)
        lines.append(f"| {label} | " + " | ".join(row_out) + " |")

    sized = {k: v for k, v in results.items() if k is not None}
    worst = {size: max(scenarios.values()) for size, scenarios in sized.items()}
    primary = {size: scenarios["phase1_published"] for size, scenarios in sized.items()}
    passing_primary = [s for s, w in sorted(primary.items()) if w < TOLERANCE_PP]
    passing_all = [s for s, w in sorted(worst.items()) if w < TOLERANCE_PP]
    lines += [
        "",
        "×印 = 半幅が tolerance 以上で、Gate B を判定できない水準。",
        "",
        "## 結論",
        "",
    ]
    current = max(results[None].values())
    lines.append(
        f"- **現状の分解能は最悪シナリオで {current:.1f}pp** "
        f"（tolerance {TOLERANCE_PP:.0f}pp に対して"
        f"{'不足' if current >= TOLERANCE_PP else '充足'}）。"
    )
    need = passing_primary[0] if passing_primary else None
    envelope = passing_all[0] if passing_all else None
    lines.append(
        f"- **主仕様（Phase 1 既報リスク）で停止規則を満たす最小の 1 行あたり検証数 = "
        f"{need if need else '>100'} 件**"
        + (f"（{primary[need]:.1f}pp）。" if need else "。")
    )
    lines.append(
        f"- 感度シナリオまで含めて満たすには **{envelope if envelope else '>100'} 件/行**"
        + (f"（最悪 {worst[envelope]:.1f}pp、`wide_gap`）。" if envelope else "。")
        + "経路間リスク差が大きいシナリオほど誤分類の影響が増幅されるため必要数が増える。"
    )
    lines.append(
        "- **どちらを停止規則に採るかは SAP で固定する。** 主仕様を規則とし感度を併記するのが"
        "承認済みの設計（主 = Phase 1 既報リスク、感度 = 仮想範囲）だが、"
        "**感度側が主の 1.6 倍を要求している**ため、この差は事前に決めておく必要がある。"
    )
    if need:
        lines += [
            "",
            f"### 主仕様（{need} 件/行）での追加数",
            "",
            "| era × 観測経路 | 現在 | 目標 | 追加 |",
            "|---|---|---|---|",
        ]
        total_extra = 0
        for era in ("era1", "era2"):
            for observed in MAIN_PATHWAYS:
                have = sum(confusion[era][observed].values())
                extra = max(0, need - have)
                total_extra += extra
                lines.append(f"| {era} {observed} | {have} | {need} | {extra} |")
        lines.append(f"| **合計** | | | **{total_extra}** |")
        if envelope:
            envelope_extra = sum(
                max(0, envelope - sum(confusion[era][o].values()))
                for era in ("era1", "era2")
                for o in MAIN_PATHWAYS
            )
            lines.append("")
            lines.append(
                f"感度シナリオまで満たす場合は {envelope} 件/行 = **追加 {envelope_extra} 件**。"
            )
    lines += [
        "",
        "**この数は Gate A の妥当性条件（§6b-2c(i)・セルあたり約 16 件）とは別の量である。**",
        "Gate A は感度・PPV の Wilson 下限を 80% 超にするための数、ここは DID 補正の",
        "分解能を tolerance より細かくするための数で、必要数の決まり方が違う。",
        "**両方を満たす必要がある。**",
        "",
        "## 限界",
        "",
        "- 行の構成比を保ったまま増やす仮定を置いている。追加抽出が不一致層を過剰抽出する",
        "  設計（SAP §6b-2b）である以上、実際の行構成は変わる。抽出確率で重み戻した後の",
        "  行で再計算すること。",
        "- 誤分類はアウトカムに対して非差異的と仮定している。差異的誤分類は Gate B の",
        "  シナリオ側（§6b-6 S4）で扱う。",
        "- アウトカムリスクは仮定値である。Phase 1b の実測が得られた時点で再計算すれば",
        "  必要数は変わりうるが、そのときには gold は既に集め終わっている必要がある。",
    ]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[-24:]))
    print(f"\nwrote={args.output}")


if __name__ == "__main__":
    main()
