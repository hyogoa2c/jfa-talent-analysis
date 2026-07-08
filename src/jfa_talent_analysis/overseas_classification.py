from __future__ import annotations

import re
from dataclasses import dataclass

# Foreign top-flight/lower-division league names that appear in Japanese
# Wikipedia career prose (real examples from this project's fetched corpus:
# 小林祐希 "エールディヴィジ・SCヘーレンフェーンへ完全移籍", 伊藤遼哉
# "レギオナルリーガ・ノルト…のSSVイェッデローに加入", 田村亮介 "Kリーグ2
# （韓国2部）のFC安養に完全移籍"). Deliberately excludes competition names that
# also host J.League clubs (ACL etc.).
FOREIGN_LEAGUE_VOCAB = (
    "エールディヴィジ",
    "エールステ・ディヴィジ",
    "ブンデスリーガ",
    "レギオナルリーガ",
    "バイエルンリーガ",
    "オーバーリーガ",
    "プレミアリーグ",  # イングランド; Jリーグに同名なし
    "EFLチャンピオンシップ",
    "ラ・リーガ",
    "リーガ・エスパニョーラ",
    "セグンダ・ディビシオン",
    "セグンダ・ジヴィゾン",
    "プリメイラ・リーガ",
    "セリエA",
    "セリエB",
    "セリエC",
    "セリエD",
    "リーグ・アン",
    "リーグ・ドゥ",
    "ジュピラー・プロ・リーグ",
    "ジュピラーリーグ",
    "スュペル・リグ",
    "スーペルリーガ",
    "エクストラクラサ",
    "スコティッシュ",
    "Kリーグ",
    "中国スーパーリーグ",
    "中国甲級リーグ",
    "タイ・リーグ",
    "タイ・プレミアリーグ",
    "Vリーグ1",
    "V.リーグ1",
    "Aリーグ",
    "MLS",
    "メジャーリーグサッカー",
    "USL",
    "カタール・スターズリーグ",
    "サウジ・プロフェッショナルリーグ",
    "UAEプロリーグ",
    "シンガポールプレミアリーグ",
    "Sリーグ",
    "マレーシア・スーパーリーグ",
    "インドネシア・リーガ1",
    "リーガ・プリメーラ",
    "スイス・スーパーリーグ",
    "スイス・チャレンジリーグ",
)

COUNTRY_NAMES = (
    "ドイツ|オランダ|ベルギー|スペイン|イタリア|フランス|イングランド|スコットランド|ウェールズ|"
    "ポルトガル|オーストリア|スイス|クロアチア|セルビア|モンテネグロ|スロベニア|スロバキア|チェコ|"
    "ポーランド|ハンガリー|ルーマニア|ブルガリア|ギリシャ|トルコ|デンマーク|ノルウェー|スウェーデン|"
    "フィンランド|アイスランド|エストニア|ラトビア|リトアニア|マルタ|キプロス|アルバニア|"
    "北マケドニア|ボスニア|ウクライナ|ロシア|ベラルーシ|モルドバ|ジョージア|アルメニア|"
    "アゼルバイジャン|カザフスタン|韓国|中国|タイ|ベトナム|インドネシア|マレーシア|シンガポール|"
    "ミャンマー|カンボジア|ラオス|フィリピン|香港|マカオ|台湾|インド|バングラデシュ|モンゴル|"
    "オーストラリア|ニュージーランド|アメリカ|カナダ|メキシコ|ブラジル|アルゼンチン|チリ|ウルグアイ|"
    "パラグアイ|コロンビア|ペルー|エクアドル|ボリビア|カタール|サウジアラビア|UAE|バーレーン|"
    "オマーン|クウェート|ヨルダン|イラク|イラン|イスラエル|エジプト|モロッコ|チュニジア|南アフリカ"
)

MOVE_VERBS = r"完全移籍|期限付き移籍|レンタル移籍|移籍|加入|入団|契約"

