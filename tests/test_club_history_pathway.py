from jfa_talent_analysis.club_history_pathway import (
    classify_institution,
    derive_pathway,
    first_pro_index,
)


def stint(index: int, institution: str, from_year: str = "", formality: str = "0") -> dict[str, str]:
    return {
        "line_index": str(index),
        "institution": institution,
        "from_year": from_year,
        "registration_formality": formality,
    }


def test_classify_institution_reads_affiliated_high_school_as_high_school():
    """A university-affiliated high school carries 大学 in its name; the
    university test must not win (prose-classifier mechanism A)."""
    assert classify_institution("流通経済大学付属柏高等学校") == "high_school"
    assert classify_institution("日本大学") == "university"


def test_derive_pathway_takes_the_stage_before_the_pro_entry():
    """Nakamachi's shape: high school -> pro -> university. Reading the list in
    order is what keeps the post-pro university out of the exposure."""
    result = derive_pathway(
        [
            stint(0, "群馬県立高崎高等学校"),
            stint(1, "湘南ベルマーレ", "2004"),
            stint(2, "慶應義塾大学", "2008"),
        ],
        birth_year=1985,
    )
    assert result.pathway_category == "high_school"
    assert result.confidence == "high"


def test_derive_pathway_keeps_a_university_that_precedes_the_pro_entry():
    result = derive_pathway(
        [
            stint(0, "松陽高校", "2004"),
            stint(1, "福岡教育大学", "2007"),
            stint(2, "ホンダロックSC", "2011"),
        ],
        birth_year=1988,
    )
    assert result.pathway_category == "university"


def test_registration_formality_is_not_a_pro_entry():
    """2種登録 / 特別指定 are pro-club registrations held during the youth
    years; treating one as the pro entry would cut the career too early."""
    stints = [
        stint(0, "ジェフユナイテッド市原・千葉", "2011", formality="1"),
        stint(1, "中京大学", "2011"),
        stint(2, "ジュビロ磐田", "2015"),
    ]
    assert first_pro_index(stints, birth_year=1992) == 2
    assert derive_pathway(stints, birth_year=1992).pathway_category == "university"


def test_childhood_club_with_a_year_is_not_a_pro_entry():
    """A club joined at age 7 carries a from_year but cannot be a pro contract."""
    stints = [stint(0, "ゴールデンキッカーズ", "1999"), stint(1, "名古屋グランパス", "2012")]
    assert first_pro_index(stints, birth_year=1992) == 1


def test_no_development_stage_returns_blank_not_a_guess():
    """Absence of evidence must not become high_school."""
    result = derive_pathway([stint(0, "ヴィッセル神戸", "2000")], birth_year=1980)
    assert result.pathway_category == ""
    assert result.confidence == "no_data"


def test_unidentifiable_pro_entry_is_routed_to_review():
    """With no year anywhere the ordering still gives a candidate, but it is not
    trustworthy enough to auto-assign."""
    result = derive_pathway([stint(0, "奈良育英高等学校"), stint(1, "ヴィッセル神戸")], birth_year=1980)
    assert result.pathway_category == "high_school"
    assert result.confidence == "needs_review"


def test_empty_history_is_no_data():
    assert derive_pathway([], birth_year=1990).confidence == "no_data"
