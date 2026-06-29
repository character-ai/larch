"""Tests for shared self-review tally expansion."""

from __future__ import annotations

from larch.review.self_review_tally import self_review_tally_items


def _ids(data: object) -> list[str]:
    return [item.finding_id for item in self_review_tally_items(data)]


def test_self_review_tally_expands_exact_ids_in_order() -> None:
    items = self_review_tally_items(
        {"mode": "self-review", "accepted_count": 2, "rejected_count": 1}
    )

    assert [item.finding_id for item in items] == [
        "SELF_REVIEW_ACCEPTED_1",
        "SELF_REVIEW_ACCEPTED_2",
        "SELF_REVIEW_REJECTED_1",
    ]
    assert [item.outcome for item in items] == ["accepted", "accepted", "rejected"]
    assert [item.index for item in items] == [1, 2, 1]


def test_self_review_tally_ignores_non_dict_or_non_self_review() -> None:
    assert not self_review_tally_items(None)
    assert not self_review_tally_items(["self-review"])
    assert not self_review_tally_items({"mode": "code-review", "accepted_count": 1})


def test_self_review_tally_coerces_counts_independently() -> None:
    assert _ids({"mode": "self-review", "accepted_count": "bad", "rejected_count": 2}) == [
        "SELF_REVIEW_REJECTED_1",
        "SELF_REVIEW_REJECTED_2",
    ]


def test_self_review_tally_invalid_missing_and_negative_counts_emit_no_side_rows() -> None:
    assert _ids({"mode": "self-review", "accepted_count": -1, "rejected_count": 1}) == [
        "SELF_REVIEW_REJECTED_1"
    ]
    assert _ids({"mode": "self-review", "accepted_count": 1}) == ["SELF_REVIEW_ACCEPTED_1"]
    assert _ids({"mode": "self-review", "accepted_count": object(), "rejected_count": {}}) == []


def test_self_review_tally_matches_int_str_parity_cases() -> None:
    assert _ids({"mode": "self-review", "accepted_count": True, "rejected_count": False}) == []
    assert _ids({"mode": "self-review", "accepted_count": 1.0, "rejected_count": 2.0}) == []
    assert _ids({"mode": "self-review", "accepted_count": " 2 ", "rejected_count": "\t1\n"}) == [
        "SELF_REVIEW_ACCEPTED_1",
        "SELF_REVIEW_ACCEPTED_2",
        "SELF_REVIEW_REJECTED_1",
    ]
