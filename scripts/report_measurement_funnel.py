from __future__ import annotations

import argparse
import csv
import statistics
from collections import Counter
from pathlib import Path

# SAP §6b-3 requires a stated trigger, not a post-hoc read of the table.
CONFIRMATION_RATE_GAP_TRIGGER_PP = 10.0

TIER_SOURCES = (
    (Path("data/interim/pathway_national_team"), "pathway_tier_{key}", ("a", "b", "c")),
    (Path("data/interim/pre2014"), "priority{key}_pathway", ("1", "2")),
)
PATHWAY_QUEUES = (
    Path("data/manual/pathway_review_queue.csv"),
    Path("data/manual/phase1_pathway_youth_vs_university_review_queue.csv"),
    Path("data/manual/pre2014_pathway_review_queue.csv"),
    Path("data/manual/pre2014_pathway_review_queue_p2.csv"),
    Path("data/manual/pre2014_pathway_review_queue_supplement.csv"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Report the per-era exposure measurement funnel (Phase 1b SAP §6b-1): "
            "eligible -> Wikipedia candidate -> identity confirmed -> pathway text -> "
            "auto high-confidence / needs review -> resolved -> unknown, plus article "
            "length and label distributions. Outcomes are never joined, so this "
            "consumes none of H1b-2's confirmatory status."
        )
    )
    parser.add_argument(
        "--pooled",
        type=Path,
        default=Path("data/processed/pooled_player_outcomes_1999_2025.csv"),
    )
    parser.add_argument(
        "--output", type=Path, default=Path("reports/generated/measurement_funnel_by_era.md")
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    pooled = {row["source_player_id"]: row for row in read_csv(args.pooled)}
    eligible = {
        pid: row for pid, row in pooled.items() if row["eligible_confirmatory"] == "1"
    }

    verified = {}
    labeled = {}
    for directory, pattern, keys in TIER_SOURCES:
        for key in keys:
            for row in read_csv(directory / f"{pattern.format(key=key)}_verified.csv"):
                verified[row["source_player_id"]] = row
            for row in read_csv(directory / f"{pattern.format(key=key)}_labeled.csv"):
                labeled[row["source_player_id"]] = row

    reviewed_ids = {
        row["source_player_id"]
        for path in PATHWAY_QUEUES
        if path.exists()
        for row in read_csv(path)
    }

    lines = [
        "# 曝露測定ファネル（era 別・SAP §6b-1）",
        "",
        f"生成: `scripts/report_measurement_funnel.py` / 入力 `{args.pooled}`",
        "",
        "**アウトカムを一切結合していない**ため、本レポートは H1b-2 の確認的地位を消費しない",
        "（`docs/review_request_phase1_corrigendum.md` Q6 の回答待ちの間に実行可能な範囲）。",
        "",
    ]

    # Ordered by actual dependency: a player needs an article, then usable
    # pathway text, then a birth-date identity match, before the classifier
    # will assign a label. (Context presence is not conditional on identity,
    # so listing identity first would make the table look non-monotone.)
    stages = ["適格", "Wikipedia 候補あり", "経路テキストあり", "identity 確認", "分類器がラベル付与"]
    counts: dict[str, dict[str, int]] = {}
    for era in ("era1", "era2"):
        ids = [pid for pid, row in eligible.items() if row["era"] == era]
        counts[era] = {
            "適格": len(ids),
            "Wikipedia 候補あり": sum(1 for pid in ids if verified.get(pid, {}).get("wikipedia_title")),
            "identity 確認": sum(
                1 for pid in ids if verified.get(pid, {}).get("identity_check") == "confirmed"
            ),
            "経路テキストあり": sum(
                1 for pid in ids if verified.get(pid, {}).get("wikipedia_pathway_context")
            ),
            "分類器がラベル付与": sum(1 for pid in ids if labeled.get(pid, {}).get("pathway_category")),
        }

    lines += ["## 1. 測定ファネル", "", "| 段階 | era1 | era2 | 差 (pp) |", "|---|---|---|---|"]
    base1, base2 = counts["era1"]["適格"], counts["era2"]["適格"]
    for stage in stages:
        n1, n2 = counts["era1"][stage], counts["era2"][stage]
        gap = pct(n1, base1) - pct(n2, base2)
        lines.append(
            f"| {stage} | {n1} ({pct(n1, base1):.1f}%) | {n2} ({pct(n2, base2):.1f}%) | {gap:+.1f} |"
        )
    lines.append("")

    lines += ["## 2. 確信度・レビュー・確定率", "", "| 指標 | era1 | era2 | 差 (pp) |", "|---|---|---|---|"]
    metrics: dict[str, dict[str, int]] = {}
    for era in ("era1", "era2"):
        ids = [pid for pid, row in eligible.items() if row["era"] == era]
        metrics[era] = {
            "auto high-confidence": sum(
                1 for pid in ids if labeled.get(pid, {}).get("pathway_confidence") == "high"
            ),
            "needs review": sum(
                1 for pid in ids if labeled.get(pid, {}).get("pathway_confidence") == "needs_review"
            ),
            "人手レビュー済み": sum(1 for pid in ids if pid in reviewed_ids),
            "経路確定（unknown 除く）": sum(
                1
                for pid in ids
                if eligible[pid]["pathway_category"]
                and eligible[pid]["pathway_category"] != "unknown"
            ),
            "unknown": sum(1 for pid in ids if eligible[pid]["pathway_category"] == "unknown"),
            "ラベルなし": sum(1 for pid in ids if not eligible[pid]["pathway_category"]),
        }
    for metric in metrics["era1"]:
        n1, n2 = metrics["era1"][metric], metrics["era2"][metric]
        gap = pct(n1, base1) - pct(n2, base2)
        lines.append(
            f"| {metric} | {n1} ({pct(n1, base1):.1f}%) | {n2} ({pct(n2, base2):.1f}%) | {gap:+.1f} |"
        )
    lines.append("")

    confirm_gap = pct(metrics["era1"]["経路確定（unknown 除く）"], base1) - pct(
        metrics["era2"]["経路確定（unknown 除く）"], base2
    )
    fired = abs(confirm_gap) > CONFIRMATION_RATE_GAP_TRIGGER_PP
    lines += [
        f"**§6b-3 トリガー判定（経路確定率の era 間差 >{CONFIRMATION_RATE_GAP_TRIGGER_PP:.0f}pp）**: "
        f"実測差 {confirm_gap:+.1f}pp → **{'発火（確認的解釈を停止し要検討）' if fired else '非発火'}**。",
        "",
        "注: §6b-3 の残りのトリガー（era 別 silent-wrong 率差・主要経路の感度/PPV・"
        "バイアス分析での符号変化）は gold セットと推定を要するため本レポートの対象外。",
        "",
    ]

    lines += ["## 3. 記事の厚さ（経路テキスト長）", "", "| era | n | 中央値 | 平均 | 25% | 75% |", "|---|---|---|---|---|---|"]
    for era in ("era1", "era2"):
        lengths = sorted(
            len(verified.get(pid, {}).get("wikipedia_pathway_context", ""))
            for pid, row in eligible.items()
            if row["era"] == era and verified.get(pid, {}).get("wikipedia_pathway_context")
        )
        if not lengths:
            continue
        lines.append(
            f"| {era} | {len(lengths)} | {statistics.median(lengths):.0f} | "
            f"{statistics.mean(lengths):.0f} | {quantile(lengths, 0.25):.0f} | "
            f"{quantile(lengths, 0.75):.0f} |"
        )
    lines.append("")

    lines += ["## 4. 経路構成（H1b-1・記述目的）", "", "| 経路 | era1 | era2 |", "|---|---|---|"]
    dist = {
        era: Counter(
            row["pathway_category"] or "(ラベルなし)"
            for row in eligible.values()
            if row["era"] == era
        )
        for era in ("era1", "era2")
    }
    for category in sorted(set(dist["era1"]) | set(dist["era2"])):
        n1, n2 = dist["era1"][category], dist["era2"][category]
        lines.append(
            f"| {category} | {n1} ({pct(n1, base1):.1f}%) | {n2} ({pct(n2, base2):.1f}%) |"
        )
    lines += [
        "",
        "H1b-1 は SAP §2 で記述目的に降格済み。「アカデミー整備による構成変化」という機序解釈はしない。",
        "",
        "## 5. バックフィルの寄与",
        "",
        "| era | 適格 | うち 2014 年以降に出場なし（＝バックフィルでのみ可視） |",
        "|---|---|---|",
    ]
    for era in ("era1", "era2"):
        ids = [pid for pid, row in eligible.items() if row["era"] == era]
        backfill = sum(1 for pid in ids if eligible[pid]["observed_2014_plus"] == "0")
        lines.append(f"| {era} | {len(ids)} | {backfill} ({pct(backfill, len(ids)):.1f}%) |")
    lines += [
        "",
        "era1 の適格標本は 2014-2025 単独ユニバースの 676 名から大きく増える。増分は"
        "**2014 年まで現役でなかった選手**であり、Phase 1 の era1 部分標本にあった"
        "生存者条件付けを外すのがバックフィルの主目的である。",
        "",
    ]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines), encoding="utf-8")
    print(f"eligible era1={base1} era2={base2}")
    print(f"経路確定率の era 間差: {confirm_gap:+.1f}pp -> trigger {'FIRED' if fired else 'not fired'}")
    print(f"wrote={args.output}")


def pct(numerator: int, denominator: int) -> float:
    return 100.0 * numerator / denominator if denominator else 0.0


def quantile(sorted_values: list[int], q: float) -> float:
    if not sorted_values:
        return 0.0
    index = min(int(q * len(sorted_values)), len(sorted_values) - 1)
    return float(sorted_values[index])


def read_csv(path: Path) -> list[dict[str, str]]:
    csv.field_size_limit(10_000_000)
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


if __name__ == "__main__":
    main()
