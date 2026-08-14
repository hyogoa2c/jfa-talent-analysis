import numpy as np
import pandas as pd
import pytest

from jfa_talent_analysis import measurement_robustness as mr
from jfa_talent_analysis import phase1b_confirmatory as pc


def synthetic(n_per_cell=1500, era1_gap=-0.30, era2_gap=-0.10, seed=7):
    """A sample whose era gaps are known, so the estimator can be checked.

    era1 has a 30pp university penalty, era2 a 10pp one, so the DID for
    university is +20pp by construction.
    """
    rng = np.random.default_rng(seed)
    rows = []
    base = {"era1": 0.55, "era2": 0.60}
    for era in ("era1", "era2"):
        gap = era1_gap if era == "era1" else era2_gap
        for pathway in pc.MAIN_PATHWAYS:
            risk = base[era] + (0.0 if pathway == "j_club_academy" else gap)
            for _ in range(n_per_cell):
                rows.append(
                    {
                        "source_player_id": str(len(rows)),
                        "eligible_confirmatory": "1",
                        "era": era,
                        "pathway_category": pathway,
                        "birth_year": rng.integers(1985, 1999),
                        "reached_j1_by_age25": rng.binomial(1, risk),
                    }
                )
    return pc.build_frame(pd.DataFrame(rows))


def test_build_frame_keeps_only_the_confirmatory_sample():
    raw = pd.DataFrame(
        {
            "source_player_id": ["1", "2", "3", "4"],
            "eligible_confirmatory": ["1", "0", "1", "1"],
            "era": ["era1", "era1", "era3", "era2"],
            "pathway_category": ["university", "university", "university", "jfa_academy"],
            "birth_year": [1990, 1990, 2001, 1996],
            "reached_j1_by_age25": [1, 1, 1, 0],
        }
    )
    frame = pc.build_frame(raw)
    assert frame["source_player_id"].tolist() == ["1"]


def test_within_era_centring_is_per_era():
    raw = pd.DataFrame(
        {
            "source_player_id": list("abcd"),
            "eligible_confirmatory": ["1"] * 4,
            "era": ["era1", "era1", "era2", "era2"],
            "pathway_category": ["university"] * 4,
            "birth_year": [1984, 1988, 1996, 2000],
            "reached_j1_by_age25": [0, 1, 0, 1],
        }
    )
    frame = pc.build_frame(raw)
    # Each era is centred on its own median, not on the pooled one.
    assert frame["within_era_birth_year"].tolist() == [-2.0, 2.0, -2.0, 2.0]


def test_g_computation_reproduces_the_observed_cell_risks():
    # With the pathway x era interaction in the model, the standardised risk for
    # a cell is that cell's own rate: the check that the machinery is wired to
    # the data and not to the intercept.
    frame = synthetic(n_per_cell=400)
    formula = pc.specs("cr(birth_year, knots=[1990.0])")[0].formula()
    risks = pc.standardized_risks(frame, formula).set_index(["era", "pathway"])["risk"]
    observed = frame.groupby(["era", "pathway_category"])["reached_j1_by_age25"].mean()
    for (era, pathway), value in risks.items():
        assert value == pytest.approx(float(observed[(era, pathway)]), abs=0.02)


def test_the_did_recovers_a_gap_that_was_built_in():
    frame = synthetic()
    formula = pc.specs("cr(birth_year, knots=[1990.0])")[0].formula()
    _, differences, values = pc.point_estimates(frame, formula)
    # university: era1 -30pp, era2 -10pp by construction, so DID is about +20pp.
    assert values["university"] == pytest.approx(0.20, abs=0.06)
    era1 = differences[(differences["era"] == "era1") & (differences["pathway"] == "university")]
    assert float(era1["risk_difference"].iloc[0]) == pytest.approx(-0.30, abs=0.06)


