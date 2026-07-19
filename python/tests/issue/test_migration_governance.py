"""Offline fixtures for migration governance blocker parity and plan receipts."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from larch.core.proc import CommandResult
from larch.issue import issue_block, migration_governance as mg
from larch.issue.issue_wire import compose_named_block


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
        "CREATE\tfoo\tpython/larch/issue/migration_governance.py\n"
        "REUSE\tbar\t#12\tpython/larch/issue/issue_block.py\n"
        "CREATE\tfoo\tpython/larch/issue/migration_governance.py\n"
        "<!-- larch:owners:end -->\n"
        "```\n<!-- larch:owners:start -->\nCREATE\thidden\tx.py\n<!-- larch:owners:end -->\n```\n"
    )
    rows = mg.parse_owner_rows(body=body)
    assert rows == (
        "CREATE\tfoo\tpython/larch/issue/migration_governance.py",
        "REUSE\tbar\t#12\tpython/larch/issue/issue_block.py",
    )
    assert mg.owner_keys_from_rows(rows=rows) == ("bar", "foo")


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
    assert rows == ()
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
    import subprocess

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
