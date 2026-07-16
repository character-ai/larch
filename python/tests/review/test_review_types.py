from __future__ import annotations

from larch.review.review_types import (
    FINDING_SCOPE_SET,
    FINDING_SCOPE_VALUES,
    FOCUS_AREA_SET,
    FOCUS_AREA_VALUES,
    FindingScope,
    FocusArea,
    count_non_security_blocks,
    finding_dedup_key,
    is_canonical_heading,
    is_oos_eligible_block,
    is_security_block_text,
    parse_blocks,
    parse_canonical_heading,
    parse_findings_text,
    render_wire_values,
)


def test_review_taxonomy_has_ordered_immutable_wire_projections() -> None:
    assert tuple(FocusArea) == (
        FocusArea.code_quality,
        FocusArea.risk_integration,
        FocusArea.correctness,
        FocusArea.architecture,
        FocusArea.security,
    )
    assert tuple(area.value for area in FocusArea) == FOCUS_AREA_VALUES
    assert frozenset(FOCUS_AREA_VALUES) == FOCUS_AREA_SET
    assert tuple(scope.value for scope in FindingScope) == FINDING_SCOPE_VALUES
    assert frozenset(FINDING_SCOPE_VALUES) == FINDING_SCOPE_SET
    assert render_wire_values(FOCUS_AREA_VALUES, quoted=True) == "`code-quality` / `risk-integration` / `correctness` / `architecture` / `security`"
    assert render_wire_values(FINDING_SCOPE_VALUES) == "in_scope / out_of_scope"


def test_parse_canonical_heading_is_exact() -> None:
    heading = parse_canonical_heading("### FINDING_12: title")
    assert heading is not None
    assert (heading.item_id, heading.kind, heading.number, heading.title) == ("FINDING_12", "FINDING", 12, "title")
    assert parse_canonical_heading("## FINDING_12: title") is None
    assert parse_canonical_heading("### finding_12: title") is None
    assert parse_canonical_heading("### OOS_x: title") is None
    assert is_canonical_heading("### OOS_2: title", kind="OOS")


def test_parse_canonical_heading_allows_horizontal_whitespace_after_hashes() -> None:
    heading = parse_canonical_heading("### \tOOS_12: title")

    assert heading is not None
    assert (heading.item_id, heading.kind, heading.number, heading.title) == ("OOS_12", "OOS", 12, "title")


def test_parse_blocks_ignores_fenced_headings() -> None:
    text = "preamble\n```md\n### FINDING_9: fake\n```\n### FINDING_1: real\nbody\n"
    blocks = parse_blocks(text)
    assert [block.item_id for block in blocks] == ["FINDING_1"]
    assert blocks[0].block == "### FINDING_1: real\nbody\n"


def test_boundary_modes_are_explicit() -> None:
    text = "### OOS_1: one\na\n### FINDING_2: middle\nb\n### OOS_3: three\nc\n### Notes\nend\n"
    oos = [block for block in parse_blocks(text, boundary="oos-heading") if block.kind == "OOS"]
    assert "### FINDING_2" in oos[0].block
    assert oos[1].block.endswith("### Notes\nend\n")
    item = parse_blocks(text, boundary="item-heading")
    assert item[0].block == "### OOS_1: one\na\n"
    level_three = parse_blocks(text, boundary="level-three-heading")
    assert level_three[-1].block == "### OOS_3: three\nc\n"


def test_findings_compatibility_is_finding_only() -> None:
    text = "### FINDING_1: one\na\n### OOS_2: two\nb\n### FINDING_3: three\nc\n"
    assert [item.finding_id for item in parse_findings_text(text)] == ["FINDING_1", "FINDING_3"]
    blocks = parse_findings_text(text, boundary="finding_heading")
    assert "### OOS_2" in blocks[0].block


