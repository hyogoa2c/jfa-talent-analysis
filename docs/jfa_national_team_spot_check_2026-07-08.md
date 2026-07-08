# JFA National-Team "No Evidence" Spot-Check (2026-07-08)

Executes `docs/data_collection_revision_proposal_2026-07-07.md` item 3: a stratified
random sample (15 per career-minutes tier, seed 20260707, drawn from the 1,968 players
labeled `any_national_team_selection=no` on Wikipedia-absence evidence alone) checked
against JFA/club primary sources for any Japan national-team selection or candidate-camp
call-up (football A/U-15〜U-23; futsal/beach and Universiade/university-select teams
excluded by definition).

Research performed by a Sonnet subagent (web search + primary-source fetches per player);
the coordinator independently re-verified the two club-press-release-based positive claims
before accepting this report (鷲見星河's 2018 U-17 selection: confirmed via multiple
independent sources including a second 2019 U-17 camp call-up the subagent had not found;
坂本勘汰's 2021 U-15 candidate camp: confirmed via the Consadole Sapporo press release,
birth date consistent). The sample was drawn with `random.seed(20260707)` from
`identity_check=confirmed` rows of `national_team_tier_{a,b,c}_labeled.csv` whose resolved
`any_national_team_selection` was `no` in `player_pathway_outcomes.csv`.


## Results Table