# Country + division ("韓国2部", "ドイツ4部に相当する", "ポルトガルの3部リーグ",
# "モンテネグロ1部リーグ") — the highest-precision foreign-move indicator found
# in the corpus.
COUNTRY_DIVISION_RE = re.compile(rf"(?:{COUNTRY_NAMES})の?\d部")
# Country + の + club + move verb ("デンマークのFCコペンハーゲンへ完全移籍").
COUNTRY_CLUB_MOVE_RE = re.compile(rf"(?:{COUNTRY_NAMES})の[^。\n]{{1,40}}?(?:へ|に)(?:{MOVE_VERBS})")
FOREIGN_LEAGUE_RE = re.compile("|".join(re.escape(name) for name in FOREIGN_LEAGUE_VOCAB))
MOVE_VERB_RE = re.compile(MOVE_VERBS)
# The (?<!の) guard excludes possessive references to SOMEONE ELSE's move
# ("伊藤敦樹の海外移籍により…キャプテンに就任", found in 西川周作's bio) while
# keeping the player's own phrasing ("海外再挑戦を目的に契約解除", 伊藤遼哉).
GENERIC_OVERSEAS_RE = re.compile(r"(?<!の)海外(?:初|再)?(?:移籍|挑戦)|(?<!の)欧州挑戦")
# Weak: bare country name + move verb in one sentence, for club names that embed
# the country ("アルビレックス新潟シンガポールに完全移籍") or phrasing outside
# the stronger patterns. Low precision on its own -> needs_review.
COUNTRY_MOVE_WEAK_RE = re.compile(rf"(?:{COUNTRY_NAMES})")

# Guard patterns: sentences these match are NOT evidence of the player's own
# senior-career foreign move (all real corpus cases):
#   風間宏希 "父の移籍に伴いドイツへ渡り" (a parent's job move)
#   加藤竜二 "ブラジルへ短期留学" (short training stint, not a transfer)
#   伊藤遼哉 "スイスに移住し、FCチューリッヒ…のユースチームでプレー" (childhood)
GUARD_RE = re.compile(r"父|母|親|家族|留学|移住|生まれ")
YOUTH_GUARD_RE = re.compile(r"ユース|Jr\.?ユース|ジュニア|下部組織|U-?1[0-8]|中学|小学|幼")
# Offer-only / fell-through / trial language: a foreign-club mention that did
# not result in an actual stint ("FCメスの入団テストを受験するも不合格",
# 林彰洋's bio) — signal sentence needs a human read.
RETRACTED_RE = re.compile(r"断|破談|見送|白紙|オファーを受けたが|残留|不合格|入団テスト|練習参加")

SENTENCE_SPLIT_RE = re.compile(r"[。\n]")

OVERSEAS_LABEL_COLUMNS = [
    "source_player_id",
    "name_ja",
    "name_en",
    "wikipedia_title",
    "moved_overseas_wiki",
    "overseas_confidence",
    "overseas_evidence",
    "overseas_reason",
]


@dataclass(frozen=True)
class OverseasClassification:
    moved_overseas: str  # "yes" / "no"
    confidence: str  # "high" or "needs_review"
    evidence: str  # first matching sentence (trimmed), for reviewer context
    reason: str


def classify_overseas_stint(text: str) -> OverseasClassification:
    """Detect evidence of a senior-career foreign-club stint in Wikipedia prose.

    "no" means no evidence found in the text — the same absence-of-evidence
    caveat as the national-team classifier, not proof of a domestic-only career.
    Youth-era foreign academies (a pathway trait, not a career outcome) and
    non-transfer stays (留学/family relocation) are excluded by guard patterns.
    """
    strong_evidence: list[str] = []
    weak_evidence: list[str] = []
    retracted = False

    for sentence in SENTENCE_SPLIT_RE.split(text):
        if not sentence.strip():
            continue
        if GUARD_RE.search(sentence) or YOUTH_GUARD_RE.search(sentence):
            continue

        strong = (
            COUNTRY_DIVISION_RE.search(sentence)
            or COUNTRY_CLUB_MOVE_RE.search(sentence)
            or (FOREIGN_LEAGUE_RE.search(sentence) and MOVE_VERB_RE.search(sentence))
            or GENERIC_OVERSEAS_RE.search(sentence)
        )
        weak = COUNTRY_MOVE_WEAK_RE.search(sentence) and MOVE_VERB_RE.search(sentence)

        if strong:
            if RETRACTED_RE.search(sentence):
                retracted = True
            strong_evidence.append(sentence.strip())
        elif weak:
            weak_evidence.append(sentence.strip())

    if strong_evidence:
        return OverseasClassification(
            moved_overseas="yes",
            confidence="needs_review" if retracted else "high",
            evidence=strong_evidence[0][:200],
            reason="retracted_language_present" if retracted else "strong_foreign_move_signal",
        )
    if weak_evidence:
        return OverseasClassification(
            moved_overseas="yes",
            confidence="needs_review",
            evidence=weak_evidence[0][:200],
            reason="weak_country_move_signal_only",
        )
    return OverseasClassification(
        moved_overseas="no",
        confidence="high",
        evidence="",
        reason="no_foreign_move_signal",
    )
