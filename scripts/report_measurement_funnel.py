from __future__ import annotations

import argparse
import csv
import hashlib
import math
import statistics
from collections import Counter
from pathlib import Path

# SAP §6b-3 requires a stated trigger, not a post-hoc read of the table.
CONFIRMATION_RATE_GAP_TRIGGER_PP = 10.0
SILENT_WRONG_GAP_TRIGGER_PP = 5.0
VALIDITY_THRESHOLD = 0.80

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
    Path("data/manual/pathway_review_queue_gate_a.csv"),
)
# Queues that exist but have not been adjudicated yet. Being listed in a queue
# is not the same as having been reviewed -- a blank reviewed_* column means
# "confirmed as-is" only once a human has actually been through the file.
PENDING_REVIEW_QUEUES: tuple[Path, ...] = ()


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
    pending_ids = {
        row["source_player_id"]
        for path in PENDING_REVIEW_QUEUES
        if path.exists()
        for row in read_csv(path)
    } - reviewed_ids

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
        sources = [eligible[pid]["pathway_category_source"] for pid in ids]
        metrics[era] = {
            # The composite rule's own vocabulary (SAP §1b-3). The prose
            # classifier's confidence is no longer the label's provenance: it is
            # one of two inputs, so reporting it here would describe a procedure
            # the analysis does not use.
            "両手順が一致（both_agree）": sources.count("both_agree"),
            "所属クラブ優先（club_list_over_prose）": sources.count("club_list_over_prose"),
            "所属クラブのみ（club_list_only）": sources.count("club_list_only"),
            "散文のみ（prose_only）": sources.count("prose_only"),
            "未決着（needs_review）": sources.count("needs_review"),
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
        "注: 主要経路の感度/PPV と silent-wrong は §8 で判定する（いずれも outcome 非結合）。"
        "バイアス分析での符号変化のみ Gate B（§6b-6）の対象。",
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

    lines += era_pathway_source_cells(eligible)
    lines += review_completion(eligible, labeled, reviewed_ids, pending_ids)
    lines += gold_confusion_matrices(eligible)
    lines += label_lock()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines), encoding="utf-8")
    print(f"eligible era1={base1} era2={base2}")
    print(f"経路確定率の era 間差: {confirm_gap:+.1f}pp -> trigger {'FIRED' if fired else 'not fired'}")
    print(f"wrote={args.output}")


MAIN_PATHWAYS = ("j_club_academy", "high_school", "university")
GOLD_SETS = (
    (Path("data/manual/goldsets/goldset_era1_gold_labels.csv"), "era1"),
    (Path("data/manual/goldsets/goldset_era2_gold_labels.csv"), "era2"),
)
# Minimum verified cases before a per-era/pathway validity claim is reportable.
# Below this the cell is "判定不能", not "合格" (external review Q2 §③ Gate A).
MIN_CELL_FOR_VALIDITY = 10


def era_pathway_source_cells(eligible: dict[str, dict[str, str]]) -> list[str]:
    """era x pathway x source counts (external review mandatory item 3).

    The interaction is estimated inside these cells, so a cell that is thin on
    one side of the era split is where a differential measurement problem would
    act. Reported without outcomes.
    """
    lines = [
        "## 6. era × 経路 × source のセル数（必須修正 3）",
        "",
        "| 経路 | source | era1 | era2 |",
        "|---|---|---|---|",
    ]
    counts = Counter(
        (row["era"], row["pathway_category"] or "(ラベルなし)", row["pathway_category_source"])
        for row in eligible.values()
    )
    keys = sorted({(pathway, source) for _, pathway, source in counts})
    for pathway, source in keys:
        n1, n2 = counts[("era1", pathway, source)], counts[("era2", pathway, source)]
        lines.append(f"| {pathway} | {source} | {n1} | {n2} |")
    lines += [
        "",
        "`human_reviewed` は era1 に厚い（主要 3 経路で era1 86 / era2 45）。Phase 1 の"
        "感度分析 5.2 が示すとおり、この層は**別の条件付き estimand** であり、era 間で"
        "その構成比が違うこと自体が差異的測定の経路になりうる（レビュー Q4）。",
        "",
    ]
    return lines


