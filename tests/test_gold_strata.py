from jfa_talent_analysis.gold_strata import STRATA, stratum


def row(**kwargs):
    base = {
        "source_player_id": "1",
        "pathway_category": "j_club_academy",
        "pathway_category_source": "both_agree",
        "pathway_prose_category": "j_club_academy",
        "pathway_club_list_category": "j_club_academy",
    }
    return {**base, **kwargs}


def test_the_direction_that_empties_the_reference_category_is_its_own_stratum():
    # The composite rule sends these to review, so their final source is
    # human_reviewed -- reading strata off the source buried all 21 of them.
    got = stratum(
        row(
            pathway_prose_category="j_club_academy",
            pathway_club_list_category="university",
            pathway_category="university",
            pathway_category_source="human_reviewed",
        ),
        set(),
    )
    assert got == "academy_out"


def test_entering_the_reference_category_is_a_different_stratum():
    got = stratum(
        row(
            pathway_prose_category="high_school",
            pathway_club_list_category="j_club_academy",
            pathway_category="j_club_academy",
            pathway_category_source="club_list_over_prose",
        ),
        set(),
    )
    assert got == "academy_in"


def test_a_disagreement_not_touching_the_reference_category():
    got = stratum(
        row(
            pathway_prose_category="university",
            pathway_club_list_category="high_school",
            pathway_category="high_school",
        ),
        set(),
    )
    assert got == "disagree_other"


def test_institution_unknown_wins_over_everything():
    # It is the residual uncertainty in the reference category, so it must be
    # sampled as such rather than scattered across other strata.
    got = stratum(row(source_player_id="7"), {"7"})
    assert got == "institution_unknown"


def test_unknown_is_not_a_competing_claim():
    got = stratum(
        row(pathway_prose_category="unknown", pathway_club_list_category="university",
            pathway_category="university"),
        set(),
    )
    assert got == "club_list_only"


def test_agreement_and_single_source_rows():
    assert stratum(row(), set()) == "both_agree"
    assert stratum(
        row(pathway_club_list_category="", pathway_category_source="prose_only"), set()
    ) == "prose_only"


def test_every_stratum_name_is_reachable():
    assert set(STRATA) >= {"academy_out", "academy_in", "institution_unknown", "both_agree"}
