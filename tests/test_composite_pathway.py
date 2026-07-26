from jfa_talent_analysis.composite_pathway import (
    BOTH_AGREE,
    CLUB_LIST_ONLY,
    CLUB_LIST_OVER_PROSE,
    HUMAN_REVIEWED,
    IDENTITY_NOT_CONFIRMED,
    NEEDS_REVIEW,
    PROSE_ONLY,
    resolve_composite_pathway,
)


def resolve(**kwargs):
    base = {
        "prose_category": "",
        "prose_confidence": "high",
        "club_category": "",
        "club_confidence": "high",
    }
    return resolve_composite_pathway(**{**base, **kwargs})


def test_agreement_is_recorded_as_such():
    got = resolve(prose_category="university", club_category="university")
    assert (got.category, got.source) == ("university", BOTH_AGREE)


def test_club_list_wins_a_plain_disagreement():
    # Nakamachi type: prose reads the post-professional university as the pathway.
    got = resolve(prose_category="university", club_category="high_school")
    assert (got.category, got.source) == ("high_school", CLUB_LIST_OVER_PROSE)


def test_losing_the_reference_category_goes_to_review_instead():
    got = resolve(prose_category="j_club_academy", club_category="university")
    assert got.source == NEEDS_REVIEW
    assert got.category == ""
    assert got.awaits_review


def test_gaining_the_reference_category_does_not_go_to_review():
    # The majority direction is left to the club list; only the direction that
    # empties the reference group is held back.
    got = resolve(prose_category="high_school", club_category="j_club_academy")
    assert (got.category, got.source) == ("j_club_academy", CLUB_LIST_OVER_PROSE)


def test_club_list_recovers_an_unknown():
    got = resolve(prose_category="unknown", club_category="university")
    assert (got.category, got.source) == ("university", CLUB_LIST_ONLY)


def test_prose_survives_when_the_club_list_is_silent():
    got = resolve(prose_category="high_school")
    assert (got.category, got.source) == ("high_school", PROSE_ONLY)


def test_neither_procedure_yields_unknown():
    assert resolve().category == "unknown"


def test_needs_review_is_never_adopted_automatically():
    # Whichever procedure flags it, the row must not acquire a label on its own.
    from_prose = resolve(
        prose_category="university", prose_confidence="needs_review", club_category="university"
    )
    from_club = resolve(
        prose_category="university", club_category="university", club_confidence="needs_review"
    )
    assert from_prose.source == NEEDS_REVIEW
    assert from_club.source == NEEDS_REVIEW
    assert from_prose.category == from_club.category == ""


def test_adjudicated_value_wins_over_both_procedures():
    got = resolve(
        prose_category="university",
        club_category="high_school",
        reviewed_category="j_club_academy",
        in_review_queue=True,
    )
    assert (got.category, got.source) == ("j_club_academy", HUMAN_REVIEWED)


def test_blank_review_confirms_what_the_reviewer_actually_saw():
    got = resolve(
        prose_category="university",
        club_category="university",
        reviewed_category="",
        in_review_queue=True,
    )
    assert (got.category, got.source) == ("university", HUMAN_REVIEWED)


def test_a_club_list_contradicting_a_confirmed_review_returns_to_review():
    # The reviewer confirmed the prose value without seeing the club list, so
    # neither value has been adjudicated against the other.
    got = resolve(
        prose_category="university",
        club_category="high_school",
        reviewed_category="",
        in_review_queue=True,
    )
    assert (got.category, got.source) == ("", NEEDS_REVIEW)


def test_a_confirmed_unknown_is_not_silently_filled_by_the_club_list():
    got = resolve(
        prose_category="unknown",
        club_category="university",
        reviewed_category="",
        in_review_queue=True,
    )
    assert got.source == NEEDS_REVIEW


def test_unconfirmed_identity_never_produces_a_label():
    got = resolve(
        prose_category="university", club_category="university", identity_confirmed=False
    )
    assert (got.category, got.source) == ("", IDENTITY_NOT_CONFIRMED)


def test_a_confirmed_unknown_is_stale_once_the_club_list_has_a_label():
    # "unknown" was a verdict about the evidence then available, and the career
    # list was out of scope at the time -- the reason reviewers themselves gave.
    got = resolve(
        prose_category="unknown",
        club_category="university",
        reviewed_category="unknown",
        in_review_queue=True,
    )
    assert (got.category, got.source) == ("", NEEDS_REVIEW)


def test_a_confirmed_unknown_stands_when_the_club_list_is_also_silent():
    got = resolve(
        prose_category="unknown",
        club_category="",
        reviewed_category="unknown",
        in_review_queue=True,
    )
    assert (got.category, got.source) == ("unknown", HUMAN_REVIEWED)
