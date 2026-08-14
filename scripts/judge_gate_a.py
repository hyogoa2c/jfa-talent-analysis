"""Judge Gate A on the independent holdout gold (SAP §6b-3).

The 2026-07-27 run judged Gate A on the development gold, where ten of twelve
validity cells were stuck at 9-13 verified rows, and §6b-3 itself says that only
more gold could move them. The 539-row holdout exists to answer those cells, and
this reads it.

The development goldsets are deliberately not consulted: §6b-2a puts those rows
in the development sample, and §11's audit trail excludes their 168 rows from
the denominator of any independence claim.

No outcome column is read. Gate A is a statement about the exposure measurement,
and keeping it that way is what lets H1b-2 stay blinded while this is settled.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

from jfa_talent_analysis.gate_a import (
    MAIN_PATHWAYS,
    SILENT_WRONG_GAP_TRIGGER_PP,
    VALIDITY_THRESHOLD,
    GoldPair,
    cell_state,
    confusion,
    per_pathway_validity,
    per_pathway_validity_weighted,
    silent_wrong,
    silent_wrong_gap_pp,
    silent_wrong_weighted,
    unverified_sensitivity,
    wilson_interval,
    wrong_needed_to_trigger,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--gold", type=Path, default=Path("data/manual/gold_holdout/gold_resolved.csv")
    )
    parser.add_argument(
        "--key", type=Path, default=Path("data/manual/gold_holdout_worksheet_key.csv")
    )
    parser.add_argument("--sample", type=Path, default=Path("data/manual/gold_holdout_sample.csv"))
    parser.add_argument(
        "--pooled",
        type=Path,
        default=Path("data/processed/pooled_player_outcomes_1999_2025.csv"),
    )
    parser.add_argument("--output", type=Path, default=Path("reports/generated/gate_a_holdout.md"))
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def build_pairs(args: argparse.Namespace) -> tuple[list[GoldPair], dict[str, int], list[str]]:
    """Gold rows joined to the pipeline label.

    Returns the verified pairs, the count of automatically-labelled rows per era
    that gold could *not* verify, and why each remaining row dropped out. The
    middle one is not bookkeeping: those rows are where an era difference could
    hide, and §6b-2b says to keep them as a category rather than as missing data.
    """
    key = {row["worksheet_id"]: row for row in read_csv(args.key)}
    weights = {row["source_player_id"]: row for row in read_csv(args.sample)}
    pooled = {row["source_player_id"]: row for row in read_csv(args.pooled)}

    pairs: list[GoldPair] = []
    unverified: Counter[str] = Counter()
    dropped: list[str] = []
    for row in read_csv(args.gold):
        worksheet_id = row["worksheet_id"]
        if row["determination"] != "confirmed":
            identity = key.get(worksheet_id)
            player = pooled.get(identity["source_player_id"]) if identity else None
            if (
                player
                and player["eligible_confirmatory"] == "1"
                and player["pathway_category"]
                and player["pathway_category_source"] != "human_reviewed"
            ):
                unverified[identity["era"]] += 1
            dropped.append(f"{worksheet_id}: gold 判定不能")
            continue
        if row["gold_pathway_category"] not in MAIN_PATHWAYS:
            dropped.append(
                f"{worksheet_id}: gold が主要3経路の外（{row['gold_pathway_category']}）"
            )
            continue
        identity = key.get(worksheet_id)
        if identity is None:
            dropped.append(f"{worksheet_id}: 対応表に無い")
            continue
        player = pooled.get(identity["source_player_id"])
        if player is None or player["eligible_confirmatory"] != "1":
            dropped.append(f"{worksheet_id}: 適格標本に無い")
            continue
        if not player["pathway_category"]:
            dropped.append(f"{worksheet_id}: パイプラインのラベルが空")
            continue
        drawn = weights.get(identity["source_player_id"])
        pairs.append(
            GoldPair(
                worksheet_id=worksheet_id,
                era=identity["era"],
                gold=row["gold_pathway_category"],
                label=player["pathway_category"],
                human_reviewed=player["pathway_category_source"] == "human_reviewed",
                weight=float(drawn["weight"]) if drawn and drawn["weight"] else 1.0,
            )
        )
    return pairs, dict(unverified), dropped


def confusion_section(pairs: list[GoldPair], eras: list[str]) -> list[str]:
    lines = ["## 1. era 別 3×3 混同行列（真の経路 → 観測経路）", ""]
    for era in eras:
        matrix = confusion(pairs, era)
        lines += [
            f"### {era}（n = {sum(1 for pair in pairs if pair.era == era)}）",
            "",
            "| gold \\ 観測 | " + " | ".join(MAIN_PATHWAYS) + " | 計 |",
            "|---|---|---|---|---|",
        ]
        for gold in MAIN_PATHWAYS:
            counts = [matrix.get((gold, label), 0) for label in MAIN_PATHWAYS]
            lines.append(
                f"| **{gold}** | " + " | ".join(str(c) for c in counts) + f" | {sum(counts)} |"
            )
        lines.append("")
    return lines


def validity_section(pairs: list[GoldPair], eras: list[str]) -> tuple[list[str], list[str]]:
    unweighted = per_pathway_validity(pairs)
    weighted = per_pathway_validity_weighted(pairs)
    failing: list[str] = []
    lines = [
        "## 2. 経路別の感度・PPV（Gate A 条件 3）",
        "",
        "判定は §6b-3 の事前指定どおり**非加重の Wilson 95% CI 下限**で行う。",
        "加重は §6b-2b の要請（抽出確率の逆数で母集団構成へ戻す）による参考値である。",
        "",
        "| era | 指標 | 経路 | 一致 / 検証数 | 率 | 95% CI (Wilson) | 加重率 | 判定 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for era in eras:
        for measure in ("感度", "PPV"):
            for pathway in MAIN_PATHWAYS:
                hits, total = unweighted[(era, measure, pathway)]
                whits, wtotal = weighted[(era, measure, pathway)]
                low, high = wilson_interval(hits, total)
                state = cell_state(hits, total)
                if state != "合格":
                    failing.append(f"{era}/{measure}/{pathway}（{state}）")
                rate = f"{hits / total:.0%}" if total else "—"
                wrate = f"{whits / wtotal:.0%}" if wtotal else "—"
                lines.append(
                    f"| {era} | {measure} | {pathway} | {hits} / {total} | {rate} "
                    f"| [{low:.0%}, {high:.0%}] | {wrate} | **{state}** |"
                )
    lines += [
        "",
        f"**合格しないセル: {len(failing)} / {len(eras) * 2 * len(MAIN_PATHWAYS)}**"
        + (f"（{', '.join(failing)}）" if failing else ""),
        "",
    ]
    return lines, failing


def silent_section(
    pairs: list[GoldPair], unverified: dict[str, int]
) -> tuple[list[str], float | None]:
    counts = silent_wrong(pairs)
    weighted = silent_wrong_weighted(pairs)
    gap = silent_wrong_gap_pp(counts)
    lines = [
        "## 3. silent-wrong（Gate A 条件 2）",
        "",
        "silent-wrong = 人手レビューを経ずに確定した最終ラベルが gold と食い違った件数。",
        "レビュー済みの行は誤っていても silent ではない。",
        "",
        "| era | silent-wrong / 自動確定の検証数 | 率 | 加重率 |",
        "|---|---|---|---|",
    ]
    for era, (wrong, total) in sorted(counts.items()):
        wwrong, wtotal = weighted[era]
        rate = f"{wrong / total:.1%}" if total else "—"
        wrate = f"{wwrong / wtotal:.1%}" if wtotal else "—"
        lines.append(f"| {era} | {wrong} / {total} | {rate} | {wrate} |")
    lines += [
        "",
        f"**era 間差 = {gap:.1f}pp**（閾値 {SILENT_WRONG_GAP_TRIGGER_PP:.0f}pp）"
        if gap is not None
        else "**era 間差 = 算出不能**",
        "",
        "### 3b. gold が検証できなかった行（この判定が置いている仮定）",
        "",
        "**この率は gold が到達できた行だけで計算されている。** gold の判定不能率は",
        "era 間で大きく違う（下表）。検証できない行こそ誤りが隠れうる場所なので、",
        "「検証済みと同じ率で誤る」という仮定がどれだけ効いているかを併記する。",
        "",
        "| era | 自動確定かつ gold 判定不能 | 検証できた自動確定 |",
        "|---|---|---|",
    ]
    for era in sorted(counts):
        lines.append(f"| {era} | {unverified.get(era, 0)} | {counts[era][1]} |")
    bounds = unverified_sensitivity(counts, unverified)
    lines += [
        "",
        "| 未検証行についての仮定 | era 間差 | 条件 2 |",
        "|---|---|---|",
    ]
    for label, value in bounds.items():
        fires = value > SILENT_WRONG_GAP_TRIGGER_PP
        lines.append(f"| {label} | {value:.1f}pp | {'**発火**' if fires else '非発火'} |")
    worst_era = max(unverified, key=lambda era: unverified[era]) if unverified else None
    tipping = wrong_needed_to_trigger(counts, unverified, worst_era) if worst_era else None
    if tipping is not None:
        share = tipping / unverified[worst_era]
        lines += [
            "",
            f"**転換点**: {worst_era} の未検証 {unverified[worst_era]} 件のうち "
            f"**{tipping} 件（{share:.0%}）以上**が誤っていれば条件 2 は発火する。"
            f"検証できた {worst_era} の silent-wrong 率は {counts[worst_era][0] / counts[worst_era][1]:.1%} である。",
        ]
    lines.append("")
    return lines, gap


def main() -> None:
    args = parse_args()
    pairs, unverified, dropped = build_pairs(args)
    eras = sorted({pair.era for pair in pairs})

    lines = [
        "# Gate A 判定（独立 holdout gold・SAP §6b-3）",
        "",
        f"gold = `{args.gold}`（{len(pairs)} 行が判定に入った）。",
        "**アウトカム列は一切読んでいない。**",
        "",
        "## 0. 判定に入らなかった行",
        "",
    ]
    reasons = Counter(reason.split(": ", 1)[1] for reason in dropped)
    for reason, count in reasons.most_common():
        lines.append(f"- {reason}: **{count} 件**")
    lines += ["", f"合計 {len(dropped)} 件が判定の分母から外れた。", ""]

    lines += confusion_section(pairs, eras)
    validity_lines, failing = validity_section(pairs, eras)
    lines += validity_lines
    silent_lines, gap = silent_section(pairs, unverified)
    lines += silent_lines

    condition2 = gap is not None and gap > SILENT_WRONG_GAP_TRIGGER_PP
    condition3 = bool(failing)
    lines += [
        "## 4. §6b-3 の条件",
        "",
        "| 条件 | 実測 | 判定 |",
        "|---|---|---|",
        "| 1. 経路確定率の era 間差 > 10pp | §6b-1 のファネル報告で −0.1pp | 非発火 |",
        f"| 2. silent-wrong 率差 > {SILENT_WRONG_GAP_TRIGGER_PP:.0f}pp "
        f"| {gap:.1f}pp | {'**発火**' if condition2 else '非発火'} |",
        f"| 3. 主要経路の感度・PPV（下限 {VALIDITY_THRESHOLD:.0%}） "
        f"| 合格しないセル {len(failing)} | {'**発火**' if condition3 else '非発火'} |",
        "| 4. レビュー未完了・未決着 | 裁定されていない不一致 0 件 | 非発火 |",
        "",
        f"> **Gate A = {'停止中' if condition2 or condition3 else '合格'}。**",
        "",
    ]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"pairs={len(pairs)} dropped={len(dropped)} -> {args.output}")
    print(f"  条件2 silent-wrong 差 = {gap:.1f}pp -> {'発火' if condition2 else '非発火'}")
    print(f"  条件3 合格しないセル = {len(failing)} -> {'発火' if condition3 else '非発火'}")
    print(f"  Gate A = {'停止中' if condition2 or condition3 else '合格'}")


if __name__ == "__main__":
    main()
