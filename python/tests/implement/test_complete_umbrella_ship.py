# pyright: reportPrivateUsage=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnusedCallResult=false
"""Standalone complete-umbrella leaf shipping tests."""

from __future__ import annotations

import subprocess
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from larch.core import config, proc
from larch.core.proc import CommandResult
from larch.git import gh
from larch.implement import complete_umbrella_ship as leaf_ship
from larch.issue import issue_wire
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


@pytest.fixture(autouse=True)
def _default_to_no_merge_queue(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        leaf_ship.gh,
        "default_branch_merge_queue_enabled",
        lambda *_args, **_kwargs: False,
    )


def _plan_body(inner: str) -> str:
    return issue_wire.compose_named_block(marker="plan", inner=inner)


def _valid_plan_inner() -> str:
    return (
        "## Plan\n\n"
        "### Closed decisions and ownership\n\n"
        "- Fixture owns the gate.\n\n"
        "### Ordered implementation\n\n"
        "1. Apply the fixture.\n\n"
        "## Files to modify/create\n\n"
        "### UPDATED: README.md\n\n"
        "## Acceptance\n\n"
        "- The fixture is accepted.\n\n"
        "## Breaking changes and migration\n\n"
        "None.\n\n"
        "diff_lines: 1\n"
    )


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


@pytest.mark.parametrize(
    ("body", "defect"),
    [
        ("", "missing-plan-block"),
        (
            _plan_body(_valid_plan_inner()) + _plan_body(_valid_plan_inner()),
            "multiple-plan-blocks",
        ),
        ("<!-- larch:plan:start -->\n", "missing-plan-block"),
    ],
)
def test_managed_leaf_admission_rejects_missing_duplicate_and_malformed_plans(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    body: str,
    defect: str,
) -> None:
    request = _request(tmp_path)
    monkeypatch.setattr(
        leaf_ship, "_is_chief_migration_umbrella", lambda *_args, **_kwargs: True
    )
    monkeypatch.setattr(leaf_ship.git, "ls_files", lambda *_args, **_kwargs: ("README.md",))

    with pytest.raises(leaf_ship.ShipError, match=defect):
        _ = leaf_ship._require_managed_leaf_plan(
            RecordingRunner(), request, issue_body=body
        )


def test_managed_leaf_admission_accepts_one_valid_plan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request = _request(tmp_path)
    monkeypatch.setattr(
        leaf_ship, "_is_chief_migration_umbrella", lambda *_args, **_kwargs: True
    )
    monkeypatch.setattr(leaf_ship.git, "ls_files", lambda *_args, **_kwargs: ("README.md",))

    assert leaf_ship._require_managed_leaf_plan(
        RecordingRunner(), request, issue_body=_plan_body(_valid_plan_inner())
    )


def test_prepare_refuses_a_managed_leaf_before_title_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request = _request(tmp_path)
    leaf = leaf_ship.issue_mutation.IssueSnapshot(
        repository="owner/repo",
        issue="42",
        title="[LEAF OF 40] Fixture",
        body="No plan exists.\n",
        labels=frozenset(),
        state="OPEN",
        updated_at="2026-08-09T00:00:00Z",
    )
    parent = leaf_ship.issue_mutation.IssueSnapshot(
        repository="owner/repo",
        issue="40",
        title="[IMPLEMENTING] [UMBRELLA] Fixture",
        body="#7 [CHIEF UMBRELLA]\n",
        labels=frozenset(),
        state="OPEN",
        updated_at="2026-08-09T00:00:00Z",
    )

    def read_snapshot(*_args: object, **kwargs: object) -> object:
        return leaf if kwargs["issue"] == "42" else parent

    monkeypatch.setattr(leaf_ship.issue_mutation, "read_snapshot", read_snapshot)
    monkeypatch.setattr(leaf_ship.git, "ls_files", lambda *_args, **_kwargs: ("README.md",))
    monkeypatch.setattr(
        leaf_ship.issue_mutation,
        "update_title",
        lambda *_args, **_kwargs: pytest.fail("title mutation must not run"),
    )

    with pytest.raises(leaf_ship.ShipError, match="missing-plan-block"):
        _ = leaf_ship.prepare_leaf(RecordingRunner(), request)


