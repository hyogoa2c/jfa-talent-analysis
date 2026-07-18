from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from jfa_talent_analysis.confirmatory_analysis import (
    BASE_PATHWAY,
    MAIN_PATHWAYS,
    adjusted_pathway_probabilities,
    aggregate_position_mode,
    bootstrap_risk_differences,
    build_analysis_frame,
    final_dev_institution,
    fit_logit,
    odds_ratio_table,
    risk_differences,
)
from jfa_talent_analysis.pathway_multiplicity import build_multipath_rows, stint_stage


def test_aggregate_position_mode_majority_and_tie_break():
    assert aggregate_position_mode(pd.Series(["MF", "MF", "FW"])) == "MF"
    # Tie between DF and FW breaks by the fixed GK->DF->MF->FW order.
    assert aggregate_position_mode(pd.Series(["FW", "DF"])) == "DF"
    assert aggregate_position_mode(pd.Series([np.nan, np.nan])) is None


def test_final_dev_institution_picks_last_youth_row():
    stints = pd.DataFrame(
        {
            "source_player_id": ["1", "1", "1", "1", "2"],
            "line_index": ["1", "2", "3", "4", "1"],
            "institution": [
                "東京ヴェルディジュニアユース",
                "東京ヴェルディユース",
                "東京ヴェルディ",  # 2種登録 formality row
                "流通経済大学サッカー部",
                "青森山田高校",
            ],
            "youth_flag": ["1", "1", "0", "1", "1"],
            "registration_formality": ["0", "0", "1", "0", "0"],
        }
    )
    result = final_dev_institution(stints)
    # Normalization strips サッカー部 and expands 高校 -> 高等学校.
    assert result.loc["1"] == "流通経済大学"
    assert result.loc["2"] == "青森山田高等学校"


def _synthetic_frame(n: int = 3000, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    pathway = rng.choice(MAIN_PATHWAYS, size=n, p=[0.3, 0.2, 0.5])
    birth_year_c = rng.integers(-10, 10, size=n).astype(float)
    logit = -0.2 + 0.05 * birth_year_c - 1.0 * (pathway == "university")
    y = rng.random(n) < 1 / (1 + np.exp(-logit))
    return pd.DataFrame(
        {
            "pathway_category": pathway,
            "birth_year_c": birth_year_c,
            "outcome": y.astype(int),
            "cluster": rng.choice([f"inst{i}" for i in range(40)], size=n),
        }
    )


FORMULA = "outcome ~ C(pathway_category, Treatment('j_club_academy')) + cr(birth_year_c, df=4)"


def test_fit_logit_cluster_and_g_computation_recover_known_effect():
    df = _synthetic_frame()
    fit = fit_logit(df, FORMULA, label="synthetic", cluster_col="cluster")
    assert fit.cov_type == "cluster"
    assert fit.n == len(df)
    assert fit.n_clusters == 40
    table = odds_ratio_table(fit)
    uni_row = table[table["term"].str.contains("university")].iloc[0]
    # True OR is exp(-1.0) ~= 0.37.
    assert 0.25 < uni_row["odds_ratio"] < 0.5

    probabilities = adjusted_pathway_probabilities(fit, df)
    assert set(probabilities) == set(MAIN_PATHWAYS)
    rds = risk_differences(probabilities)
    assert BASE_PATHWAY not in rds
    # University penalty of -1.0 on the logit scale near p~0.45 is a clearly
    # negative risk difference; high_school (no true effect) should be near 0.
    assert rds["university"] < -0.1
    assert abs(rds["high_school"]) < 0.08


def test_fit_logit_raises_on_silent_row_drop():
    # NaN in a cr() spline variable errors inside patsy itself, so exercise the
    # row-drop guard with a spline-free formula where patsy drops silently.
    df = _synthetic_frame(n=500)
    df.loc[df.index[:5], "birth_year_c"] = np.nan
    formula = "outcome ~ C(pathway_category, Treatment('j_club_academy')) + birth_year_c"
    with pytest.raises(ValueError, match="dropped"):
        fit_logit(df, formula, label="bad", cluster_col="cluster")


def test_bootstrap_risk_differences_brackets_point_estimate():
    df = _synthetic_frame(n=1500)
    fit = fit_logit(df, FORMULA, label="synthetic")
    point = risk_differences(adjusted_pathway_probabilities(fit, df))
    ci = bootstrap_risk_differences(df, FORMULA, cluster_col="cluster", n_boot=30, seed=1)
    uni = ci[ci["pathway"] == "university"].iloc[0]
    assert uni["n_boot_ok"] > 0
    assert uni["rd_ci_low"] <= point["university"] <= uni["rd_ci_high"]


def test_build_analysis_frame_derivations():
    outcomes = pd.DataFrame(
        {
            "source_player_id": ["1", "2", "3"],
            "birth_date": ["1995/04/02", "2000/01/15", ""],
            "national_team_categories": ["U17|A", "", "U15"],
            "reached_j1_ever": ["1", "0", "1"],
            "moved_overseas_final": ["1", "", "0"],
            "any_national_team_selection": ["yes", "unclear", "yes"],
            "pathway_category": ["university", "high_school", "jfa_academy"],
            "pathway_category_source": [
                "human_reviewed",
                "auto_high_confidence",
                "identity_not_confirmed",
            ],
            "career_minutes": ["3200", "800", "100"],
        }
    )
    df = build_analysis_frame(outcomes)
    assert df.loc[0, "birth_year_c"] == 0
    assert df.loc[0, "youth_selected"] == 1 and df.loc[0, "a_team_selected"] == 1
    assert df.loc[1, "youth_selected"] == 0
    assert bool(df.loc[1, "overseas_labeled"]) is False
    assert bool(df.loc[1, "nt_labeled"]) is False
    assert list(df["in_main_pathways"]) == [True, True, False]
    assert list(df["minutes_tier"]) == ["A", "B", "C"]
    assert list(df["identified"]) == [1, 1, 0]


def test_stint_stage_classification():
    assert stint_stage("東京ヴェルディジュニアユース") is None
    assert stint_stage("FC東京U-15深川") is None
    assert stint_stage("東京ヴェルディユース") == "j_club_academy"
    assert stint_stage("市立船橋高校") == "high_school"
    assert stint_stage("明治大学サッカー部") == "university"
    assert stint_stage("JFAアカデミー福島") == "jfa_academy"


def test_build_multipath_rows_sequence_and_flags():
    stints = pd.DataFrame(
        {
            "source_player_id": ["1", "1", "1", "2", "2"],
            "line_index": ["1", "2", "3", "1", "2"],
            "institution": [
                "浦和レッズジュニアユース",
                "浦和レッドダイヤモンズユース",
                "明治大学",
                "市立船橋高校",
                "市立船橋高等学校",
            ],
            "youth_flag": ["1", "1", "1", "1", "1"],
            "registration_formality": ["0", "0", "0", "0", "0"],
        }
    )
    rows = build_multipath_rows(stints).set_index("source_player_id")
    assert rows.loc["1", "pathway_sequence"] == "j_club_academy>university"
    assert rows.loc["1", "pathway_count"] == 2
    assert rows.loc["1", "has_j_club_academy"] == 1
    assert rows.loc["1", "has_high_school"] == 0
    # Consecutive same-stage stints collapse: two 高校 rows -> single stage.
    assert rows.loc["2", "pathway_sequence"] == "high_school"
    assert rows.loc["2", "pathway_count"] == 1
