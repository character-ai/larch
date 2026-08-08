# pyright: reportUnusedCallResult=false
"""Tests for tracking_issue.py."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from larch.core import config
from larch.issue import issue_mutation, issue_wire, migration_governance
from larch.issue import tracking_issue
from larch.errors import ShipError
from larch.core.proc import CommandResult


from test_support import RecordingRunner


def test_link_pr_closes_appends() -> None:
    body = "Summary\n"
    linked = tracking_issue.link_pr_closes(body=body, issue_number=42)
    assert "Closes #42" in linked


def test_link_pr_closes_idempotent() -> None:
    body = "Summary\n\nCloses #42\n"
    linked = tracking_issue.link_pr_closes(body=body, issue_number=42)
    assert linked == body


def test_link_pr_closes_ignores_prose_mentions() -> None:
    body = "Summary says Closes #42 should be added as a footer.\n"
    linked = tracking_issue.link_pr_closes(body=body, issue_number=42)
    assert linked.count("Closes #42") == 2
    assert linked.rstrip().endswith("Closes #42")


def test_link_pr_closes_ignores_mermaid_mentions() -> None:
    body = "```mermaid\nflowchart LR\n  A[Closes #42] --> B\n```\n"
    linked = tracking_issue.link_pr_closes(body=body, issue_number=42)
    assert linked.count("Closes #42") == 2
    assert linked.rstrip().endswith("Closes #42")


def test_link_pr_closes_ignores_fenced_exact_line() -> None:
    body = "```text\nCloses #42\n```\n"
    linked = tracking_issue.link_pr_closes(body=body, issue_number=42)
    assert linked.count("Closes #42") == 2
    assert linked.rstrip().endswith("Closes #42")


def test_link_pr_closes_ignores_non_footer_exact_line() -> None:
    body = "Closes #42\n\n## Test plan\n\n- [x] passed\n"
    linked = tracking_issue.link_pr_closes(body=body, issue_number=42)
    assert linked.count("Closes #42") == 2
    assert linked.rstrip().endswith("Closes #42")


def test_link_pr_closes_no_prefix_collision() -> None:
    body = "Summary\n\nCloses #421\n"
    linked = tracking_issue.link_pr_closes(body=body, issue_number=42)
    assert "Closes #421" in linked
    assert "Closes #42\n" in linked


def test_initialize_lease_pins_both_gates_to_supplied_head(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    receipt = migration_governance.PlanReceipt(
        plan_sha256="1" * 64,
        base_sha="a" * 40,
        blockers_sha256="2" * 64,
        owners_sha256="3" * 64,
    )
    plan_body = issue_wire.compose_named_block(
        marker="plan", inner="## Plan\n\nImplement the test."
    )
    body = migration_governance.upsert_receipt(body=plan_body, receipt=receipt)
    before = issue_mutation.IssueSnapshot(
        repository="o/r",
        issue="7",
        title="[DESIGNED] Test",
        body=body,
        labels=frozenset(),
        state="OPEN",
        updated_at="2026-07-26T00:00:00Z",
    )
    evaluated_heads: list[object] = []

    def passing_gate(
        *_args: object, **kwargs: object
    ) -> migration_governance.GovernanceGateVerdict:
        evaluated_heads.append(kwargs.get("head_sha"))
        return migration_governance.GovernanceGateVerdict(
            parity=migration_governance.ParityVerdict(reasons=()),
            freshness=migration_governance.FreshnessVerdict(reasons=()),
        )

    def update_lease(
        _runner: object, **kwargs: object
    ) -> issue_mutation.VerifiedIssueMutation:
        after = issue_mutation.IssueSnapshot(
            repository=before.repository,
            issue=before.issue,
            title=before.title,
            body=str(kwargs["body"]),
            labels=before.labels,
            state=before.state,
            updated_at="2026-07-26T00:00:01Z",
        )
        return issue_mutation.VerifiedIssueMutation(
            before=before,
            after=after,
            fields=frozenset(
                {issue_mutation.MutationField.IMPLEMENTATION_LEASE}
            ),
        )

    def read_snapshot(
        _runner: object, **_kwargs: object
    ) -> issue_mutation.IssueSnapshot:
        return before

    monkeypatch.setattr(
        tracking_issue.issue_mutation, "read_snapshot", read_snapshot
    )
    monkeypatch.setattr(
        tracking_issue.issue_mutation, "update_implementation_lease", update_lease
    )
    monkeypatch.setattr(
        migration_governance, "evaluate_governance_gate", passing_gate
    )

    lease = tracking_issue.initialize_implementation_lease(
        RecordingRunner(),
        run=tracking_issue.ImplementationLeaseRun(
            issue="7", repo="o/r", run_id="run-7", cwd=str(tmp_path)
        ),
        branch="feature/test",
        head_sha="b" * 40,
    )

    assert lease.base == "a" * 40
    assert evaluated_heads == ["b" * 40, "b" * 40]


def test_rename_strips_legacy_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = RecordingRunner()

    def update_title(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr(tracking_issue.issue_mutation, "update_title", update_title)
    title = "[IN PROGRESS] [DONE] My feature"
    new = tracking_issue.rename(
        runner,
        "1",
        "done",
        repo="o/r",
        current_title=title,
    )
    assert new.startswith(config.TRACKING_ISSUE_PREFIX_BY_STATE["done"])
    assert "[IN PROGRESS]" not in new


@pytest.mark.parametrize("current_title", ["[BUG] My feature", "[DESIGNED] [BUG] My feature"])
def test_rename_prepends_lifecycle_prefix_without_stripping_bug_prefix(
    current_title: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = RecordingRunner()
    captured: dict[str, str] = {}

    def update_title(*_args: object, title: str, **_kwargs: object) -> None:
        captured["title"] = title

    monkeypatch.setattr(tracking_issue.issue_mutation, "update_title", update_title)
    new = tracking_issue.rename(
        runner,
        "1",
        "implementing",
        repo="o/r",
        current_title=current_title,
    )
    assert new == "[IMPLEMENTING] [BUG] My feature"
    assert captured["title"] == new


def test_append_comment_rejects_invalid_lifecycle_marker() -> None:
    runner = RecordingRunner()
    with pytest.raises(ShipError, match="invalid lifecycle marker"):
        tracking_issue.append_comment(
            runner,
            "1",
            "body",
            repo="o/r",
            lifecycle_marker="bad--marker",
        )


def test_append_comment_accepts_colon_lifecycle_marker() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("gh", "issue", "comment", "1"), 0, "", "", 0.01),
        ],
    )
    tracking_issue.append_comment(
        runner,
        "1",
        "body",
        repo="o/r",
        lifecycle_marker="pr:opened",
    )
    assert runner.calls[-1][1:3] == ["issue", "comment"]


def test_upsert_summary_patches_existing_comment() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("gh", "api"),
                0,
                '[{"id":12,"body":"<!-- larch:final-summary -->\\nold"}]',
                "",
                0.01,
            ),
            CommandResult(("gh", "api"), 0, "", "", 0.01),
        ],
    )
    tracking_issue.upsert_summary(runner, "1", "new body", repo="o/r")
    assert runner.calls[-1][1] == "api"
    assert "PATCH" in runner.calls[-1]


def test_upsert_token_report_truncates_title_prefix() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("gh", "api"),
                0,
                "[]",
                "",
                0.01,
            ),
            CommandResult(("gh", "issue", "comment", "1"), 0, "", "", 0.01),
        ],
    )
    long_body = "x" * 400
    tracking_issue.upsert_token_report(runner, "1", long_body, repo="o/r")
    posted = runner.calls[-1]
    assert "comment" in posted


def test_upsert_token_report_rename_matrix() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("gh", "api"),
                0,
                '[{"id":5,"body":"<!-- larch:token-report -->\\nold"}]',
                "",
                0.01,
            ),
            CommandResult(("gh", "api"), 0, "", "", 0.01),
        ],
    )
    tracking_issue.upsert_token_report(runner, "1", "updated", repo="o/r")
    assert runner.calls[-1][1] == "api"
    assert "PATCH" in runner.calls[-1]


def test_rename_truncates_after_redaction(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = RecordingRunner()
    captured: dict[str, str] = {}

    def update_title(*_args: object, title: str, **_kwargs: object) -> None:
        captured.setdefault("title", title)

    monkeypatch.setattr(
        tracking_issue.issue_mutation,
        "update_title",
        update_title,
    )
    long_tail = "x" * 300
    title = f"[DESIGNING] {long_tail}"
    new = tracking_issue.rename(
        runner,
        "1",
        "implementing",
        repo="o/r",
        current_title=title,
    )
    assert len(new) <= config.TRACKING_TITLE_MAX_LEN
    assert len(captured["title"]) <= config.TRACKING_TITLE_MAX_LEN


def test_rename_skips_edit_when_redacted_canonical_current_matches() -> None:
    runner = RecordingRunner()
    long_tail = "x" * 300
    title = f"[IMPLEMENTING] {long_tail}"
    new = tracking_issue.rename(
        runner,
        "1",
        "implementing",
        repo="o/r",
        current_title=title,
    )
    assert len(new) <= config.TRACKING_TITLE_MAX_LEN
    assert not runner.calls


def test_rename_raises_on_truncated_redaction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = RecordingRunner()

    def fake_redact(_text: str) -> str:
        return "x [content truncated — safety]"

    monkeypatch.setattr(tracking_issue.redact, "redact", fake_redact)
    with pytest.raises(ShipError, match="redaction failed"):
        _ = tracking_issue.rename(
            runner,
            "1",
            "done",
            repo="o/r",
            current_title="[DESIGNING] title",
        )


def test_rename_public_adapter_wraps_cli_failure() -> None:
    runner = RecordingRunner()
    with pytest.raises(ShipError, match="invalid --state"):
        _ = tracking_issue.rename(
            runner,
            "1",
            "bogus",
            repo="o/r",
            current_title="[DESIGNING] title",
        )


def test_strip_lifecycle_prefix_strips_exactly_one() -> None:
    assert tracking_issue.strip_lifecycle_prefix("[PLANNED] [DONE] Work") == "[DONE] Work"
    assert tracking_issue.strip_lifecycle_prefix("Work") == "Work"


def test_read_sentinel_returns_frozen_result_with_named_fields(tmp_path: Path) -> None:
    path = tmp_path / "sentinel.md"
    path.write_text("\ufeffISSUE_NUMBER=5\nRUN_ID=run-1\nADOPTED=true\n", encoding="utf-8")
    result = tracking_issue.read_sentinel(str(path))
    assert isinstance(result, tracking_issue.SentinelReadResult)
    assert result.issue_number == "5"
    assert result.run_id == "run-1"
    assert result.adopted == "true"
    with pytest.raises(FrozenInstanceError):
        result.issue_number = "6"  # type: ignore[misc]  # assign to frozen field to assert FrozenInstanceError


def test_read_sentinel_preserves_empty_valid_fields(tmp_path: Path) -> None:
    path = tmp_path / "sentinel.md"
    path.write_text("ISSUE_NUMBER=\nRUN_ID=\nADOPTED=\n", encoding="utf-8")
    result = tracking_issue.read_sentinel(str(path))
    assert (result.issue_number, result.run_id, result.adopted) == ("", "", "")


def test_read_sentinel_first_value_wins(tmp_path: Path) -> None:
    path = tmp_path / "sentinel.md"
    path.write_text("ISSUE_NUMBER=5\nISSUE_NUMBER=9\n", encoding="utf-8")
    assert tracking_issue.read_sentinel(str(path)).issue_number == "5"


def test_read_sentinel_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(tracking_issue.CliFailure) as exc:
        tracking_issue.read_sentinel(str(tmp_path / "missing.md"))
    assert exc.value.exit_code == 1
    assert "sentinel file not found" in exc.value.message


@pytest.mark.parametrize(
    ("content", "needle"),
    [
        ("ISSUE_NUMBER=abc\n", "invalid ISSUE_NUMBER"),
        ("RUN_ID=bad id\n", "invalid RUN_ID"),
        ("ADOPTED=maybe\n", "invalid ADOPTED"),
    ],
)
def test_read_sentinel_rejects_malformed_values(tmp_path: Path, content: str, needle: str) -> None:
    path = tmp_path / "sentinel.md"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(tracking_issue.CliFailure) as exc:
        tracking_issue.read_sentinel(str(path))
    assert exc.value.exit_code == 1
    assert needle in exc.value.message


def test_resolve_repo_or_fail_explicit_and_canonical(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tracking_issue.gh, "resolve_repo", lambda *_a, **_k: "from/gh")  # type: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    assert tracking_issue._resolve_repo_or_fail(RecordingRunner([]), "owner/repo") == "owner/repo"  # type: ignore[reportPrivateUsage]
    assert tracking_issue._resolve_repo_or_fail(RecordingRunner([]), None) == "from/gh"  # type: ignore[reportPrivateUsage]
    with pytest.raises(tracking_issue.CliFailure, match="invalid repo"):
        tracking_issue._resolve_repo_or_fail(RecordingRunner([]), "bad..repo")  # type: ignore[reportPrivateUsage]


def test_resolve_repo_or_fail_unresolved_and_cwd(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    def fake_resolve(_runner: object, *, cwd: str | None = None) -> str | None:
        seen["cwd"] = cwd

    monkeypatch.setattr(tracking_issue.gh, "resolve_repo", fake_resolve)
    with pytest.raises(tracking_issue.CliFailure) as exc:
        tracking_issue._resolve_repo_or_fail(RecordingRunner([]), None, cwd="/tmp/work")  # type: ignore[reportPrivateUsage]
    assert exc.value.exit_code == 2
    assert "could not determine repo" in str(exc.value)
    assert seen["cwd"] == "/tmp/work"
