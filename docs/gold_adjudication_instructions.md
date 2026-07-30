# 裁定の手引き（gold holdout）

対象: `data/manual/gold_pilot_adjudication_worklist.csv`（パイロット 30 件から 10 件）。
本番 539 件でも同じ手順・同じ列を使う。

**記入するのは末尾の 4 列だけ。** 他の列は判定者2名の回答と自動判定なので触らない。

| 列 | 入れるもの |
|---|---|
| `adjudicated_category` | `j_club_academy` / `high_school` / `university` / `other` / `unknown` |
| `adjudicated_institution` | 機関の正式名称。`unknown` のときは空欄 |
| `adjudicated_determination` | `confirmed` / `indeterminate` / `unreachable` |
| `adjudicator_note` | 判断の理由（短くてよい）。**判定者と違う結論にしたときは必須** |

**空欄 = 判定者2名に同意、ではない。** 全行に記入する（`review_reason` ごとに問いが違う）。

---

## `review_reason` ごとに何を判断するか

### `disagreement`（5 件）— 片方が確定・片方が判定不能

**カテゴリの対立ではない。** パイロットでは、双方が `confirmed` した行のカテゴリは 20/20 一致した。
不一致はすべて「片方は根拠に到達し、片方は到達できなかった」型である。

**問い: 確定した側の根拠は、プロトコル v2 §2 の要件を満たしているか。**

- 満たしている → 確定した側の `category` / `institution` を採り、`confirmed`
- 満たしていない（下記の「単独では根拠にならないソース」しかない） → **`unknown` / `indeterminate`**

見るのは `a_evidence_url` / `b_evidence_url` と `a_quote` / `b_quote`。
`a_weak_evidence` / `b_weak_evidence` 列に理由が入っていれば、自動判定が既に該当を検出している。

**単独では根拠にならないソース**: Wikipedia とそのミラー（kiddle.co・wikiwand・unionpedia）、
出典を示さないアグリゲータ（jitenon・weblio）、個人ブログ・SNS（ameblo・note・mixi）、
有志運営／利用者編集のデータベース（fansaka.info・soccer-db.net・transfermarkt）、ファンサイト。

**判定不能を選ぶのは失敗ではない。** 弱い根拠で埋めるほうが害が大きい
（率として報告され、設計は判定不能 25% でも tolerance 内に収まることを確認済み）。

### `weak_evidence`（3 件）— 両者のカテゴリは一致、しかし根拠が弱い

**問い: 弱くないソースが 1 つでもあるか。**

- ある（もう一方の判定者が公式・報道で裏を取っている等） → その根拠で `confirmed`。
  `adjudicator_note` にどちらの根拠を採ったか書く
- ない → **`indeterminate`**（カテゴリが両者一致していても、根拠が基準を満たさなければ確定しない）

機関名の表記が2人で違う場合（例: `四日市中央工業高等学校` と `三重県立四日市中央工業高等学校`）は、
**正式名称のほうを採る**。これは不一致ではなく表記ゆれである。

### `agreement_spot_check`（2 件）— 抜き取り点検

一致行から seed 固定で抽出した。**一致は独立の証拠にならない**——判定者2名はいずれも LLM で、
同じ日本語ウェブを引くため、同じ誤りに揃うことがありうる。ここで見るのはその可能性である。

**問い: 引用された根拠は、実際にそのカテゴリを支持しているか。**

- 支持している → 両者と同じ値を記入（`confirmed`）
- 支持していない → 正しい値に直し、`adjudicator_note` に**何がずれていたか**を書く。
  点検で誤りが出た場合は、同種の誤りが一致行全体に広がっている可能性があるため、
  点検の割合を上げるか二者判定に戻すかを検討する

---

## 記入例

```csv
worksheet_id,...,adjudicated_category,adjudicated_institution,adjudicated_determination,adjudicator_note
W001,...,unknown,,indeterminate,B の根拠は fansaka.info 単独で v2 の要件を満たさない。A の判断を採る
W005,...,high_school,三重県立四日市中央工業高等学校,confirmed,両者一致。正式名称を採用。根拠はブログのみだが四中工は…（要確認）
W019,...,university,慶應義塾大学,confirmed,岡山公式の経歴表記を確認。点検で問題なし
```

## 終わったら

`adjudicated_*` を埋めたファイルをそのまま保存する（BOM が付いても問題ない。
読み取り側は `utf-8-sig` で開く）。裁定結果は次の 2 つに使われる:

1. **gold の確定値**（混同行列の入力）
2. **判定体制の復帰規則の判断**（SAP §6b-2b-rate）。信頼性サブサンプルで
   「双方 `confirmed` なのにカテゴリが食い違う」率が 5% を超えたら、単一判定を二者判定に戻す
