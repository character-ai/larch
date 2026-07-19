"""Contract tests for the freshness-checked issue mutation owner."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from larch.core.proc import CommandResult
from larch.issue import issue_mutation


@dataclass
class MutationRunner:
    title: str = "Regular issue"
    body: str = "Body"
    labels: set[str] = field(default_factory=set)
    state: str = "OPEN"
    second: int = 0
    advance_timestamp: bool = True
    edit_failure_after_apply: bool = False
    calls: list[list[str]] = field(default_factory=list)

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
        if args[:4] == ["gh", "issue", "view", "7"]:  # lint-gh-argv-literal: fixture assertion
            return CommandResult(tuple(args), 0, self._snapshot(), "", 0.01)
        if args[:4] == ["gh", "issue", "edit", "7"]:  # lint-gh-argv-literal: fixture assertion
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
    runner: MutationRunner, *, fields: frozenset[issue_mutation.MutationField], **kwargs: object
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
    monkeypatch.setattr(issue_mutation.redact, "redact_secrets_only", lambda _value: "[content truncated")
    with pytest.raises(issue_mutation.ProtectedIssueMutation, match="redaction-failed"):
        _ = issue_mutation.apply(runner, request)