def review_completion(
    eligible: dict[str, dict[str, str]],
    labeled: dict[str, dict[str, str]],
    reviewed_ids: set[str],
    pending_ids: set[str],
) -> list[str]:
    """Are all needs_review rows actually adjudicated? Gate A stops if not."""
    lines = [
        "## 7. レビュー完了状況（Gate A の停止条件）",
        "",
        "| era | needs_review | レビュー済み | **未レビュー（キュー生成済み）** | キュー未生成 |",
        "|---|---|---|---|---|",
    ]
    pending_total = missing_total = 0
    for era in ("era1", "era2"):
        ids = [pid for pid, row in eligible.items() if row["era"] == era]
        needs = [
            pid for pid in ids if labeled.get(pid, {}).get("pathway_confidence") == "needs_review"
        ]
        done = sum(1 for pid in needs if pid in reviewed_ids)
        pending = sum(1 for pid in needs if pid in pending_ids)
        missing = len(needs) - done - pending
        pending_total += pending
        missing_total += missing
        lines.append(f"| {era} | {len(needs)} | {done} | {pending} | {missing} |")
    outstanding = pending_total + missing_total
    lines += [
        "",
        f"**判定: 未決着の needs_review = {outstanding} 件"
        f"（未レビュー {pending_total} / キュー未生成 {missing_total}）** → "
        + (
            "Gate A の「未解決レビュー」条件は満たされている（停止事由なし）。"
            if outstanding == 0
            else "**Gate A で停止**。`data/manual/pathway_review_queue_gate_a.csv` の"
            "人手レビューを完了させること。キューに載っているだけでは決着ではない"
            "（`reviewed_*` 空欄＝現ラベル確認済み、の意味は人が一度目を通して初めて成立する）。"
        ),
        "",
    ]
    return lines


def wilson_interval(hits: int, total: int) -> tuple[float, float]:
    if total == 0:
        return 0.0, 1.0
    z = 1.96
    denominator = 1 + z * z / total
    proportion = hits / total
    centre = (proportion + z * z / (2 * total)) / denominator
    half = z * math.sqrt(proportion * (1 - proportion) / total + z * z / (4 * total * total))
    half /= denominator
    return max(0.0, centre - half), min(1.0, centre + half)


