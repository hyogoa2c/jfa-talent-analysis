from jfa_talent_analysis.gate_a import (
    GoldPair,
    cell_state,
    confusion,
    per_pathway_validity,
    per_pathway_validity_weighted,
    silent_wrong,
    silent_wrong_gap_pp,
    wilson_interval,
)


def pair(gold, label, era="era1", human_reviewed=False, weight=1.0, worksheet_id="W001"):
    return GoldPair(worksheet_id, era, gold, label, human_reviewed, weight)


def test_a_cell_that_is_perfect_but_small_is_undetermined_not_a_pass():
    # The 2026-07-27 run's ten stuck cells were all of this shape: 100% right,
    # and still short of the threshold because n was 9 to 13.
    assert cell_state(9, 9) == "判定不能"
    low, _ = wilson_interval(13, 13)
    assert low < 0.80
    assert cell_state(13, 13) == "判定不能"


def test_a_large_perfect_cell_passes():
    assert cell_state(60, 60) == "合格"


def test_a_large_cell_below_the_threshold_fails():
    assert cell_state(40, 60) == "不合格"


def test_sensitivity_and_ppv_answer_different_questions():
    pairs = [
        pair("j_club_academy", "j_club_academy"),
        pair("j_club_academy", "university"),  # missed academy: costs sensitivity
        pair("high_school", "j_club_academy"),  # wrong academy call: costs PPV
    ]
    validity = per_pathway_validity(pairs)
    assert validity[("era1", "感度", "j_club_academy")] == (1, 2)
    assert validity[("era1", "PPV", "j_club_academy")] == (1, 2)


def test_weighting_moves_the_estimate_toward_the_population():
    # An error drawn from a stratum sampled at 1-in-10 stands for ten players;
    # a correct row drawn with certainty stands for one.
    pairs = [
        pair("j_club_academy", "j_club_academy", weight=1.0),
        pair("j_club_academy", "university", weight=10.0),
    ]
    unweighted = per_pathway_validity(pairs)[("era1", "感度", "j_club_academy")]
    weighted = per_pathway_validity_weighted(pairs)[("era1", "感度", "j_club_academy")]
    assert unweighted == (1, 2)
    assert weighted == (1.0, 11.0)


def test_a_reviewed_row_is_not_silent_even_when_wrong():
    pairs = [
        pair("high_school", "university", human_reviewed=True),
        pair("high_school", "university", human_reviewed=False),
    ]
    assert silent_wrong(pairs) == {"era1": (1, 1)}


def test_the_gap_is_between_the_eras_not_within_one():
    counts = {"era1": (0, 20), "era2": (1, 10)}
    assert silent_wrong_gap_pp(counts) == 10.0
    assert silent_wrong_gap_pp({"era1": (0, 20)}) is None


def test_confusion_counts_gold_against_the_assigned_label():
    pairs = [
        pair("university", "university"),
        pair("university", "j_club_academy"),
        pair("university", "j_club_academy", era="era2"),
    ]
    assert confusion(pairs, "era1") == {
        ("university", "university"): 1,
        ("university", "j_club_academy"): 1,
    }


def test_the_unverified_rows_are_reported_as_a_range_not_ignored():
    from jfa_talent_analysis.gate_a import unverified_sensitivity, wrong_needed_to_trigger

    counts = {"era1": (5, 141), "era2": (7, 145)}
    unverified = {"era1": 36, "era2": 3}
    bounds = unverified_sensitivity(counts, unverified)
    # Assuming the unverifiable rows behave like the verified ones is an
    # assumption, and the worst case is what shows how much it is carrying.
    assert bounds["検証済みと同率"] < 2
    assert bounds["最悪（全部誤り）"] > 15
    # 13 of era1's 36 unverified rows being wrong is enough to fire condition 2.
    assert wrong_needed_to_trigger(counts, unverified, "era1") == 13


def test_no_tipping_point_when_the_unverified_cannot_move_it():
    from jfa_talent_analysis.gate_a import wrong_needed_to_trigger

    counts = {"era1": (5, 141), "era2": (7, 145)}
    assert wrong_needed_to_trigger(counts, {"era1": 0, "era2": 0}, "era1") is None
