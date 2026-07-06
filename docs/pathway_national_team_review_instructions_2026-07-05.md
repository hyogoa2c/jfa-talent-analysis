# Pathway / National-Team Review Instructions (2026-07-05)

対象ファイル:

- `data/manual/pathway_review_queue.csv`（169行）
- `data/manual/national_team_review_queue.csv`（295行）

いずれも `scripts/label_pathway_categories.py` / `scripts/label_national_team_selections.py` の
`needs_review`（要レビュー）行だけを抽出したもの。`high`（高信頼度）判定の行は含まれていない
——22名パイロットの正解データに対する検証で誤りが0件だったため、レビュー不要と判断している
（詳細は `docs/pathway_source_pilot_2026-07-03.md` / `docs/national_team_pilot_2026-07-03.md` の
Labeling Phase節を参照）。

## 記入ルール（共通）

- 分類器の自動判定（`pathway_category` / `any_national_team_selection` / `national_team_categories`
  列）が**正しければ、reviewed_*列は空欄のままでよい**。訂正が必要な行だけ記入する。
- `wikipedia_pathway_context` / `wikipedia_national_team_context` 列に、判定根拠となった
  Wikipedia本文（該当セクション、なければ記事全文）がそのまま入っている。別ファイルを開く必要はない。
- 判断に迷う行は `reviewer_note` に一言残しておくと後で見返しやすい（必須ではない）。

## pathway_review_queue.csv の確認ポイント

`pathway_category` の正式な値: `j_club_academy` / `high_school` / `university` / `jfa_academy` /
`grassroots_club` / `unknown`（`docs/source_audit_pathway_classification.md`のタクソノミー）。
判定ルールは「進学した最終学歴段階（university > high_school > jfa_academy > j_club_academy >
grassroots_club の優先順）」。`reviewed_pathway_category`にはこの6値のいずれかを記入する。

`pathway_reason`別の内訳と確認ポイント:

| reason | 件数 | 確認ポイント |
|---|---|---|
| `no_institution_keyword_found` | 131 | 分類器が学歴/クラブに関する語句を本文中に一切見つけられなかった行（`unknown`判定）。本文を読み、①本当に情報がない（プロ入り後の経歴のみ記載）→`unknown`のままでOK、②分類器の語彙にない言い回し（例:「〜学園」「〜学院」等、`高等学校`/`大学`/`ユース`/`下部組織`/`アカデミー`を含まない表現）で実際は情報がある→正しいカテゴリを`reviewed_pathway_category`に記入。 |
| `possible_incidental_schooling_around_club_academy` | 25 | 本文に学校名(`高等学校`/`大学`)とクラブアカデミー関連語(`ユース`/`下部組織`/`アカデミー`)が両方あり、かつ「寮生活」「誘われ」等の言い回しも含む行。**本当に独立して高校/大学に進学したのか**（→学校名の方を採用）、**それともクラブのアカデミー在籍のための便宜的な進学**（例:練習場が遠いための寮生活）**なのか**（→`j_club_academy`等クラブ側を採用）を本文から判断する。7493西川周作（大分トリニータU-18入団後、寮生活のために高校進学）が典型例。 |
| `overseas_relocation_language_no_domestic_institution` | 13 | 「移住」「渡欧」等の言葉があり、国内の学校/クラブ情報が見つからない行。海外クラブの下部組織のみで育った可能性が高い(伊藤遼哉のようなケース)。現行タクソノミーに「海外アカデミー」というカテゴリが無いため、`unknown`のままにするか、便宜上`j_club_academy`（分類器の自動判定）を採用するか、レビューで判断する。どちらを選んでもタクソノミーの制約であり、事実誤認ではない旨を`reviewer_note`に残しておくと後工程で分かりやすい。 |

## national_team_review_queue.csv の確認ポイント

`any_national_team_selection` の正式な値: `yes` / `no` / `unclear`。カテゴリの正式な値:
`A` / `U23` / `U20` / `U19` / `U18` / `U17` / `U16` / `U15` / `university` / `other`
（`docs/data_collection_plan.md`のnational_team_selectionsスキーマ）。

全295行が単一の理由 `negation_or_candidate_language_present`（本文中に代表選出関連の文脈で
「候補」または「落選」等の否定語が出現）。確認ポイントは2パターンに分かれる:

- **候補どまりのケース**（例:「U-18日本代表候補に選出された」）: 実際の招集・出場が明記されて
  いなければ `unclear` が妥当。他の文で実際の出場（例:「◯試合出場」「デビュー」等）が確認できれば
  `yes` に訂正し、該当カテゴリを`reviewed_categories`に記入。
- **落選・選外のケース**（例:「U-17ワールドカップのメンバーからは落選した」）: その大会/年代への
  選出はなかったことを意味するが、**同じ選手が別の年代/大会で実際に選出されている場合は`yes`が
  正しい**（分類器は否定文だけを除外し、他の文の実際の選出は別途カウントしているはずだが、複雑な
  経歴の選手は本文を通し読みして総合判断するとよい）。

`national_team_categories` 列は分類器のベストエフォート抽出であり、上記いずれのケースでも
本文を読んだ上でカテゴリの過不足があれば `reviewed_categories` に正しい値（`|`区切りで複数可）を
記入する。

## 進め方の提案

- `tier` 列（a=通算3000分以上/b=500-2999分/c=500分未満）でソートし、Tier A（主力級選手）から
  確認すると、分析上の重要度が高い選手から片付けられる。
- 分類器の判定が明らかに正しいと分かる行は空欄のまま次へ進んでよい——全169+295行を均等な時間で
  読む必要はない。
