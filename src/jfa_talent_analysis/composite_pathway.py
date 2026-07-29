"""The composite exposure rule fixed in SAP §1b-3.

Two procedures now measure `pathway_category`: the prose classifier reading
来歴-style sections, and the derivation over the `所属クラブ` career list. This
module is the single place that decides what the final label is when they are
combined with human review, because the external review
(`docs/review_results_phase1b_sap_v3.md`) found that validating the club-list
derivation *alone* does not validate the rule the analysis actually uses.

Two properties the review demanded, both enforced here rather than by callers:

1. A row needing review is never adopted automatically. `needs_review` from
   either procedure, and the academy-losing disagreement direction, all resolve
   to NEEDS_REVIEW and stay there until a human adjudicates.
2. The source of every label is recorded, so per-source validity can be
   reported and the rule can be re-estimated per stratum.
"""

from __future__ import annotations

from dataclasses import dataclass

MAIN_PATHWAYS = ("j_club_academy", "high_school", "university")

# Sources, in the vocabulary SAP §1b-3 and Gate A reporting use.
HUMAN_REVIEWED = "human_reviewed"
BOTH_AGREE = "both_agree"
CLUB_LIST_OVER_PROSE = "club_list_over_prose"
CLUB_LIST_ONLY = "club_list_only"
PROSE_ONLY = "prose_only"
NEEDS_REVIEW = "needs_review"
IDENTITY_NOT_CONFIRMED = "identity_not_confirmed"


@dataclass(frozen=True)
class CompositeLabel:
    category: str
    source: str
    reason: str

    @property
    def awaits_review(self) -> bool:
        return self.source == NEEDS_REVIEW


def loses_reference_category(prose: str, club: str) -> bool:
    """Does this disagreement move a player out of the reference category?

    j_club_academy is the reference, so a disagreement that takes a player out
    of it changes the baseline risk the interaction is measured against. SAP
    §1b-3 routes this direction to review instead of letting the club list win
    by default: it is the minority direction (era1 15, era2 7) and the one the
    review singled out as unreproducible under symmetric misclassification.
    """
    return prose == "j_club_academy" and club in ("university", "high_school")


def resolve_composite_pathway(
    *,
    prose_category: str,
    prose_confidence: str,
    club_category: str,
    club_confidence: str,
    reviewed_category: str = "",
    in_review_queue: bool = False,
    review_saw_club_list: bool = False,
    identity_confirmed: bool = True,
) -> CompositeLabel:
    """Resolve one player's final pathway label and its source.

    reviewed_category is the adjudicated value; blank *while* in_review_queue
    means "confirmed as-is", which is only meaningful once a human has been
    through the file (the distinction that left 43 rows unadjudicated before).
    """
    if not identity_confirmed:
        return CompositeLabel("", IDENTITY_NOT_CONFIRMED, "identity_not_confirmed")

    if in_review_queue:
        if reviewed_category == "unknown" and club_category and not review_saw_club_list:
            # "unknown" is not a verdict about the pathway, it is a verdict about
            # the evidence available at the time -- and the career list was out
            # of scope then, which is the reason reviewers gave for these rows.
            # A new source with a label makes the verdict stale, not wrong.
            #
            # Once a reviewer has ruled *with* the career list in front of them,
            # "unknown" is a real finding (a pathway outside the category scheme,
            # say) and must stick, or the row reopens on every rebuild.
            return CompositeLabel("", NEEDS_REVIEW, "club_list_answers_confirmed_unknown")
        if reviewed_category:
            return CompositeLabel(reviewed_category, HUMAN_REVIEWED, "adjudicated")
        # A blank reviewed column means "confirmed as-is", and what the reviewer
        # confirmed was the value in front of them -- the prose label. It cannot
        # be reused to confirm the club list, which they never saw: that would
        # relabel 129 unknowns and 38 disagreements with no human in the loop.
        # A contradicting club list is therefore a *new* disagreement, and goes
        # back to review rather than being resolved either way.
        if club_category and club_category != prose_category:
            return CompositeLabel("", NEEDS_REVIEW, "club_list_contradicts_confirmed_review")
        return CompositeLabel(prose_category, HUMAN_REVIEWED, "confirmed_as_is")

    prose = prose_category if prose_category != "unknown" else ""
    club = club_category

    # Either procedure flagging the row blocks automatic adoption.
    if prose and prose_confidence == "needs_review":
        return CompositeLabel("", NEEDS_REVIEW, "prose_needs_review")
    if club and club_confidence == "needs_review":
        return CompositeLabel("", NEEDS_REVIEW, f"club_{club_confidence}")

    if prose and club:
        if prose == club:
            return CompositeLabel(club, BOTH_AGREE, "both_agree")
        if loses_reference_category(prose, club):
            return CompositeLabel("", NEEDS_REVIEW, "academy_loses_to_club_list")
        return CompositeLabel(club, CLUB_LIST_OVER_PROSE, f"club_list_over_{prose}")
    if club:
        return CompositeLabel(club, CLUB_LIST_ONLY, "club_list_only")
    if prose:
        return CompositeLabel(prose, PROSE_ONLY, "prose_only")
    return CompositeLabel("unknown", PROSE_ONLY, "no_evidence")
