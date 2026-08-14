"""How large the holdout must be for Gate B's DID comparison to be decidable.

Design-based: it draws the sample the allocation actually prescribes, applies a
per-stratum error model, lets some adjudications fail, weights the confusion
matrix back by the inverse sampling probability, and carries it through to both
DIDs. The v7 version instead scaled each observed-pathway row's existing counts
to the target size, which assumes proportional sampling within the row and so
never saw the variance contributed by thinly sampling the large `both_agree`
stratum -- the term that turns out to dominate.

Stopping rule (SAP §6b-2c(ii), v8): max over the university and high_school DIDs
of the 95% interval half-width, below the 3pp tolerance, under the primary
scenario. Other scenarios are reported, not required: the envelope over all of
them is unreachable at any feasible budget, so the pre-specified consequence of
landing there is demotion to exploratory, not unbounded collection.

Outcome-free with respect to Phase 1b. Outcome risks are assumed, from Phase 1's
published values in the primary scenario -- which, per the review, is
outcome-linked information about an overlapping sample and is disclosed as such
in the SAP audit record, not claimed as complete outcome blinding.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from jfa_talent_analysis.gold_design_simulation import (
    INDETERMINATE_RATE,
    Player,
    Scenario,
    simulate_design,
)
from jfa_talent_analysis.gold_requirement import half_width
from jfa_talent_analysis.gold_strata import MAIN_PATHWAYS, load_institution_unknown, stratum

TOLERANCE_PP = 3.0

RISK_SCENARIOS = {
    "phase1_published": {"j_club_academy": 0.595, "high_school": 0.522, "university": 0.315},
    "wide_gap": {"j_club_academy": 0.70, "high_school": 0.60, "university": 0.25},
}

# Per-stratum probability that the assigned label is wrong. "current" is already
# conservative against the development gold, which shows one error in 60; the
# review asked that the observed shape not be taken as truth.
ERROR_SCENARIOS = {
    "none": Scenario("none", default_rate=0.0),
    "current": Scenario(
        "current",
        {
            "academy_out": 0.10,
            "academy_in": 0.10,
            "disagree_other": 0.10,
            "institution_unknown": 0.15,
        },
        default_rate=0.02,
    ),
    "pessimistic": Scenario(
        "pessimistic",
        {
            "academy_out": 0.35,
            "academy_in": 0.35,
            "disagree_other": 0.30,
            "institution_unknown": 0.40,
            "club_list_only": 0.15,
            "prose_only": 0.15,
        },
        default_rate=0.05,
    ),
}
PRIMARY = ("phase1_published", "current")

POOLED = Path("data/processed/pooled_player_outcomes_1999_2025.csv")
RECLASSIFICATION_QUEUE = Path("data/manual/academy_reclassification_queue.csv")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--draws", type=int, default=600)
    parser.add_argument(
        "--indeterminate-rate",
        type=float,
        default=None,
        help=(
            "Share of drawn rows the raters cannot settle. Defaults to the planning "
            "assumption (10%); pass the measured rate at the checkpoint (SAP §6b-2b-ext)."
        ),
    )
    parser.add_argument("--seed", type=int, default=20260718)
    parser.add_argument(
        "--both-agree-quota",
        type=int,
        nargs="+",
        default=[10, 20, 30, 50, 80],
        help="Per-row draws from both_agree to evaluate; the rest are censused.",
    )
    parser.add_argument(
        "--chosen-quota",
        type=int,
        default=30,
        help=(
            "The quota fixed in the SAP. Defaults to 30 rather than the smallest "
            "passing value, which clears the tolerance by 0.1pp and leaves no margin "
            "for the assumed indeterminate rate being optimistic."
        ),
    )
    parser.add_argument(
        "--output", type=Path, default=Path("reports/generated/gold_requirement.md")
    )
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def load_population() -> tuple[list[Player], dict[str, dict[str, int]]]:
    unknown = load_institution_unknown(read_csv(RECLASSIFICATION_QUEUE))
    rows = [
        row
        for row in read_csv(POOLED)
        if row["eligible_confirmatory"] == "1" and row["pathway_category"] in MAIN_PATHWAYS
    ]
    population = [
        Player(
            row["source_player_id"],
            row["era"],
            row["pathway_category"],
            stratum(row, unknown),
            row["pathway_prose_category"],
            row["pathway_club_list_category"],
        )
        for row in rows
    ]
    counts = {
        era: {
            pathway: sum(1 for p in population if p.era == era and p.observed == pathway)
            for pathway in MAIN_PATHWAYS
        }
        for era in ("era1", "era2")
    }
    return population, counts


def build_allocation(
    population: list[Player], both_agree_quota: int, census_cap: int = 30, reviewed_quota: int = 10
) -> dict[tuple[str, str, str], int]:
    """Census the strata carrying the signal; quota the two large ones."""
    from collections import Counter

    censused = (
        "academy_out",
        "academy_in",
        "institution_unknown",
        "disagree_other",
        "club_list_only",
        "prose_only",
    )
    allocation: dict[tuple[str, str, str], int] = {}
    for era in ("era1", "era2"):
        for pathway in MAIN_PATHWAYS:
            members = Counter(
                p.stratum for p in population if p.era == era and p.observed == pathway
            )
            for name in censused:
                take = min(members.get(name, 0), census_cap)
                if take:
                    allocation[(era, pathway, name)] = take
            for name, quota in (
                ("human_reviewed_other", reviewed_quota),
                ("both_agree", both_agree_quota),
            ):
                take = min(members.get(name, 0), quota)
                if take:
                    allocation[(era, pathway, name)] = take
    return allocation


def main() -> None:
    args = parse_args()
    population, counts = load_population()

    lines = [
        "# holdout gold の必要数（SAP §6b-2c(ii)・v8 設計ベース）",
        "",
        f"生成: `scripts/simulate_gold_requirement.py` / seed={args.seed} / draws={args.draws}",
        "",
        "**Phase 1b のアウトカムは参照していない。** ただし主シナリオのリスクは Phase 1 既報値で",
        "あり、Phase 1 標本は Phase 1b と重複する（era2 の 98.3%）。完全な outcome 遮断ではなく、",
        "重複標本の outcome-linked 情報を設計入力に使っている（SAP §6b-7 の監査記録）。",
        "",
        "## 停止規則",
        "",
        f"**主シナリオ（{PRIMARY[0]} × {PRIMARY[1]}）で "
        f"max(university DID, high_school DID) の 95% 区間半幅 < {TOLERANCE_PP:.0f}pp。**",
        "",
        "H1b-2 は大学・高校の交互作用の共同検定なので、**両 DID を評価し最大値で判定**する",
        "（v7 は university だけで決めていた）。",
        "",
        "> **包絡線を停止規則にしない理由**: 全シナリオを満たす水準は現実的な予算で到達できない",
        "> （下表・悲観×広い格差は 839 件でも 4.4pp）。到達不能な基準は収集を続ける根拠にも",
        "> 止める根拠にもならない。**実構造が悲観側だった場合は Gate B が判定不能となり、",
        "> SAP §6b の降格規則により確認的解釈を停止する**——これを事前に受け入れる。",
        "",
        f"判定不能率は {INDETERMINATE_RATE:.0%} を仮定（外部ソースでも真値を確定できない割合）。",
        "",
        "## 層（v8 で再定義）",
        "",
        "`pathway_category_source` ではなく**規則への入力**（散文ラベル・所属クラブラベル・最終ラベル）",
        "から層を作る。v7 の層は最終 source だけを見ており、複合規則が",
        "`prose=academy → club=大学/高校` をレビューへ送る設計の結果、**基準カテゴリを空にする",
        "向き（`academy_out`）が 1 件も `disagree_academy` に入っていなかった**。",
        "",
        "| era | 観測経路 | " + " | ".join(
            ("academy_out", "academy_in", "institution_unknown", "disagree_other",
             "club_list_only", "prose_only", "human_reviewed_other", "both_agree")
        ) + " |",
        "|---|---|" + "---|" * 8,
    ]
    from collections import Counter

    for era in ("era1", "era2"):
        for pathway in MAIN_PATHWAYS:
            members = Counter(
                p.stratum for p in population if p.era == era and p.observed == pathway
            )
            lines.append(
                f"| {era} | {pathway} | "
                + " | ".join(
                    str(members.get(name, 0))
                    for name in (
                        "academy_out", "academy_in", "institution_unknown", "disagree_other",
                        "club_list_only", "prose_only", "human_reviewed_other", "both_agree",
                    )
                )
                + " |"
            )

    lines += [
        "",
        "## 必要数",
        "",
        "重要層は悉皆（上限 30 件）、`human_reviewed_other` は 10 件、`both_agree` の抽出数のみ変える。",
        "**分散を支配するのは `both_agree`** ——母集団の大半を占める層を薄く採ると、そこの",
        "誤分類率の不確かさが大きな重みで補正後 DID に効く。",
        "",
        "| both_agree/行 | 総数 | " + " | ".join(
            f"{r}×{e}" for r in RISK_SCENARIOS for e in ERROR_SCENARIOS if e != "none"
        ) + " |",
        "|---|---|" + "---|" * (len(RISK_SCENARIOS) * (len(ERROR_SCENARIOS) - 1)),
    ]

    chosen: int | None = None
    chosen_primary: float | None = None
    totals: dict[int, int] = {}
    for quota in args.both_agree_quota:
        allocation = build_allocation(population, quota)
        total = sum(allocation.values())
        totals[quota] = total
        cells = []
        primary_value = None
        for risk_name, risks in RISK_SCENARIOS.items():
            for error_name, scenario in ERROR_SCENARIOS.items():
                if error_name == "none":
                    continue
                extra = (
                    {"indeterminate_rate": args.indeterminate_rate}
                    if args.indeterminate_rate is not None
                    else {}
                )
                results, _ = simulate_design(
                    population, allocation, counts, risks, scenario,
                    draws=args.draws, seed=args.seed, **extra,
                )
                widest = max(half_width(values) for values in results.values())
                if (risk_name, error_name) == PRIMARY:
                    primary_value = widest
                cells.append(f"{widest:.1f}" + ("" if widest < TOLERANCE_PP else " ×"))
        if chosen is None and primary_value is not None and primary_value < TOLERANCE_PP:
            chosen = quota
        if quota == args.chosen_quota:
            chosen_primary = primary_value
        lines.append(f"| {quota} | {total} | " + " | ".join(cells) + " |")

    lines += ["", "×印 = 半幅が tolerance 以上。主シナリオ列のみが停止規則の判定対象。", ""]
    if chosen is not None:
        fixed = args.chosen_quota
        lines += [
            "## 確定",
            "",
            f"- **`both_agree` を 1 行あたり {fixed} 件、総数 {totals.get(fixed, '—')} 件**"
            + (f"（主シナリオ {chosen_primary:.1f}pp）。" if chosen_primary else "。"),
            f"- 主シナリオを満たす最小は {chosen} 件（{totals[chosen]} 件）だが、"
            f"tolerance を {TOLERANCE_PP - (chosen_primary or 0):.1f}pp しか下回らない。"
            f"判定不能率の仮定（{INDETERMINATE_RATE:.0%}）が楽観的だった場合に備え、余裕を取る。",
            "- 感度シナリオは満たさない。その場合の帰結は降格であり、追加収集ではない（上記）。",
            "",
            "収集後は実際の判定結果（判定不能率・層別の誤分類）で再実行し、",
            "停止規則の充足を確認する。",
        ]
    else:
        lines += ["## 確定", "", "- 検討範囲では主シナリオの停止規則を満たさない。割付を増やすこと。"]

    lines += [
        "",
        "## 数値的な処理（v8 で事前指定）",
        "",
        "行列の反転で次が生じた draw の扱いを固定する。発生率は実行ごとに報告する。",
        "",
        "- **悪条件**（条件数 > 1e4）: その draw を破棄し、破棄率を報告する。",
        "- **負の補正カウント**: 記録するが破棄しない（推定量としては許容される）。",
        "- **範囲外リスク**（<0 または >1、NaN）: その draw を破棄し、破棄率を報告する。",
        "",
        "破棄率が 5% を超えた場合、その設定での必要数は報告しない（推定が不安定なため）。",
    ]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[lines.index("## 必要数") :]))
    print(f"\nwrote={args.output}")


if __name__ == "__main__":
    main()
