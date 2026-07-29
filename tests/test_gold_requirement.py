import numpy as np
import pytest

from jfa_talent_analysis.gold_requirement import (
    MAIN_PATHWAYS,
    EraInputs,
    corrected_risks,
    did,
    exposure_matrix,
    half_width,
    mean_matrix,
    observed_by_outcome,
    simulate,
)


def roundtrip(confusion, counts, risks):
    matrix, true_counts = exposure_matrix(mean_matrix(confusion), counts)
    cases, non_cases = observed_by_outcome(matrix, true_counts, risks)
    return matrix, cases, non_cases, corrected_risks(cases, non_cases, matrix)

PERFECT = {o: {t: (100 if o == t else 0) for t in MAIN_PATHWAYS} for o in MAIN_PATHWAYS}
COUNTS = {"j_club_academy": 200, "high_school": 300, "university": 500}
RISKS = {"j_club_academy": 0.60, "high_school": 0.50, "university": 0.30}


def test_perfect_measurement_leaves_risks_alone():
    _, _, _, corrected = roundtrip(PERFECT, COUNTS, RISKS)
    for pathway in MAIN_PATHWAYS:
        assert corrected[pathway] == pytest.approx(RISKS[pathway], abs=0.01)


def test_correction_recovers_risks_diluted_by_misclassification():
    # A tenth of the observed academy group are really university players, so the
    # observed academy risk is pulled down; correcting with the same matrix that
    # produced it should put it back.
    confusion = {
        "j_club_academy": {"j_club_academy": 90, "high_school": 0, "university": 10},
        "high_school": {"j_club_academy": 0, "high_school": 100, "university": 0},
        "university": {"j_club_academy": 0, "high_school": 0, "university": 100},
    }
    matrix, cases, non_cases, corrected = roundtrip(confusion, COUNTS, RISKS)
    # The observed academy group is diluted by university players, so its raw
    # risk sits below the truth; the correction has to put it back.
    raw = cases[0] / (cases[0] + non_cases[0])
    assert raw < RISKS["j_club_academy"]
    assert corrected["j_club_academy"] == pytest.approx(RISKS["j_club_academy"], abs=0.02)


def test_did_is_the_difference_of_the_two_gaps():
    era1 = {"j_club_academy": 0.60, "high_school": 0.50, "university": 0.30}
    era2 = {"j_club_academy": 0.50, "high_school": 0.45, "university": 0.35}
    # era1 gap -0.30, era2 gap -0.15
    assert did(era1, era2, "university") == pytest.approx(-0.15)


def test_more_gold_narrows_the_correction():
    era = EraInputs(COUNTS, PERFECT, RISKS)
    small = half_width(simulate(era, era, per_cell=10, draws=400))
    large = half_width(simulate(era, era, per_cell=100, draws=400))
    assert large < small


def test_a_wider_risk_gap_needs_more_gold_for_the_same_resolution():
    # Misallocating a player between categories moves the corrected risk in
    # proportion to how different those categories' risks are.
    narrow = {"j_club_academy": 0.50, "high_school": 0.48, "university": 0.45}
    wide = {"j_club_academy": 0.70, "high_school": 0.60, "university": 0.25}
    at = lambda risks: half_width(  # noqa: E731
        simulate(
            EraInputs(COUNTS, PERFECT, risks),
            EraInputs(COUNTS, PERFECT, risks),
            per_cell=20,
            draws=400,
        )
    )
    assert at(wide) > at(narrow)


def test_half_width_is_reported_in_percentage_points():
    values = np.array([-0.02, 0.0, 0.02])
    assert half_width(values) == pytest.approx(1.98, abs=0.1)
