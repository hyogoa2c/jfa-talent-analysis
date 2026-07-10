結論（TLDR）

全体として非常に規律の高いリサーチリポジトリです（限界の明文化、診断CSV、バリデータ、source_url/retrieved_at の徹底）。その上で、重要度の高い所見トップ5：

1. 【High】手動レビュー資産を破壊しうる上書き経路が2つある — enrich_manual_review_queue_with_wikipedia.py は --limit N を付けるとキュー全体を N行に切り詰めて入力ファイル自身に書き戻す。また build_overseas_manual_review_queue.py の再実行は manual_decision 等を空欄で再生成する。唯一の人手成果物である data/manual/ を機械が消せる状態。
2. 【High】研究の根幹である名寄せ・joinロジックがスクリプト内にありテストゼロ — 全下流データの品質を決める exact-match join + override 解決が scripts/build_joined_appearance_sample.py に住んでいて、33件のテストのどれもカバーしていない。
3. 【High】長時間収集ランに耐障害性がない — J.LeagueサイトとWikidataへのHTTPにリトライがなく、結果は全件完了後に一括書き出し。数時間ランの途中の一度のネットワークエラーで全収集分が失われる。
4. 【Medium】SFIX03パースの zip(strict=False) がサイト構造変化時に選手を無警告で脱落させる。
5. 【Medium】Wikidata照合に人物型・生年月日の絞り込みがなく、candidate_foreign_stint 行を検証するワークフローが存在しない（needs_manual_review だけがキューに入る）。

---
詳細所見

High

H1. --limit 付き実行で手動レビューキューが切り詰められる（データ損失）
scripts/enrich_manual_review_queue_with_wikipedia.py:47-48 で rows = rows[:args.limit] した後、:74 で limited な rows だけを出力へ書く。出力のデフォルトは :31-35 で入力と同じ data/manual/overseas_transfer_manual_review_queue_2023_2025_gap2.csv。つまり「試しに --limit 3」と実行しただけでキューが3行のファイルになる。現在キューは15行・全行 manual_decision 未記入（確認済み）なので実害はまだ無く、git追跡（.gitignore で !data/manual/ ）が防護になっているが、レビュー記入後に踏むと人手作業が消える。
推奨: limit時は残り行もそのまま書き出す／既存の非空 manual_decision を検出したら上書き拒否、のどちらか。

H2. キュー再ビルドが手動判定を空欄で上書きする
src/jfa_talent_analysis/overseas_review.py:89-98 は manual_decision/manual_note/evidence_url を常に空文字で生成し、scripts/build_overseas_manual_review_queue.py:42-47 はマージも存在チェックもせず上書き保存する。audit をやり直してキューを作り直すと記入済み判定が全滅する。
推奨: 既存キューを読み、source_player_id + reappearance_season キーで手動列を引き継ぐマージ処理。

H3. 名寄せ・identity解決ロジックが未テストのままスクリプトに滞留
scripts/build_joined_appearance_sample.py:108-132（index_players_by_name / find_override / join_record）は全季節データセットの基盤だが、テストが1件もない（テストは純関数のパース・集計に集中。スクリプト系は test_multi_season_features_script.py のみ）。同じ index_players_by_name・normalize_name が scripts/suggest_identity_overrides_from_profiles.py:188-196 にコピーされており、正規化ルールが乖離すると静かに突合が壊れる。
推奨: src/jfa_talent_analysis/matching.py（仮）に引き上げ、①1候補一致 ②複数候補→ambiguous ③override優先 ④override が未知IDを指す場合のエラー、の4ケースをテスト化。

H4. 収集・監査ランの障害耐性ゼロ
- src/jfa_talent_analysis/sources/jleague_data_site.py:283-307 — fetch_url/post_form にリトライ・バックオフなし。
- scripts/collect_appearance_records_sample.py:79-124 — 全チーム分をメモリに貯めて最後に書き出し。1リーグ数十チーム×--sleep 0.5 のラン途中の例外で全ロス。
- scripts/audit_wikidata_reappearance_candidates.py:42-56 — WDQSは429/503を返しやすいのに例外処理なし＋一括書き出し。対照的にWikipedia側 (sources/wikipedia.py:88-97) には429リトライがあり、方針が非対称。
推奨: fetch_url 系に指数バックオフの薄いリトライ、収集スクリプトに逐次追記または チーム/行単位のチェックポイント再開。

Medium

M1. zip(strict=False) による無警告の選手脱落
src/jfa_talent_analysis/sources/jleague_data_site.py:374 — playerIdList の hidden input 数とテーブル行数がズレた場合（サイト改修で起こりうる）、超過分が静かに捨てられる。件数不一致を検出して例外か警告を出すべき。名寄せ元データの欠落は下流で「unmatched」として現れ、原因追跡が困難になる。

