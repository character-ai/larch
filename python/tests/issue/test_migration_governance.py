"""Offline fixtures for migration governance blocker parity and plan receipts."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from larch.core.proc import CommandResult
from larch.errors import ShipError
from larch.issue import issue_block, issue_mutation, migration_governance as mg
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


def test_refresh_rust_line_budget_deviation_preserves_decision_and_rationale() -> None:
    plan = _plan_inner().replace(
        "diff_lines: 12\n",
        "## Rust line budget deviation\n\n"
        "- Split decision: retain this leaf as one PR\n"
        "- Rationale: The atomic migration and compatibility repair share one boundary.\n"
        f"- Base SHA: {'a' * 40}\n"
        f"- Head SHA: {'b' * 40}\n"
        "- Added non-generated Rust lines: 1501\n"
        "- Preserved note: this text is not a measurement field.\n\n"
        "diff_lines: 12\n",
    )

    refreshed = mg.refresh_rust_line_budget_deviation(
        plan_inner=plan,
        base_sha="c" * 40,
        head_sha="d" * 40,
        added_lines=1503,
    )

    parsed = mg.parse_rust_line_budget_deviation(plan_inner=refreshed)
    assert parsed.defects == ()
    assert parsed.deviation == mg.RustLineBudgetDeviation(
        split_decision="retain this leaf as one PR",
        rationale="The atomic migration and compatibility repair share one boundary.",
        base_sha="c" * 40,
        head_sha="d" * 40,
        added_lines=1503,
    )
    assert "- Preserved note: this text is not a measurement field.\n" in refreshed
    with pytest.raises(ShipError, match="missing or malformed"):
        _ = mg.refresh_rust_line_budget_deviation(
            plan_inner=_plan_inner(),
            base_sha="c" * 40,
            head_sha="d" * 40,
            added_lines=1503,
        )


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
    assert mg.hash_owner_rows(rows=("b", "a", "a")) == mg.hash_owner_rows(
        rows=("a", "b")
    )


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
    assert updated.index("<!-- larch:plan:end -->") < updated.index(
        "larch:plan-receipt"
    )
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


def test_missing_receipt_is_advisory_but_a_malformed_receipt_still_blocks(
    tmp_path: Path,
) -> None:
    body = compose_named_block(marker="plan", inner=_plan_inner())
    missing = mg.validate_receipt_freshness(
        object(),  # type: ignore[arg-type]
        body=body,
        repo_root=tmp_path,
        blocker_rows=(),
    )
    assert missing.ok
    assert missing.reasons == ()

    malformed = mg.validate_receipt_freshness(
        object(),  # type: ignore[arg-type]
        body=body + "\n<!-- larch:plan-receipt -->\n",
        repo_root=tmp_path,
        blocker_rows=(),
    )
    assert malformed.reasons == (mg.REASON_STALE_PLAN_BODY,)

    valid = mg.upsert_receipt(
        body=body,
        receipt=mg.PlanReceipt(
            plan_sha256=mg.hash_plan_block(plan_inner=_plan_inner()),
            base_sha="a" * 40,
            blockers_sha256=mg.hash_blocker_rows(rows=()),
            owners_sha256=mg.hash_owner_rows(rows=()),
        ),
    )
    assert mg.parse_receipt(body=valid + "<!-- larch:plan-receipt -->\n") is None


def test_scope_drift_requires_preflight_semantic_revalidation() -> None:
    scope_only = mg.FreshnessVerdict(reasons=(mg.REASON_STALE_PLAN_BASE_SCOPE,))
    assert not scope_only.ok
    assert scope_only.hard_reasons == ()
    assert scope_only.semantic_revalidation_reasons == (
        mg.REASON_STALE_PLAN_BASE_SCOPE,
    )
    assert scope_only.scope_revalidation_only

    mixed = mg.FreshnessVerdict(
        reasons=(mg.REASON_STALE_PLAN_BASE_SCOPE, mg.REASON_STALE_PLAN_BODY)
    )
    assert not mixed.ok
    assert mixed.hard_reasons == (mg.REASON_STALE_PLAN_BODY,)
    assert not mixed.scope_revalidation_only


def test_plan_receipt_refresh_cli_persists_the_checked_base_sha(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    preflight_tmpdir = tmp_path / "preflight"
    preflight_tmpdir.mkdir()
    plan_inner = _plan_inner()
    _ = (preflight_tmpdir / "plan-from-issue.txt").write_text(
        plan_inner, encoding="utf-8"
    )
    prior_receipt = mg.PlanReceipt(
        plan_sha256=mg.hash_plan_block(plan_inner=plan_inner),
        base_sha="a" * 40,
        blockers_sha256="c" * 64,
        owners_sha256="d" * 64,
    )
    preflight_body = mg.upsert_receipt(
        body=compose_named_block(marker="plan", inner=plan_inner),
        receipt=prior_receipt,
    )
    _ = (preflight_tmpdir / "issue.json").write_text(
        json.dumps({"number": 7, "body": preflight_body}), encoding="utf-8"
    )
    receipt = mg.PlanReceipt(
        plan_sha256=mg.hash_plan_block(plan_inner=plan_inner),
        base_sha="b" * 40,
        blockers_sha256="c" * 64,
        owners_sha256="d" * 64,
    )
    captured: dict[str, object] = {}

    def persist(
        _runner: object,
        *,
        issue: str,
        repo: str,
        repo_root: Path,
        base_sha: str | None = None,
        expected_plan_sha256: str | None = None,
        expected_prior_receipt: mg.PlanReceipt | None = None,
        cwd: str | None = None,
    ) -> mg.PlanReceipt:
        captured.update(
            issue=issue,
            repo=repo,
            repo_root=repo_root,
            base_sha=base_sha,
            expected_plan_sha256=expected_plan_sha256,
            expected_prior_receipt=expected_prior_receipt,
            cwd=cwd,
        )
        return receipt

    refreshed_body = mg.upsert_receipt(
        body=compose_named_block(marker="plan", inner=plan_inner), receipt=receipt
    )

    def read_snapshot(
        _runner: object, *, repository: str, issue: str, cwd: str | None = None
    ) -> issue_mutation.IssueSnapshot:
        assert (repository, issue, cwd) == ("owner/repo", "7", str(tmp_path))
        return issue_mutation.IssueSnapshot(
            repository=repository,
            issue=issue,
            title="[DESIGNED] Work",
            body=refreshed_body,
            labels=frozenset({"ready"}),
            state="OPEN",
            updated_at="2026-08-13T00:00:00Z",
        )

    def rev_parse(_runner: object, ref: str, *, cwd: str | None = None) -> str:
        assert (ref, cwd) == ("origin/main", str(tmp_path))
        return "b" * 40

    def render_scope_drift(
        _runner: object,
        *,
        previous_base_sha: str,
        target_base_sha: str,
        plan_inner: str,
        cwd: str,
    ) -> str:
        assert (previous_base_sha, target_base_sha, plan_inner, cwd) == (
            "a" * 40,
            "b" * 40,
            _plan_inner(),
            str(tmp_path),
        )
        return "- receipt scope drift\n"

    monkeypatch.setattr(mg, "persist_plan_receipt", persist)
    monkeypatch.setattr(issue_mutation, "read_snapshot", read_snapshot)
    monkeypatch.setattr(mg.git, "rev_parse", rev_parse)
    monkeypatch.setattr(mg, "_render_preflight_scope_drift", render_scope_drift)
    assert (
        mg.plan_receipt_refresh_main(
            [
                "--issue",
                "7",
                "--repo",
                "owner/repo",
                "--repo-root",
                str(tmp_path),
                "--preflight-tmpdir",
                str(preflight_tmpdir),
                "--base-ref",
                "origin/main",
                "--previous-base-sha",
                "a" * 40,
                "--base-sha",
                "b" * 40,
            ]
        )
        == 0
    )
    assert captured == {
        "issue": "7",
        "repo": "owner/repo",
        "repo_root": tmp_path,
        "base_sha": "b" * 40,
        "expected_plan_sha256": mg.hash_plan_block(plan_inner=plan_inner),
        "expected_prior_receipt": prior_receipt,
        "cwd": str(tmp_path),
    }
    assert capsys.readouterr().out == (
        "PLAN_RECEIPT_REFRESHED=true\n"
        f"PLAN_RECEIPT_BASE_SHA={'b' * 40}\n"
        "PLAN_RECEIPT_SNAPSHOT_UPDATED=true\n"
        "PLAN_RECEIPT_SCOPE_DRIFT_LOGGED=true\n"
    )
    snapshot = json.loads((preflight_tmpdir / "issue.json").read_text(encoding="utf-8"))
    assert snapshot == {
        "body": refreshed_body,
        "labels": [{"name": "ready"}],
        "number": 7,
        "state": "OPEN",
        "title": "[DESIGNED] Work",
        "updatedAt": "2026-08-13T00:00:00Z",
    }
    assert (preflight_tmpdir / "receipt-scope-drift.md").read_text(
        encoding="utf-8"
    ) == "- receipt scope drift\n"


def test_plan_receipt_refresh_cli_resolves_the_local_repository(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preflight_tmpdir = tmp_path / "preflight"
    preflight_tmpdir.mkdir()
    plan_inner = _plan_inner()
    _ = (preflight_tmpdir / "plan-from-issue.txt").write_text(
        plan_inner, encoding="utf-8"
    )
    prior_receipt = mg.PlanReceipt(
        plan_sha256=mg.hash_plan_block(plan_inner=plan_inner),
        base_sha="a" * 40,
        blockers_sha256="c" * 64,
        owners_sha256="d" * 64,
    )
    _ = (preflight_tmpdir / "issue.json").write_text(
        json.dumps(
            {
                "number": 7,
                "body": mg.upsert_receipt(
                    body=compose_named_block(marker="plan", inner=plan_inner),
                    receipt=prior_receipt,
                ),
            }
        ),
        encoding="utf-8",
    )
    receipt = mg.PlanReceipt(
        plan_sha256=mg.hash_plan_block(plan_inner=plan_inner),
        base_sha="b" * 40,
        blockers_sha256="c" * 64,
        owners_sha256="d" * 64,
    )
    repositories: list[str] = []

    def persist(
        _runner: object,
        *,
        issue: str,
        repo: str,
        repo_root: Path,
        base_sha: str | None = None,
        expected_plan_sha256: str | None = None,
        expected_prior_receipt: mg.PlanReceipt | None = None,
        cwd: str | None = None,
    ) -> mg.PlanReceipt:
        _ = (
            issue,
            repo_root,
            base_sha,
            expected_plan_sha256,
            expected_prior_receipt,
            cwd,
        )
        repositories.append(repo)
        return receipt

    def resolve_repo(_runner: object, *, cwd: str | None = None) -> str:
        assert cwd == str(tmp_path)
        return "owner/repo"

    def write_snapshot(*_args: object, **_kwargs: object) -> None:
        return None

    def rev_parse(_runner: object, ref: str, *, cwd: str | None = None) -> str:
        assert (ref, cwd) == ("origin/main", str(tmp_path))
        return "b" * 40

    def render_scope_drift(*_args: object, **_kwargs: object) -> str:
        return "- receipt scope drift\n"

    monkeypatch.setattr(mg, "persist_plan_receipt", persist)
    monkeypatch.setattr(mg.gh, "resolve_repo", resolve_repo)
    monkeypatch.setattr(mg, "_write_refreshed_preflight_snapshot", write_snapshot)
    monkeypatch.setattr(mg.git, "rev_parse", rev_parse)
    monkeypatch.setattr(mg, "_render_preflight_scope_drift", render_scope_drift)
    assert (
        mg.plan_receipt_refresh_main(
            [
                "--issue",
                "7",
                "--repo-root",
                str(tmp_path),
                "--preflight-tmpdir",
                str(preflight_tmpdir),
                "--base-ref",
                "origin/main",
                "--previous-base-sha",
                "a" * 40,
                "--base-sha",
                "b" * 40,
            ]
        )
        == 0
    )
    assert repositories == ["owner/repo"]


def test_plan_receipt_refresh_cli_rejects_an_invalid_resolved_repository(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    preflight_tmpdir = tmp_path / "preflight"
    preflight_tmpdir.mkdir()
    _ = (preflight_tmpdir / "plan-from-issue.txt").write_text(
        _plan_inner(), encoding="utf-8"
    )

    def persist(*_args: object, **_kwargs: object) -> mg.PlanReceipt:
        pytest.fail("receipt persistence must not run for an invalid repository")

    def resolve_repo(_runner: object, *, cwd: str | None = None) -> str:
        _ = cwd
        return "owner/repo/extra"

    monkeypatch.setattr(mg, "persist_plan_receipt", persist)
    monkeypatch.setattr(mg.gh, "resolve_repo", resolve_repo)
    assert (
        mg.plan_receipt_refresh_main(
            [
                "--issue",
                "7",
                "--repo-root",
                str(tmp_path),
                "--preflight-tmpdir",
                str(preflight_tmpdir),
                "--base-ref",
                "origin/main",
                "--previous-base-sha",
                "a" * 40,
                "--base-sha",
                "b" * 40,
            ]
        )
        == 2
    )
    output = capsys.readouterr()
    assert output.out == "PLAN_RECEIPT_REFRESHED=false\n"
    assert "--repo must be exactly owner/name" in output.err


def test_plan_receipt_refresh_cli_refuses_when_the_reviewed_base_moved(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    preflight_tmpdir = tmp_path / "preflight"
    preflight_tmpdir.mkdir()
    _ = (preflight_tmpdir / "plan-from-issue.txt").write_text(
        _plan_inner(), encoding="utf-8"
    )

    def persist(*_args: object, **_kwargs: object) -> mg.PlanReceipt:
        pytest.fail("receipt persistence must not run after base movement")

    def moved_rev_parse(*_args: object, **_kwargs: object) -> str:
        return "a" * 40

    monkeypatch.setattr(mg, "persist_plan_receipt", persist)
    monkeypatch.setattr(mg.git, "rev_parse", moved_rev_parse)
    assert (
        mg.plan_receipt_refresh_main(
            [
                "--issue",
                "7",
                "--repo",
                "owner/repo",
                "--repo-root",
                str(tmp_path),
                "--preflight-tmpdir",
                str(preflight_tmpdir),
                "--base-ref",
                "origin/main",
                "--previous-base-sha",
                "a" * 40,
                "--base-sha",
                "b" * 40,
            ]
        )
        == 2
    )
    output = capsys.readouterr()
    assert output.out == "PLAN_RECEIPT_REFRESHED=false\n"
    assert "plan-receipt-refresh-base-moved" in output.err


def test_plan_receipt_refresh_cli_rechecks_base_before_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    preflight_tmpdir = tmp_path / "preflight"
    preflight_tmpdir.mkdir()
    plan_inner = _plan_inner()
    _ = (preflight_tmpdir / "plan-from-issue.txt").write_text(
        plan_inner, encoding="utf-8"
    )
    prior_receipt = mg.PlanReceipt(
        plan_sha256=mg.hash_plan_block(plan_inner=plan_inner),
        base_sha="a" * 40,
        blockers_sha256="c" * 64,
        owners_sha256="d" * 64,
    )
    _ = (preflight_tmpdir / "issue.json").write_text(
        json.dumps(
            {
                "number": 7,
                "body": mg.upsert_receipt(
                    body=compose_named_block(marker="plan", inner=plan_inner),
                    receipt=prior_receipt,
                ),
            }
        ),
        encoding="utf-8",
    )
    revisions = iter(("b" * 40, "c" * 40))

    def rev_parse(_runner: object, _ref: str, *, cwd: str | None = None) -> str:
        assert cwd == str(tmp_path)
        return next(revisions)

    def persist(*_args: object, **_kwargs: object) -> mg.PlanReceipt:
        pytest.fail("receipt persistence must not run after base movement")

    def render_scope_drift(*_args: object, **_kwargs: object) -> str:
        return "drift\n"

    monkeypatch.setattr(mg.git, "rev_parse", rev_parse)
    monkeypatch.setattr(mg, "persist_plan_receipt", persist)
    monkeypatch.setattr(mg, "_render_preflight_scope_drift", render_scope_drift)
    assert (
        mg.plan_receipt_refresh_main(
            [
                "--issue",
                "7",
                "--repo",
                "owner/repo",
                "--repo-root",
                str(tmp_path),
                "--preflight-tmpdir",
                str(preflight_tmpdir),
                "--base-ref",
                "origin/main",
                "--previous-base-sha",
                "a" * 40,
                "--base-sha",
                "b" * 40,
            ]
        )
        == 2
    )
    output = capsys.readouterr()
    assert output.out == "PLAN_RECEIPT_REFRESHED=false\n"
    assert "plan-receipt-refresh-base-moved" in output.err


def test_plan_receipt_refresh_cli_refuses_a_changed_preflight_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    preflight_tmpdir = tmp_path / "preflight"
    preflight_tmpdir.mkdir()
    plan_inner = _plan_inner()
    _ = (preflight_tmpdir / "plan-from-issue.txt").write_text(
        plan_inner, encoding="utf-8"
    )
    mismatched_receipt = mg.PlanReceipt(
        plan_sha256=mg.hash_plan_block(plan_inner=plan_inner),
        base_sha="c" * 40,
        blockers_sha256="d" * 64,
        owners_sha256="e" * 64,
    )
    _ = (preflight_tmpdir / "issue.json").write_text(
        json.dumps(
            {
                "number": 7,
                "body": mg.upsert_receipt(
                    body=compose_named_block(marker="plan", inner=plan_inner),
                    receipt=mismatched_receipt,
                ),
            }
        ),
        encoding="utf-8",
    )

    def persist(*_args: object, **_kwargs: object) -> mg.PlanReceipt:
        pytest.fail("receipt persistence must not run with an unreviewed receipt")

    def current_rev_parse(*_args: object, **_kwargs: object) -> str:
        return "b" * 40

    monkeypatch.setattr(mg, "persist_plan_receipt", persist)
    monkeypatch.setattr(mg.git, "rev_parse", current_rev_parse)
    assert (
        mg.plan_receipt_refresh_main(
            [
                "--issue",
                "7",
                "--repo",
                "owner/repo",
                "--repo-root",
                str(tmp_path),
                "--preflight-tmpdir",
                str(preflight_tmpdir),
                "--base-ref",
                "origin/main",
                "--previous-base-sha",
                "a" * 40,
                "--base-sha",
                "b" * 40,
            ]
        )
        == 2
    )
    output = capsys.readouterr()
    assert output.out == "PLAN_RECEIPT_REFRESHED=false\n"
    assert "preflight receipt base does not match scope revalidation" in output.err


def test_persist_plan_receipt_refuses_a_changed_preflight_plan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = compose_named_block(marker="plan", inner=_plan_inner())
    snapshot = issue_mutation.IssueSnapshot(
        repository="owner/repo",
        issue="7",
        title="[DESIGNED] Work",
        body=body,
        labels=frozenset(),
        state="OPEN",
        updated_at="2026-08-13T00:00:00Z",
    )
    receipt = mg.PlanReceipt(
        plan_sha256="a" * 64,
        base_sha="b" * 40,
        blockers_sha256="c" * 64,
        owners_sha256="d" * 64,
    )

    def read_snapshot(
        *_args: object, **_kwargs: object
    ) -> issue_mutation.IssueSnapshot:
        return snapshot

    def build_receipt(
        *_args: object, **_kwargs: object
    ) -> tuple[mg.PlanReceipt, mg.ParityVerdict]:
        return receipt, mg.ParityVerdict(reasons=())

    monkeypatch.setattr(issue_mutation, "read_snapshot", read_snapshot)
    monkeypatch.setattr(
        mg,
        "build_receipt_for_body",
        build_receipt,
    )
    with pytest.raises(ShipError, match="plan-receipt-refresh-plan-mismatch"):
        _ = mg.persist_plan_receipt(
            object(),  # type: ignore[arg-type]
            issue="7",
            repo="owner/repo",
            repo_root=tmp_path,
            base_sha="b" * 40,
            expected_plan_sha256="e" * 64,
        )


def test_persist_plan_receipt_refuses_changed_governance_inputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan_inner = _plan_inner()
    prior_receipt = mg.PlanReceipt(
        plan_sha256=mg.hash_plan_block(plan_inner=plan_inner),
        base_sha="a" * 40,
        blockers_sha256="c" * 64,
        owners_sha256="d" * 64,
    )
    snapshot = issue_mutation.IssueSnapshot(
        repository="owner/repo",
        issue="7",
        title="[DESIGNED] Work",
        body=mg.upsert_receipt(
            body=compose_named_block(marker="plan", inner=plan_inner),
            receipt=prior_receipt,
        ),
        labels=frozenset(),
        state="OPEN",
        updated_at="2026-08-13T00:00:00Z",
    )
    changed_receipt = mg.PlanReceipt(
        plan_sha256=prior_receipt.plan_sha256,
        base_sha="b" * 40,
        blockers_sha256="e" * 64,
        owners_sha256=prior_receipt.owners_sha256,
    )

    def read_snapshot(
        *_args: object, **_kwargs: object
    ) -> issue_mutation.IssueSnapshot:
        return snapshot

    def build_receipt(
        *_args: object, **_kwargs: object
    ) -> tuple[mg.PlanReceipt, mg.ParityVerdict]:
        return changed_receipt, mg.ParityVerdict(reasons=())

    monkeypatch.setattr(issue_mutation, "read_snapshot", read_snapshot)
    monkeypatch.setattr(
        mg,
        "build_receipt_for_body",
        build_receipt,
    )
    with pytest.raises(
        ShipError, match="plan-receipt-refresh-governance-input-mismatch"
    ):
        _ = mg.persist_plan_receipt(
            object(),  # type: ignore[arg-type]
            issue="7",
            repo="owner/repo",
            repo_root=tmp_path,
            base_sha="b" * 40,
            expected_plan_sha256=prior_receipt.plan_sha256,
            expected_prior_receipt=prior_receipt,
        )


def test_preflight_bound_receipt_refresh_never_falls_back_to_whole_body_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan_inner = _plan_inner()
    prior_receipt = mg.PlanReceipt(
        plan_sha256=mg.hash_plan_block(plan_inner=plan_inner),
        base_sha="a" * 40,
        blockers_sha256="c" * 64,
        owners_sha256="d" * 64,
    )
    body = mg.upsert_receipt(
        body=compose_named_block(marker="plan", inner=plan_inner),
        receipt=prior_receipt,
    )
    snapshot = issue_mutation.IssueSnapshot(
        repository="owner/repo",
        issue="7",
        title="[DESIGNED] Work",
        body=body,
        labels=frozenset(),
        state="OPEN",
        updated_at="2026-08-13T00:00:00Z",
    )
    refreshed_receipt = mg.PlanReceipt(
        plan_sha256=prior_receipt.plan_sha256,
        base_sha="b" * 40,
        blockers_sha256=prior_receipt.blockers_sha256,
        owners_sha256=prior_receipt.owners_sha256,
    )

    def read_snapshot(
        *_args: object, **_kwargs: object
    ) -> issue_mutation.IssueSnapshot:
        return snapshot

    def build_receipt(
        *_args: object, **_kwargs: object
    ) -> tuple[mg.PlanReceipt, mg.ParityVerdict]:
        return refreshed_receipt, mg.ParityVerdict(reasons=())

    monkeypatch.setattr(issue_mutation, "read_snapshot", read_snapshot)
    monkeypatch.setattr(
        mg,
        "build_receipt_for_body",
        build_receipt,
    )

    def named_block_conflict(*_args: object, **_kwargs: object) -> None:
        raise issue_mutation.ProtectedIssueMutation("stale-identity")

    def whole_body_fallback(*_args: object, **_kwargs: object) -> None:
        pytest.fail("preflight-bound receipt refresh must not overwrite whole bodies")

    monkeypatch.setattr(issue_mutation, "update_named_block", named_block_conflict)
    monkeypatch.setattr(issue_mutation, "update_body", whole_body_fallback)
    with pytest.raises(issue_mutation.ProtectedIssueMutation, match="stale-identity"):
        _ = mg.persist_plan_receipt(
            object(),  # type: ignore[arg-type]
            issue="7",
            repo="owner/repo",
            repo_root=tmp_path,
            base_sha="b" * 40,
            expected_plan_sha256=prior_receipt.plan_sha256,
            expected_prior_receipt=prior_receipt,
        )


def test_scope_drift_record_is_json_quoted_bounded_and_disables_external_diff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    tracked_shas: list[str] = []

    def tracked_paths(_runner: object, *, sha: str, cwd: str) -> frozenset[str]:
        assert cwd == "/repo"
        tracked_shas.append(sha)
        return (
            frozenset({"removed.md"}) if sha == "a" * 40 else frozenset({"README.md"})
        )

    monkeypatch.setattr(mg, "_tracked_paths_at_sha", tracked_paths)

    def diff_name_status(
        _runner: object,
        base: str,
        head: str,
        *,
        paths: tuple[str, ...],
        no_ext_diff: bool,
        cwd: str,
    ) -> CommandResult:
        captured.update(
            base=base,
            head=head,
            paths=paths,
            no_ext_diff=no_ext_diff,
            cwd=cwd,
        )
        return CommandResult(
            ("git", "diff"),
            0,
            "".join(f"M\tpath-{index}\n" for index in range(129)),
            "",
            0.01,
        )

    monkeypatch.setattr(mg.git, "diff_name_status", diff_name_status)
    rendered = mg._render_preflight_scope_drift(  # pyright: ignore[reportPrivateUsage]
        object(),  # type: ignore[arg-type]
        previous_base_sha="a" * 40,
        target_base_sha="b" * 40,
        plan_inner=_plan_inner().replace("README.md", "*.md"),
        cwd="/repo",
    )

    assert captured == {
        "base": "a" * 40,
        "head": "b" * 40,
        "paths": ("README.md", "removed.md"),
        "no_ext_diff": True,
        "cwd": "/repo",
    }
    assert tracked_shas == ["a" * 40, "b" * 40]
    lines = rendered.splitlines()
    assert lines[:5] == [
        "- **Preflight plan-receipt scope refresh**: semantic materiality passed.",
        f"  - Receipt base: `{'a' * 40}`",
        f"  - Reviewed target: `{'b' * 40}`",
        "  - Scope diff (JSON-quoted name-status rows):",
        "    ```text",
    ]
    rows = lines[5:-1]
    assert len(rows) == 128
    assert all(row.startswith("    ") for row in rows)
    assert [json.loads(row[4:]) for row in rows[-2:]] == [
        "M\tpath-126",
        "[truncated: additional scope-diff rows omitted]",
    ]
    assert lines[-1] == "    ```"


def test_load_blocker_snapshot_fail_closed_on_api_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(
        *_args: object, **_kwargs: object
    ) -> list[issue_block.BlockedByDependency]:
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
    _ = subprocess.run(
        ["git", "add", "README.md"], cwd=repo, check=True, capture_output=True
    )
    _ = subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-m", "init"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    base_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
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
        def run(
            self, argv: list[str] | tuple[str, ...], **kwargs: object
        ) -> CommandResult:
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
    _ = subprocess.run(
        ["git", "add", "README.md"], cwd=repo, check=True, capture_output=True
    )
    _ = subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-m", "change"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    head_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    stale_scope = mg.validate_receipt_freshness(
        runner,  # type: ignore[arg-type]
        body=body,
        repo_root=repo,
        blocker_rows=blocker_rows,
        head_sha=head_sha,
    )
    assert mg.REASON_STALE_PLAN_BASE_SCOPE in stale_scope.reasons
    assert not stale_scope.ok
    assert stale_scope.scope_revalidation_only

    # Unrelated main movement: add out-of-scope file, keep README at base content via...
    # Re-create a branch where README matches base but an unrelated file advanced HEAD.
    _ = subprocess.run(
        ["git", "checkout", "-B", "unrelated", base_sha],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    other = repo / "OTHER.md"
    _ = other.write_text("other\n", encoding="utf-8")
    _ = subprocess.run(
        ["git", "add", "OTHER.md"], cwd=repo, check=True, capture_output=True
    )
    _ = subprocess.run(
        [
            "git",
            "-c",
            "user.email=t@t",
            "-c",
            "user.name=t",
            "commit",
            "-m",
            "unrelated",
        ],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    unrelated_head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
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


def test_read_blocked_by_dependencies_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_read(*_a: object, **_k: object) -> CommandResult:
        return CommandResult(("gh",), 1, "", "boom", 0.01)

    monkeypatch.setattr("larch.git.gh.issue_blocked_by_read", fail_read)
    with pytest.raises(issue_block.DependencyReadError):
        _ = issue_block.read_blocked_by_dependencies(object(), "1", repo="o/r")  # type: ignore[arg-type]


def _owner_block(*rows: str) -> str:
    return (
        "\n".join(("<!-- larch:owners:start -->", *rows, "<!-- larch:owners:end -->"))
        + "\n"
    )


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
    plan = (
        _plan_inner()
        .replace(
            "- Fixture owns this plan.",
            "- Reuse the existing command registry.",
        )
        .replace("None.\n\n", f"{migration_text}\n\n")
    )

    assert not mg.migration_requires_owner_block(plan_inner=plan)


def test_additive_migration_passes_owner_admission_without_block() -> None:
    plan = (
        _plan_inner()
        .replace(
            "- Fixture owns this plan.",
            "- Reuse the existing command registry and typed adapter.",
        )
        .replace("None.\n\n", "No breaking changes to existing behavior.\n\n")
    )
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
    assert verdict.reasons == ("active-owner-conflict owner=shared-owner issue=#8",)


def test_reuse_source_requires_native_edge_and_valid_owner_snapshot(
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
    assert reasons == ("reuse-missing-native-blocker owner=shared-owner issue=#6",)
    source_body = compose_named_block(marker="plan", inner=source_plan) + source_owners
    reasons = mg._validate_reuse_sources(  # pyright: ignore[reportPrivateUsage]
        RecordingRunner(responses=[]),
        block=parsed.block,
        body="Native blocker: #6.\n",
        repo="o/r",
        cwd=None,
    )
    assert reasons == ()
    source_body += "\n<!-- larch:plan-receipt -->\n"
    reasons = mg._validate_reuse_sources(  # pyright: ignore[reportPrivateUsage]
        RecordingRunner(responses=[]),
        block=parsed.block,
        body="Native blocker: #6.\n",
        repo="o/r",
        cwd=None,
    )
    assert reasons == ("reuse-owner-snapshot-invalid owner=shared-owner issue=#6",)


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
