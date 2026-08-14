"""Draw and freeze the holdout sample (SAP §6b-2b, v8; extension rule §6b-2b-ext, v9).

Writes the actual player ids, not just per-stratum counts. The review required
the target list, the seed, the within-stratum order, the replacement rule and
the treatment of indeterminate adjudications to be fixed and hashed *before* any
gold is looked at, so that the sample cannot drift toward convenient cases once
verification starts.

Strata come from `gold_strata.py`, which reads the inputs to the composite rule
rather than its output source -- the v7 strata missed every row in the direction
that empties the reference category.

`--both-agree-quota` exists for the extension rule alone. The within-stratum
permutation does not depend on the quota, so re-running at a higher quota
reproduces the frozen targets and promotes the reserves in draw order rather
than drawing a different sample (`tests/test_gold_allocation.py`).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
from collections import Counter
from pathlib import Path

import numpy as np

from jfa_talent_analysis.gold_strata import MAIN_PATHWAYS, load_institution_unknown, stratum

CENSUSED = (
    "academy_out",
    "academy_in",
    "institution_unknown",
    "disagree_other",
    "club_list_only",
    "prose_only",
)
CENSUS_CAP = 30
REVIEWED_QUOTA = 10
BOTH_AGREE_QUOTA = 30  # SAP §6b-2c(ii): 539 total, primary scenario 2.4pp
EXTENSION_CAP = 80  # SAP §6b-2b-ext: 839 total, the first level clearing 3pp when pessimistic

COLUMNS = [
    "draw_order",
    "source_player_id",
    "era",
    "observed_pathway",
    "stratum",
    "population_size",
    "sampled",
    "sampling_probability",
    "weight",
    "role",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pooled", type=Path, default=Path("data/processed/pooled_player_outcomes_1999_2025.csv")
    )
    parser.add_argument(
        "--reclassification-queue",
        type=Path,
        default=Path("data/manual/academy_reclassification_queue.csv"),
    )
    parser.add_argument("--seed", type=int, default=20260718)
    parser.add_argument(
        "--reserve",
        type=int,
        default=10,
        help="Reserves drawn per stratum, used in fixed order when a target is unusable.",
    )
    parser.add_argument(
        "--both-agree-quota",
        type=int,
        default=BOTH_AGREE_QUOTA,
        help=(
            "Per-row draws from both_agree. Only the extension rule (SAP §6b-2b-ext) "
            "may raise this, and only to 80. Raising it keeps the frozen targets: the "
            "within-stratum permutation does not depend on the quota, so the extra "
            "draws are the reserves in draw order and then the rest of the same order."
        ),
    )
    parser.add_argument("--sample", type=Path, default=Path("data/manual/gold_holdout_sample.csv"))
    parser.add_argument("--output", type=Path, default=Path("reports/generated/gold_allocation.md"))
    args = parser.parse_args()
    if args.both_agree_quota > EXTENSION_CAP:
        parser.error(
            f"--both-agree-quota {args.both_agree_quota} exceeds the cap of {EXTENSION_CAP} "
            "fixed in SAP §6b-2b-ext. Beyond the cap the rule is to stop collecting and "
            "let Gate B fall to indeterminate, not to draw more."
        )
    return args


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def quota_for(name: str, population: int, both_agree_quota: int = BOTH_AGREE_QUOTA) -> int:
    if name in CENSUSED:
        return min(population, CENSUS_CAP)
    if name == "human_reviewed_other":
        return min(population, REVIEWED_QUOTA)
    if name == "both_agree":
        return min(population, both_agree_quota)
    return 0


def main() -> None:
    args = parse_args()
    unknown = load_institution_unknown(read_csv(args.reclassification_queue))
    rows = [
        row
        for row in read_csv(args.pooled)
        if row["eligible_confirmatory"] == "1" and row["pathway_category"] in MAIN_PATHWAYS
    ]

    groups: dict[tuple[str, str, str], list[str]] = {}
    for row in rows:
        key = (row["era"], row["pathway_category"], stratum(row, unknown))
        groups.setdefault(key, []).append(row["source_player_id"])

    rng = np.random.default_rng(args.seed)
    sample_rows: list[dict[str, str]] = []
    order = 0
    for key in sorted(groups):
        era, pathway, name = key
        # Sort before shuffling so the draw depends only on the seed, not on the
        # order rows happened to arrive in the input file.
        members = sorted(groups[key], key=int)
        take = quota_for(name, len(members), args.both_agree_quota)
        if take == 0:
            continue
        permutation = rng.permutation(len(members))
        probability = take / len(members)
        for rank, index in enumerate(permutation):
            if rank >= take + args.reserve:
                break
            role = "target" if rank < take else "reserve"
            order += 1
            sample_rows.append(
                {
                    "draw_order": str(order),
                    "source_player_id": members[index],
                    "era": era,
                    "observed_pathway": pathway,
                    "stratum": name,
                    "population_size": str(len(members)),
                    "sampled": str(take),
                    "sampling_probability": f"{probability:.6f}",
                    "weight": f"{1 / probability:.6f}",
                    "role": role,
                }
            )

    with args.sample.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(sample_rows)
    digest = hashlib.sha256(args.sample.read_bytes()).hexdigest()

    targets = [r for r in sample_rows if r["role"] == "target"]
    reserves = [r for r in sample_rows if r["role"] == "reserve"]

    lines = [
        "# holdout gold の抽出（SAP §6b-2b・v8）",
        "",
        f"生成: `scripts/build_gold_allocation.py` / seed={args.seed}",
        f"抽出リスト: `{args.sample}`",
        f"SHA-256: `{digest}`",
        "",
        f"**対象 {len(targets)} 件 / 予備 {len(reserves)} 件。**",
        "",
        "**アウトカムも gold 判定結果も見ずに確定した。** 以降この抽出を変更しない。",
        "",
        "## 抽出規則（事前固定）",
        "",
        f"- 層 = era × 観測経路 × 層（`gold_strata.py`）。重要層は上限 {CENSUS_CAP} 件まで悉皆、",
        f"  `human_reviewed_other` は {REVIEWED_QUOTA} 件、`both_agree` は {args.both_agree_quota} 件。",
        f"- 層内は seed={args.seed} の置換で順序を決め、先頭から対象、続く {args.reserve} 件を予備とする。",
        "- **代替規則**: 対象が検証不能（記事なし・同名別人等で外部ソースに到達できない）と判明した",
        "  場合のみ、同一層の予備を `draw_order` 順に繰り上げる。**都合のよい対象を選ばない。**",
        "- **判定不能の扱い**: 外部ソースに到達できたが真値を確定できない場合は、繰り上げず",
        "  `indeterminate` として保存する（欠測として捨てない）。層別の判定不能率を報告する。",
        "- 二者独立判定。不一致は合議し、初回判定・最終判定・根拠 URL・判定者を保存する。",
        "- **outcome・両分類器の出力・最終採用ラベルを見ずに判定する。**",
        "",
        "## 層別の内訳",
        "",
        "| era | 観測経路 | 層 | 母集団 | 対象 | 抽出確率 | 重み |",
        "|---|---|---|---|---|---|---|",
    ]

    for key in sorted(groups):
        era, pathway, name = key
        population = len(groups[key])
        take = quota_for(name, population, args.both_agree_quota)
        if take == 0:
            continue
        lines.append(
            f"| {era} | {pathway} | `{name}` | {population} | {take} | "
            f"{take / population:.1%} | {population / take:.2f} |"
        )

    by_stratum = Counter(row["stratum"] for row in targets)
    lines += [
        "",
        f"**合計 {len(targets)} 件。** 層別: "
        + "、".join(f"`{name}` {count}" for name, count in by_stratum.most_common()),
        "",
        "## 注記",
        "",
        "- 悉皆層は抽出確率 100%、重み 1.00 で標本誤差を持たない。有限母集団のその層については",
        "  誤分類率が誤差なく得られる（判定不能分を除く）。",
        "- `both_agree` は重みが最大で、**必要数を支配しているのはこの層**である",
        "  （`reports/generated/gold_requirement.md`）。",
        "- これは既存 gold への上積みではない。規則の形成に用いた行は開発標本であり",
        "  （SAP §6b-2a）、本標本は独立 holdout である。",
    ]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"targets={len(targets)} reserves={len(reserves)}")
    print(f"sha256={digest}")
    for name, count in by_stratum.most_common():
        print(f"  {name:22s} {count}")
    print(f"wrote={args.sample} / {args.output}")


if __name__ == "__main__":
    main()
