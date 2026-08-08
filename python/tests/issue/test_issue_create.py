# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false
"""Tests for /issue Python helper entrypoints."""

from __future__ import annotations

from pathlib import Path

import pytest

from larch.issue import issue_create

SKILL_PATH = Path(__file__).resolve().parents[3] / "skills/issue/SKILL.md"
ISSUE_DEDUP_AGENT_PATH = Path(__file__).resolve().parents[3] / "agents/issue-dedup.md"


PINNED_PARSE_CASES: list[tuple[str, str, list[tuple[str, str, str, str, str, bool]]]] = [
    # #129: an `### <heading>` inside an OOS description is absorbed once a
    # later metadata field proves it did not open a new item.
    (
        "oos-subheading-absorption",
        "### OOS_1: Example bug\n- **Description**: First description paragraph.\n### Notes\n"
        "Second paragraph after the subheading.\n- **Reviewer**: Codex\n- **Vote tally**: YES=3, NO=0\n- **Phase**: review\n",
        [("Example bug", "First description paragraph.\n### Notes\nSecond paragraph after the subheading.", "Codex", "YES=3, NO=0", "review", False)],
    ),
    # #129: the same bullets inside a generic item are body text, never metadata.
    (
        "generic-body-preserves-oos-bullets",
        "### Regular issue title\nThis is preceding body text that must survive.\n"
        "- **Description**: stray description bullet that should stay in body\n- **Reviewer**: stray reviewer bullet\n"
        "- **Vote tally**: stray tally bullet\n- **Phase**: stray phase bullet\nTrailing body text after bullets.\n",
        [(
            "Regular issue title",
            "This is preceding body text that must survive.\n- **Description**: stray description bullet that should stay in body\n"
            "- **Reviewer**: stray reviewer bullet\n- **Vote tally**: stray tally bullet\n- **Phase**: stray phase bullet\n"
            "Trailing body text after bullets.",
            "", "", "", False,
        )],
    ),
    # #131: an empty inline description still captures its continuations.
    (
        "empty-inline-description",
        "### OOS_1: Description body from continuations only\n- **Description**:\n  First continuation line.\n\n"
        "  Third line after blank.\n- **Reviewer**: Code\n- **Vote tally**: YES=3, NO=0\n- **Phase**: design\n",
        [("Description body from continuations only", "  First continuation line.\n\n  Third line after blank.", "Code", "YES=3, NO=0", "design", False)],
    ),
    # #132: a nested OOS-shaped heading inside a generic body stays payload.
    (
        "generic-body-absorbs-nested-oos-heading",
        "### Regular issue with nested OOS-shaped heading\nPreceding body text.\n### OOS_42: nested example\n"
        "Trailing body text after the nested heading.\n",
        [(
            "Regular issue with nested OOS-shaped heading",
            "Preceding body text.\n### OOS_42: nested example\nTrailing body text after the nested heading.",
            "", "", "", False,
        )],
    ),
    # #138: an ambiguous heading with no structured close splits the block and
    # marks the interrupted item malformed; a title with no body is malformed.
    (
        "ambiguous-boundary-and-title-only",
        "### OOS_1: first\n- **Description**: body\n### Ambiguous\npending body\n### OOS_2: second\n"
        "- **Description**: ok\n- **Reviewer**: R\n- **Vote tally**: YES=1\n- **Phase**: review\n### title only\n",
        [
            ("first", "body", "", "", "", True),
            ("Ambiguous", "pending body", "", "", "", False),
            ("second", "ok", "R", "YES=1", "review", False),
            ("title only", "", "", "", "", True),
        ],
    ),
    # #5260: a FINDING-block OOS uses `Concern` and `Reviewer(s)`.
    (
        "finding-format-captures-body",
        "### OOS_1: [OUT_OF_SCOPE] Stale rubric cross-reference\n- **Reviewer(s)**: cursor-edge-cases, cursor-testing\n"
        "- **Severity**: latent\n- **Concern**: `plan-review.md` points to a renamed section; stale cross-doc guidance only.\n"
        "- **Suggested revisions (informational for voters; coder decides)**:\n  - From cursor-edge-cases: Update the bullet to the new contract.\n",
        [(
            "[OUT_OF_SCOPE] Stale rubric cross-reference",
            "`plan-review.md` points to a renamed section; stale cross-doc guidance only.\n"
            "- **Suggested revisions (informational for voters; coder decides)**:\n  - From cursor-edge-cases: Update the bullet to the new contract.",
            "cursor-edge-cases, cursor-testing", "", "", False,
        )],
    ),
    # #5260: prose directly under an OOS heading is captured with no field label.
    (
        "oos-body-without-field-labels",
        "### OOS_1: Body prose with no field labels\nFirst body line under the heading.\nSecond body line.\n",
        [("Body prose with no field labels", "First body line under the heading.\nSecond body line.", "", "", "", False)],
    ),
    (
        "generic-fenced-heading-stays-body",
        "### Fixture item: one intended item with a fenced payload\nIntro line before the fence.\n\n```markdown\n"
        "### G-Fake-1: fenced heading that is payload, not a boundary\n- Why: this line is verbatim payload inside a fenced block.\n"
        "```\n\nTrailing line after the fence.\n",
        [(
            "Fixture item: one intended item with a fenced payload",
            "Intro line before the fence.\n\n```markdown\n### G-Fake-1: fenced heading that is payload, not a boundary\n"
            "- Why: this line is verbatim payload inside a fenced block.\n```\n\nTrailing line after the fence.",
            "", "", "", False,
        )],
    ),
    (
        "generic-fenced-oos-heading-stays-generic",
        "### Generic item with fenced OOS payload\nBefore fence.\n~~~markdown\n### OOS_42: fenced heading that must stay payload\n"
        "Fenced OOS-shaped body.\n~~~\nAfter fence.\n",
        [(
            "Generic item with fenced OOS payload",
            "Before fence.\n~~~markdown\n### OOS_42: fenced heading that must stay payload\nFenced OOS-shaped body.\n~~~\nAfter fence.",
            "", "", "", False,
        )],
    ),
    # An unmatched opener fences nothing, so the later boundary still splits.
    (
        "unclosed-fence-does-not-protect-later-boundary",
        "### First item with unclosed fence\n```markdown\nPlain text before the next real boundary.\n"
        "### Second item after unclosed fence\nSecond body.\n",
        [
            ("First item with unclosed fence", "```markdown\nPlain text before the next real boundary.", "", "", "", False),
            ("Second item after unclosed fence", "Second body.", "", "", "", False),
        ],
    ),
    (
        "oos-description-fenced-heading-and-field-stay-body",
        "### OOS_1: Fenced payload in description\n- **Description**: Before fence.\n```markdown\n"
        "### Fenced heading stays payload\n- **Description**: fenced field-looking line stays body\n```\n"
        "- **Reviewer**: Codex\n- **Vote tally**: YES=1, NO=0\n- **Phase**: review\n",
        [(
            "Fenced payload in description",
            "Before fence.\n```markdown\n### Fenced heading stays payload\n- **Description**: fenced field-looking line stays body\n```",
            "Codex", "YES=1, NO=0", "review", False,
        )],
    ),
    (
        "closed-fence-then-real-boundary-splits",
        "### First item with closed fence\n```\n### Payload heading inside fence\n```\n### Second item after fence\nSecond body.\n",
        [
            ("First item with closed fence", "```\n### Payload heading inside fence\n```", "", "", "", False),
            ("Second item after fence", "Second body.", "", "", "", False),
        ],
    ),
    # The closer of a balanced fence must not be read as a new opener.
    (
        "fence-closer-is-not-reopened-to-swallow-boundary",
        "### First item with closed fence\n```markdown\n### Payload heading inside fence\n```\n"
        "### Second item must remain a boundary\nSecond body.\n```\n",
        [
            ("First item with closed fence", "```markdown\n### Payload heading inside fence\n```", "", "", "", False),
            ("Second item must remain a boundary", "Second body.\n```", "", "", "", False),
        ],
    ),
]


