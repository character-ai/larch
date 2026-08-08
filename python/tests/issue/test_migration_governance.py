"""Offline fixtures for migration governance blocker parity and plan receipts."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from larch.core.proc import CommandResult
from larch.issue import issue_block, migration_governance as mg
from larch.issue.open_rows import OpenIssueRow
from larch.issue.issue_wire import compose_named_block

from test_support import RecordingRunner


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _plan_inner() -> str:
    return (
        "## Plan\n\n"
        "### Closed decisions and ownership\n\n"
        "- Fixture owns this plan.\n\n"
        "### Ordered implementation\n\n"
        "1. Apply the change.\n\n"
        "## Files to modify/create\n\n"
        "### UPDATED: README.md\n\n"
        "## Acceptance\n\n"
        "- Fixture acceptance holds.\n\n"
        "## Breaking changes and migration\n\n"
        "None.\n\n"
        "diff_lines: 12\n"
    )


def test_parse_native_blocker_exact_fields_only() -> None:
    body = (
        "Native blockers: #7780 and #7781.\n"
        "Blocked by #9\n"
        "Depends on #8\n"
        "```\nNative blocker: #1\n```\n"
        "Native blocker: #2.\n"
    )
    assert mg.parse_native_blocker_refs(body=body) == (2, 7780, 7781)


def test_parse_owner_rows_exact_block() -> None:
    body = (
        "prologue\n"
        "<!-- larch:owners:start -->\n"
        "COMMAND\tissue\tmigration-audit\n"
        "CREATE\tfoo\tpython/larch/issue/migration_governance.py\n"
        "REUSE\tbar\t#12\tpython/larch/issue/issue_block.py\n"
        "<!-- larch:owners:end -->\n"
        "```\n<!-- larch:owners:start -->\nCREATE\thidden\tx.py\n<!-- larch:owners:end -->\n```\n"
    )
    rows = mg.parse_owner_rows(body=body)
    assert rows == (
        "COMMAND\tissue\tmigration-audit",
        "CREATE\tfoo\tpython/larch/issue/migration_governance.py",
        "REUSE\tbar\t#12\tpython/larch/issue/issue_block.py",
    )
    assert mg.owner_keys_from_rows(rows=rows) == ("bar", "foo")


def test_command_audit_input_uses_canonical_owner_and_plan_parsers() -> None:
    registry = (
        mg.CommandAuditKey("git", "commit"),
        mg.CommandAuditKey("git", "stage"),
    )
    body = (
        _owner_block(
            "COMMAND\tgit\tcommit",
            "REUSE\tgit-owner\t#7735\tcrates/larch-cli/src/git_commands.rs",
        )
        + compose_named_block(
            marker="plan",
            inner=_plan_inner().replace(
                "1. Apply the change.",
                "1. Move `git commit` through the verified entrypoint.\n"
                "2. Do not treat `git stage-extra` as a selector mention.",
            ),
        )
    )

    row = mg.build_command_audit_issue(
        number=7735,
        state="OPEN",
        executable_leaf=True,
        body=body,
        registry_commands=registry,
    )

    assert row.command == mg.CommandAuditKey("git", "commit")
    assert row.plan_commands == (mg.CommandAuditKey("git", "commit"),)
    payload = json.loads(
        mg.render_command_audit_input(rows=(row,), rollout_enabled=True)
    )
    assert payload == {
        "schema_version": 1,
        "rollout_enabled": True,
        "issues": [
            {
                "number": 7735,
                "state": "open",
                "executable_leaf": True,
                "command": {"domain": "git", "verb": "commit"},
                "plan_commands": [{"domain": "git", "verb": "commit"}],
            }
        ],
    }


def test_command_audit_input_is_stable_and_rejects_duplicate_issues() -> None:
    first = mg.CommandAuditIssue(
        number=8, state="closed", executable_leaf=False, command=None, plan_commands=()
    )
    second = mg.CommandAuditIssue(
        number=7, state="open", executable_leaf=True, command=None, plan_commands=()
    )
    rendered = mg.render_command_audit_input(
        rows=(first, second), rollout_enabled=False
    )
    assert rendered == mg.render_command_audit_input(
        rows=(second, first), rollout_enabled=False
    )
    with pytest.raises(mg.ShipError, match="duplicate-command-audit-issue"):
        _ = mg.render_command_audit_input(
            rows=(first, first), rollout_enabled=False
        )


def test_blocker_parity_directions_and_closed_report_only() -> None:
    missing = mg.compare_blocker_parity(
        body_rows=(mg.BlockerSnapshotRow(10, "open", "t1"),),
        native_rows=(),
    )
    assert missing.blocking
    assert missing.reasons == ("missing-native-blocker-edge issue=#10",)

    undocumented = mg.compare_blocker_parity(
        body_rows=(),
        native_rows=(mg.BlockerSnapshotRow(11, "open", "t1"),),
    )
    assert undocumented.blocking
    assert undocumented.reasons == ("undocumented-native-blocker-edge issue=#11",)

    closed = mg.compare_blocker_parity(
        body_rows=(mg.BlockerSnapshotRow(12, "open", "t1"),),
        native_rows=(
            mg.BlockerSnapshotRow(12, "open", "t1"),
            mg.BlockerSnapshotRow(13, "closed", "t2"),
        ),
    )
    assert not closed.blocking
    assert closed.report_only == ("closed-blocker-edge-retained issue=#13",)


def test_hash_canonicalization_is_order_independent() -> None:
    rows_a = (
        mg.BlockerSnapshotRow(2, "open", "t2"),
        mg.BlockerSnapshotRow(1, "closed", "t1"),
    )
    rows_b = (
        mg.BlockerSnapshotRow(1, "closed", "t1"),
        mg.BlockerSnapshotRow(2, "open", "t2"),
    )
    assert mg.hash_blocker_rows(rows=rows_a) == mg.hash_blocker_rows(rows=rows_b)
    assert mg.hash_owner_rows(rows=("b", "a", "a")) == mg.hash_owner_rows(rows=("a", "b"))


def test_receipt_parse_render_upsert_roundtrip() -> None:
    plan_inner = _plan_inner()
    body = compose_named_block(marker="plan", inner=plan_inner)
    receipt = mg.PlanReceipt(
        plan_sha256=mg.hash_plan_block(plan_inner=plan_inner),
        base_sha="a" * 40,
        blockers_sha256=_sha(""),
        owners_sha256=_sha(""),
    )
    updated = mg.upsert_receipt(body=body, receipt=receipt)
    assert mg.parse_receipt(body=updated) == receipt
    assert updated.index("<!-- larch:plan:end -->") < updated.index("larch:plan-receipt")
    replaced = mg.upsert_receipt(
        body=updated,
        receipt=mg.PlanReceipt(
            plan_sha256=receipt.plan_sha256,
            base_sha="b" * 40,
            blockers_sha256=receipt.blockers_sha256,
            owners_sha256=receipt.owners_sha256,
        ),
    )
    assert replaced.count("larch:plan-receipt") == 1
    assert mg.parse_receipt(body=replaced) is not None
    assert mg.parse_receipt(body=replaced).base_sha == "b" * 40  # type: ignore[union-attr]


def test_load_blocker_snapshot_fail_closed_on_api_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(*_args: object, **_kwargs: object) -> list[issue_block.BlockedByDependency]:
        raise issue_block.DependencyReadError("api down")

    monkeypatch.setattr(issue_block, "read_blocked_by_dependencies", boom)
    rows, parity = mg.load_blocker_snapshot(
        object(),  # type: ignore[arg-type]
        issue="1",
        repo="o/r",
        body="Native blocker: #2.\n",
    )
    assert not rows
    assert parity.reasons == (mg.REASON_BLOCKER_READ_UNAVAILABLE,)
    assert parity.blocking


def test_freshness_detects_plan_owner_blocker_and_base_scope_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    readme = repo / "README.md"
    _ = readme.write_text("v1\n", encoding="utf-8")
    # Minimal git repo for ls-tree/rev-parse.
    _ = subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    _ = subprocess.run(["git", "add", "README.md"], cwd=repo, check=True, capture_output=True)
    _ = subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-m", "init"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    base_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()

    plan_inner = _plan_inner()
    owners = (
        "<!-- larch:owners:start -->\n"
        "CREATE\tfixture-owner\tREADME.md\n"
        "<!-- larch:owners:end -->\n"
    )
    body = (
        "Native blockers: none.\n"
        + compose_named_block(marker="plan", inner=plan_inner)
        + "\n"
        + owners
    )
    blocker_rows: tuple[mg.BlockerSnapshotRow, ...] = ()
    receipt = mg.PlanReceipt(
        plan_sha256=mg.hash_plan_block(plan_inner=plan_inner),
        base_sha=base_sha,
        blockers_sha256=mg.hash_blocker_rows(rows=blocker_rows),
        owners_sha256=mg.hash_owner_rows(rows=mg.parse_owner_rows(body=body)),
    )
    body = mg.upsert_receipt(body=body, receipt=receipt)

    class _GitRunner:
        def run(self, argv: list[str] | tuple[str, ...], **kwargs: object) -> CommandResult:
            completed = subprocess.run(
                list(argv),
                cwd=str(kwargs.get("cwd") or repo),
                capture_output=True,
                text=True,
                check=False,
            )
            return CommandResult(
                tuple(argv),
                completed.returncode,
                completed.stdout,
                completed.stderr,
                0.01,
            )

    runner = _GitRunner()
    ok = mg.validate_receipt_freshness(
        runner,  # type: ignore[arg-type]
        body=body,
        repo_root=repo,
        blocker_rows=blocker_rows,
        head_sha=base_sha,
    )
    assert ok.ok

    # Plan body edit
    edited_plan = plan_inner + "\n# drift\n"
    edited_body = mg.upsert_receipt(
        body=compose_named_block(marker="plan", inner=edited_plan) + "\n" + owners,
        receipt=receipt,
    )
    stale_plan = mg.validate_receipt_freshness(
        runner,  # type: ignore[arg-type]
        body=edited_body,
        repo_root=repo,
        blocker_rows=blocker_rows,
        head_sha=base_sha,
    )
    assert mg.REASON_STALE_PLAN_BODY in stale_plan.reasons

    # Owner edit
    owners2 = (
        "<!-- larch:owners:start -->\n"
        "CREATE\tother-owner\tREADME.md\n"
        "<!-- larch:owners:end -->\n"
    )
    owner_body = mg.upsert_receipt(
        body=compose_named_block(marker="plan", inner=plan_inner) + "\n" + owners2,
        receipt=receipt,
    )
    stale_owner = mg.validate_receipt_freshness(
        runner,  # type: ignore[arg-type]
        body=owner_body,
        repo_root=repo,
        blocker_rows=blocker_rows,
        head_sha=base_sha,
    )
    assert mg.REASON_STALE_OWNER_SNAPSHOT in stale_owner.reasons

    # Blocker snapshot drift
    stale_blocker = mg.validate_receipt_freshness(
        runner,  # type: ignore[arg-type]
        body=body,
        repo_root=repo,
        blocker_rows=(mg.BlockerSnapshotRow(9, "open", "t9"),),
        head_sha=base_sha,
    )
    assert mg.REASON_STALE_BLOCKER_SNAPSHOT in stale_blocker.reasons

    # In-scope change at HEAD vs base
    _ = readme.write_text("v2\n", encoding="utf-8")
    _ = subprocess.run(["git", "add", "README.md"], cwd=repo, check=True, capture_output=True)
    _ = subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-m", "change"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    head_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()
    stale_scope = mg.validate_receipt_freshness(
        runner,  # type: ignore[arg-type]
        body=body,
        repo_root=repo,
        blocker_rows=blocker_rows,
        head_sha=head_sha,
    )
    assert mg.REASON_STALE_PLAN_BASE_SCOPE in stale_scope.reasons

    # Unrelated main movement: add out-of-scope file, keep README at base content via...
    # Re-create a branch where README matches base but an unrelated file advanced HEAD.
    _ = subprocess.run(["git", "checkout", "-B", "unrelated", base_sha], cwd=repo, check=True, capture_output=True)
    other = repo / "OTHER.md"
    _ = other.write_text("other\n", encoding="utf-8")
    _ = subprocess.run(["git", "add", "OTHER.md"], cwd=repo, check=True, capture_output=True)
    _ = subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-m", "unrelated"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    unrelated_head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()
    still_ok = mg.validate_receipt_freshness(
        runner,  # type: ignore[arg-type]
        body=body,
        repo_root=repo,
        blocker_rows=blocker_rows,
        head_sha=unrelated_head,
    )
    assert still_ok.ok
    _ = monkeypatch  # reserved for future runner seams


def test_read_blocked_by_dependencies_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_read(*_a: object, **_k: object) -> CommandResult:
        return CommandResult(("gh",), 1, "", "boom", 0.01)

    monkeypatch.setattr("larch.git.gh.issue_blocked_by_read", fail_read)
    with pytest.raises(issue_block.DependencyReadError):
        _ = issue_block.read_blocked_by_dependencies(object(), "1", repo="o/r")  # type: ignore[arg-type]


def _owner_block(*rows: str) -> str:
    return "\n".join(("<!-- larch:owners:start -->", *rows, "<!-- larch:owners:end -->")) + "\n"


@pytest.mark.parametrize(
    "migration_text",
    [
        "No breaking changes to existing behavior.",
        "The change is additive and uses existing contracts.",
        "None.\n\nConfidence: high",
        "N/A.",
        "No migration is required.",
        "No new shared adapter is created.",
        "There is no need for a new shared adapter.",
        "Add a flag through the existing adapter.",
        "Create adapter tests for existing behavior.",
        "Add client compatibility through the existing adapter.",
    ],
)
def test_additive_migration_does_not_require_owner_block(migration_text: str) -> None:
    plan = _plan_inner().replace(
        "- Fixture owns this plan.",
        "- Reuse the existing command registry.",
    ).replace("None.\n\n", f"{migration_text}\n\n")

    assert not mg.migration_requires_owner_block(plan_inner=plan)


def test_additive_migration_passes_owner_admission_without_block() -> None:
    plan = _plan_inner().replace(
        "- Fixture owns this plan.",
        "- Reuse the existing command registry and typed adapter.",
    ).replace("None.\n\n", "No breaking changes to existing behavior.\n\n")
    body = compose_named_block(marker="plan", inner=plan)

    verdict = mg.evaluate_owner_admission(
        RecordingRunner(responses=[]), issue="7983", repo="o/r", body=body
    )

    assert verdict.ok


@pytest.mark.parametrize(
    "migration_text",
    [
        "Creates a new shared adapter for migration.",
        "Add a shared registry for command discovery.",
        "Introduce a typed runtime resolver.",
        "A state machine will be created for migration.",
        "Create a new shared\nadapter for migration.",
        "Create a shared adapter module for migration.",
        "No breaking changes and adds a new shared adapter.",
    ],
)
def test_affirmative_shared_owner_creation_requires_block(
    migration_text: str,
) -> None:
    plan = _plan_inner().replace("None.\n\n", f"{migration_text}\n\n")

    assert mg.migration_requires_owner_block(plan_inner=plan)


def test_migration_shared_owner_requires_block() -> None:
    plan = _plan_inner().replace(
        "None.\n\n", "Creates a new shared adapter for migration.\n\n"
    )
    body = compose_named_block(marker="plan", inner=plan)
    verdict = mg.evaluate_owner_admission(
        RecordingRunner(responses=[]), issue="7", repo="o/r", body=body
    )
    assert verdict.reasons == (mg.REASON_MISSING_OWNER_BLOCK,)


@pytest.mark.parametrize("active_title", ["[IMPLEMENTING] other", "[DESIGNED] pending"])
def test_active_create_conflicts_with_active_or_pending_reuse(
    active_title: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = _plan_inner()
    body = compose_named_block(marker="plan", inner=plan) + _owner_block(
        "COMMAND\tissue\tmigration-audit",
        "CREATE\tshared-owner\tpython/larch/issue/migration_governance.py",
    )
    active_body = _owner_block(
        "COMMAND\tissue\tother-command",
        "REUSE\tshared-owner\t#6\tpython/larch/issue/migration_governance.py",
    )
    active_body = mg.issue_wire.upsert_implementation_lease(
        body=active_body,
        lease=mg.issue_wire.ImplementationLeaseMarker(
            run_id="run-8",
            branch="feature/pending",
            base="a" * 40,
            plan="b" * 64,
            updated_at="2026-07-19T00:00:00Z",
        ),
    )
    active = OpenIssueRow(
        number=8,
        title=active_title,
        state="open",
        labels=(),
        body=active_body,
    )
    def read_open(*_args: object, **_kwargs: object) -> tuple[OpenIssueRow, ...]:
        return (active,)

    def no_stale(*_args: object, **_kwargs: object) -> tuple[()]:
        return ()

    monkeypatch.setattr(mg.open_rows, "open_issue_rows_read", read_open)
    monkeypatch.setattr(mg, "audit_stale_implementation_leases", no_stale)
    verdict = mg.evaluate_owner_admission(
        RecordingRunner(responses=[]), issue="7", repo="o/r", body=body
    )
    assert verdict.reasons == (
        "active-owner-conflict owner=shared-owner issue=#8",
    )


def test_reuse_source_requires_native_edge_and_owner_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_owners = _owner_block(
        "COMMAND\tissue\tmigration-audit",
        "CREATE\tshared-owner\tpython/larch/issue/migration_governance.py",
    )
    source_plan = _plan_inner()
    source_body = compose_named_block(marker="plan", inner=source_plan) + source_owners
    source_receipt = mg.PlanReceipt(
        plan_sha256=mg.hash_plan_block(plan_inner=source_plan),
        base_sha="a" * 40,
        blockers_sha256=mg.hash_blocker_rows(rows=()),
        owners_sha256=mg.hash_owner_rows(rows=mg.parse_owner_rows(body=source_body)),
    )
    source_body = mg.upsert_receipt(body=source_body, receipt=source_receipt)

    def fake_view(*_args: object, **_kwargs: object) -> CommandResult:
        return CommandResult(
            ("gh", "issue", "view"),
            0,
            json.dumps({"body": source_body, "state": "OPEN"}),
            "",
            0.01,
        )

    monkeypatch.setattr(mg.gh, "issue_view_field_read", fake_view)
    parsed = mg.issue_wire.parse_owner_block(
        body=_owner_block(
            "COMMAND\tissue\tconsumer",
            "REUSE\tshared-owner\t#6\tpython/larch/issue/migration_governance.py",
        )
    )
    assert parsed.block is not None
    reasons = mg._validate_reuse_sources(  # pyright: ignore[reportPrivateUsage]
        RecordingRunner(responses=[]), block=parsed.block, body="", repo="o/r", cwd=None
    )
    assert reasons == (
        "reuse-missing-native-blocker owner=shared-owner issue=#6",
    )
    source_body = compose_named_block(marker="plan", inner=source_plan) + source_owners
    reasons = mg._validate_reuse_sources(  # pyright: ignore[reportPrivateUsage]
        RecordingRunner(responses=[]), block=parsed.block, body="Native blocker: #6.\n", repo="o/r", cwd=None
    )
    assert reasons == (
        "reuse-owner-snapshot-invalid owner=shared-owner issue=#6",
    )


def test_stale_lease_watchdog_is_report_only_and_checks_open_pr() -> None:
    lease = mg.issue_wire.ImplementationLeaseMarker(
        run_id="run-1",
        branch="feature/shared-owner",
        base="a" * 40,
        plan="b" * 64,
        updated_at="2026-07-19T00:00:00Z",
    )
    active = OpenIssueRow(
        number=8,
        title="[IMPLEMENTING] other",
        state="open",
        labels=(),
        body=mg.issue_wire.upsert_implementation_lease(body="body\n", lease=lease),
    )
    runner = RecordingRunner(
        responses=[CommandResult(("gh", "pr", "list"), 0, "[]", "", 0.01)]
    )
    findings = mg.audit_stale_implementation_leases(
        runner,
        repo="o/r",
        active_rows=(active,),
        now=datetime(2026, 7, 19, 13, tzinfo=UTC),
    )
    assert len(findings) == 1
    assert findings[0].token == "stale-implementation-lease issue=#8 age_hours=13"
    assert findings[0].cleanup_command == (
        "scripts/larch.sh tracking-issue rename --issue 8 "
        "--state stalled --repo o/r --run-id run-1"
    )
    assert not any(call[1:3] == ["issue", "edit"] for call in runner.calls)

    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("gh", "pr", "list"),
                0,
                json.dumps([{"headRefName": "feature/shared-owner"}]),
                "",
                0.01,
            )
        ]
    )
    assert not mg.audit_stale_implementation_leases(
        runner,
        repo="o/r",
        active_rows=(active,),
        now=datetime(2026, 7, 19, 13, tzinfo=UTC),
    )
