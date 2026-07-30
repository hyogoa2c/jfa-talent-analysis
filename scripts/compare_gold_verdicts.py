"""Compare the two raters and build the adjudication worklist (SAP §6b-2b, §11-2).

Agreement between two LLM raters is weaker evidence than agreement between two
people, so this script does not treat a match as settled: it emits the
disagreements *and* a fixed 10% sample of the agreements for the user to check,
which is what the protocol asks for.

It also flags evidence that cannot support a verdict on its own -- Wikipedia and
its mirrors (the source being measured), plus blogs, SNS posts and fan-maintained
databases -- because the pilot found raters reaching for those when official
sources ran out, and a Wikipedia mirror in the evidence column silently undoes
the independence the holdout exists to provide.
"""

from __future__ import annotations

import argparse
import csv
import statistics
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

import numpy as np

# Hosts that may support a verdict but never carry it alone.
WEAK_HOSTS = {
    "wikipedia.org": "Wikipedia（測定対象と同一）",
    "kiddle.co": "Wikipedia ミラー",
    "wikiwand.com": "Wikipedia ミラー",
    "weblio.jp": "Wikipedia を含む辞書アグリゲータ",
    "jitenon.jp": "出典不明のアグリゲータ",
    "ameblo.jp": "個人ブログ",
    "mixi.jp": "SNS",
    "note.com": "個人ブログ",
    "blog.livedoor.jp": "個人ブログ",
    "fc2.com": "個人ブログ",
    "fansaka.info": "有志運営のデータベース",
    "soccer-db.net": "有志運営のデータベース",
    "transfermarkt.jp": "利用者編集のデータベース",
    "transfermarkt.com": "利用者編集のデータベース",
    "unionpedia.org": "Wikipedia 派生",
    "consadeconsa.com": "ファンサイト",
}