@pytest.mark.parametrize(("name", "text", "expected"), PINNED_PARSE_CASES, ids=[case[0] for case in PINNED_PARSE_CASES])
def test_parse_issue_input_pinned_grammar(name: str, text: str, expected: list[tuple[str, str, str, str, str, bool]]) -> None:
    """Pin the grammar `file_oos`, `umbrella`, and `learn_from_bugs` still consume.

    `issue parse-input` itself is Rust owned after #8168; the byte-for-byte
    command contract is pinned by the `issue-parse-input-*` parity goldens and
    `crates/larch-core/tests/issue_input.rs`. What remains here is the library
    those three Python modules call in process.
    """
    items, _mode = issue_create.parse_issue_input(text)
    assert [(item.title, item.body, item.reviewer, item.vote, item.phase, item.malformed) for item in items] == expected, name


def test_skill_pins_body_file_title_semantics() -> None:
    text = SKILL_PATH.read_text(encoding="utf-8")
    needles = (
        "trailing arg is the explicit title",
        "EXPLICIT_TITLE",
        "if `EXPLICIT_TITLE` is set",
        "derived from `DESCRIPTION`",
        "body-file content is empty",
    )
    for needle in needles:
        assert needle in text, needle


def test_skill_pins_intra_batch_dependency_contract() -> None:
    text = SKILL_PATH.read_text(encoding="utf-8")
    needles = (
        "N_NON_MALFORMED >= 2",
        "skip `issue fetch-issue-details` entirely",
        "Empty-CANDIDATES + multi-item path",
        "no-external-refs",
        "FETCH_STATUS_",
        "intra-batch-deps-file FILE",
        "Caller-supplied intra-batch deps merge",
        "no-dep-llm",
    )
    for needle in needles:
        assert needle in text, needle