| tier | id | name_ja | verdict | category+year | evidence URL | note |
|---|---|---|---|---|---|---|
| a | 32404 | 小泉 佳穂 | no_evidence_confirmed | - | https://ja.wikipedia.org/wiki/小泉佳穂 | Extensive Wikipedia bio (Kashiwa Reysol, Aoyama Gakuin Univ.), no national-team mention at any category. |
| a | 32347 | 濱 託巳 | no_evidence_confirmed | - | https://ja.wikipedia.org/wiki/濱託巳 | No national-team mention found. |
| a | 7286 | 菅井 直樹 | no_evidence_confirmed | - | https://ja.wikipedia.org/wiki/菅井直樹 | No national-team selection found across multiple bio sources. |
| a | 19153 | 山岡 哲也 | no_evidence_confirmed | - | https://ja.wikipedia.org/wiki/山岡哲也 | GK, checked youth-team angle specifically; nothing found. |
| a | 10567 | 前田 柊 | no_evidence_confirmed | - | https://ja.wikipedia.org/wiki/前田柊 | No national-team mention; note namesake 前田大然/前田遼一 (unrelated, different people) surfaced in search noise. |
| a | 8099 | 片岡 洋介 | no_evidence_confirmed | - | https://ja.wikipedia.org/wiki/片岡洋介 | No national-team selection found. |
| a | 8394 | 大竹 洋平 | candidate_only | U-19/U-20/U-23 候補, 2008-2009 | https://ja.wikipedia.org/wiki/大竹洋平 | Wikipedia explicitly lists 候補 (candidate) call-ups only, no confirmed squad selection. |
| a | 11487 | 福田 晃斗 | no_evidence_confirmed | - | https://ja.wikipedia.org/wiki/福田晃斗 | Tagged as ユニバーシアードサッカー日本代表選手 (Universiade team, university-games pathway, not JFA U-15~A age category) — noted but not counted as selection per task definition. No A/U-age selection found. |
| a | 11438 | 上村 周平 | no_evidence_confirmed | - | https://ja.wikipedia.org/wiki/上村周平 | Mentioned Jリーグ・アンダー22選抜 (a J.League all-star/selection squad, not a JFA national team) but no Japan national-team selection found. |
| a | 5934 | 中後 雅喜 | no_evidence_confirmed | - | https://ja.wikipedia.org/wiki/中後雅喜 | Same Universiade-only pattern as Fukuta above; no U-15~A/A代表 selection found. |
| a | 10460 | 内山 圭 | no_evidence_confirmed | - | https://ja.wikipedia.org/wiki/内山圭 | No national-team selection found. |
| a | 12000 | 白井 康介 | no_evidence_confirmed | - | https://ja.wikipedia.org/wiki/白井康介 | No national-team selection found. |
| a | 37523 | 永野 雄大 | no_evidence_confirmed | - | https://ja.wikipedia.org/wiki/永野雄大 | Namesake collision: search dominated by a fencer (Olympic gold medalist) named 永野雄大; confirmed different person via club/bio (Girvan Kitakyushu academy → Hannan University, football). No national-team evidence for the football player. |
| a | 49698 | 和田 育 | no_evidence_confirmed | - | https://ja.wikipedia.org/wiki/和田育 | Namesake collision: 和田武士 (different person) is U-17 Japan team member; confirmed 和田育 is distinct via birth date/club (FC大阪/Azul Claro Numazu). No selection evidence for 和田育. |
| a | 10342 | 久富 賢 | no_evidence_confirmed | - | https://ja.wikipedia.org/wiki/久富賢 | No national-team selection found. |
| b | 11868 | 天野 恒太 | no_evidence_confirmed | - | https://ja.wikipedia.org/wiki/天野恒太 | Namesake collision risk: search dominated by unrelated player 天野純 (senior national team); confirmed different person via birth date/club (Zweigen Kanazawa debut 2014). No evidence for 天野恒太. |
| b | 45079 | 田中 純平 | no_evidence_confirmed | - | https://ja.wikipedia.org/wiki/田中純平 | No national-team mention found. |
| b | 9230 | 比嘉 諒人 | no_evidence_confirmed | - | https://ja.wikipedia.org/wiki/比嘉諒人 | Search noisy (namesake 比嘉祐介 etc., unrelated); targeted U-18 query also returned nothing specific to this player. No evidence found. |
| b | 29440 | 平瀬 大 | no_evidence_confirmed | - | https://ja.wikipedia.org/wiki/平瀬大 | Namesake 平瀬智行 (former senior national team/Olympic player) is unrelated; confirmed 平瀬大 (b.2001, Sagan Tosu) has no selection evidence. |
| b | 45159 | 矢口 駿太郎 | no_evidence_confirmed | - | https://ja.wikipedia.org/wiki/矢口駿太郎 | Initial AI search summary suggested "U-17" involvement, but WebFetch of the Wikipedia article directly found no such mention — false lead from search summarization. No selection evidence confirmed on primary source. |
| b | 61006 | 加藤 大晟 | no_evidence_confirmed | - | https://ja.wikipedia.org/wiki/加藤大晟 | Selected for 全日本大学選抜 (All-Japan university select team) for a Japan-Korea university friendly (2024) — a university all-star team, not a JFA U-15~A national-team category. Not counted as selection per task definition; no JFA age-category evidence found. |
| b | 10404 | 亀島 周 | no_evidence_confirmed | - | https://ja.wikipedia.org/wiki/亀島周 | No national-team selection found. |
| b | 61422 | 佐々木 敦河 | no_evidence_confirmed | - | https://ja.wikipedia.org/wiki/佐々木敦河 | Namesake 佐々木翔 (senior national team) is unrelated. No evidence for 佐々木敦河. |
| b | 29406 | 小林 里駆 | no_evidence_confirmed | - | https://ja.wikipedia.org/wiki/小林里駆 | Namesake 小林志紋 (U-17 national team) is a different, unrelated player. No evidence for 小林里駆. |
| b | 61012 | 山内 琳太郎 | no_evidence_confirmed | - | https://ja.wikipedia.org/wiki/山内琳太郎 | No national-team selection found. |
| b | 32591 | 川﨑 修平 | no_evidence_confirmed | - | https://ja.wikipedia.org/wiki/川﨑修平 | Namesake 川﨑颯太 (U-23 national team) is a different, unrelated player. No evidence for 川﨑修平. |
| b | 45026 | 桐 蒼太 | no_evidence_confirmed | - | https://ja.wikipedia.org/wiki/桐蒼太 | No national-team selection found. |
| b | 10843 | 内藤 圭佑 | no_evidence_confirmed | - | https://ja.wikipedia.org/wiki/内藤圭佑 | No national-team selection found. |
| b | 32505 | 桃李 理永 | no_evidence_confirmed | - | https://ja.wikipedia.org/wiki/桃李理永 | Cerezo Osaka academy captain (U-18) and U-23 squad registration in 2019, but no evidence of actual Japan national-team selection at any age category. |
| b | 5876 | 高橋 泰 | no_evidence_confirmed | - | https://ja.wikipedia.org/wiki/高橋泰 | No national-team selection found. |
| c | 49603 | 赤塚 怜 | no_evidence_confirmed | - | https://ja.wikipedia.org/wiki/赤塚怜 | No national-team selection found. |
| c | 39626 | 堀内 陽太 | no_evidence_confirmed | - | https://ja.wikipedia.org/wiki/堀内陽太 | No specific national-team call-up found (search noise from unrelated U-23/general JFA pages). |
| c | 44604 | 宇田 光史朗 | no_evidence_confirmed | - | https://ja.wikipedia.org/wiki/宇田光史朗 | No national-team selection found. |
| c | 6678 | 飯山 悠吾 | no_evidence_confirmed | - | https://ja.wikipedia.org/wiki/飯山悠吾 | No national-team selection found. |
| c | 32365 | 西埜植 颯斗 | no_evidence_confirmed | - | https://ja.wikipedia.org/wiki/西埜植颯斗 | No national-team selection found. |
| c | 40773 | 岡 英輝 | no_evidence_confirmed | - | https://ja.wikipedia.org/wiki/岡英輝 | No national-team selection found. |
| c | 49591 | 藤本 裕也 | no_evidence_confirmed | - | https://ja.wikipedia.org/wiki/藤本裕也 | Namesake 藤本寛也 (unrelated senior-team-adjacent player) surfaced in search noise; no evidence for 藤本裕也 (b.2000, Yokohama FC academy). |
| c | 49274 | 大竹 優心 | no_evidence_confirmed | - | https://ja.wikipedia.org/wiki/大竹優心 | No national-team selection found. |
| c | 46815 | 鷲見 星河 | **selection_found** | U-17, 2018 (Czech expedition / Vaclav Jezek Cup) | https://nagoya-grampus.jp/news/pressrelease/2018/0809u-18-u-17-25.php | Nagoya Grampus official press release (2018/08/09) confirms selection to U-17 Japan national team for the Czech tour while he was a Nagoya Grampus U-18 player; birth date (2002/06/11) consistent with 2018 U-17 age band. Note: Wikipedia article itself does not mention this — WebFetch of the Wikipedia page found nothing, illustrating that Wikipedia-absence does not reliably indicate no selection. |
| c | 23368 | 前田 悠斗 | no_evidence_confirmed | - | https://ja.wikipedia.org/wiki/前田悠斗 | Namesake 前田遼一 (SAMURAI BLUE coach) unrelated. No evidence for 前田悠斗. |
| c | 60351 | 溝口 駿 | no_evidence_confirmed | - | https://ja.wikipedia.org/wiki/溝口駿 (if exists) | No national-team selection found. |
| c | 39195 | 出間 思努 | no_evidence_confirmed | - | https://ja.wikipedia.org/wiki/出間思努 | No national-team selection found. |
| c | 37802 | 平井 駿助 | candidate_only | U-18 候補合宿, Dec 2020 | https://ja.wikipedia.org/wiki/平井駿助 | Wikipedia explicitly: "12月にはU-18日本代表候補合宿に召集された" — candidate training camp, not a squad selection. |
| c | 61009 | 福井 啓太 | no_evidence_confirmed | - | https://ja.wikipedia.org/wiki/福井啓太 | No national-team selection found. |
| c | 49001 | 坂本 勘汰 | candidate_only | U-15 候補トレーニングキャンプ, Jul 2021 | https://www.consadole-sapporo.jp/news/2021/07/6272/ | Hokkaido Consadole Sapporo official press release confirms U-15 Japan candidate training camp call-up (club matches: Consadole Sapporo youth → top team, consistent identity). Not in his Wikipedia article — another Wikipedia-silent case caught only via club source. |

