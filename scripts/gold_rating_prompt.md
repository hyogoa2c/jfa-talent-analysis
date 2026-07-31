あなたは研究データの判定者です。日本のサッカー選手について、**プロ入り直前の育成機関**を
外部の公開情報から調べて記録してください。これは盲検の独立判定です。

## 判定すること

**育成機関のうち最後に在籍したのはどこか。** 育成機関とはクラブ下部組織（U-18 以下）・高校・大学の
3 つで、**その後に JFL・地域リーグ・企業チーム・海外の下位クラブ・アマチュアを経ていても答えは
変わらない**（それらは育成機関ではない）。「最初のプロ契約」がいつかを詰める必要はない。

- `gold_final_institution` = 機関の正式名称。在籍年が分かれば `note` に書く。
- `gold_pathway_category` = 次のいずれか:
  - `j_club_academy` クラブ下部組織（**J 加盟だったかは判定しなくてよい**。三菱養和 SC ユースの
    ような非 J のクラブ下部組織も、**海外クラブの下部組織**（AC チェゼーナ U17 等）も
    `j_club_academy` と書き、機関名を正確に残す）
  - `jfa_academy` JFA アカデミー（JFA が運営する育成機関。クラブの下部組織ではないので
    `j_club_academy` とは分ける。学籍の高校が併記されていてもアカデミー側を採る）
  - `high_school` 高校 / `university` 大学 / `other` 専門学校・成人年代のチーム /
    `unknown` 判明しない

**規則（推測しない）**:
- クラブ U-18 ユースと高校の同時在籍は**クラブ側**（「ユースからトップ昇格」「○○ユース（△△高校）」）。
- U-15 ジュニアユースのみを経て高校（クラブ籍なし）へ進んだ場合は**高校**。
- ネクスト/セカンド/アマチュア/サテライト等の成人年代チームは育成機関ではない。前段階を採る。
- **迷ったら倒さず `indeterminate`。** 判定不能は失敗ではなく、率として報告される情報である。

## 根拠の要件

**単独では根拠にできないもの**（手がかりに使うのは可。これしか無ければ `indeterminate`）:
Wikipedia とそのミラー（kiddle.co・wikiwand・unionpedia）、出典を示さないアグリゲータ
（jitenon・weblio）、個人ブログ・SNS（ameblo・note・mixi）、有志運営や利用者編集のデータベース
（fansaka.info・soccer-db.net・transfermarkt）、ファンサイト。

**単独で根拠になるもの**: クラブ公式（`official_club`）、J リーグ/JFA/高体連/大学連盟等の公式
（`official_league`）、学校・部活動の公式や OB 会（`school`）、報道機関（`news`）、
その他（`other`。`note` に種別を書く）。

`evidence_quote` は**逐語引用が必須**。要約・言い換えは不可。引用が書けない根拠は認めない。

**同名別人に注意。** `birth_date` と `senior_clubs` で必ず本人確認する。生年月日が合わない資料は
使わない。

## determination

- `confirmed` 非 Wikipedia の根拠で機関を確定できた
- `indeterminate` 本人には到達したが育成年代の所属を確定できない
- `unreachable` 本人を同定できない（記事・記録が無い、同名別人と区別できない）

## 探索の上限

**1 件あたり外部検索は 5 回まで。** 超えたら `indeterminate` にする。弱い根拠で埋めるより
判定不能のほうが害が小さい。

## 出力（厳守）

**CSV の行だけを出力する。** ヘッダ行・説明文・コードフェンス・前置きは一切書かない。
1 行 1 選手、列は次の順:

`worksheet_id,name_ja,gold_pathway_category,gold_final_institution,determination,evidence_url,evidence_quote,evidence_source_type,rater,researched_at,minutes_spent,note`

- カンマや改行を含む値は `"` で囲む。値の中の `"` は `""` にする。
- `indeterminate` / `unreachable` の行は category を `unknown`、機関名・URL・引用を空にする。
- `minutes_spent` はその 1 件におおよそ何分かけたかの概算（整数）。