def test_rust_line_budget_counts_tests_and_skips_generated_renamed_and_deleted_rows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request = _request(tmp_path)
    numstat = (
        "2\t0\tsrc/live.rs\0"
        "1700\t0\tsrc/generated.rs\0"
        "0\t0\t\0src/old.rs\0src/moved.rs\0"
        "0\t4\tsrc/deleted.rs\0"
        "3\t0\ttests/only.rs\0"
    )
    monkeypatch.setattr(leaf_ship.git, "merge_base", lambda *_args, **_kwargs: "b" * 40)
    monkeypatch.setattr(
        leaf_ship.git,
        "diff_numstat_z",
        lambda *_args, **_kwargs: CommandResult(("git", "diff"), 0, numstat, "", 0.01),
    )

    def show_file(*args: object, **_kwargs: object) -> CommandResult:
        spec = args[1]
        assert isinstance(spec, str)
        source = "// Code generated by fixture\n" if spec.endswith("generated.rs") else "fn x() {}\n"
        return CommandResult(("git", "show"), 0, source, "", 0.01)

    monkeypatch.setattr(leaf_ship.git, "show_file", show_file)

    budget = leaf_ship._measure_rust_line_budget(
        RecordingRunner(), request, head_sha=_HEAD
    )

    assert budget.base_sha == "b" * 40
    assert budget.head_sha == _HEAD
    assert budget.added_lines == 5
    assert budget.added_lines < config.MANAGED_LEAF_RUST_LINE_LIMIT


def test_rust_line_budget_uses_a_fixed_rename_threshold() -> None:
    runner = RecordingRunner()

    _ = leaf_ship.git.diff_numstat_z(
        runner,
        "a" * 40,
        "b" * 40,
        find_renames=True,
    )

    assert runner.calls == [
        [
            "git",
            "diff",
            "--no-ext-diff",
            "--numstat",
            "-z",
            "-M50%",
            "a" * 40,
            "b" * 40,
        ]
    ]