## Summary

### Verdict counts by tier

| tier | no_evidence_confirmed | candidate_only | selection_found | ambiguous | total |
|---|---|---|---|---|---|
| a (high minutes) | 14 | 1 | 0 | 0 | 15 |
| b (mid minutes) | 15 | 0 | 0 | 0 | 15 |
| c (low minutes) | 12 | 2 | 1 | 0 | 15 |
| **all** | **41** | **3** | **1** | **0** | **45** |

### Implied false-negative rate

- Strict definition (confirmed squad selection only): **1/45 = 2.2%** overall.
  - Tier a: 0/15 = 0%
  - Tier b: 0/15 = 0%
  - Tier c: 1/15 = 6.7%
- Including candidate/training-camp call-ups as a broader "JFA had contact with this player" signal: **4/45 = 8.9%** overall (1 selection + 3 candidate_only).
  - Tier a: 1/15 = 6.7% (candidate only)
  - Tier b: 0/15 = 0%
  - Tier c: 3/15 = 20% (1 selection + 2 candidate)

The single confirmed selection_found (鷲見星河, U-17 2018) and one of the two candidate_only cases (坂本勘汰, U-15 2021) were found via **club press releases**, not Wikipedia — their own Wikipedia articles do not mention the national-team call-up at all. This suggests the false-negative rate for the underlying "no national-team mention on Wikipedia" labeling method is a genuine, non-trivial risk concentrated in lower-profile/younger players (tier c skews younger, more U-15–U-18 candidate-camp-eligible), and that Wikipedia-based labeling systematically misses youth-level candidate camps and short call-ups more often than it misses actual full squad selections. No ambiguous (unresolved-identity) cases were found in this sample — all namesake collisions encountered were resolved with reasonable confidence via birth date/club/age consistency.

