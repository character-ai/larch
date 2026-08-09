"""Golden and transport tests for the read-only migration aggregate."""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pytest

from larch.core import proc
from larch.core.proc import CommandResult
from larch.errors import ShipError
from larch.issue import issue_wire, migration_governance as mg

from test_support import RecordingRunner


SNAPSHOT_TIME = "2026-07-19T12:00:00Z"


def _git_repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _ = (repo / "README.md").write_text("fixture\n", encoding="utf-8")
    _ = subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    _ = subprocess.run(["git", "add", "README.md"], cwd=repo, check=True, capture_output=True)
    _ = subprocess.run(
        ["git", "-c", "user.name=test", "-c", "user.email=t@t", "commit", "-m", "init"],
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
    return repo, head


def _plan() -> str:
    return (
        "## Plan\n\n"
        "### Closed decisions and ownership\n\n"
        "- Use the existing validator.\n\n"
        "### Ordered implementation\n\n"
        "1. Compose the report.\n\n"
        "## Files to modify/create\n\n"
        "### UPDATED: README.md\n\n"
        "## Acceptance\n\n"
        "- The report is stable.\n\n"
        "## Breaking changes and migration\n\n"
        "None.\n\n"
        "diff_lines: 10\n"
    )


def _valid_leaf(*, number: int, head: str) -> mg.MigrationIssueSnapshot:
    plan = _plan()
    body = (
        "Chief umbrella: #7687.\nNative blockers: none.\n"
        + issue_wire.compose_named_block(marker="plan", inner=plan)
    )
    receipt = mg.PlanReceipt(
        plan_sha256=mg.hash_plan_block(plan_inner=plan),
        base_sha=head,
        blockers_sha256=mg.hash_blocker_rows(rows=()),
        owners_sha256=mg.hash_owner_rows(rows=()),
    )
    return mg.MigrationIssueSnapshot(
        number=number,
        title=f"[LEAF OF 7779] Fixture {number}",
        state="open",
        body=mg.upsert_receipt(body=body, receipt=receipt),
        updated_at=SNAPSHOT_TIME,
    )


def _snapshot(
    *,
    head: str,
    open_issues: tuple[mg.MigrationIssueSnapshot, ...],
    referenced: tuple[mg.MigrationIssueSnapshot, ...] = (),
    dependencies: tuple[mg.DependencySnapshot, ...],
    closed_issues: tuple[mg.MigrationIssueSnapshot, ...] = (),
) -> mg.MigrationAuditSnapshot:
    return mg.MigrationAuditSnapshot(
        repository="owner/repo",
        chief_issue=7687,
        snapshot_timestamp=SNAPSHOT_TIME,
        head_sha=head,
        open_issues=open_issues,
        referenced_issues=referenced,
        dependencies=dependencies,
        open_pr_branches=frozenset(),
        tracked_paths=frozenset({"README.md"}),
        closed_issues=closed_issues,
    )


def test_empty_report_golden(tmp_path: Path) -> None:
    repo, head = _git_repo(tmp_path)
    leaf = _valid_leaf(number=10, head=head)
    report = mg.build_migration_audit_report(
        proc,
        snapshot=_snapshot(
            head=head,
            open_issues=(leaf,),
            dependencies=(mg.DependencySnapshot(issue=10, blockers=()),),
        ),
        repo_root=repo,
    )

    assert mg.render_migration_audit_json(report=report) == (
        '{"chief_issue":7687,"counts":{"active_owner_conflicts":0,'
        '"clean_install_coverage_gaps":0,"executable_leaves":1,'
        '"historical_managed_leaves":0,"historical_missing_plan_evidence":0,'
        '"historical_recorded_rust_line_budget_deviations":0,'
        '"historical_unverified_rust_line_budgets":0,'
        '"missing_caller_surfaces":0,"missing_or_stale_blockers":0,'
        '"production_runtime_escape_hatches":0,"python_retirement_violations":0,'
        '"registry_state_violations":0,"stale_implementation_leases":0,'
        '"valid_plans":1},"findings":[],"issues":[{"finding_reasons":[],'
        '"number":10,"plan_valid":true}],"repository":"owner/repo",'
        '"schema_version":2,"snapshot_timestamp":"2026-07-19T12:00:00Z"}\n'
    )


def test_mixed_report_counts_and_reordered_input_are_stable(tmp_path: Path) -> None:
    repo, head = _git_repo(tmp_path)
    valid = _valid_leaf(number=10, head=head)
    blocker = mg.MigrationIssueSnapshot(
        number=2,
        title="blocker",
        state="open",
        body="",
        updated_at=SNAPSHOT_TIME,
    )
    bad = mg.MigrationIssueSnapshot(
        number=11,
        title="[IMPLEMENTING] [LEAF OF 7779] Bad fixture",
        state="open",
        body="Chief umbrella: #7687.\nNative blocker: #2.\nsecret=fixture-secret\n",
        updated_at=SNAPSHOT_TIME,
    )
    repository_findings = (
        mg.AggregateFinding("production_runtime_escape_hatch", "runtime finding"),
        mg.AggregateFinding("clean_install_coverage_gap", "clean-install-coverage-missing x y"),
        mg.AggregateFinding("missing_caller_surface", "production caller x is missing from the ledger"),
        mg.AggregateFinding("python_retirement_violation", "python-entrypoint-still-called x: y"),
        mg.AggregateFinding("registry_state_violation", "non-atomic-rust-owner x y"),
    )
    first = _snapshot(
        head=head,
        open_issues=(valid, bad, blocker),
        dependencies=(
            mg.DependencySnapshot(issue=10, blockers=()),
            mg.DependencySnapshot(issue=11, blockers=()),
        ),
    )
    second = _snapshot(
        head=head,
        open_issues=(blocker, bad, valid),
        dependencies=tuple(reversed(first.dependencies)),
    )

    rendered: list[str] = []
    for snapshot in (first, second):
        report = mg.build_migration_audit_report(
            proc,
            snapshot=snapshot,
            repo_root=repo,
            repository_findings=tuple(reversed(repository_findings)),
        )
        rendered.append(mg.render_migration_audit_json(report=report))
    assert rendered[0] == rendered[1]
    payload = cast("dict[str, object]", json.loads(rendered[0]))
    assert payload["counts"] == {
        "active_owner_conflicts": 0,
        "clean_install_coverage_gaps": 1,
        "executable_leaves": 2,
        "historical_managed_leaves": 0,
        "historical_missing_plan_evidence": 0,
        "historical_recorded_rust_line_budget_deviations": 0,
        "historical_unverified_rust_line_budgets": 0,
        "missing_caller_surfaces": 1,
        "missing_or_stale_blockers": 2,
        "production_runtime_escape_hatches": 1,
        "python_retirement_violations": 1,
        "registry_state_violations": 1,
        "stale_implementation_leases": 0,
        "valid_plans": 1,
    }
    assert "fixture-secret" not in rendered[0]
    assert "secret=" not in rendered[0]


def test_historical_leaves_report_only_missing_plan_or_budget_evidence(
    tmp_path: Path,
) -> None:
    repo, head = _git_repo(tmp_path)
    missing_plan = mg.MigrationIssueSnapshot(
        number=12,
        title="[DONE] [LEAF OF 7779] Missing plan",
        state="closed",
        body="Chief umbrella: #7687.\n",
        updated_at=SNAPSHOT_TIME,
    )
    unverified_budget = mg.MigrationIssueSnapshot(
        number=13,
        title="[DONE] [LEAF OF 7779] No budget record",
        state="closed",
        body="Chief umbrella: #7687.\n" + issue_wire.compose_named_block(
            marker="plan", inner=_plan()
        ),
        updated_at=SNAPSHOT_TIME,
    )
    recorded_budget = mg.MigrationIssueSnapshot(
        number=14,
        title="[DONE] [LEAF OF 7779] Recorded budget",
        state="closed",
        body="Chief umbrella: #7687.\n"
        + issue_wire.compose_named_block(
            marker="plan",
            inner=_plan().replace(
                "diff_lines: 10\n",
                "## Rust line budget deviation\n\n"
                "- Split decision: retain this leaf as one PR\n"
                "- Rationale: The coupled public wire change could not split safely.\n"
                f"- Base SHA: {head}\n"
                f"- Head SHA: {head}\n"
                "- Added non-generated Rust lines: 1501\n\n"
                "diff_lines: 10\n",
            ),
        ),
        updated_at=SNAPSHOT_TIME,
    )
    parent = mg.MigrationIssueSnapshot(
        number=7779,
        title="[IMPLEMENTING] [UMBRELLA] Fixture",
        state="open",
        body="This umbrella is part of #7687, **[CHIEF UMBRELLA] Fixture**.\n",
        updated_at=SNAPSHOT_TIME,
    )
    inherited_chief = mg.MigrationIssueSnapshot(
        number=15,
        title="[DONE] [LEAF OF 7779] Chief inherited from parent",
        state="closed",
        body=(
            "This is a leaf of umbrella #7779. Read the umbrella in full before acting.\n"
            "\n"
            "This historical body predates an explicit Chief umbrella line.\n"
        ),
        updated_at=SNAPSHOT_TIME,
    )

    report = mg.build_migration_audit_report(
        proc,
        snapshot=_snapshot(
            head=head,
            open_issues=(parent,),
            closed_issues=(
                missing_plan,
                unverified_budget,
                recorded_budget,
                inherited_chief,
            ),
            dependencies=(),
        ),
        repo_root=repo,
    )

    payload = json.loads(mg.render_migration_audit_json(report=report))
    assert payload["counts"]["historical_managed_leaves"] == 4
    assert payload["counts"]["historical_missing_plan_evidence"] == 2
    assert payload["counts"]["historical_unverified_rust_line_budgets"] == 1
    assert payload["counts"]["historical_recorded_rust_line_budget_deviations"] == 1
    assert payload["counts"]["valid_plans"] == 0
    assert payload["issues"] == [
        {
            "finding_reasons": [
                "historical-plan-evidence-missing defects=missing-plan-block"
            ],
            "number": 12,
            "plan_valid": False,
        },
        {
            "finding_reasons": ["historical-rust-line-budget-unverified"],
            "number": 13,
            "plan_valid": True,
        },
        {"finding_reasons": [], "number": 14, "plan_valid": True},
        {
            "finding_reasons": [
                "historical-plan-evidence-missing defects=missing-plan-block"
            ],
            "number": 15,
            "plan_valid": False,
        },
    ]


def test_rust_line_budget_deviation_parser_is_fail_closed() -> None:
    valid = (
        "## Plan\n\n"
        "## Rust line budget deviation\n\n"
        "- Split decision: retain this leaf as one PR\n"
        "- Rationale: One atomic compatibility change remains coupled.\n"
        f"- Base SHA: {'a' * 40}\n"
        f"- Head SHA: {'b' * 40}\n"
        "- Added non-generated Rust lines: 1501\n"
    )
    parsed = mg.parse_rust_line_budget_deviation(plan_inner=valid)
    assert parsed.deviation == mg.RustLineBudgetDeviation(
        split_decision="retain this leaf as one PR",
        rationale="One atomic compatibility change remains coupled.",
        base_sha="a" * 40,
        head_sha="b" * 40,
        added_lines=1501,
    )
    assert not parsed.defects
    assert mg.parse_rust_line_budget_deviation(plan_inner="## Plan\n").deviation is None
    malformed = mg.parse_rust_line_budget_deviation(
        plan_inner="## Rust line budget deviation\n\n- Split decision: split it\n"
    )
    assert malformed.defects == ("malformed-rust-line-budget-deviation",)
    duplicate = mg.parse_rust_line_budget_deviation(
        plan_inner=valid + "\n## Rust line budget deviation\n"
    )
    assert duplicate.defects == ("multiple-rust-line-budget-deviations",)
    fenced_fields = mg.parse_rust_line_budget_deviation(
        plan_inner=(
            "## Rust line budget deviation\n\n```text\n"
            "- Split decision: retain this leaf as one PR\n"
            "- Rationale: A code example is not durable evidence.\n"
            f"- Base SHA: {'a' * 40}\n"
            f"- Head SHA: {'b' * 40}\n"
            "- Added non-generated Rust lines: 1501\n```\n"
        )
    )
    assert fenced_fields.defects == ("malformed-rust-line-budget-deviation",)


def test_stale_lease_includes_exact_cleanup_command(tmp_path: Path) -> None:
    repo, head = _git_repo(tmp_path)
    lease = issue_wire.ImplementationLeaseMarker(
        run_id="run-10",
        branch="issue-10",
        base="a" * 40,
        plan="b" * 64,
        updated_at="2026-07-18T12:00:00Z",
    )
    implementing = mg.MigrationIssueSnapshot(
        number=10,
        title="[IMPLEMENTING] Fixture",
        state="open",
        body=issue_wire.upsert_implementation_lease(body="", lease=lease),
        updated_at=SNAPSHOT_TIME,
    )

    report = mg.build_migration_audit_report(
        proc,
        snapshot=_snapshot(
            head=head,
            open_issues=(implementing,),
            dependencies=(),
        ),
        repo_root=repo,
    )

    payload = json.loads(mg.render_migration_audit_json(report=report))
    assert payload["counts"]["stale_implementation_leases"] == 1
    assert payload["findings"] == [
        {
            "category": "stale_implementation_lease",
            "cleanup_command": (
                "scripts/larch.sh tracking-issue rename --issue 10 "
                "--state stalled --repo owner/repo --run-id run-10"
            ),
            "issue": 10,
            "reason": "stale-implementation-lease issue=#10 age_hours=24",
        }
    ]


def test_snapshot_api_failure_is_required_evidence_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, _head = _git_repo(tmp_path)

    def fail(*_args: object, **_kwargs: object) -> list[object]:
        raise ShipError("api failed with secret=do-not-copy")

    monkeypatch.setattr(mg.gh, "issue_list_read", fail)
    with pytest.raises(mg.MigrationAuditError, match="issue snapshot unavailable"):
        _ = mg.load_migration_audit_snapshot(
            object(),  # type: ignore[arg-type]
            repository="owner/repo",
            chief_issue=7687,
            repo_root=repo,
        )


def test_snapshot_rejects_malformed_pull_request_evidence(
    tmp_path: Path,
) -> None:
    repo, head = _git_repo(tmp_path)
    runner = RecordingRunner(
        responses=[
            CommandResult(("gh", "issue", "list"), 0, "[]", "", 0.01),
            CommandResult(
                ("gh", "pr", "list"),
                0,
                '[{"headRefName":null}]',
                "",
                0.01,
            ),
            CommandResult(("git", "rev-parse", "HEAD"), 0, f"{head}\n", "", 0.01),
        ]
    )

    with pytest.raises(mg.MigrationAuditError, match="pull request snapshot unavailable"):
        _ = mg.load_migration_audit_snapshot(
            runner,
            repository="owner/repo",
            chief_issue=7687,
            repo_root=repo,
        )


def test_snapshot_transport_has_no_mutation_path(tmp_path: Path) -> None:
    repo, head = _git_repo(tmp_path)
    runner = RecordingRunner(
        responses=[
            CommandResult(("gh", "issue", "list"), 0, "[]", "", 0.01),
            CommandResult(("gh", "pr", "list"), 0, "[]", "", 0.01),
            CommandResult(("git", "rev-parse", "HEAD"), 0, f"{head}\n", "", 0.01),
            CommandResult(("git", "ls-files"), 0, "README.md\0", "", 0.01),
        ]
    )

    snapshot = mg.load_migration_audit_snapshot(
        runner,
        repository="owner/repo",
        chief_issue=7687,
        repo_root=repo,
        now=datetime(2026, 7, 19, 12, tzinfo=UTC),
    )

    assert not snapshot.open_issues
    issue_list = runner.calls[0]
    assert issue_list[issue_list.index("--state") + 1] == "all"
    flattened = "\n".join(" ".join(call) for call in runner.calls)
    assert " issue edit " not in f" {flattened} "
    assert " api graphql " not in f" {flattened} "
    assert " mutation" not in flattened.casefold()
    assert all(call[0] in {"gh", "git"} for call in runner.calls)


def test_repository_audit_invokes_installed_larch_binary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, head = _git_repo(tmp_path)
    registry = repo / "crates" / "larch-lint" / "data" / "command-registry.toml"
    registry.parent.mkdir(parents=True)
    _ = registry.write_text(
        '[[commands]]\ndomain = "issue"\nverb = "migration-audit"\n',
        encoding="utf-8",
    )
    runner = RecordingRunner.default_queue(
        CommandResult(("larch",), 0, "", "", 0.01)
    )

    def find_lint(name: str) -> str:
        assert name == "larch"
        return "/opt/bin/larch"

    monkeypatch.setattr(mg.shutil, "which", find_lint)

    findings = mg.collect_repository_audit_findings(
        runner,
        snapshot=_snapshot(head=head, open_issues=(), dependencies=()),
        repo_root=repo,
    )

    assert not findings
    assert runner.calls[0] == [
        "/opt/bin/larch",
        "lint",
        "--root",
        str(repo),
        "rule",
        "command-registry",
    ]
    assert runner.calls[1] == [
        "/opt/bin/larch",
        "lint",
        "--root",
        str(repo),
        "rule",
        "production-cargo-run",
    ]
    assert runner.calls[2][:7] == [
        "/opt/bin/larch",
        "lint",
        "--root",
        str(repo),
        "command-registry",
        "audit",
        "--input",
    ]
    assert len(runner.calls[2]) == 8


@pytest.mark.parametrize(
    ("repository_findings", "expected_status"),
    [
        ((), 0),
        ((mg.AggregateFinding("registry_state_violation", "fixture finding"),), 1),
    ],
)
def test_main_exit_statuses_and_machine_stdout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    repository_findings: tuple[mg.AggregateFinding, ...],
    expected_status: int,
) -> None:
    repo, head = _git_repo(tmp_path)
    snapshot = _snapshot(head=head, open_issues=(), dependencies=())

    def consumer_root(**_kwargs: object) -> Path:
        return repo

    def load_snapshot(*_args: object, **_kwargs: object) -> mg.MigrationAuditSnapshot:
        return snapshot

    def collect_findings(
        *_args: object, **_kwargs: object
    ) -> tuple[mg.AggregateFinding, ...]:
        return repository_findings

    monkeypatch.setattr(mg.repo_roots, "consumer_repo_root", consumer_root)
    monkeypatch.setattr(mg, "load_migration_audit_snapshot", load_snapshot)
    monkeypatch.setattr(mg, "collect_repository_audit_findings", collect_findings)

    status = mg.migration_audit_main(
        ["--repo", "owner/repo", "--chief", "7687", "--table-output", "none"]
    )

    captured = capsys.readouterr()
    assert status == expected_status
    assert json.loads(captured.out)["findings"] == [
        finding.as_dict() for finding in repository_findings
    ]
    assert captured.err == ""


def test_main_returns_two_for_required_evidence_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, head = _git_repo(tmp_path)
    snapshot = _snapshot(head=head, open_issues=(), dependencies=())

    def consumer_root(**_kwargs: object) -> Path:
        return repo

    def load_snapshot(*_args: object, **_kwargs: object) -> mg.MigrationAuditSnapshot:
        return snapshot

    monkeypatch.setattr(mg.repo_roots, "consumer_repo_root", consumer_root)
    monkeypatch.setattr(mg, "load_migration_audit_snapshot", load_snapshot)
    secret = "ghp_" + "a" * 36

    def fail(*_args: object, **_kwargs: object) -> tuple[mg.AggregateFinding, ...]:
        raise mg.MigrationAuditError(f"required evidence failed token={secret}")

    monkeypatch.setattr(mg, "collect_repository_audit_findings", fail)

    status = mg.migration_audit_main(
        ["--repo", "owner/repo", "--chief", "7687", "--table-output", "none"]
    )

    captured = capsys.readouterr()
    assert status == 2
    assert captured.out == ""
    assert "required evidence failed" in captured.err
    assert secret not in captured.err
