"""Contract tests for the freshness-checked issue mutation owner."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from larch.core.proc import CommandResult
from larch.issue import issue_mutation, issue_wire


def _empty_labels() -> set[str]:
    return set()


def _empty_calls() -> list[list[str]]:
    return []


@dataclass
class MutationRunner:
    title: str = "Regular issue"
    body: str = "Body"
    labels: set[str] = field(default_factory=_empty_labels)
    state: str = "OPEN"
    second: int = 0
    advance_timestamp: bool = True
    edit_failure_after_apply: bool = False
    calls: list[list[str]] = field(default_factory=_empty_calls)

    @property
    def updated_at(self) -> str:
        return f"2026-07-19T00:00:{self.second:02d}Z"

    def _snapshot(self) -> str:
        return json.dumps(
            {
                "title": self.title,
                "body": self.body,
                "labels": [{"name": name} for name in sorted(self.labels)],
                "state": self.state,
                "updatedAt": self.updated_at,
            }
        )

    def _advance(self) -> None:
        if self.advance_timestamp:
            self.second += 1

    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = None,
        cwd: str | None = None,
        env: Mapping[str, str] | None = None,
        check: bool = False,
        stdout: int | None = None,
        stderr: int | None = None,
    ) -> CommandResult:
        _ = (timeout, cwd, env, check, stdout, stderr)
        args = list(argv)
        self.calls.append(args)
        if args[:4] == ["gh", "issue", "view", "7"]:  # lint-gh-argv-literal: ok fixture assertion
            return CommandResult(tuple(args), 0, self._snapshot(), "", 0.01)
        if args[:4] == ["gh", "issue", "edit", "7"]:  # lint-gh-argv-literal: ok fixture assertion
            if "--title" in args:
                self.title = args[args.index("--title") + 1]
            if "--body-file" in args:
                self.body = Path(args[args.index("--body-file") + 1]).read_text(encoding="utf-8")
            if "--add-label" in args:
                self.labels.add(args[args.index("--add-label") + 1])
            if "--remove-label" in args:
                self.labels.discard(args[args.index("--remove-label") + 1])
            self._advance()
            if self.edit_failure_after_apply:
                return CommandResult(tuple(args), 1, "", "network unavailable", 0.01)
            return CommandResult(tuple(args), 0, "", "", 0.01)
        raise AssertionError(f"unexpected command: {args}")


def _request(
    runner: MutationRunner, *, fields: frozenset[issue_mutation.MutationField], **kwargs: Any
) -> issue_mutation.IssueMutationRequest:
    snapshot = issue_mutation.read_snapshot(runner, repository="owner/repo", issue="7")
    return issue_mutation.request_for_snapshot(snapshot, fields=fields, **kwargs)


def test_title_and_label_mutations_read_back_a_strictly_fresh_snapshot() -> None:
    runner = MutationRunner(labels={"old"})
    title = _request(
        runner,
        fields=frozenset({issue_mutation.MutationField.TITLE}),
        title="Renamed",
    )
    title_result = issue_mutation.apply(runner, title)
    assert title_result.after.title == "Renamed"
    assert title_result.after.updated_at > title_result.before.updated_at

    labels = _request(
        runner,
        fields=frozenset({issue_mutation.MutationField.LABELS}),
        labels=frozenset({"new"}),
    )
    label_result = issue_mutation.apply(runner, labels)
    assert label_result.after.labels == frozenset({"new"})
    assert [call[-2:] for call in runner.calls if "--label" in " ".join(call)] == []


def test_stale_state_and_unchanged_read_back_fail_closed() -> None:
    runner = MutationRunner()
    request = _request(
        runner,
        fields=frozenset({issue_mutation.MutationField.TITLE}),
        title="Renamed",
    )
    runner.second = 1
    with pytest.raises(issue_mutation.ProtectedIssueMutation, match="stale-identity"):
        _ = issue_mutation.apply(runner, request)

    runner = MutationRunner()
    request = _request(
        runner,
        fields=frozenset({issue_mutation.MutationField.TITLE}),
        title="Renamed",
    )
    runner.state = "CLOSED"
    with pytest.raises(issue_mutation.ProtectedIssueMutation, match="stale-identity"):
        _ = issue_mutation.apply(runner, request)

    runner = MutationRunner(advance_timestamp=False)
    request = _request(
        runner,
        fields=frozenset({issue_mutation.MutationField.TITLE}),
        title="Renamed",
    )
    with pytest.raises(issue_mutation.ProtectedIssueMutation, match="non-fresh-read-back"):
        _ = issue_mutation.apply(runner, request)


def test_transport_failure_reconciles_a_landed_idempotent_write() -> None:
    runner = MutationRunner(edit_failure_after_apply=True)
    request = _request(
        runner,
        fields=frozenset({issue_mutation.MutationField.TITLE}),
        title="Renamed",
    )
    assert issue_mutation.apply(runner, request).after.title == "Renamed"


def test_protected_body_requires_its_matching_named_marker_and_lease() -> None:
    runner = MutationRunner(
        title="[IMPLEMENTING] Protected",
        body="prefix\n<!-- larch:plan:start -->\nold\n<!-- larch:plan:end -->\n",
    )
    foreign = _request(
        runner,
        fields=frozenset({issue_mutation.MutationField.BODY}),
        body="foreign rewrite",
    )
    with pytest.raises(issue_mutation.ProtectedIssueMutation, match="protected-body"):
        _ = issue_mutation.apply(runner, foreign)

    replacement = "prefix\n<!-- larch:plan:start -->\nnew\n<!-- larch:plan:end -->\n"
    missing_lease = _request(
        runner,
        fields=frozenset({issue_mutation.MutationField.NAMED_BLOCK}),
        body=replacement,
        marker="plan",
    )
    with pytest.raises(issue_mutation.ProtectedIssueMutation, match="missing-lease"):
        _ = issue_mutation.apply(runner, missing_lease)

    allowed = _request(
        runner,
        fields=frozenset({issue_mutation.MutationField.NAMED_BLOCK}),
        body=replacement,
        marker="plan",
        lease=issue_mutation.ImplementationLease(run_id="run-7", marker="plan"),
    )
    assert issue_mutation.apply(runner, allowed).after.body == replacement


def test_managed_umbrella_conversion_is_atomic_and_shape_restricted() -> None:
    original_body = "Original body with its plan.\n"
    runner = MutationRunner(title="[DESIGNING] [BUG] Split this work", body=original_body)
    converted = issue_mutation.convert_managed_issue_to_umbrella(
        runner,
        repository="owner/repo",
        issue="7",
        title="[UMBRELLA] [BUG] Split this work",
        body=original_body + "\n<!-- larch:umbrella-proposal -->\n",
    )
    assert converted.after.title == "[UMBRELLA] [BUG] Split this work"
    assert converted.after.body.endswith("<!-- larch:umbrella-proposal -->\n")
    assert len(
        [
            call
            for call in runner.calls
            if call[:3] == ["gh", "issue", "edit"]  # lint-gh-argv-literal: ok fixture assertion
        ]
    ) == 1

    invalid = [
        ("[UMBRELLA] Renamed", original_body + "\n<!-- larch:umbrella-proposal -->\n"),
        ("[UMBRELLA] [BUG] Split this work", "replacement without original"),
        ("[UMBRELLA] [BUG] Split this work", original_body + "\nNo protected proposal record.\n"),
    ]
    for title, body in invalid:
        fresh = MutationRunner(title="[DESIGNING] [BUG] Split this work", body=original_body)
        with pytest.raises(issue_mutation.ProtectedIssueMutation, match="invalid-umbrella-conversion"):
            _ = issue_mutation.convert_managed_issue_to_umbrella(
                fresh,
                repository="owner/repo",
                issue="7",
                title=title,
                body=body,
            )

    spaced = MutationRunner(title="[IMPLEMENTING]  Preserve spacing", body=original_body)
    assert issue_mutation.convert_managed_issue_to_umbrella(
        spaced,
        repository="owner/repo",
        issue="7",
        title="[UMBRELLA]  Preserve spacing",
        body=original_body + "\n<!-- larch:umbrella-proposal -->\n",
    ).after.title == "[UMBRELLA]  Preserve spacing"

    for rejected in (
        MutationRunner(title="[DESIGNED] Split this work", body=original_body),
        MutationRunner(title="[IMPLEMENTING] Split this work", body=original_body, state="CLOSED"),
    ):
        with pytest.raises(issue_mutation.ProtectedIssueMutation, match="invalid-umbrella-conversion"):
            _ = issue_mutation.convert_managed_issue_to_umbrella(
                rejected,
                repository="owner/repo",
                issue="7",
                title="[UMBRELLA] Split this work",
                body=original_body + "\n<!-- larch:umbrella-proposal -->\n",
            )


def test_named_block_rejects_foreign_text_and_redaction_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = MutationRunner(body="prefix\n<!-- larch:plan:start -->\nold\n<!-- larch:plan:end -->\n")
    request = _request(
        runner,
        fields=frozenset({issue_mutation.MutationField.NAMED_BLOCK}),
        body="changed prefix\n<!-- larch:plan:start -->\nnew\n<!-- larch:plan:end -->\n",
        marker="plan",
    )
    with pytest.raises(issue_mutation.ProtectedIssueMutation, match="foreign-marker-or-body-change"):
        _ = issue_mutation.apply(runner, request)

    request = _request(
        runner,
        fields=frozenset({issue_mutation.MutationField.BODY}),
        body="new body",
    )
    def truncated_redaction(_value: str) -> str:
        return "[content truncated"

    monkeypatch.setattr(issue_mutation.redact, "redact_secrets_only", truncated_redaction)
    with pytest.raises(issue_mutation.ProtectedIssueMutation, match="redaction-failed"):
        _ = issue_mutation.apply(runner, request)


def test_implementation_lease_mutation_is_run_scoped_and_terminal_atomic() -> None:
    old = issue_wire.ImplementationLeaseMarker(
        run_id="run-7",
        branch="feature/owner",
        base="a" * 40,
        plan="b" * 64,
        updated_at="2026-07-19T00:00:00Z",
    )
    new = issue_wire.ImplementationLeaseMarker(
        run_id=old.run_id,
        branch=old.branch,
        base=old.base,
        plan=old.plan,
        updated_at="2026-07-19T01:00:00Z",
    )
    runner = MutationRunner(
        title="[IMPLEMENTING] Protected",
        body=issue_wire.upsert_implementation_lease(body="Body\n", lease=old),
    )
    body = issue_wire.upsert_implementation_lease(body=runner.body, lease=new)
    result = issue_mutation.update_implementation_lease(
        runner,
        repository="owner/repo",
        issue="7",
        body=body,
        run_id="run-7",
        title="[DONE] Protected",
    )
    assert result.after.title == "[DONE] Protected"
    assert issue_wire.parse_implementation_lease(body=result.after.body) == new
    assert sum(1 for call in runner.calls if tuple(call[:4]) == ("gh", "issue", "edit", "7")) == 1

    runner = MutationRunner(
        title="[IMPLEMENTING] Protected",
        body=issue_wire.upsert_implementation_lease(body="Body\n", lease=old),
    )
    with pytest.raises(issue_mutation.ProtectedIssueMutation, match="lease-run-mismatch"):
        _ = issue_mutation.update_implementation_lease(
            runner,
            repository="owner/repo",
            issue="7",
            body=body,
            run_id="other-run",
        )

    runner = MutationRunner(
        title="[IMPLEMENTING] Protected",
        body=issue_wire.upsert_implementation_lease(body="Body\n", lease=old),
    )
    expected = issue_mutation.read_snapshot(
        runner, repository="owner/repo", issue="7"
    )
    runner.title = "[IMPLEMENTING] Concurrent edit"
    runner.second += 1
    with pytest.raises(issue_mutation.ProtectedIssueMutation, match="stale-identity"):
        _ = issue_mutation.update_implementation_lease(
            runner,
            repository="owner/repo",
            issue="7",
            body=body,
            run_id="run-7",
            title="[DONE] Protected",
            expected_snapshot=expected,
        )
    assert runner.title == "[IMPLEMENTING] Concurrent edit"
