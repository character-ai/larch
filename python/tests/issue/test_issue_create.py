# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false
"""Structural tests for the Rust-owned `/issue` workflow surface."""

from __future__ import annotations

from pathlib import Path

SKILL_PATH = Path(__file__).resolve().parents[3] / "skills/issue/SKILL.md"
ISSUE_DEDUP_AGENT_PATH = Path(__file__).resolve().parents[3] / "agents/issue-dedup.md"


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


def test_skill_assigns_every_created_issue_to_the_authenticated_user() -> None:
    text = SKILL_PATH.read_text(encoding="utf-8")
    assert text.count("--assign-authenticated-user") == 1
    assert "requests authenticated-user assignment on every create" in text
    assert "verifies it on the issue read-back" in text
    assert "`/umbrella`, `/file-bug`, and `/learn-from-bugs` inherit this behavior" in text


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