VERDICT_KEY = "worksheet_id"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rater-a", type=Path, required=True)
    parser.add_argument("--rater-b", type=Path, required=True)
    parser.add_argument(
        "--key", type=Path, default=Path("data/manual/gold_holdout_worksheet_key.csv")
    )
    parser.add_argument("--check-fraction", type=float, default=0.10)
    parser.add_argument("--seed", type=int, default=20260729)
    parser.add_argument("--worklist", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def weak_reason(url_field: str) -> str:
    """Why this row's evidence cannot stand alone, or "" if some source can."""
    reasons = []
    for url in (u.strip() for u in url_field.split(";")):
        if not url:
            continue
        host = urlparse(url).netloc.lower()
        for suffix, reason in WEAK_HOSTS.items():
            if host == suffix or host.endswith("." + suffix) or suffix in host:
                reasons.append(f"{host}={reason}")
                break
        else:
            return ""  # at least one source is not on the list
    return "; ".join(reasons) if reasons else "根拠 URL なし"


def minutes(rows: list[dict[str, str]]) -> list[float]:
    out = []
    for row in rows:
        try:
            out.append(float(row.get("minutes_spent", "")))
        except ValueError:
            continue
    return out


def main() -> None:
    args = parse_args()
    a = {row[VERDICT_KEY]: row for row in read_csv(args.rater_a)}
    b = {row[VERDICT_KEY]: row for row in read_csv(args.rater_b)}
    shared = sorted(set(a) & set(b))
    if not shared:
        raise SystemExit("the two verdict files share no worksheet_id")

    strata = {}
    if args.key.exists():
        strata = {row["worksheet_id"]: row for row in read_csv(args.key)}

    rows = []
    for key in shared:
        left, right = a[key], b[key]
        both_confirmed = left["determination"] == right["determination"] == "confirmed"
        agree = left["gold_pathway_category"] == right["gold_pathway_category"]
        rows.append(
            {
                "worksheet_id": key,
                "name_ja": left.get("name_ja", right.get("name_ja", "")),
                "stratum": strata.get(key, {}).get("stratum", ""),
                "era": strata.get(key, {}).get("era", ""),
                "a_category": left["gold_pathway_category"],
                "b_category": right["gold_pathway_category"],
                "a_institution": left["gold_final_institution"],
                "b_institution": right["gold_final_institution"],
                "a_determination": left["determination"],
                "b_determination": right["determination"],
                "agree_category": "1" if agree else "0",
                "both_confirmed": "1" if both_confirmed else "0",
                # Only a `confirmed` row makes a claim its evidence has to carry;
                # an indeterminate row with no URL is the protocol working.
                "a_weak_evidence": weak_reason(left["evidence_url"])
                if left["determination"] == "confirmed"
                else "",
                "b_weak_evidence": weak_reason(right["evidence_url"])
                if right["determination"] == "confirmed"
                else "",
                "a_evidence_url": left["evidence_url"],
                "b_evidence_url": right["evidence_url"],
                "a_quote": left["evidence_quote"],
                "b_quote": right["evidence_quote"],
            }
        )

    disagreements = [r for r in rows if r["agree_category"] == "0"]
    agreements = [r for r in rows if r["agree_category"] == "1"]
    weak = [r for r in rows if r["a_weak_evidence"] or r["b_weak_evidence"]]

    rng = np.random.default_rng(args.seed)
    take = max(1, round(len(agreements) * args.check_fraction)) if agreements else 0
    checked = {agreements[i]["worksheet_id"] for i in rng.permutation(len(agreements))[:take]}

    worklist = []
    for row in rows:
        if row["agree_category"] == "0":
            reason = "disagreement"
        elif row["worksheet_id"] in checked:
            reason = "agreement_spot_check"
        elif row["a_weak_evidence"] or row["b_weak_evidence"]:
            reason = "weak_evidence"
        else:
            continue
        # The adjudicator sees the evidence, not the stratum: knowing a row was
        # drawn because the two measurement sources disagreed is itself a hint.
        blinded = {k: v for k, v in row.items() if k not in ("stratum", "era")}
        worklist.append(
            {
                **blinded,
                "review_reason": reason,
                "adjudicated_category": "",
                "adjudicated_institution": "",
                "adjudicated_determination": "",
                "adjudicator_note": "",
            }
        )

    args.worklist.parent.mkdir(parents=True, exist_ok=True)
    with args.worklist.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(worklist[0]) if worklist else ["worksheet_id"]
        )
        writer.writeheader()
        writer.writerows(worklist)

    both_confirmed = [r for r in rows if r["both_confirmed"] == "1"]
    agree_confirmed = [r for r in both_confirmed if r["agree_category"] == "1"]
    a_minutes, b_minutes = minutes(list(a.values())), minutes(list(b.values()))

    lines = [
        "# 判定者2名の突合（gold holdout）",
        "",
        f"対象 {len(rows)} 件（rater A = `{args.rater_a}` / rater B = `{args.rater_b}`）",
        "",
        "## 一致",
        "",
        f"- カテゴリ一致 **{len(agreements)}/{len(rows)} = {len(agreements) / len(rows):.1%}**",
        f"- 双方 `confirmed` の行に限ると **{len(agree_confirmed)}/{len(both_confirmed)}"
        f" = {len(agree_confirmed) / len(both_confirmed):.1%}**"
        if both_confirmed
        else "",
        f"- 不一致 {len(disagreements)} 件、うち双方 `confirmed` は "
        f"{sum(1 for r in disagreements if r['both_confirmed'] == '1')} 件",
        "",
        "## 判定不能率（設計シミュレーションの仮定は 10%）",
        "",
        "| 判定者 | confirmed | indeterminate | unreachable |",
        "|---|---|---|---|",
    ]
    for name, source in (("A", a), ("B", b)):
        counts = Counter(row["determination"] for row in source.values())
        lines.append(
            f"| {name} | {counts.get('confirmed', 0)} | {counts.get('indeterminate', 0)} "
            f"| {counts.get('unreachable', 0)} |"
        )

    both_out = [
        r
        for r in rows
        if r["a_determination"] != "confirmed" and r["b_determination"] != "confirmed"
    ]
    one_out = [
        r
        for r in rows
        if (r["a_determination"] == "confirmed") != (r["b_determination"] == "confirmed")
    ]
    lines += [
        "",
        f"**設計に効くのは「両者とも確定できなかった」率** = {len(both_out)}/{len(rows)} = "
        f"**{len(both_out) / len(rows):.1%}**。片方だけが確定した {len(one_out)} 件は裁定で",
        "決着しうるので、判定不能として設計に入れるのは過大評価になる（裁定結果で確定する）。",
    ]

    lines += [
        "",
        "## 所要時間（1 件あたり・自己申告）",
        "",
        f"- A: 中央値 {statistics.median(a_minutes):.1f} 分 / 合計 {sum(a_minutes):.0f} 分"
        if a_minutes
        else "- A: 記録なし",
        f"- B: 中央値 {statistics.median(b_minutes):.1f} 分 / 合計 {sum(b_minutes):.0f} 分"
        if b_minutes
        else "- B: 記録なし",
        "",
        "## 単独では根拠にならないソース",
        "",
        f"**{len(weak)} 件**がどちらかの判定者で該当（Wikipedia・そのミラー・ブログ・SNS・有志データベース）。",
        "",
    ]
    for row in weak:
        for name in ("a", "b"):
            if row[f"{name}_weak_evidence"]:
                lines.append(
                    f"- {row['worksheet_id']} {row['name_ja']}（rater {name.upper()}）: "
                    f"{row[f'{name}_weak_evidence']}"
                )

    if disagreements:
        lines += ["", "## 不一致の一覧", "", "| id | 氏名 | 層 | A | B |", "|---|---|---|---|---|"]
        for row in disagreements:
            lines.append(
                f"| {row['worksheet_id']} | {row['name_ja']} | `{row['stratum']}` | "
                f"{row['a_category']} / {row['a_institution']} | "
                f"{row['b_category']} / {row['b_institution']} |"
            )

    lines += [
        "",
        "## 裁定ワークリスト",
        "",
        f"`{args.worklist}` に {len(worklist)} 件"
        f"（不一致 {len(disagreements)}・一致行の {args.check_fraction:.0%} 点検 {len(checked)}"
        f"・弱い根拠 {len(worklist) - len(disagreements) - len(checked)}）。",
        "",
        "一致は独立の証拠にならない（判定者2名はいずれも LLM で、同じ日本語ウェブを引く）。",
        f"点検標本は seed={args.seed} で固定した。",
    ]

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(line for line in lines if line != "") + "\n", encoding="utf-8")
    print(f"agreement={len(agreements)}/{len(rows)} worklist={len(worklist)} -> {args.worklist}")
    print(f"report={args.report}")


if __name__ == "__main__":
    main()