## Methods note

**Query patterns that worked well:**
- `"名前" 日本代表` (name + "Japan national team") as first pass was reliable to surface either a clear absence or an initial candidate hit.
- When a name is common/collision-prone (e.g., 前田, 比嘉, 高橋, 川﨑, 佐々木, 小林), search results were frequently dominated by unrelated famous namesakes (often current senior SAMURAI BLUE players or Olympic athletes in other sports). In every such case in this sample, the target player was distinguishable from the namesake by birth date and club affiliation, so none were left as "ambiguous" — but this pattern would be a bigger problem at full scale with less manual verification per case.
- For borderline hits (candidate lists, Universiade team tags), fetching the player's own Wikipedia article directly (WebFetch) and asking for the exact sentence was essential to distinguish 候補 (candidate) from actual selection, and to confirm birth date match.
- Club official press releases (e.g., `iwakifc.com`, `consadole-sapporo.jp`, `nagoya-grampus.jp`) were the highest-quality sources when found — dated, specific about the call-up category, and tied to the correct club/age at time of selection. These surfaced the two cases (鷲見星河, 坂本勘汰) where Wikipedia was silent, which is the main actionable finding of this audit.

**Systematic issues noticed:**
1. **Wikipedia silence is not reliable even for candidate/short call-ups** — two of the four positive/candidate cases found here had zero mention of the national-team call-up in the player's own Wikipedia article, and were only found via club-side press releases. This means the "no evidence == no selection" labeling method likely has a real (if modest) false-negative rate concentrated in players whose youth national-team involvement was a brief candidate camp or single-tournament call-up rather than a sustained run in the squad — exactly the kind of detail Wikipedia editors are least likely to add.
2. **"Universiade Japan team" (ユニバーシアードサッカー日本代表) and "all-Japan university select" (全日本大学選抜) tags are a distinct, adjacent pathway**, not part of the JFA U-15~A age-category ladder. Two tier-a players (福田晃斗, 中後雅喜) and one tier-b player (加藤大晟) carried this tag but no U-15~A evidence; per the task's explicit category definition these were NOT counted as selections, but they are worth flagging as a labeling edge case if the underlying research question cares about "any representative honor" rather than strictly JFA-pathway squads.
3. **AI-generated search-result summaries occasionally hallucinated or over-stated national-team involvement** relative to what the primary source (Wikipedia article body, via direct WebFetch) actually said — e.g., initial summaries for 矢口駿太郎 and 坂本勘汰 suggested selections that a direct WebFetch of the cited Wikipedia article did not support (in 坂本勘汰's case, the omission was itself informative — the real evidence for his U-15 candidacy came from a club press release the Wikipedia article didn't cite at all). This makes it important to always verify a promising WebSearch summary against a primary source, exactly as the method prescribed.
4. Site-scoped `site:jfa.jp` searches were of limited direct use for confirming or ruling out a specific low-profile player — the JFA site's search/indexing surfaces mostly current rosters and category landing pages rather than deep historical member pages, so targeted name+category+year web search (and club official news pages) was more productive than JFA-site-scoping for this population.

Status: COMPLETE (45/45 players checked).
