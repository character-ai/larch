# pyright: reportPrivateUsage=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnusedCallResult=false
"""Standalone complete-umbrella leaf shipping tests."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from larch.core import config
from larch.core.proc import CommandResult
from larch.git import gh
from larch.implement import complete_umbrella_ship as leaf_ship
from test_support import RecordingRunner

if TYPE_CHECKING:
    from collections.abc import Callable


def _request(tmp_path: Path) -> leaf_ship.LeafShipRequest:
    handoff = tmp_path / "handoff"
    handoff.mkdir()
    return leaf_ship.LeafShipRequest(
        repository="owner/repo",
        repo_root=tmp_path,
        handoff_root=handoff,
        umbrella=40,
        leaf=42,
    )


def _pr(*, state: str = "OPEN") -> gh.PullRequest:
    return gh.PullRequest(
        number=77,
        url="https://github.com/owner/repo/pull/77",
        state=state,
        head_ref="complete-umbrella/leaf-42",
    )


_HEAD = "a" * 40


def test_leaf_titles_change_only_the_managed_prefix() -> None:
    original = "[LEAF OF 40] Preserve every other byte"
    active = leaf_ship._active_leaf_title(original, umbrella=40)

    assert (
        active == f"{config.TRACKING_ISSUE_PREFIX_BY_STATE['implementing']}{original}"
    )
    assert leaf_ship._active_leaf_title(active, umbrella=40) == active
    assert leaf_ship._done_leaf_title(active, umbrella=40) == (
        "[DONE] [LEAF OF 40] Preserve every other byte"
    )


def test_cli_help_is_success() -> None:
    assert leaf_ship.main(["--help"]) == config.EXIT_OK


@pytest.mark.parametrize(
    "title",
    [
        "ordinary title",
        "[LEAF OF 41] Wrong umbrella",
        "[DONE] [LEAF OF 40] Already done",
    ],
)
def test_active_leaf_title_rejects_unmanaged_lifecycle(title: str) -> None:
    with pytest.raises(leaf_ship.ShipError, match="exact managed leaf prefix"):
        _ = leaf_ship._active_leaf_title(title, umbrella=40)


def test_state_parser_rejects_duplicate_and_stale_identity(tmp_path: Path) -> None:
    request = _request(tmp_path)
    state = leaf_ship.LeafShipState(repository="owner/repo", umbrella=40, leaf=42)
    text = leaf_ship.larch_io.format_kvs(leaf_ship._state_rows(state))

    with pytest.raises(leaf_ship.ShipError, match="missing, unknown, or duplicate"):
        _ = leaf_ship._parse_state(request, f"{text}LEAF=42\n")
    with pytest.raises(leaf_ship.ShipError, match="identity does not match"):
        _ = leaf_ship._parse_state(request, text.replace("LEAF=42\n", "LEAF=43\n"))


def test_ci_wait_refreshes_only_after_exact_five_minute_delay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _request(tmp_path)
    statuses = iter((("pending", None), ("pass", None)))
    polls: list[int] = []
    sleeps: list[float] = []

    def checks_status(*_args: object, **kwargs: object) -> tuple[str, str | None]:
        pr_number = kwargs["pr"]
        assert isinstance(pr_number, int)
        polls.append(pr_number)
        return next(statuses)

    monkeypatch.setattr(leaf_ship.ci_monitor, "checks_status", checks_status)

    outcome = leaf_ship._wait_for_ci(
        RecordingRunner(),
        request,
        pr_number=77,
        sleep_fn=sleeps.append,
    )

    assert outcome.status == "pass"
    assert polls == [77, 77]
    assert sleeps == [float(config.COMPLETE_UMBRELLA_CI_POLL_INTERVAL_SEC)]
    assert sleeps == [300.0]


def test_merge_uses_verified_head_admin_squash_and_branch_deletion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _request(tmp_path)
    calls: list[tuple[str, object]] = []
    monkeypatch.setattr(
        leaf_ship.gh,
        "pr_merge_state",
        lambda *_args, **_kwargs: gh.MergeState(
            merge_state_status="CLEAN",
            head_ref_oid=_HEAD,
        ),
    )
    monkeypatch.setattr(
        leaf_ship.gh,
        "pr_checks_all_pass",
        lambda *_args, **_kwargs: True,
    )

    def merge(*_args: object, **kwargs: object) -> CommandResult:
        calls.extend(sorted(kwargs.items()))
        return CommandResult(("gh", "pr", "merge"), 0, "", "", 0.01)

    monkeypatch.setattr(leaf_ship.gh, "pr_merge", merge)
    monkeypatch.setattr(
        leaf_ship.gh,
        "pr_view",
        lambda *_args, **_kwargs: _pr(state="MERGED"),
    )

    merged = leaf_ship._merge_pr(
        RecordingRunner(),
        request,
        pull_request=_pr(),
        head_sha=_HEAD,
        sleep_fn=lambda _delay: None,
    )

    assert merged.state == "MERGED"
    assert ("merge_method", "squash") in calls
    assert ("admin", True) in calls
    assert ("delete_branch", True) in calls


def _stub_happy_ship(
    monkeypatch: pytest.MonkeyPatch,
    *,
    wait: leaf_ship.CiWaitOutcome,
    distill: Callable[..., Path] | None = None,
) -> None:
    monkeypatch.setattr(
        leaf_ship,
        "_push_branch",
        lambda *_args: ("complete-umbrella/leaf-42", _HEAD),
    )
    monkeypatch.setattr(leaf_ship, "_ensure_pr", lambda *_args, **_kwargs: _pr())
    monkeypatch.setattr(leaf_ship, "_wait_for_ci", lambda *_args, **_kwargs: wait)
    if distill is not None:
        monkeypatch.setattr(leaf_ship, "_distill_ci_failure", distill)


def test_ship_happy_path_persists_complete_only_after_verification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _request(tmp_path)
    leaf_ship._write_state(
        request,
        leaf_ship.LeafShipState(repository="owner/repo", umbrella=40, leaf=42),
    )
    _stub_happy_ship(monkeypatch, wait=leaf_ship.CiWaitOutcome(status="pass"))
    events: list[str] = []
    monkeypatch.setattr(
        leaf_ship,
        "_merge_pr",
        lambda *_args, **_kwargs: events.append("merge") or _pr(state="MERGED"),
    )
    monkeypatch.setattr(
        leaf_ship,
        "_finish_leaf_issue",
        lambda *_args, **_kwargs: events.append("finish-issue"),
    )
    monkeypatch.setattr(
        leaf_ship,
        "_sync_main_and_delete_branch",
        lambda *_args, **_kwargs: events.append("cleanup"),
    )

    def verify(*_args: object, **_kwargs: object) -> None:
        state = leaf_ship._read_state(request)
        assert state is not None
        assert state.status == "finalizing"
        events.append("verify")

    monkeypatch.setattr(leaf_ship, "_verify_complete", verify)

    outcome = leaf_ship.ship_leaf(
        RecordingRunner(), request, sleep_fn=lambda _delay: None
    )

    assert outcome.status == "complete"
    assert events == ["merge", "finish-issue", "cleanup", "verify"]
    persisted = leaf_ship._read_state(request)
    assert persisted is not None
    assert persisted.status == "complete"
    assert persisted.head_sha == _HEAD
    assert persisted.pr_number == 77
    assert persisted.ci_fix_attempts == 0


def test_ship_ci_failure_stops_before_merge_and_hands_off_bounded_digest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _request(tmp_path)
    leaf_ship._write_state(
        request,
        leaf_ship.LeafShipState(repository="owner/repo", umbrella=40, leaf=42),
    )
    errors_file = request.handoff_root / "ci-errors-991.md"
    errors_file.write_text("bounded evidence\n", encoding="utf-8")
    _stub_happy_ship(
        monkeypatch,
        wait=leaf_ship.CiWaitOutcome(status="fail", failed_run_id="991"),
        distill=lambda *_args, **_kwargs: errors_file,
    )
    monkeypatch.setattr(
        leaf_ship,
        "_merge_pr",
        lambda *_args, **_kwargs: pytest.fail("merge must not run after failed CI"),
    )

    outcome = leaf_ship.ship_leaf(
        RecordingRunner(), request, sleep_fn=lambda _delay: None
    )

    assert outcome.status == "ci_failed"
    assert outcome.ci_errors_file == str(errors_file)
    persisted = leaf_ship._read_state(request)
    assert persisted is not None
    assert persisted.status == "ci_failed"
    assert persisted.ci_errors_file == str(errors_file)


def test_merged_reentry_never_replays_premerge_mutations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _request(tmp_path)
    leaf_ship._write_state(
        request,
        leaf_ship.LeafShipState(
            repository="owner/repo",
            umbrella=40,
            leaf=42,
            branch="complete-umbrella/leaf-42",
            head_sha=_HEAD,
            pr_number=77,
            pr_url=_pr().url,
            status="monitoring",
        ),
    )
    monkeypatch.setattr(
        leaf_ship.gh, "pr_view", lambda *_args, **_kwargs: _pr(state="MERGED")
    )
    monkeypatch.setattr(leaf_ship.gh, "pr_base_ref", lambda *_args, **_kwargs: "main")
    monkeypatch.setattr(
        leaf_ship.gh,
        "pr_merge_state",
        lambda *_args, **_kwargs: gh.MergeState("CLEAN", _HEAD),
    )
    monkeypatch.setattr(
        leaf_ship,
        "_push_branch",
        lambda *_args, **_kwargs: pytest.fail("merged reentry must not push"),
    )
    monkeypatch.setattr(leaf_ship, "_finish_leaf_issue", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        leaf_ship,
        "_sync_main_and_delete_branch",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(leaf_ship, "_verify_complete", lambda *_args, **_kwargs: None)

    outcome = leaf_ship.ship_leaf(
        RecordingRunner(), request, sleep_fn=lambda _delay: None
    )

    assert outcome.status == "complete"


def test_merged_reentry_rejects_a_different_remote_head(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _request(tmp_path)
    leaf_ship._write_state(
        request,
        leaf_ship.LeafShipState(
            repository="owner/repo",
            umbrella=40,
            leaf=42,
            branch="complete-umbrella/leaf-42",
            head_sha=_HEAD,
            pr_number=77,
            pr_url=_pr().url,
            status="merged",
        ),
    )
    monkeypatch.setattr(
        leaf_ship.gh, "pr_view", lambda *_args, **_kwargs: _pr(state="MERGED")
    )
    monkeypatch.setattr(leaf_ship.gh, "pr_base_ref", lambda *_args, **_kwargs: "main")
    monkeypatch.setattr(
        leaf_ship.gh,
        "pr_merge_state",
        lambda *_args, **_kwargs: gh.MergeState("CLEAN", "b" * 40),
    )

    with pytest.raises(leaf_ship.ShipError, match="PR head changed"):
        _ = leaf_ship.ship_leaf(RecordingRunner(), request, sleep_fn=lambda _delay: None)


def test_state_rejects_a_branch_not_bound_to_the_leaf(tmp_path: Path) -> None:
    request = _request(tmp_path)
    with pytest.raises(leaf_ship.ShipError, match="branch does not match the leaf"):
        leaf_ship._write_state(
            request,
            leaf_ship.LeafShipState(
                repository="owner/repo",
                umbrella=40,
                leaf=42,
                branch="unrelated/branch",
                head_sha=_HEAD,
                pr_number=77,
                pr_url=_pr().url,
                status="monitoring",
            ),
        )


def test_ci_failed_reentry_requires_a_new_head_and_enforces_fix_cap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _request(tmp_path)
    errors_file = request.handoff_root / "ci-errors-1.md"
    errors_file.write_text("bounded evidence\n", encoding="utf-8")
    state = leaf_ship.LeafShipState(
        repository="owner/repo",
        umbrella=40,
        leaf=42,
        branch="complete-umbrella/leaf-42",
        head_sha="a" * 40,
        pr_number=77,
        pr_url=_pr().url,
        status="ci_failed",
        ci_errors_file=str(errors_file),
        ci_fix_attempts=config.COMPLETE_UMBRELLA_CI_FIX_ATTEMPTS,
    )
    leaf_ship._write_state(request, state)
    monkeypatch.setattr(leaf_ship.gh, "pr_view", lambda *_args, **_kwargs: _pr())
    monkeypatch.setattr(
        leaf_ship,
        "_push_branch",
        lambda *_args, **_kwargs: ("complete-umbrella/leaf-42", "b" * 40),
    )

    with pytest.raises(leaf_ship.ShipError, match="fix attempt cap reached"):
        _ = leaf_ship.ship_leaf(
            RecordingRunner(), request, sleep_fn=lambda _delay: None
        )

    leaf_ship._write_state(request, replace(state, ci_fix_attempts=0))
    monkeypatch.setattr(
        leaf_ship,
        "_push_branch",
        lambda *_args, **_kwargs: ("complete-umbrella/leaf-42", "a" * 40),
    )
    with pytest.raises(leaf_ship.ShipError, match="no fixer commit changed"):
        _ = leaf_ship.ship_leaf(
            RecordingRunner(), request, sleep_fn=lambda _delay: None
        )


def test_failed_ci_at_fix_cap_does_not_request_another_fixer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _request(tmp_path)
    errors_file = request.handoff_root / "ci-errors-991.md"
    errors_file.write_text("bounded evidence\n", encoding="utf-8")
    state = leaf_ship.LeafShipState(
        repository="owner/repo",
        umbrella=40,
        leaf=42,
        branch="complete-umbrella/leaf-42",
        head_sha=_HEAD,
        pr_number=77,
        pr_url=_pr().url,
        status="monitoring",
        ci_fix_attempts=config.COMPLETE_UMBRELLA_CI_FIX_ATTEMPTS,
    )
    leaf_ship._write_state(request, state)
    monkeypatch.setattr(leaf_ship.gh, "pr_view", lambda *_args, **_kwargs: _pr())
    _stub_happy_ship(
        monkeypatch,
        wait=leaf_ship.CiWaitOutcome(status="fail", failed_run_id="991"),
        distill=lambda *_args, **_kwargs: errors_file,
    )

    with pytest.raises(leaf_ship.ShipError, match="cap reached after failed CI"):
        _ = leaf_ship.ship_leaf(
            RecordingRunner(), request, sleep_fn=lambda _delay: None
        )

    persisted = leaf_ship._read_state(request)
    assert persisted is not None
    assert persisted.status == "ci_failed"
    assert persisted.ci_fix_attempts == config.COMPLETE_UMBRELLA_CI_FIX_ATTEMPTS
