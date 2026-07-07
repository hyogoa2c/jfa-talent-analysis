from jfa_talent_analysis.pathway_outcome_analysis import (
    birth_cohort,
    parse_birth_year,
    wilson_confidence_interval,
)


def test_parse_birth_year_handles_slash_format():
    assert parse_birth_year("1995/01/01") == 1995


def test_parse_birth_year_blank_is_none():
    assert parse_birth_year("") is None


def test_birth_cohort_buckets():
    assert birth_cohort(1988) == "<1990"
    assert birth_cohort(1990) == "1990-1994"
    assert birth_cohort(1994) == "1990-1994"
    assert birth_cohort(1995) == "1995-1999"
    assert birth_cohort(2003) == "2000-2004"
    assert birth_cohort(2006) == "2005+"
    assert birth_cohort(None) == "unknown"


def test_wilson_confidence_interval_matches_known_case():
    lower, upper = wilson_confidence_interval(50, 100)
    assert 0.40 < lower < 0.41
    assert 0.59 < upper < 0.60


def test_wilson_confidence_interval_zero_n():
    assert wilson_confidence_interval(0, 0) == (0.0, 0.0)


def test_wilson_confidence_interval_narrows_with_larger_n():
    small_lower, small_upper = wilson_confidence_interval(5, 10)
    large_lower, large_upper = wilson_confidence_interval(500, 1000)
    assert (large_upper - large_lower) < (small_upper - small_lower)
