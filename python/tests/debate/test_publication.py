"""GitHub lifecycle coverage for the public debate caller."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import pytest

from larch.core import config, proc
from larch.debate import publication
from larch.issue import issue_mutation


class _IssueStore:
    def __init__(self, title: str = "Choose a queue design") -> None:
        self.snapshot = issue_mutation.IssueSnapshot(
            repository="owner/repo",
            issue="17",
            title=title,
            body="Compare bounded and unbounded queues.",
            labels=frozenset(),
            state="OPEN",
            updated_at="2026-08-05T12:00:00Z",
        )

    def read(self, _runner: object, *, repository: str, issue: str) -> issue_mutation.IssueSnapshot:
        assert (repository, issue) == ("owner/repo", "17")
        return self.snapshot

    def apply(
        self, _runner: object, request: issue_mutation.IssueMutationRequest
    ) -> issue_mutation.VerifiedIssueMutation:
        before = self.snapshot
        assert request.expected_updated_at == before.updated_at
        assert request.title is not None
        self.snapshot = replace(
            before,
            title=request.title,
            updated_at="2026-08-05T12:00:01Z",
        )
        return issue_mutation.VerifiedIssueMutation(
            before=before,
            after=self.snapshot,
            fields=request.fields,
        )


def _install(store: _IssueStore, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(publication.issue_mutation, "read_snapshot", store.read)
    monkeypatch.setattr(publication.issue_mutation, "apply", store.apply)


def test_prepare_writes_sanitized_subject_and_owned_titles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = _IssueStore()
    _install(store, monkeypatch)

    metadata, subject_path = publication.prepare_issue(
        debate_tmpdir=tmp_path,
        repository="owner/repo",
        issue="17",
    )

    assert metadata.debating_title == "[DEBATING] Choose a queue design"
    assert metadata.debated_title == "[DEBATED] Choose a queue design"
    assert "Compare bounded and unbounded queues." in subject_path.read_text(encoding="utf-8")
    assert (tmp_path / "debate-source.json").is_file()


def test_title_lifecycle_is_freshness_checked_and_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = _IssueStore()
    _install(store, monkeypatch)
    _ = publication.prepare_issue(debate_tmpdir=tmp_path, repository="owner/repo", issue="17")

    changed, owned, _updated_at = publication.transition_title(
        debate_tmpdir=tmp_path, mode="start"
    )
    assert (changed, owned) == (True, True)
    changed, owned, _updated_at = publication.transition_title(
        debate_tmpdir=tmp_path, mode="start"
    )
    assert (changed, owned) == (False, True)

    changed, owned, _updated_at = publication.transition_title(
        debate_tmpdir=tmp_path, mode="finish"
    )
    assert (changed, owned) == (True, True)
    assert store.snapshot.title.startswith(config.DEBATE_TITLE_PREFIX_BY_STATE["DEBATED"])


def test_abort_restore_skips_a_foreign_title(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = _IssueStore()
    _install(store, monkeypatch)
    _ = publication.prepare_issue(debate_tmpdir=tmp_path, repository="owner/repo", issue="17")
    _ = publication.transition_title(debate_tmpdir=tmp_path, mode="start")
    store.snapshot = replace(
        store.snapshot,
        title="Operator-owned replacement",
        updated_at="2026-08-05T12:00:02Z",
    )

    changed, owned, _updated_at = publication.transition_title(
        debate_tmpdir=tmp_path, mode="restore"
    )

    assert (changed, owned) == (False, False)
    assert store.snapshot.title == "Operator-owned replacement"


def test_abort_restore_reinstates_owned_title_after_source_closes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = _IssueStore()
    _install(store, monkeypatch)
    _ = publication.prepare_issue(debate_tmpdir=tmp_path, repository="owner/repo", issue="17")
    _ = publication.transition_title(debate_tmpdir=tmp_path, mode="start")
    store.snapshot = replace(
        store.snapshot,
        state="CLOSED",
        updated_at="2026-08-05T12:00:02Z",
    )

    changed, owned, _updated_at = publication.transition_title(
        debate_tmpdir=tmp_path, mode="restore"
    )

    assert (changed, owned) == (True, True)
    assert store.snapshot.title == "Choose a queue design"


@pytest.mark.parametrize("prefix", ["[IMPLEMENTING]", "[debating]"])
def test_prepare_rejects_a_lifecycle_owned_issue(
    prefix: str,
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = _IssueStore(f"{prefix} busy")
    _install(store, monkeypatch)

    with pytest.raises(ValueError, match="protected lifecycle"):
        _ = publication.prepare_issue(
            debate_tmpdir=tmp_path,
            repository="owner/repo",
            issue="17",
        )


def test_proposal_body_links_back_to_the_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = _IssueStore()
    _install(store, monkeypatch)
    _ = publication.prepare_issue(debate_tmpdir=tmp_path, repository="owner/repo", issue="17")
    body = tmp_path / config.DEBATE_PROPOSAL_BODY_FILENAME
    _ = body.write_text("Use a bounded queue.\n", encoding="utf-8")

    linked = publication.link_proposal_body(
        debate_tmpdir=tmp_path,
        body_file=body,
    )

    text = linked.read_text(encoding="utf-8")
    assert text.startswith("Use a bounded queue.\n")
    assert "Source: [#17](https://github.com/owner/repo/issues/17)" in text


def test_proposal_link_rejects_a_noncanonical_body(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = _IssueStore()
    _install(store, monkeypatch)
    _ = publication.prepare_issue(debate_tmpdir=tmp_path, repository="owner/repo", issue="17")
    other = tmp_path / "other.md"
    _ = other.write_text("Unverified body.\n", encoding="utf-8")

    with pytest.raises(ValueError, match="unexpected debate artifact"):
        _ = publication.link_proposal_body(
            debate_tmpdir=tmp_path,
            body_file=other,
        )


def test_comment_verification_requires_exact_fresh_readback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = _IssueStore()
    _install(store, monkeypatch)
    _ = publication.prepare_issue(debate_tmpdir=tmp_path, repository="owner/repo", issue="17")
    marker = "<!-- larch:debate-aborted runid=test-run -->"
    content = tmp_path / "aborted-comment.md"
    _ = content.write_text(
        "The debate ended before proposal publication. No outcome was adopted.\n",
        encoding="utf-8",
    )
    body = f"{marker}\n\n{content.read_text(encoding='utf-8').rstrip()}"

    def read_comments(
        _runner: object,
        issue: str,
        *,
        repo: str,
        cwd: str | None = None,
    ) -> proc.CommandResult:
        assert (issue, repo, cwd) == ("17", "owner/repo", None)
        return proc.CommandResult(
            argv=("gh",),
            returncode=0,
            stdout=json.dumps([{"id": 91, "body": body}]),
            stderr="",
            duration=0,
        )

    monkeypatch.setattr(
        publication.gh,
        "issue_comments_list_read",
        read_comments,
    )

    assert publication.verify_comment(
        debate_tmpdir=tmp_path,
        marker=marker,
        content_file=content,
    ) == "91"


def test_comment_verification_rejects_a_mismatched_body(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = _IssueStore()
    _install(store, monkeypatch)
    _ = publication.prepare_issue(debate_tmpdir=tmp_path, repository="owner/repo", issue="17")
    marker = "<!-- larch:debate-proposal runid=test-run -->"
    content = tmp_path / "proposal-comment.md"
    _ = content.write_text("Proposal: #18\n", encoding="utf-8")

    def read_comments(
        _runner: object,
        issue: str,
        *,
        repo: str,
        cwd: str | None = None,
    ) -> proc.CommandResult:
        assert (issue, repo, cwd) == ("17", "owner/repo", None)
        return proc.CommandResult(
            argv=("gh",),
            returncode=0,
            stdout=json.dumps([{"id": 92, "body": f"{marker}\n\nforeign"}]),
            stderr="",
            duration=0,
        )

    monkeypatch.setattr(
        publication.gh,
        "issue_comments_list_read",
        read_comments,
    )

    with pytest.raises(ValueError, match="postcondition mismatch"):
        _ = publication.verify_comment(
            debate_tmpdir=tmp_path,
            marker=marker,
            content_file=content,
        )


@pytest.mark.parametrize(
    ("entrypoint", "operation"),
    [
        (publication.issue_prepare_main, "issue-prepare"),
        (publication.title_transition_main, "title-transition"),
        (publication.proposal_link_main, "proposal-link"),
        (publication.comment_verify_main, "comment-verify"),
    ],
)
def test_publication_usage_errors_emit_machine_envelopes(
    entrypoint: Callable[[list[str] | None], int],
    operation: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert entrypoint([]) != 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["operation"] == operation
