import numpy as np

from jfa_talent_analysis.gold_design_simulation import (
    Player,
    Scenario,
    draw_sample,
    true_label,
    weighted_confusion,
)


def player(pid, stratum, observed="j_club_academy", prose="", club=""):
    return Player(pid, "era1", observed, stratum, prose, club)


def test_an_error_in_a_disagreement_picks_the_other_candidate():
    # Not "some other pathway": the rule chose one of two named claims, so being
    # wrong means the other one was right.
    p = player("1", "academy_in", observed="j_club_academy", prose="university", club="j_club_academy")
    always_wrong = Scenario("x", {"academy_in": 1.0})
    assert true_label(p, always_wrong, np.random.default_rng(0)) == "university"


def test_no_error_returns_the_observed_label():
    p = player("1", "both_agree")
    assert true_label(p, Scenario("clean"), np.random.default_rng(0)) == "j_club_academy"


def test_censused_strata_carry_weight_one():
    population = [player(str(i), "academy_out") for i in range(5)]
    sampled = draw_sample(population, {("era1", "j_club_academy", "academy_out"): 5},
                          np.random.default_rng(0))
    assert len(sampled) == 5
    assert {weight for _, weight in sampled} == {1.0}


def test_thin_sampling_carries_a_large_weight():
    population = [player(str(i), "both_agree") for i in range(100)]
    sampled = draw_sample(population, {("era1", "j_club_academy", "both_agree"): 10},
                          np.random.default_rng(0))
    assert len(sampled) == 10
    assert {weight for _, weight in sampled} == {10.0}


def test_weights_reconstruct_the_population_shape():
    # 10 of 100 both_agree and all 5 academy_out; the weighted confusion must
    # reflect the population's 100:5 balance, not the sample's 10:5.
    population = [player(str(i), "both_agree") for i in range(100)]
    population += [player(f"a{i}", "academy_out", prose="j_club_academy", club="university")
                   for i in range(5)]
    allocation = {
        ("era1", "j_club_academy", "both_agree"): 10,
        ("era1", "j_club_academy", "academy_out"): 5,
    }
    rng = np.random.default_rng(1)
    sampled = draw_sample(population, allocation, rng)
    total_weight = sum(weight for _, weight in sampled)
    assert total_weight == 105.0


def test_indeterminate_adjudications_leave_the_matrix():
    population = [player(str(i), "both_agree") for i in range(50)]
    sampled = draw_sample(population, {("era1", "j_club_academy", "both_agree"): 50},
                          np.random.default_rng(0))
    _, adjudicated, indeterminate = weighted_confusion(
        sampled, Scenario("clean"), np.random.default_rng(0), "era1"
    )
    assert adjudicated + indeterminate == 50
    assert indeterminate > 0