def test_the_joint_test_sees_an_interaction_that_is_there_and_not_one_that_is_not():
    with_interaction = pc.joint_interaction_test(synthetic(), pc.specs("cr(birth_year, knots=[1990.0])")[0])
    assert with_interaction["df"] == 2  # two contrasts x one era comparison
    assert with_interaction["p_value"] < 0.001

    flat = synthetic(n_per_cell=800, era1_gap=-0.20, era2_gap=-0.20, seed=11)
    without = pc.joint_interaction_test(flat, pc.specs("cr(birth_year, knots=[1990.0])")[0])
    assert without["p_value"] > 0.05


def test_the_bootstrap_interval_brackets_the_point_estimate():
    frame = synthetic(n_per_cell=400)
    formula = pc.specs("cr(birth_year, knots=[1990.0])")[0].formula()
    _, _, values = pc.point_estimates(frame, formula)
    interval = pc.bootstrap_did(frame, formula, n_boot=40, seed=1).set_index("pathway")
    low = float(interval.loc["university", "did_ci_low"])
    high = float(interval.loc["university", "did_ci_high"])
    assert low <= values["university"] <= high
    assert int(interval.loc["university", "n_boot_ok"]) > 30


def test_quintile_knots_are_the_five_year_quantiles():
    years = pd.Series(range(1980, 2000))
    knots = pc.quintile_knots(years)
    assert len(knots) == 4
    assert knots == sorted(knots)


def test_a_perfect_gold_matrix_leaves_the_labels_alone():
    pairs = pd.DataFrame(
        [
            {"era": "era1", "gold": p, "label": p, "weight": 1.0}
            for p in pc.MAIN_PATHWAYS
            for _ in range(100)
        ]
    )
    counts = mr.true_given_observed(pairs, "era1")
    rng = np.random.default_rng(0)
    matrices = {"era1": mr._draw_matrix(counts, rng), "era2": mr._draw_matrix(counts, rng)}
    frame = synthetic(n_per_cell=200)
    redrawn = mr._reassign(frame, matrices, rng)
    agreement = (redrawn["pathway_category"] == frame["pathway_category"]).mean()
    assert agreement > 0.95


def test_weighted_gold_counts_keep_the_verified_sample_size():
    pairs = pd.DataFrame(
        [
            {"era": "era1", "gold": "university", "label": "university", "weight": 10.0},
            {"era": "era1", "gold": "high_school", "label": "university", "weight": 1.0},
        ]
    )
    counts = mr.true_given_observed(pairs, "era1")
    # Two rows verified, so the Dirichlet gets two counts' worth of confidence,
    # while the weights still decide how the mass splits between the truths.
    assert sum(counts["university"].values()) == pytest.approx(2.0)
    assert counts["university"]["university"] > counts["university"]["high_school"]


def test_stressing_only_the_academy_direction_touches_only_that_column():
    counts = {
        "university": {"university": 90.0, "j_club_academy": 5.0, "high_school": 5.0},
        "high_school": {"high_school": 90.0, "j_club_academy": 5.0, "university": 5.0},
        "j_club_academy": {"j_club_academy": 95.0, "university": 3.0, "high_school": 2.0},
    }
    stressed = mr._stress_into_academy(counts, 2.0)
    assert stressed["university"]["j_club_academy"] == 10.0
    assert stressed["university"]["high_school"] == 5.0
    assert stressed["j_club_academy"] == counts["j_club_academy"]


def test_stopping_conditions_flag_a_sign_flip_and_a_large_shift():
    main = {"university": 0.20, "high_school": 0.10}
    scenarios = [
        mr.ScenarioResult("S1", "", {"university": 0.19, "high_school": 0.09}, {}, {}, 100),
        mr.ScenarioResult("S3", "", {"university": -0.02, "high_school": 0.11}, {}, {}, 100),
    ]
    table = mr.stopping_conditions(main, scenarios).set_index("pathway")
    assert "S3" in table.loc["university", "条件1_符号反転"]
    assert "S3" in table.loc["university", "条件2_差が許容差以上"]
    assert table.loc["high_school", "条件1_符号反転"] == "なし"
