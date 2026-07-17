from jfa_talent_analysis.coach_exposure import (
    impute_stint_years,
    institution_stage,
    role_rank,
    school_year_cohort,
    select_primary_dev_coach,
    year_overlap,
)


def test_institution_stage_classification():
    assert institution_stage("早稲田大学") == "university"
    assert institution_stage("青森山田高等学校") == "high_school"
    assert institution_stage("FC東京U-18") == "j_club_academy"


def test_school_year_cohort_uses_april_fiscal_boundary():
    assert school_year_cohort("2000/05/01") == 2000
    assert school_year_cohort("2000/04/01") == 2000
    # 早生まれ: January-March births belong to the previous school cohort.
    assert school_year_cohort("2001/03/31") == 2000
    assert school_year_cohort("2001-02-15") == 2000


def test_school_year_cohort_unparseable_returns_none():
    assert school_year_cohort("") is None
    assert school_year_cohort("2000") is None
    assert school_year_cohort("unknown/xx") is None


def test_impute_stint_years_matches_recorded_case():
    # 山本英臣 (born 1980/05, cohort 1980) has a RECORDED ジェフ youth stint of
    # exactly 1996-1998 — the imputation must reproduce it.
    cohort = school_year_cohort("1980/05/12")
    assert impute_stint_years("j_club_academy", cohort) == (1996, 1998)


def test_impute_stint_years_stage_ranges():
    assert impute_stint_years("high_school", 2000) == (2016, 2018)
    assert impute_stint_years("university", 2000) == (2019, 2022)


def test_year_overlap_counts_inclusive_years():
    assert year_overlap(2010, 2013, 2012, 2015) == 2  # 2012, 2013
    assert year_overlap(2010, 2013, 2014, 2016) == 0


def test_year_overlap_with_missing_bounds_is_weak_positive():
    assert year_overlap(None, None, 2010, 2012) == 1
    assert year_overlap(2010, None, None, None) == 1


def test_year_overlap_both_open_ended_on_same_side_is_weak_positive():
    # stint 2010- (open end) and tenure 2008- (open end): they overlap from
    # 2010 onward but with no known end, so it's a present-but-unbounded case.
    assert year_overlap(2010, None, 2008, None) == 1
    assert year_overlap(None, 2013, None, 2015) == 1


def test_year_overlap_one_side_open_still_measures():
    # stint 2010- overlapping tenure -2012 brackets a real 2010-2012 window.
    assert year_overlap(2010, None, None, 2012) == 3


def test_role_rank_prefers_head_coach():
    assert role_rank("監督") > role_rank("総監督")
    assert role_rank("監督") > role_rank("ヘッドコーチ")
    assert role_rank("部長") == 0


def exposure(**kw: str) -> dict[str, str]:
    row = {
        "normalized_institution": "早稲田大学",
        "coach_name": "コーチA",
        "role_type": "監督",
        "stint_from_year": "2010",
        "stint_to_year": "2013",
        "tenure_from_year": "2008",
        "tenure_to_year": "2012",
    }
    row.update(kw)
    return row


def test_select_primary_prefers_greater_overlap():
    exposures = [
        exposure(coach_name="長い", tenure_from_year="2010", tenure_to_year="2013"),
        exposure(coach_name="短い", tenure_from_year="2012", tenure_to_year="2013"),
    ]
    primary = select_primary_dev_coach(exposures)
    assert primary is not None
    assert primary.coach_name == "長い"


def test_select_primary_breaks_tie_toward_head_coach():
    exposures = [
        exposure(coach_name="総監督さん", role_type="総監督"),
        exposure(coach_name="監督さん", role_type="監督"),
    ]
    primary = select_primary_dev_coach(exposures)
    assert primary is not None
    assert primary.coach_name == "監督さん"


def test_select_primary_returns_none_when_no_stage_exposure():
    assert select_primary_dev_coach([]) is None