def test_rust_line_budget_parses_git_rename_numstat_output(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    handoff = tmp_path / "handoff"
    handoff.mkdir()
    _ = subprocess.run(
        ["git", "init", "-b", "main"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    _ = subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    _ = subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    source = repo / "src"
    source.mkdir()
    tests = repo / "tests"
    tests.mkdir()
    (source / "live.rs").write_text("fn base() {}\n", encoding="utf-8")
    (source / "renamed.rs").write_text("fn renamed() {}\n", encoding="utf-8")
    (source / "deleted.rs").write_text("fn deleted() {}\n", encoding="utf-8")
    _ = subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    _ = subprocess.run(
        ["git", "commit", "-m", "base"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    base = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    _ = subprocess.run(
        ["git", "update-ref", "refs/remotes/origin/main", base],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    (source / "live.rs").write_text(
        "fn base() {}\nfn extra_one() {}\nfn extra_two() {}\n",
        encoding="utf-8",
    )
    (source / "generated.rs").write_text(
        "// Code generated by fixture\n" + "fn generated() {}\n" * 1700,
        encoding="utf-8",
    )
    (tests / "only.rs").write_text(
        "fn one() {}\nfn two() {}\nfn three() {}\n",
        encoding="utf-8",
    )
    _ = subprocess.run(
        ["git", "mv", "src/renamed.rs", "src/moved.rs"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    (source / "deleted.rs").unlink()
    _ = subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    _ = subprocess.run(
        ["git", "commit", "-m", "change"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    request = leaf_ship.LeafShipRequest(
        repository="owner/repo",
        repo_root=repo,
        handoff_root=handoff,
        umbrella=40,
        leaf=42,
    )

    budget = leaf_ship._measure_rust_line_budget(proc, request, head_sha=head)

    assert budget.base_sha == base
    assert budget.added_lines == 5


def test_rust_line_budget_reports_over_limit_and_blocks_merge(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request = _request(tmp_path)
    issue = leaf_ship.issue_mutation.IssueSnapshot(
        repository="owner/repo",
        issue="42",
        title="[IMPLEMENTING] [LEAF OF 40] Fixture",
        body=_plan_body(_valid_plan_inner()),
        labels=frozenset(),
        state="OPEN",
        updated_at="2026-08-09T00:00:00Z",
    )
    monkeypatch.setattr(
        leaf_ship,
        "_is_chief_migration_umbrella",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        leaf_ship,
        "_measure_rust_line_budget",
        lambda *_args, **_kwargs: leaf_ship.RustLineBudget("b" * 40, _HEAD, 1501),
    )
    monkeypatch.setattr(
        leaf_ship.issue_mutation, "read_snapshot", lambda *_args, **_kwargs: issue
    )

    outcome = leaf_ship._rust_line_budget_outcome(
        RecordingRunner(), request, head_sha=_HEAD
    )
    assert outcome.status == "deviation-required"
    assert outcome.budget is not None
    assert outcome.budget.added_lines > config.MANAGED_LEAF_RUST_LINE_LIMIT

    with pytest.raises(leaf_ship.ShipError, match="exceeds the Rust line budget"):
        leaf_ship._require_rust_line_budget(RecordingRunner(), request, head_sha=_HEAD)


def test_rust_line_budget_accepts_an_exact_durable_deviation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request = _request(tmp_path)
    plan = _valid_plan_inner().replace(
        "diff_lines: 1\n",
        "## Rust line budget deviation\n\n"
        "- Split decision: retain this leaf as one PR\n"
        "- Rationale: The atomic compatibility repair cannot split safely.\n"
        f"- Base SHA: {'b' * 40}\n"
        f"- Head SHA: {_HEAD}\n"
        "- Added non-generated Rust lines: 1501\n\n"
        "diff_lines: 1\n",
    )
    issue = leaf_ship.issue_mutation.IssueSnapshot(
        repository="owner/repo",
        issue="42",
        title="[IMPLEMENTING] [LEAF OF 40] Fixture",
        body=_plan_body(plan),
        labels=frozenset(),
        state="OPEN",
        updated_at="2026-08-09T00:00:00Z",
    )
    monkeypatch.setattr(
        leaf_ship,
        "_is_chief_migration_umbrella",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        leaf_ship,
        "_measure_rust_line_budget",
        lambda *_args, **_kwargs: leaf_ship.RustLineBudget("b" * 40, _HEAD, 1501),
    )
    monkeypatch.setattr(
        leaf_ship.issue_mutation, "read_snapshot", lambda *_args, **_kwargs: issue
    )

    outcome = leaf_ship._rust_line_budget_outcome(
        RecordingRunner(), request, head_sha=_HEAD
    )

    assert outcome.status == "deviation-recorded"


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
    monkeypatch.setattr(leaf_ship.gh, "pr_base_ref", lambda *_args, **_kwargs: "main")
    monkeypatch.setattr(
        leaf_ship, "_require_rust_line_budget", lambda *_args, **_kwargs: None
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

    assert merged.pull_request.state == "MERGED"
    assert merged.queued is False
    assert ("merge_method", "squash") in calls
    assert ("admin", True) in calls
    assert ("delete_branch", True) in calls


def test_merge_queue_submission_omits_admin_strategy_and_branch_deletion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _request(tmp_path)
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        leaf_ship.gh,
        "pr_merge_state",
        lambda *_args, **_kwargs: gh.MergeState("CLEAN", _HEAD),
    )
    monkeypatch.setattr(
        leaf_ship.gh,
        "pr_checks_all_pass",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(leaf_ship.gh, "pr_base_ref", lambda *_args, **_kwargs: "main")
    monkeypatch.setattr(
        leaf_ship,
        "_require_rust_line_budget",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        leaf_ship.gh,
        "default_branch_merge_queue_enabled",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        leaf_ship.gh,
        "confirm_pr_merge_queue_submission",
        lambda *_args, **_kwargs: gh.MergeQueueStatus("OPEN", "QUEUED"),
    )

    def merge(*_args: object, **kwargs: object) -> CommandResult:
        calls.append(dict(kwargs))
        return CommandResult(("gh", "pr", "merge"), 0, "", "", 0.01)

    monkeypatch.setattr(leaf_ship.gh, "pr_merge", merge)
    monkeypatch.setattr(leaf_ship.gh, "pr_view", lambda *_args, **_kwargs: _pr())

    outcome = leaf_ship._merge_pr(
        RecordingRunner(),
        request,
        pull_request=_pr(),
        head_sha=_HEAD,
        sleep_fn=lambda _delay: None,
    )

    assert outcome.queued is True
    assert outcome.pull_request.state == "OPEN"
    assert calls == [
        {
            "repo": "owner/repo",
            "merge_method": "squash",
            "admin": False,
            "delete_branch": False,
            "merge_queue": True,
            "cwd": str(tmp_path),
        },
    ]


def test_merge_refuses_an_over_limit_managed_leaf_before_admin_merge(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _request(tmp_path)
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
    monkeypatch.setattr(leaf_ship.gh, "pr_base_ref", lambda *_args, **_kwargs: "main")

    def refuse(*_args: object, **_kwargs: object) -> None:
        raise leaf_ship.ShipError("managed chief leaf exceeds the Rust line budget")

    monkeypatch.setattr(leaf_ship, "_require_rust_line_budget", refuse)
    monkeypatch.setattr(
        leaf_ship.gh,
        "pr_merge",
        lambda *_args, **_kwargs: pytest.fail("admin merge must not run"),
    )

    with pytest.raises(leaf_ship.ShipError, match="exceeds the Rust line budget"):
        _ = leaf_ship._merge_pr(
            RecordingRunner(),
            request,
            pull_request=_pr(),
            head_sha=_HEAD,
            sleep_fn=lambda _delay: None,
        )


def test_merge_rechecks_the_main_base_before_admin_merge(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _request(tmp_path)
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
        "pr_base_ref",
        lambda *_args, **_kwargs: "release",
    )
    monkeypatch.setattr(
        leaf_ship.gh,
        "pr_merge",
        lambda *_args, **_kwargs: pytest.fail("admin merge must not run"),
    )

    with pytest.raises(leaf_ship.ShipError, match="does not target main"):
        _ = leaf_ship._merge_pr(
            RecordingRunner(),
            request,
            pull_request=_pr(),
            head_sha=_HEAD,
            sleep_fn=lambda _delay: None,
        )


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
        lambda *_args, **_kwargs: events.append("merge")
        or leaf_ship.MergePrOutcome(pull_request=_pr(state="MERGED")),
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


def test_queued_reentry_waits_without_replaying_premerge_mutations(
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
            status="queued",
        ),
    )
    monkeypatch.setattr(leaf_ship.gh, "pr_view", lambda *_args, **_kwargs: _pr())
    monkeypatch.setattr(leaf_ship.gh, "pr_base_ref", lambda *_args, **_kwargs: "main")
    monkeypatch.setattr(
        leaf_ship.gh,
        "pr_merge_state",
        lambda *_args, **_kwargs: gh.MergeState("CLEAN", _HEAD),
    )
    monkeypatch.setattr(
        leaf_ship.ci_monitor,
        "wait_for_pr_merge",
        lambda *_args, **_kwargs: _pr(state="MERGED"),
    )
    monkeypatch.setattr(
        leaf_ship,
        "_push_branch",
        lambda *_args, **_kwargs: pytest.fail("queued reentry must not push"),
    )
    monkeypatch.setattr(
        leaf_ship,
        "_merge_pr",
        lambda *_args, **_kwargs: pytest.fail("queued reentry must not resubmit"),
    )
    monkeypatch.setattr(leaf_ship, "_finish_leaf_issue", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        leaf_ship,
        "_sync_main_and_delete_branch",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(leaf_ship, "_verify_complete", lambda *_args, **_kwargs: None)

    outcome = leaf_ship.ship_leaf(
        RecordingRunner(),
        request,
        sleep_fn=lambda _delay: None,
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