M2. Wikidata照合の精度と、candidate_foreign_stint の検証経路の欠如
- sources/wikidata.py:42-63 のSPARQLは exact label のみで、P31=Q5（人間）や P106（サッカー選手）、生年月日の絞り込みがない。同名の非サッカー選手が単独ヒットすると誤って no_wikidata_foreign_stint に落ちる（偽陰性）。docs自身が改善必要と認識済み（docs/source_audit_overseas_transfers.md:108-111）。
- summarize_stints (wikidata.py:99-117) は 全キャリアの外国クラブを数え、gap期間（previous_observed_season〜reappearance_season）との重なりを見ていない。P54に開始/終了 (P580/P582) を取得済みなのに未活用。
- overseas_review.py:64 のフィルタにより、candidate_foreign_stint（18件）はキューに入らず、manual_decision を記録する場所がどこにもない。docsは「候補証拠であり最終ラベルではない」と正しく書いているが、それを検証するワークフロー成果物が未定義。
- 未検証事項: 髙/高・﨑/崎 等の異体字での取りこぼし規模は実データ未確認。

M3. 1フレーム内の全competitionを単一リーグラベルで合算（未検証の膨張リスク）
scripts/collect_appearance_records_sample.py:76-117 はフレーム内の全 competition_id を回し、リーグ名はフレーム表示名で統一。2015/16の2ステージ対応は意図的（docs/data_collection_plan.md:262）だが、チャンピオンシップや昇格プレーオフのような別competitionが同フレームに含まれる場合、minutesが二重計上気味になる。未検証（実データでのcompetition一覧突合が必要）。診断CSVは league/team 数のみで competition 単位の内訳がない。推奨: per-competition の行数診断を出す、または competition 名のホワイトリスト。

M4. ユーティリティの重複と意味の不一致
- parse_int が5箇所に定義され挙動が異なる: jleague_data_site.py:353（None返し）、pipeline.py:101・features.py:140・reappearance.py:57（0返し）、overseas_review.py:102（int() なので負数を受理）。
- read_csv/write_csv が pipeline.py:83-98 と6スクリプトに重複（存在チェックの有無もバラバラ）。
- LEAGUE_FRAME_IDS が pipeline.py:9 と collect_appearance_records_sample.py:18、poc_sfpr01_appearance_records.py:16 に三重定義。
今は破綻していないが、スクリプトが「増加中」の構造で最初にドリフトする箇所。

M5. pandas が宣言だけされて未使用
pyproject.toml:8 に pandas>=3.0.3 があるが、src/scripts/tests/notebooks のどこにも import がない（grepで確認）。実装は全て stdlib csv。使う予定がなければ削除、predictor モデリング段階で使うなら現状維持でも可だが README の実態説明と併せて整理を。

M6. docs のコマンド例が実際には繋がらない
docs/source_audit_overseas_transfers.md:38-41 の audit コマンドは --output 未指定（デフォルト wikidata_reappearance_candidates.csv）なのに、:53 の次工程は wikidata_reappearance_candidates_2023_2025_gap2.csv を読む。手順書どおりに実行するとファイルが見つからない。

M7. CIがない
.github/ 不在。pytest/ruff はローカル実行頼み。テストが0.05秒で終わる構成なので、GitHub Actions で pytest + ruff を回すコストはほぼゼロ、H1/H2 のようなリグレッション検出の土台にもなる。

Low

L1. scripts/suggest_identity_overrides_from_profiles.py:200 — normalize_team_name に replace("岩手", "盛岡") がハードコード。いわてグルージャ盛岡の改名対応と思われるが、コメントも設定化もなく、他の「わる。エイリアス表（data/manual/team_aliases.csv 等）へ。

L2. ruff はデフォルトルールのみ（pyproject.toml に select なし）。I（import順）、B（bugbear）、UP あたりは低コスト。型ヒントが全面的に付いているので mypy/pyright の導入障壁も低い。

L3. README にスクリプト23本の使い分け一覧と、海外移籍レビューワークフロー（実質の運用手順書である docs/source_audit_overseas_transfers.md）への導線がない。「Starting Point」はリサーチノート1件のみ。  は git log を読まないと全体像が掴めない。

L4. enrich 再実行時、一時的な検索失敗行は既存の wikipedia_titles をエラー文字列で潰す（enrich_manual_review_queue_with_wikipedia.py:64-70）。失敗時は既存値保持が安全。

---
推奨アクション順序

1. data/manual 保護（H1・H2）— 最小で「非空 manual_decision の上書き拒否」ガード。人手成果物の保全が最優先。
2. join ロジックの src 引き上げ + テスト（H3、M4 も同時に解消）。
3. fetch リトライ + 収集の逐次書き出し（H4）— 今後の 2005-2013 バックフィルや全量収集の前提。
4. CI 追加（M7）— 上記の定着装置。
5. Wikidata クエリ強化と candidate_foreign_stint 検証キュー（M2）は、次の研究フェーズ（outcome ラベル確定）の設計と一緒にやるのが効率的。

なお、docs の誠実さ（限界・COVID期・2013年以前の非可用性の明文化）、診断CSVの設計、バリデータの存在、data/manual の git 追跡は、この規模のソロ研究リポジトリとして明確に良い実践です。
