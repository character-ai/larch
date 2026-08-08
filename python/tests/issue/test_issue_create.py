# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false
"""Tests for /issue Python helper entrypoints."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from larch.core import config as _issue_create_config
from larch.issue import issue_create
from larch.core import proc

SKILL_PATH = Path(__file__).resolve().parents[3] / "skills/issue/SKILL.md"
ISSUE_DEDUP_AGENT_PATH = Path(__file__).resolve().parents[3] / "agents/issue-dedup.md"


def _result(argv: list[str], returncode: int = 0, stdout: str = "", stderr: str = "") -> proc.CommandResult:
    return proc.CommandResult(tuple(argv), returncode, stdout, stderr, 0.0)


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


def test_add_blocked_by_transient_retry(monkeypatch: Any, capsys: Any) -> None:
    calls: list[list[str]] = []
    api_calls = 0

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        calls.append(argv)
        if argv[:3] == ["gh", "api", "/repos/o/r/issues/2"]:  # lint-gh-argv-literal: ok fixture assertion
            return _result(argv, stdout="200\n")
        if argv[:3] == ["gh", "api", "/repos/o/r/issues/1/dependencies/blocked_by"]:  # lint-gh-argv-literal: ok fixture assertion
            nonlocal api_calls
            api_calls += 1
            if api_calls < 3:
                return _result(argv, returncode=1, stderr="HTTP 503")
            return _result(argv)
        return _result(argv)

    sleeps: list[float] = []

    def record_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr(issue_create.proc, "run", fake_run)
    rc = issue_create.add_blocked_by_main(
        argv=["--client-issue", "1", "--blocker-issue", "2", "--repo", "o/r", "--operator-invoked"],
        sleep_fn=record_sleep,
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "BLOCKED_BY_ADDED=true" in out
    assert sleeps == [10.0, 30.0]
    assert api_calls == 3


def test_add_blocked_by_retry_idempotent(monkeypatch: Any, capsys: Any) -> None:
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        calls.append(argv)
        if argv[:3] == ["gh", "api", "/repos/o/r/issues/2"]:  # lint-gh-argv-literal: ok fixture assertion
            return _result(argv, stdout="200\n")
        return _result(argv, returncode=1, stderr="HTTP 422 duplicate dependency")

    sleeps: list[float] = []
    monkeypatch.setattr(issue_create.proc, "run", fake_run)
    def record_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    rc = issue_create.add_blocked_by_main(
        argv=["--client-issue", "1", "--blocker-issue", "2", "--repo", "o/r", "--operator-invoked"],
        sleep_fn=record_sleep,
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "BLOCKED_BY_ADDED=true" in out
    assert not sleeps
    assert len(calls) == 2


def _blocked_by_fixture(
    monkeypatch: Any,
    *,
    post_stderr: str,
    read_stdout: str = "",
    read_returncode: int = 0,
) -> tuple[int, list[list[str]], list[float]]:
    """Drive add-blocked-by with one deterministic POST failure and one read-back."""
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        calls.append(list(argv))
        if argv[:3] == ["gh", "api", "/repos/o/r/issues/2"]:  # lint-gh-argv-literal: ok fixture assertion
            return _result(argv, stdout="200\n")
        if "--paginate" in argv:
            return _result(argv, returncode=read_returncode, stdout=read_stdout, stderr="HTTP 403 Forbidden")
        return _result(argv, returncode=1, stderr=post_stderr)

    sleeps: list[float] = []

    def record_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr(issue_create.proc, "run", fake_run)
    rc = issue_create.add_blocked_by_main(
        argv=["--client-issue", "1", "--blocker-issue", "2", "--repo", "o/r", "--operator-invoked"],
        sleep_fn=record_sleep,
    )
    return rc, calls, sleeps


def test_add_blocked_by_already_taken_succeeds_by_read_back(monkeypatch: Any, capsys: Any) -> None:
    rc, calls, sleeps = _blocked_by_fixture(
        monkeypatch,
        post_stderr=(
            "gh: An error occurred while adding the blocking issue to the issue. "
            "Validation failed: Target issue has already been taken (HTTP 422)"
        ),
        read_stdout='[{"number":2}]',
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "BLOCKED_BY_ADDED=true" in out
    assert not sleeps
    assert [call for call in calls if "--paginate" in call]
    assert len(calls) == 3


def test_add_blocked_by_422_absent_edge_fails_fast(monkeypatch: Any, capsys: Any) -> None:
    rc, calls, sleeps = _blocked_by_fixture(
        monkeypatch,
        post_stderr="gh: Validation failed: Issue may not be blocked by itself (HTTP 422)",
        read_stdout="[]",
    )
    out = capsys.readouterr().out
    assert rc == 2
    assert "BLOCKED_BY_FAILED=true" in out
    assert "may not be blocked by itself" in out
    assert "all 3 attempts failed" not in out
    assert not sleeps
    assert len(calls) == 3


def test_add_blocked_by_read_back_transport_failure_fails_closed(monkeypatch: Any, capsys: Any) -> None:
    rc, _calls, sleeps = _blocked_by_fixture(
        monkeypatch,
        post_stderr="gh: Validation failed: Target issue has already been taken (HTTP 422)",
        read_returncode=1,
    )
    out = capsys.readouterr().out
    assert rc == 2
    assert "BLOCKED_BY_FAILED=true" in out
    assert not sleeps


def test_add_sub_issue_verifies_native_relation(monkeypatch: Any, capsys: Any) -> None:
    calls: list[tuple[str, str, str]] = []

    def add_sub_issue(_runner: object, parent: str, child_id: int, *, repo: str) -> proc.CommandResult:
        calls.append((parent, str(child_id), repo))
        return _result(["gh", "api"])  # lint-gh-argv-literal: ok fixture assertion

    def read_sub_issues(_runner: object, parent: str, *, repo: str) -> proc.CommandResult:
        assert (parent, repo) == ("1", "o/r")
        return _result(["gh", "api"], stdout='[{"number":2}]')  # lint-gh-argv-literal: ok fixture assertion

    monkeypatch.setattr(issue_create.gh, "issue_add_sub_issue", add_sub_issue)
    monkeypatch.setattr(issue_create.gh, "issue_sub_issues_read", read_sub_issues)
    rc = issue_create.add_sub_issue_main(
        ["--parent-issue", "1", "--child-issue", "2", "--child-id", "200", "--repo", "o/r", "--operator-invoked"],
        sleep_fn=lambda _seconds: None,
    )
    assert rc == 0
    assert calls == [("1", "200", "o/r")]
    assert "SUB_ISSUE_ADDED=true" in capsys.readouterr().out


DUPLICATE_SUB_ISSUE_STDERR = (
    "gh: An error occurred while adding the sub-issue to the parent issue. "
    "Issue may not contain duplicate sub-issues and Sub issue may only have one parent (HTTP 422)"
)


def _sub_issue_fixture(
    monkeypatch: Any, *, read_stdout: str, read_returncode: int = 0
) -> tuple[int, int, list[float]]:
    """Drive add-sub-issue with one deterministic 422 and one read-back."""
    attempts = 0

    def add_sub_issue(_runner: object, _parent: str, _child_id: int, *, repo: str) -> proc.CommandResult:
        assert repo == "o/r"
        nonlocal attempts
        attempts += 1
        return _result(["gh", "api"], returncode=1, stderr=DUPLICATE_SUB_ISSUE_STDERR)  # lint-gh-argv-literal: ok fixture assertion

    def read_sub_issues(_runner: object, parent: str, *, repo: str) -> proc.CommandResult:
        assert (parent, repo) == ("1", "o/r")
        return _result(["gh", "api"], returncode=read_returncode, stdout=read_stdout)  # lint-gh-argv-literal: ok fixture assertion

    sleeps: list[float] = []

    def record_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr(issue_create.gh, "issue_add_sub_issue", add_sub_issue)
    monkeypatch.setattr(issue_create.gh, "issue_sub_issues_read", read_sub_issues)
    rc = issue_create.add_sub_issue_main(
        ["--parent-issue", "1", "--child-issue", "2", "--child-id", "200", "--repo", "o/r", "--operator-invoked"],
        sleep_fn=record_sleep,
    )
    return rc, attempts, sleeps


def test_add_sub_issue_duplicate_relation_succeeds_by_read_back(monkeypatch: Any, capsys: Any) -> None:
    rc, attempts, sleeps = _sub_issue_fixture(monkeypatch, read_stdout='[{"number":2}]')
    out = capsys.readouterr().out
    assert rc == 0
    assert "SUB_ISSUE_ADDED=true" in out
    assert attempts == 1
    assert not sleeps


def test_add_sub_issue_422_absent_relation_fails_fast(monkeypatch: Any, capsys: Any) -> None:
    rc, attempts, sleeps = _sub_issue_fixture(monkeypatch, read_stdout='[{"number":3}]')
    out = capsys.readouterr().out
    assert rc == 2
    assert "SUB_ISSUE_FAILED=true" in out
    assert "Sub issue may only have one parent" in out
    assert "all 3 attempts failed" not in out
    assert attempts == 1
    assert not sleeps


def test_add_sub_issue_read_back_transport_failure_fails_closed(monkeypatch: Any, capsys: Any) -> None:
    rc, attempts, sleeps = _sub_issue_fixture(monkeypatch, read_stdout="", read_returncode=1)
    out = capsys.readouterr().out
    assert rc == 2
    assert "SUB_ISSUE_FAILED=true" in out
    assert attempts == 1
    assert not sleeps


def test_sub_issue_read_back_accepts_paginated_pages(monkeypatch: Any) -> None:
    def read_sub_issues(_runner: object, _parent: str, *, repo: str) -> proc.CommandResult:
        assert repo == "o/r"
        return _result(["gh", "api"], stdout='[{"number":1}]\n[{"number":2}]\n')  # lint-gh-argv-literal: ok fixture assertion

    monkeypatch.setattr(issue_create.gh, "issue_sub_issues_read", read_sub_issues)
    assert issue_create._sub_issue_read_back(parent="7", child="2", repo="o/r")  # pyright: ignore[reportPrivateUsage]  # read-back helper has no public alias


def test_blocked_by_read_back_accepts_paginated_pages(monkeypatch: Any) -> None:
    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        assert "--paginate" in argv
        return _result(argv, stdout='[{"number":1}]\n[{"number":2}]\n')

    monkeypatch.setattr(issue_create.proc, "run", fake_run)
    assert issue_create._blocked_by_read_back(client="7", blocker="2", repo="o/r")  # pyright: ignore[reportPrivateUsage]  # read-back helper has no public alias


def test_add_blocked_by_404_no_retry(monkeypatch: Any, capsys: Any) -> None:
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        calls.append(argv)
        if argv[:3] == ["gh", "api", "/repos/o/r/issues/2"]:  # lint-gh-argv-literal: ok fixture assertion
            return _result(argv, stdout="200\n")
        return _result(argv, returncode=1, stderr="HTTP 404: Not Found")

    monkeypatch.setattr(issue_create.proc, "run", fake_run)
    rc = issue_create.add_blocked_by_main(argv=["--client-issue", "1", "--blocker-issue", "2", "--repo", "o/r", "--operator-invoked"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "BLOCKED_BY_FAILED=true" in out
    assert len(calls) == 2


def test_add_blocked_by_redaction_failure_exits_three(monkeypatch: Any, capsys: Any) -> None:
    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        if argv[:3] == ["gh", "api", "/repos/o/r/issues/2"]:  # lint-gh-argv-literal: ok fixture assertion
            return _result(argv, stdout="200\n")
        return _result(argv, returncode=1, stderr="HTTP 404: Not Found")

    def boom(_text: str) -> str:
        raise RuntimeError("redact failed")

    monkeypatch.setattr(issue_create.proc, "run", fake_run)
    monkeypatch.setattr(issue_create, "redact_secrets_outbound", boom)
    rc = issue_create.add_blocked_by_main(argv=["--client-issue", "1", "--blocker-issue", "2", "--repo", "o/r", "--operator-invoked"])
    out = capsys.readouterr().out
    assert rc == 3
    assert "BLOCKED_BY_FAILED=true" in out
    assert "ERROR=redaction:" in out


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


def test_blocked_by_result_sanitizes_hostile_diagnostic(capsys: Any) -> None:
    rc = issue_create.emit_blocked_by_result(
        issue_create.BlockedByResult(
            client="1",
            blocker="2",
            added=False,
            error="dependency failed\rFORGED=value",
            exit_code=2,
        )
    )

    assert rc == 2
    assert capsys.readouterr().out == (
        "BLOCKED_BY_FAILED=true\nCLIENT=1\nBLOCKER=2\nERROR=dependency failedFORGED=value\n"
    )


def test_add_blocked_by_refuses_without_authorization_before_request(
    monkeypatch: Any, capsys: Any
) -> None:
    """The gate rejects unauthenticated writes before even the blocker lookup."""
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        calls.append(argv)
        return _result(argv)

    monkeypatch.setattr(issue_create.proc, "run", fake_run)
    rc = issue_create.add_blocked_by_main(
        ["--client-issue", "1", "--blocker-issue", "2", "--repo", "o/r"]
    )

    captured = capsys.readouterr()
    assert rc == _issue_create_config.EXIT_MUTATION_REFUSED
    assert _issue_create_config.LIVE_MUTATION_REFUSAL_STATUS in captured.out
    assert "BLOCKED_BY_FAILED=true" in captured.out
    assert not calls


def test_add_blocked_by_accepts_valid_session_authorization(
    monkeypatch: Any, tmp_path: Path, capsys: Any
) -> None:
    session_root = tmp_path / "claude-implement-run-1"
    session_root.mkdir()
    context = session_root / "session-env.sh"
    _ = context.write_text(
        "LARCH_LIVE_MUTATION_OK=true\nLARCH_RUN_ID=run-1\n", encoding="utf-8"
    )
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        calls.append(argv)
        if argv[:3] == ["gh", "api", "/repos/o/r/issues/2"]:  # lint-gh-argv-literal: ok fixture assertion
            return _result(argv, stdout="200\n")
        return _result(argv)

    monkeypatch.delenv(_issue_create_config.LIVE_MUTATION_TEST_DENY_KEY)
    monkeypatch.setattr(issue_create.proc, "run", fake_run)
    rc = issue_create.add_blocked_by_main(
        [
            "--client-issue",
            "1",
            "--blocker-issue",
            "2",
            "--repo",
            "o/r",
            "--context-file",
            str(context),
            "--run-id",
            "run-1",
            "--trusted-root",
            str(session_root),
        ]
    )

    assert rc == 0
    assert "BLOCKED_BY_ADDED=true" in capsys.readouterr().out
    assert len(calls) == 2

