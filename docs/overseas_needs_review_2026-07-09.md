# Overseas Classifier needs_review Human Review (2026-07-09)

Follows up on `docs/data_collection_revision_proposal_2026-07-07.md` item 2's `moved_overseas`
expansion: `overseas_classification.py`'s classifier flagged 210 of 3,403 confirmed players'
`yes` calls as `needs_review` (later 196 after a classifier bug fix found during this review —
see below). All 196 were read and resolved by hand, not sampled.

## Method

Reviewed every `needs_review` row's Wikipedia evidence sentence(s), pulling the full article
extract for cases where the flagged sentence alone was ambiguous (e.g. a bare section header
`=== 海外挑戦 ===` with no visible content, or a declined-offer sentence that might still be
followed by a real move later in the article). Decisions and reasoning are recorded in
`data/manual/overseas_review_queue.csv` (`reviewed_moved_overseas` + `reviewer_note` columns),
following this project's established review-queue format.

## A classifier bug found mid-review: "中国" is ambiguous

35 of the 210 flagged rows were `retracted_language_present` (offer/trial language like
`不合格`/`破談`/`練習参加` near an otherwise-matching sentence); the other 175 were
`weak_country_move_signal_only` (a bare country name + move verb, not matching a stronger
structural pattern).

Working through the weak-signal rows surfaced a real bug: **"中国" is ambiguous in Japanese** —
it means China, but "中国サッカーリーグ"/"中国リーグ" is a real **domestic** Japanese regional
league (中国地方, the Chugoku region of western Honshu), one tier below JFL. 15 rows had matched
on this: 福山シティFC (Fukuyama, Hiroshima), レノファ山口FC (Yamaguchi), ベルガロッソいわみ
(Iwami, Shimane) — all Japanese clubs, none in China. All 15 were still `needs_review` (never
silently high-confidence), so nothing was wrong at scale, but the false-positive rate would have
stayed elevated on every future rerun without a fix.

Fixed with a negative lookahead in `overseas_classification.py`'s `COUNTRY_NAMES` pattern
(`中国(?!地方|サッカーリーグ|リーグ)`), re-validated against the pilot golden set and the
existing 33-player manual queue (still 32/32 and consistent), then reran the full-population
classifier: `needs_review` dropped from 210 to 196 and `yes` count from 640 to 626 before the
remaining human review pass.

## Review outcome

Of 196 reviewed rows: **110 confirmed** as a real foreign-club stint, **86 not confirmed**.
Common patterns on each side:

- **Confirmed despite the flag**: a real, well-documented transfer whose evidence sentence
  happened to also contain trial/offer language *about an earlier, different, declined
  approach* elsewhere in the same sentence window (e.g. 堂安律's flagged sentence describes a
  declined PSV offer, but his article documents an actual FC Groningen move later); or a bare
  country name + move verb that was in fact the correct, simply-phrased evidence (most
  frequently アルビレックス新潟シンガポール — Albirex Niigata's Singapore satellite club,
  which plays in the Singapore Premier League and is treated as a genuine overseas move here
  despite the Japanese parent organization, since the player physically relocates to play in a
  foreign league).
- **Not confirmed**: an offer/trial that fell through (`〜のオファーを受けたが残留`,
  `契約締結には至らず`), a sentence actually about a *different* player (teammate, competing
  import signing, or opposing player) mentioned in the same sentence, or a youth-academy-only
  stint abroad predating the player's professional debut (e.g. 金城クリストファー達樹's
  Fortuna Düsseldorf U-19 spell, age 15-16, years before his J-League debut — treated as a
  pathway signal, not a career-outcome overseas transfer, for consistency with how
  `pathway_classification.py` treats foreign youth academies).

## Impact

`moved_overseas_final`'s `yes` count fell from 640 (before the China/Chugoku classifier fix)
to 626 (after the fix, still pre-human-review) to 543 (post-review) out of 3,408 labeled players. The regression coefficients
in `reports/generated/initial_analysis_report.md` moved only slightly (university odds ratio for
overseas move: 0.48 → 0.49 plain, 0.56 → 0.57 with the J1-attainment mediator) — the review
corrected real errors but did not change the substantive conclusion in
`docs/initial_analysis_interpretation_2026-07-09.md`.

`moved_overseas_final` is now held to the same confidence standard as `pathway_category` and
`any_national_team_selection`: every row is either from direct manual review (33 players) or a
classifier output that is either high-confidence-and-unreviewed or has passed this needs_review
pass (196 players). See `data/manual/overseas_review_queue.csv` for the full row-by-row record.