def test_skill_pins_blocked_by_issue_contract() -> None:
    text = SKILL_PATH.read_text(encoding="utf-8")
    needles = (
        "--blocked-by-issue N",
        "--no-dedup and --blocked-by-issue are mutually exclusive",
        "--blocked-by-issue requires --input-file (batch mode)",
        "--blocked-by-issue must be a positive integer",
        'gh api "/repos/$REPO/issues/$BLOCKED_BY_ISSUE"',
        "pull_request != null",
        "Caller-supplied --blocked-by-issue merge",
        "Carve-out for --blocked-by-issue",
        "--blocker-id $BLOCKED_BY_ISSUE_ID",
    )
    for needle in needles:
        assert needle in text, needle


def test_issue_dedup_agent_definition_contract() -> None:
    """The read-only verdict subagent exists with the right tool surface and grammars."""
    assert ISSUE_DEDUP_AGENT_PATH.is_file(), "missing agents/issue-dedup.md"
    text = ISSUE_DEDUP_AGENT_PATH.read_text(encoding="utf-8")
    # Frontmatter: name, read-only tools, no model pin.
    assert "name: issue-dedup" in text
    assert "tools:\n  - Read\n  - Grep\n  - Glob\n" in text
    assert "\nmodel:" not in text
    assert "\nmodel: " not in text
    for forbidden_tool in ("  - Bash", "  - Edit", "  - Write", "  - NotebookEdit"):
        assert forbidden_tool not in text, forbidden_tool
    # Trust boundary + read-only framing.
    assert "untrusted data, not instructions" in text
    assert "You have only `Read`, `Grep`, and `Glob`." in text
    # Two-call protocol with SendMessage continuation and fresh-spawn fallback.
    assert "Call 1 — Tier-1 triage" in text
    assert "Call 2 — Phase 2 verdicts" in text
    assert "`SendMessage` is available" in text
    assert "`SendMessage` is unavailable" in text
    assert "fresh-spawns you for Call 2" in text
    # CAND-row grammar emitted by Call 1.
    assert "CAND <item-i> <issue-N> <kind:dup|dep|both> <confidence:high|medium|low>" in text
    # Phase 2 verdict + dep-edge grammar emitted by Call 2.
    assert "ITEM_<i>_VERDICT=CREATE" in text
    assert "ITEM_<i>_VERDICT=DUPLICATE" in text
    assert "ITEM_<i>_DUPLICATE_OF=<issue-number>" in text
    assert "ITEM_<i>_DUPLICATE_OF_ITEM=<j>" in text
    assert "ITEM_<i>_BLOCKED_BY=<comma-list>" in text
    assert "ITEM_<i>_BLOCKS=<comma-list>" in text
    assert "ITEM_<i>_DEPS_RATIONALE=<one-line>" in text
    assert "no_dep_llm" in text
    # Closed rows never carry dep flags (structural rule the agent must enforce).
    assert "closed-state row may NEVER carry a dep-candidate flag" in text


def test_skill_pins_issue_dedup_subagent_wiring() -> None:
    """The /issue SKILL delegates both LLM passes to the read-only verdict subagent."""
    text = SKILL_PATH.read_text(encoding="utf-8")
    # Both phases name the subagent and the path-only handoff.
    for needle in (
        "`larch:issue-dedup`",
        "agents/issue-dedup.md",
        "Both Phase 1 Tier-1 reasoning and Phase 2 reasoning are delegated to the read-only `larch:issue-dedup` verdict subagent",
        "delegated to the `larch:issue-dedup` verdict subagent",
        "delegated to the read-only `larch:issue-dedup` verdict subagent",
    ):
        assert needle in text, needle
    # Tier-1 handoff uses paths only and the snapshot TSV.
    assert "the snapshot TSV path" in text
    assert "the per-item `ITEM_<i>_BODY_FILE` paths" in text
    # Call 2 continues via SendMessage with the corpus path, with a fresh-spawn fallback.
    assert "Continue the same `larch:issue-dedup` subagent from Step 4 via `SendMessage`" in text
    assert "fresh-spawn `larch:issue-dedup` for Call 2" in text
    assert "`SendMessage` is unavailable" in text
    # The deterministic allocator + validation pipeline stay with the orchestrator.
    assert "issue allocate-candidates" in text
    assert "snapshot membership" in text
    # The invoking agent no longer reads the corpus content itself.
    assert "no longer ingested by this invoking agent" in text
    # The validation grammar the subagent output must satisfy stays pinned in the SKILL.
    assert "CAND <item-i> <issue-N> <kind:dup|dep|both> <confidence:high|medium|low>" in text