def gold_confusion_matrices(eligible: dict[str, dict[str, str]]) -> list[str]:
    """Per-era gold-vs-label agreement (mandatory item 3).

    The gold sets are heavily stratified -- roughly 44% of each 50 sits in the
    deliberately over-sampled `unknown_label` / `no_confirmed_article` strata --
    so a raw agreement rate over all 50 is NOT an era accuracy estimate, and
    re-weighting needs sampling probabilities that are not yet fixed (review Q4
    §③). What is comparable across eras today is the `auto_high_conf` stratum,
    which is also 81-87% of the analysed population.
    """
    lines = [
        "## 8. gold 検証（era 別・必須修正 3）",
        "",
        "> **重要**: gold 各 50 名は `unknown_label` / `no_confirmed_article` を意図的に"
        "過剰抽出した層化標本である（各 era で 22/50 がこの 2 層）。**全 50 名を分母にした"
        "一致率は era の精度推定ではない。** 母集団への重み戻しには抽出確率の固定が必要で、"
        "これは v5 の課題（レビュー Q4 §③）。",
        "",
        "> **経路をプールした一致率は使わない**（外部レビュー `review_results_phase1b_sap_v3.md` "
        "停止理由 1）。§6b-3 が要求するのは**主要経路ごとの感度・PPV** であり、"
        "プール率では高頻度の `university` が支配して少数の academy 方向の誤りを覆い隠す。"
        "評価対象も所属クラブ導出単独ではなく、**最終的な複合ラベル**（SAP §1b-3）とする。",
        "",
        "### 8.1 最終複合ラベルの経路別妥当性（`determination=confirmed`・主要 3 経路）",
        "",
        "| era | 指標 | 経路 | 一致 / 検証数 | 率 | 95% CI (Wilson) | 判定 |",
        "|---|---|---|---|---|---|---|",
    ]
    per_pathway = per_pathway_validity(eligible)
    undetermined = []
    for era, _label in GOLD_SETS_ERAS:
        for measure in ("感度", "PPV"):
            for pathway in MAIN_PATHWAYS:
                hits, total = per_pathway[(era, measure, pathway)]
                low, high = wilson_interval(hits, total)
                rate = f"{hits / total:.0%}" if total else "—"
                if total < MIN_CELL_FOR_VALIDITY:
                    state = f"検証数 {total} 件で不足 → **判定不能**"
                    undetermined.append(f"{era}/{measure}/{pathway}")
                elif low < VALIDITY_THRESHOLD:
                    state = f"CI 下限 {low:.0%} < {VALIDITY_THRESHOLD:.0%} → **判定不能**"
                    undetermined.append(f"{era}/{measure}/{pathway}")
                else:
                    state = f"CI 下限 {low:.0%} → 合格"
                lines.append(
                    f"| {era} | {measure} | {pathway} | {hits} / {total} | {rate} "
                    f"| [{low:.0%}, {high:.0%}] | {state} |"
                )
    total_cells = len(GOLD_SETS_ERAS) * 2 * len(MAIN_PATHWAYS)
    lines += [
        "",
        f"**判定不能のセル: {len(undetermined)} / {total_cells}**"
        + (f"（{', '.join(undetermined)}）" if undetermined else ""),
        "",
        (
            "**Gate A の gold 妥当性条件は満たされていない。** §6b-3 が要求するのは"
            "「主要経路の感度・PPV」であって経路をプールした一致率ではない。"
            "セルあたり 9〜17 件では、一致率 100% でも Wilson 下限は 70〜74% にしかならず、"
            "下限 80% を超えるには 1 セルおおむね 16 件以上を要する。"
            "→ **Gate A は判定不能。追加 gold（v5・セル単位割付）まで合格にしない。**"
            if undetermined
            else "**全セルが合格。**"
        ),
        "",
        "### 8.1b silent-wrong（Gate A 内で算出・outcome 非結合）",
        "",
        "silent-wrong = 人手レビューを経ずに確定した最終ラベルが gold と食い違った件数。"
        "レビュー Q4 §③ の指摘どおり gold と予測ラベルだけで算出できるため、"
        "Gate B ではなく Gate A で完結させる。",
        "",
        "| era | silent-wrong / 自動確定の検証数 | 率 |",
        "|---|---|---|",
    ]
    silent = silent_wrong(eligible)
    rates = {}
    for era, _label in GOLD_SETS_ERAS:
        wrong, total = silent[era]
        rates[era] = pct(wrong, total)
        rate = f"{rates[era]:.1f}%" if total else "—"
        lines.append(f"| {era} | {wrong} / {total} | {rate} |")
    gap = rates["era1"] - rates["era2"]
    fired = abs(gap) > SILENT_WRONG_GAP_TRIGGER_PP
    lines += [
        "",
        f"**§6b-3 トリガー（era 別 silent-wrong 率差 >{SILENT_WRONG_GAP_TRIGGER_PP:.0f}pp）**: "
        f"実測差 {gap:+.1f}pp → **{'発火' if fired else '非発火'}**。"
        "ただし分母が小さく、この判定自体も追加 gold で作り直す必要がある。",
        "",
        "### 8.2 混同行列（参考・層化標本のため率は算出しない）",
        "",
    ]
    for path, era in GOLD_SETS:
        gold_rows = read_csv(path)
        if not gold_rows:
            continue
        matrix: Counter = Counter()
        outside = 0
        for row in gold_rows:
            player = eligible.get(row["source_player_id"])
            if player is None:
                outside += 1
                continue
            matrix[(row["gold_pathway_category"], player["pathway_category"] or "(ラベルなし)")] += 1
        observed = sorted({obs for _, obs in matrix})
        lines += [
            f"**{era}**（gold {len(gold_rows)} 名、うち適格標本内 {len(gold_rows) - outside} 名）",
            "",
            "| gold \\ 現ラベル | " + " | ".join(observed) + " | 計 |",
            "|" + "---|" * (len(observed) + 2),
        ]
        for truth in MAIN_PATHWAYS:
            row_counts = [matrix[(truth, obs)] for obs in observed]
            lines.append(
                f"| {truth} | " + " | ".join(str(c) for c in row_counts) + f" | {sum(row_counts)} |"
            )
        lines.append("")
    lines += [
        "`(ラベルなし)` 列は**誤分類ではなく未分類**（identity 未確認等）である。両者を合算した"
        "率は「分類器の正確さ」でも「捕捉率」でもない量になるため、本節では率を出さない。",
        "",
    ]
    return lines


