# 人手レビュー指示（Phase 1b + Phase 1 corrigendum、2026-07-20）

対象は 5 つのレビューキュー（計 288 行）。分類器の `needs_review` 行のみ抽出済みで、
`high`（高信頼）行は含まない（held-out gold 56 名で高信頼の silent-wrong は 0 と検証済み、
`docs/measurement_equivalence_phase1b_2026-07-20.md`）。各行に判定根拠の Wikipedia 本文
（`wikipedia_pathway_context` / `wikipedia_national_team_context` 列）が入っているので、
別ファイルを開く必要はない。

## ★ 最重要: 経路分類の新定義（SAP §3 追記 2026-07-20、全キュー共通で適用）

測定同等性検証で、Jクラブユースと高校の**同時在籍**の扱いを次のように確定した
（`docs/research_plan_phase1b.md` §1b）。**従来の「高校 > ユース」優先順は撤回**:

- **Jクラブ U-18 ユース + 高校の同時在籍 → `j_club_academy`**（育成主体はアカデミー、
  高校は提携通学先）。判定の目印:
  - 「(クラブ)ユースからトップチームに昇格」（＝ユースから昇格した ＝ アカデミー育成）
  - 「○○ユース（△△高校）」の並記
  - 「高校時代は△△高校に通いながら○○ユースに所属」
- **ただし「トップ昇格できなかった / せず / ならず」→ 昇格していない**。この場合、その後
  進んだ大学・高校が最終経路（例: 「下部組織 → 昇格せず → 大学 → プロ」は `university`）。
- U-15 ジュニアユース**のみ**（クラブ籍を離れて高校へ）→ 従来どおり `high_school`。
- 2種登録でプロ相当出場後に大学進学した境界例 → 最初のプロ契約前の段階を採る。

`pathway_category` の正式値: `j_club_academy` / `high_school` / `university` / `jfa_academy` /
`grassroots_club` / `unknown`。訂正が必要な行だけ `reviewed_pathway_category` に記入
（正しければ空欄でよい）。迷ったら `reviewer_note` に一言。

## 優先順位（週次リミットが厳しい場合はこの順で）

| 優先  | キュー                                                            | 行数   | 用途                          | なぜこの優先度か                                                                                  |
| ----- | ----------------------------------------------------------------- | ------ | ----------------------------- | ------------------------------------------------------------------------------------------------- |
| **1** | `data/manual/phase1_pathway_youth_vs_university_review_queue.csv` | **61** | Phase 1 corrigendum           | 中心結果を動かしうる university↔academy 曖昧ケース。ここを固めないと公式 corrigendum が確定しない |
| **2** | `data/manual/pre2014_pathway_review_queue.csv`                    | **52** | Phase 1b 確認的（era-1 経路） | Phase 1b の確認的分析標本（born 1981-89）の曝露変数                                               |
| 3     | `data/manual/pre2014_national_team_review_queue.csv`              | 45     | Phase 1b 探索（era-1 代表）   | 代表は副アウトカムで探索的降格済み → 優先度中                                                     |
| 4     | `data/manual/pre2014_pathway_review_queue_p2.csv`                 | 88     | 記述専用（born ≤1980 経路）   | 確認的分析に入らない記述層 → 後回し可                                                             |
| 5     | `data/manual/pre2014_national_team_review_queue_p2.csv`           | 42     | 記述専用（born ≤1980 代表）   | 同上・最も後回し可                                                                                |

時間が優先 1+2（計 113 行）までしか取れなくても、確認的結果と corrigendum は前進できる。
3-5 は記述・探索用なので次サイクル以降でよい。

## 優先1: Phase 1 university↔academy 曖昧キュー（61 行）の見方

列: `production_pathway_category`（正本の現ラベル）, `classifier_suggestion`（新分類器が
university を維持）, `wikipedia_pathway_context`。全 61 行が「Jクラブ下部組織の履歴 + 昇格
言及 + 大学」が同居し、新定義のどちらに当たるか本文を読まないと決まらないケース。

- 本文が「ユース**から昇格**（してプロ）」→ `j_club_academy`
- 本文が「昇格**せず/できず** → 大学 → プロ」→ `university`（＝現ラベル維持、空欄でよい）
- production が空欄（12 行）は identity 未確認等。本文で判断できれば記入、無理なら空欄。

## 優先2-3: era-1 pathway / NT キューの reason 別ポイント

`pre2014_pathway_review_queue.csv`（52 行）の `pathway_reason`:

| reason                                                 | 確認ポイント                                                                                                                                       |
| ------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| `no_institution_keyword_found`                         | 学歴/クラブ語句が本文にない行。①本当に情報なし（プロ後経歴のみ）→ `unknown` のまま、②「〜学園」等の未収録表現で実は情報あり → 正しいカテゴリを記入 |
| `university_entry_after_pro_entry`                     | プロ入り後に大学へ進んだ順序を検出。**最初のプロ入り前**の段階（多くは高校）が正解                                                                 |
| `possible_declined_university_offer`                   | 「大学から誘いを受けたが（プロ入り）」= 大学には**進学していない**。高校等が正解                                                                   |
| `youth_promotion_vs_university_ambiguous`              | 優先1 と同じ判断（昇格した→academy / せず→university）                                                                                             |
| `possible_incidental_schooling_around_club_academy`    | 学校とアカデミーが両方あり「寮生活/誘われ」等。新定義に照らし、アカデミー育成の便宜的通学なら `j_club_academy`                                     |
| `overseas_relocation_language_no_domestic_institution` | 海外アカデミー育ちで国内機関なし。タクソノミー外なので `unknown` か、`reviewer_note` に理由を残す                                                  |

代表キュー（`any_national_team_selection` の値: `yes`/`no`/`unclear`。カテゴリ: `A`/`U23`/
`U20`/`U19`/`U18`/`U17`/`U16`/`U15`/`university`/`other`）:

- 「候補に選出」どまりで実出場の記載なし → `unclear`
- 「落選」等でも、別年代/大会で実際に選出があれば `yes`
- カテゴリの過不足は `reviewed_categories` に `|` 区切りで訂正

## 記入後の流れ（金曜リミットリセット後にこちらで実施）

レビュー済みキューを push いただければ、(a) 補正ラベルで `player_pathway_outcomes` を再構築、
(b) 正本パイプライン（RCS・機関クラスター SE）で Phase 1 を再実行し corrigendum を確定、
(c) Phase 1b の確認的分析（J1 到達 by25 × era 交互作用）に進む。
