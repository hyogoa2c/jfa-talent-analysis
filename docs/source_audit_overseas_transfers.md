# Overseas Transfer Source Audit

## Purpose

Evaluate sources that can turn J.League reappearance candidates into source-backed overseas
transfer or overseas-return records.

The current J.League Data Site pipeline can identify players who disappear from observed
J1/J2/J3 appearances and later reappear. That signal is useful for discovery, but it is not
proof of overseas movement.

## Initial Source Candidates

| Source | Expected use | Current assessment |
|---|---|---|
| Wikidata | Career-history hints through `member of sports team` (`P54`) and club country | Good first audit target because it has a query endpoint and reusable identifiers. Coverage and date quality must be checked. |
| Club official profiles | Player career histories and return announcements | High credibility, but scraping and layout vary by club. Better for verification than broad initial collection. |
| JFA/J.League and club announcements | Confirm individual transfers and returns | High credibility, but broad historical search is expensive. |
| Wikipedia | Human-readable career chronology and references | Useful hint source; not enough alone for final labels. |
| Transfermarkt / Soccerway / WorldFootball.net | Structured transfer and club-history hints | Potentially useful, but terms-of-use and redistribution constraints must be checked before automated collection. |
| News articles | Individual transfer evidence | Useful for verification and edge cases; broad collection will be noisy. |

## Wikidata Audit Plan

Start with the 2023-2025 reappearance candidates:

```bash
uv run python scripts/build_reappearance_candidates.py \
  --features data/processed/player_season_features_2014_2025_J1_J2_J3.csv \
  --target-start-season 2023 \
  --target-end-season 2025 \
  --min-gap-seasons 2
```

Then audit Wikidata coverage:

```bash
uv run python scripts/audit_wikidata_reappearance_candidates.py \
  --input data/processed/reappearance_candidates_2023_2025_gap2.csv \
  --limit 20
```

The audit output is local-only and gitignored:

```text
data/interim/source_audit/wikidata_reappearance_candidates.csv
```

## Initial Wikidata Findings

An initial top-20 audit against `reappearance_candidates_2023_2025_gap2.csv` found:

| Metric | Count |
|---|---:|
| Audited reappearance candidates | 20 |
| Candidates with a Wikidata person match | 19 |
| Candidates with at least one foreign-club `P54` team | 6 |
| Candidates without a person match | 1 |

Foreign-club hints were found for:

| Player | Wikidata item | Foreign countries in team history |
|---|---|---|
| 原口 元気 | `Q982163` | ドイツ, ベルギー |
| 奥川 雅也 | `Q18700901` | オーストリア |
| 柴崎 岳 | `Q2011456` | スペイン |
| 中島 翔哉 | `Q7503330` | ポルトガル, アラブ首長国連邦, カタール, トルコ |
| 中山 雄太 | `Q18817905` | オランダ, イギリス |
| 安部 裕葵 | `Q27917453` | スペイン |

`シュミット ダニエル / SCHMIDT Daniel` did not match in the initial exact-label query,
even though this is a likely relevant case. This confirms that Wikidata label matching should
be improved with aliases, birth dates, and/or an item-search fallback before being used as a
broad recall-oriented source.

## Interpretation Rules

- Treat Wikidata matches as candidate evidence, not final labels.
- A foreign club in Wikidata `P54` is evidence that the player likely had an overseas stint,
  but dates and identity must be validated before producing final outcomes.
- Exact label matching can miss players because labels may omit spaces, use different roman
  ordering, or contain aliases instead of labels.
- Exact label matching can also return multiple people for common names, so `source_player_id`,
  birth date, and career chronology still matter.