def test_security_and_oos_eligibility_policy() -> None:
    blocks = parse_blocks(
        "### OOS_1: public\nbody\n"
        "### FINDING_2: [OUT_OF_SCOPE] legacy\nbody\n"
        "### FINDING_3: bare\nbody\n"
        "### OOS_4: [security] private\nbody\n"
    )
    assert [is_oos_eligible_block(block) for block in blocks] == [True, True, False, True]
    assert is_security_block_text(blocks[-1].block)
    assert not is_security_block_text("### OOS_1: example\n```\nfocus-area=security\n```\n")
    assert count_non_security_blocks("".join(block.block for block in blocks)) == 2


def test_security_header_allows_whitespace_after_hashes() -> None:
    assert is_security_block_text("### OOS_1: [security] private\nbody\n")


def test_finding_dedup_key_parity() -> None:
    first = "### FINDING_1: a\n- **Location**: x.py:1\n- **Concern**:  Bad   thing\n"
    second = "### FINDING_9: b\n- **Location**: x.py:1\n- **Concern**: Bad thing\n"
    assert finding_dedup_key(first) == finding_dedup_key(second)


def test_parse_canonical_heading_depth_and_case() -> None:
    assert parse_canonical_heading("## FINDING_1: t") is None
    assert parse_canonical_heading("#### OOS_1: t") is None
    assert parse_canonical_heading("### finding_1: t") is None
    assert parse_canonical_heading("### FINDING_abc: t") is None
    h = parse_canonical_heading("### OOS_7: title: with colon")
    assert h is not None
    assert h.title == "title: with colon"
    assert h.number == 7


def test_parse_blocks_empty_and_preamble() -> None:
    assert not parse_blocks("")
    assert not parse_blocks("preamble only\nno headings\n")
    blocks = parse_blocks("preamble\n### FINDING_1: t\nbody\n")
    assert len(blocks) == 1
    assert blocks[0].start > 0


def test_parse_blocks_crlf() -> None:
    text = "### FINDING_1: t\r\nbody\r\n### OOS_2: u\r\nbody2\r\n"
    blocks = parse_blocks(text, boundary="item-heading")
    assert len(blocks) == 2
    assert blocks[0].kind == "FINDING"
    assert blocks[1].kind == "OOS"


def test_oos_heading_does_not_split_on_finding() -> None:
    text = "### OOS_1: first\na\n### FINDING_2: middle\nb\n### OOS_3: second\nc\n"
    oos_blocks = [b for b in parse_blocks(text, boundary="oos-heading") if b.kind == "OOS"]
    assert len(oos_blocks) == 2
    assert "### FINDING_2" in oos_blocks[0].block


def test_oos_eligibility_trailing_tag_forms() -> None:
    blocks = parse_blocks(
        "### FINDING_1: [OOS] tagged\nbody\n"
        "### FINDING_2: bare\nbody\n"
        "### FINDING_3: plain [OUT_OF_SCOPE]\nbody\n"
        "### OOS_4: canonical\nbody\n"
    )
    eligible = [is_oos_eligible_block(b) for b in blocks]
    assert eligible == [True, False, True, True]


def test_count_non_security_blocks_excludes_bare_finding() -> None:
    text = (
        "### OOS_1: public\nbody\n"
        "### FINDING_2: [OOS] tagged\nbody\n"
        "### FINDING_3: bare in-scope\nbody\n"
        "### OOS_4: [security] private\nbody\n"
    )
    assert count_non_security_blocks(text) == 2


def test_parse_findings_text_boundary_any_heading() -> None:
    text = "### FINDING_1: f\nbody\n### Notes\nnotes body\n### FINDING_2: g\nbody2\n"
    results = parse_findings_text(text, boundary="any_heading")
    assert [f.finding_id for f in results] == ["FINDING_1", "FINDING_2"]
    assert "### Notes" not in results[0].block


def test_dedup_key_fallback_uses_full_block() -> None:
    block_no_fields = "### FINDING_1: concern here\nsome content\n"
    key = finding_dedup_key(block_no_fields)
    assert key
    assert isinstance(key, str)