GOLD_SETS_ERAS = (("era1", "era1"), ("era2", "era2"))


def gold_rows_with_labels(
    eligible: dict[str, dict[str, str]],
) -> dict[str, list[tuple[str, dict[str, str]]]]:
    """Gold rows paired with the final composite label, per era.

    Restricted to confirmed determinations and the three main pathways, since
    those are the cells §6b-3 states a condition about.
    """
    paired: dict[str, list[tuple[str, dict[str, str]]]] = {"era1": [], "era2": []}
    for path, era in GOLD_SETS:
        for row in read_csv(path):
            if row["determination"] != "confirmed":
                continue
            if row["gold_pathway_category"] not in MAIN_PATHWAYS:
                continue
            player = eligible.get(row["source_player_id"])
            if player is None or not player["pathway_category"]:
                continue
            paired[era].append((player["pathway_category"], row))
    return paired


def per_pathway_validity(
    eligible: dict[str, dict[str, str]],
) -> dict[tuple[str, str, str], tuple[int, int]]:
    """Sensitivity and PPV of the final label, per era and pathway.

    Sensitivity conditions on the gold pathway, PPV on the assigned label. They
    answer different failure modes -- missing a true academy player versus
    calling someone an academy player who is not -- and the reference category
    makes the second one the one that moves the baseline risk.
    """
    result: dict[tuple[str, str, str], tuple[int, int]] = {}
    paired = gold_rows_with_labels(eligible)
    for era, rows in paired.items():
        for pathway in MAIN_PATHWAYS:
            truth = [(label, row) for label, row in rows if row["gold_pathway_category"] == pathway]
            assigned = [(label, row) for label, row in rows if label == pathway]
            result[(era, "感度", pathway)] = (
                sum(1 for label, _ in truth if label == pathway),
                len(truth),
            )
            result[(era, "PPV", pathway)] = (
                sum(1 for _, row in assigned if row["gold_pathway_category"] == pathway),
                len(assigned),
            )
    return result


def silent_wrong(eligible: dict[str, dict[str, str]]) -> dict[str, tuple[int, int]]:
    """Labels that were wrong without ever being flagged for a human.

    A row a reviewer adjudicated is not silent even if it is wrong: the failure
    mode this measures is the pipeline being confidently mistaken, which is what
    an era difference in it would bias.
    """
    result: dict[str, tuple[int, int]] = {}
    for era, rows in gold_rows_with_labels(eligible).items():
        auto = [
            (label, row)
            for label, row in rows
            if eligible[row["source_player_id"]]["pathway_category_source"] != "human_reviewed"
        ]
        wrong = sum(1 for label, row in auto if label != row["gold_pathway_category"])
        result[era] = (wrong, len(auto))
    return result


def label_lock() -> list[str]:
    """Hash every label input so the analysed version is identifiable later."""
    lines = [
        "## 9. ラベル版のロック（必須修正 3）",
        "",
        "本レポートが参照した曝露ラベル入力の SHA-256（先頭 12 桁）。"
        "以降の解析はこの版に対して行う。",
        "",
        "| ファイル | sha256[:12] | bytes |",
        "|---|---|---|",
    ]
    paths = [
        directory / f"{pattern.format(key=key)}_labeled.csv"
        for directory, pattern, keys in TIER_SOURCES
        for key in keys
    ] + list(PATHWAY_QUEUES)
    for path in paths:
        if not path.exists():
            continue
        data = path.read_bytes()
        lines.append(f"| `{path}` | `{hashlib.sha256(data).hexdigest()[:12]}` | {len(data)} |")
    lines.append("")
    return lines


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
