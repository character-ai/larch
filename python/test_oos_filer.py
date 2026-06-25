"""Tests for oos_filer.py."""

# pyright: reportUnusedCallResult=false, reportPrivateUsage=false

from __future__ import annotations

import contextlib
import io
import json
import subprocess
from pathlib import Path

import pytest
import config
import file_oos
import issue_create
import oos_filer


def _cp(args: list[str], stdout: str = "", stderr: str = "", rc: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args, rc, stdout, stderr)


class FakeCli:
    def __init__(self, tmp_path: Path) -> None:
        self.tmp_path = tmp_path
        self.calls: list[list[str]] = []
        self.created_bodies: list[str] = []
        self.urls = ["https://github.com/owner/repo/issues/101", "https://github.com/owner/repo/issues/102"]
        self.fail_create = False
        self.fail_create_after = 0
        self.duplicate = False
        self.codex_output = ""
        self.codex_rc = 0
        self.fail_blocked_by = False
        self.blocker_probe_rc = 0
        self.checkpoint_rc = 0
        self.file_conflict_deps_rc = 0
        self.file_conflict_deps_text: str | None = None
        self.file_conflict_deps_write_output = True

    def __call__(self, args: list[str], *, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
        self.calls.append(args)
        if args[:2] == ["run-log", "manifest"]:
            return _cp(args)
        if args[:2] == ["oos", "disposition-checkpoint"]:
            return _cp(args, stderr="checkpoint failed" if self.checkpoint_rc else "", rc=self.checkpoint_rc)
        if args[:2] == ["oos", "file-conflict-deps"]:
            output = Path(args[args.index("--output") + 1])
            if self.file_conflict_deps_rc == 0:
                if self.file_conflict_deps_write_output:
                    if self.file_conflict_deps_text is None:
                        source = Path(args[args.index("--input-file") + 1])
                        deps = file_oos.file_conflict_deps(source)
                        text = "".join(f"{left}\t{right}\n" for left, right in deps)
                    else:
                        text = self.file_conflict_deps_text
                    output.write_text(text, encoding="utf-8")
                return _cp(args)
            if self.file_conflict_deps_rc == 1:
                output.unlink(missing_ok=True)
            return _cp(args, stderr="file-conflict failed", rc=self.file_conflict_deps_rc)
        if args[:2] == ["agent", "launch-codex-exec"]:
            if self.codex_rc != 0:
                return _cp(args, stderr="codex failed", rc=self.codex_rc)
            output = Path(args[args.index("--output") + 1])
            output.write_text(self.codex_output, encoding="utf-8")
            return _cp(args)
        if args[:2] == ["issue", "parse-input"]:
            source = Path(args[args.index("--input-file") + 1])
            out_dir = Path(args[args.index("--output-dir") + 1])
            out_dir.mkdir(parents=True, exist_ok=True)
            items, _mode = issue_create.parse_issue_input(source.read_text(encoding="utf-8"))
            lines: list[str] = []
            for index, item in enumerate(items, start=1):
                lines.append(f"ITEM_{index}_TITLE={item.title}")
                if item.body:
                    body = out_dir / f"item-{index}-body.txt"
                    body.write_text(item.body, encoding="utf-8")
                    lines.append(f"ITEM_{index}_BODY_FILE={body}")
                if item.malformed:
                    lines.append(f"ITEM_{index}_MALFORMED=true")
                if item.reviewer:
                    lines.append(f"ITEM_{index}_REVIEWER={item.reviewer}")
                if item.vote:
                    lines.append(f"ITEM_{index}_VOTE_TALLY={item.vote}")
                if item.phase:
                    lines.append(f"ITEM_{index}_PHASE={item.phase}")
            lines.append(f"ITEMS_TOTAL={len(items)}")
            return _cp(args, stdout="\n".join(lines) + "\n")
        if args[:2] == ["issue", "create-one"]:
            body_file = Path(args[args.index("--body-file") + 1])
            self.created_bodies.append(body_file.read_text(encoding="utf-8"))
            if self.fail_create or (self.fail_create_after and len(self.created_bodies) >= self.fail_create_after):
                return _cp(args, stdout="ISSUE_FAILED=true\n", rc=0)
            url = self.urls[min(len(self.created_bodies) - 1, len(self.urls) - 1)]
            if self.duplicate:
                return _cp(args, stdout=f"ISSUE_DUPLICATE_OF_URL={url}\nISSUE_TITLE=[OOS] Duplicate\n")
            return _cp(args, stdout=f"ISSUE_NUMBER={url.rsplit('/', 1)[-1]}\nISSUE_URL={url}\nISSUE_TITLE=[OOS] Filed\n")
        if args[:2] == ["issue", "add-blocked-by"]:
            if self.fail_blocked_by:
                return _cp(args, stdout="BLOCKED_BY_FAILED=true\nERROR=blocked-by failed\n", rc=2)
            return _cp(args, stdout="BLOCKED_BY_ADDED=true\n")
        if args[:2] == ["issue", "cleanup-failed"]:
            return _cp(args, stdout="CLOSED=true\n")
        return _cp(args, stderr=f"unexpected call: {args}", rc=1)


def _setup(tmp_path: Path) -> None:
    (tmp_path / "ship-pr-state.sh").write_text(
        "RUN_ID=run-1\nREPO=owner/repo\nFORKED_TARGET=false\nREPO_UNAVAILABLE=false\n",
        encoding="utf-8",
    )
    run_dir = tmp_path / "larch-logs" / "implement" / "run-1"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.json").write_text('{"schema_version":2,"steps_ran":{}}\n', encoding="utf-8")


def _write_oos(tmp_path: Path, text: str) -> None:
    (tmp_path / "oos-accepted-main-agent.md").write_text(text, encoding="utf-8")


def _run(tmp_path: Path, fake: FakeCli, monkeypatch: pytest.MonkeyPatch) -> tuple[int, dict[str, object]]:
    monkeypatch.setattr(oos_filer, "_run_cli", fake)
    monkeypatch.setattr(oos_filer, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(oos_filer, "_probe_tracking_blocker", lambda **_a: fake.blocker_probe_rc == 0)  # type: ignore[arg-type]
    rc = oos_filer.cmd_file(["--implement-tmpdir", str(tmp_path), "--codex-timeout", "1"])
    return rc, {}


def test_empty_batch_writes_zero_statistics_and_stamps_true(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(tmp_path)
    fake = FakeCli(tmp_path)
    rc, _payload = _run(tmp_path, fake, monkeypatch)
    assert rc == 0
    assert "Run run-1: 0 OOS issue(s) filed." in (tmp_path / "larch-logs" / "implement" / "run-1" / "run-statistics.md").read_text(encoding="utf-8")
    assert any("steps_ran.step9a1=true" in call for call in fake.calls for call in call)
    assert any(call[:2] == ["oos", "disposition-checkpoint"] for call in fake.calls)
    assert not any(call[:2] == ["issue", "create-one"] for call in fake.calls)


def test_single_item_files_issue_and_writes_sentinel(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(tmp_path)
    _write_oos(tmp_path, "### OOS_1: First\n- **Description**: Fix later.\n- **Reviewer**: A\n- **Vote tally**: 2-0\n- **Phase**: implement\n")
    fake = FakeCli(tmp_path)
    rc, _payload = _run(tmp_path, fake, monkeypatch)
    assert rc == 0
    assert any(call[:2] == ["issue", "parse-input"] for call in fake.calls)
    assert any(call[:2] == ["issue", "create-one"] for call in fake.calls)
    assert "https://github.com/owner/repo/issues/101" in (tmp_path / "oos-issues-created.md").read_text(encoding="utf-8")
    assert any("steps_ran.step9a1=true" in call for call in fake.calls for call in call)


def test_malformed_item_skipped_not_filed_as_empty_issue(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """#5260 Defect 2: a malformed accepted-OOS block must not be filed as an empty public issue."""
    _setup(tmp_path)
    # Metadata-only block: a Reviewer(s) line is captured but there is no Concern/
    # Description body, so the parser flags it malformed even after the Defect 1 fix.
    _write_oos(
        tmp_path,
        "### OOS_1: Metadata only, missing concern\n- **Reviewer(s)**: someone\n- **Severity**: latent\n",
    )
    fake = FakeCli(tmp_path)
    _run(tmp_path, fake, monkeypatch)
    assert any(call[:2] == ["issue", "parse-input"] for call in fake.calls)
    assert not any(call[:2] == ["issue", "create-one"] for call in fake.calls)
    log = (tmp_path / "execution-issues.md").read_text(encoding="utf-8")
    assert "skipped malformed accepted-OOS item" in log


def test_two_items_codex_success_uses_combined_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OOS_ISSUES_PER_RUN_CAP", "99")
    _setup(tmp_path)
    _write_oos(tmp_path, "### OOS_1: First\n- **Description**: A.\n\n### OOS_2: Second\n- **Description**: B.\n")
    fake = FakeCli(tmp_path)
    fake.codex_output = "### OOS_1: Combined\n- **Description**: A and B.\n"
    monkeypatch.setattr(oos_filer, "_codex_available", lambda: True)
    rc, _payload = _run(tmp_path, fake, monkeypatch)
    assert rc == 0
    codex_calls = [call for call in fake.calls if call[:2] == ["agent", "launch-codex-exec"]]
    assert codex_calls
    assert str(tmp_path) in codex_calls[0]
    prompt = (tmp_path / "oos-combine-prompt.md").read_text(encoding="utf-8")
    assert "## Batch markdown" in prompt
    assert len([call for call in fake.calls if call[:2] == ["issue", "create-one"]]) == 1


def test_two_items_codex_invalid_falls_back(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OOS_ISSUES_PER_RUN_CAP", "99")
    _setup(tmp_path)
    _write_oos(tmp_path, "### OOS_1: First\n- **Description**: A.\n\n### OOS_2: Second\n- **Description**: B.\n")
    fake = FakeCli(tmp_path)
    fake.codex_output = "not oos markdown\n"
    monkeypatch.setattr(oos_filer, "_codex_available", lambda: True)
    rc, _payload = _run(tmp_path, fake, monkeypatch)
    assert rc == 0
    assert len([call for call in fake.calls if call[:2] == ["issue", "create-one"]]) == 2


def test_codex_item_count_increase_falls_back(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OOS_ISSUES_PER_RUN_CAP", "99")
    _setup(tmp_path)
    _write_oos(tmp_path, "### OOS_1: First\n- **Description**: A.\n\n### OOS_2: Second\n- **Description**: B.\n")
    fake = FakeCli(tmp_path)
    fake.codex_output = (
        "### OOS_1: One\n- **Description**: A.\n\n"
        "### OOS_2: Two\n- **Description**: B.\n\n"
        "### OOS_3: Three\n- **Description**: C.\n"
    )
    monkeypatch.setattr(oos_filer, "_codex_available", lambda: True)
    rc, _payload = _run(tmp_path, fake, monkeypatch)
    assert rc == 0
    assert len([call for call in fake.calls if call[:2] == ["issue", "create-one"]]) == 2


def test_codex_available_honors_explicit_false_binary_found_with_codex_on_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CODEX_BINARY_FOUND", "false")
    monkeypatch.delenv("LARCH_OOS_CODEX_BINARY_FOUND", raising=False)

    def fake_which(name: str) -> str | None:
        return "/usr/bin/codex" if name == "codex" else None

    monkeypatch.setattr(oos_filer.shutil, "which", fake_which)
    assert oos_filer._codex_available() is False  # pyright: ignore[reportPrivateUsage]


def test_codex_available_ignores_stale_larch_oos_codex_available_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LARCH_OOS_CODEX_AVAILABLE", "false")
    monkeypatch.delenv("LARCH_OOS_CODEX_BINARY_FOUND", raising=False)
    monkeypatch.delenv("CODEX_BINARY_FOUND", raising=False)
    def fake_which(name: str) -> str | None:
        return "/usr/bin/codex" if name == "codex" else None

    monkeypatch.setattr(oos_filer.shutil, "which", fake_which)
    assert oos_filer._codex_available() is True  # pyright: ignore[reportPrivateUsage]


def test_two_items_codex_unavailable_skips_combine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OOS_ISSUES_PER_RUN_CAP", "99")
    _setup(tmp_path)
    _write_oos(tmp_path, "### OOS_1: First\n- **Description**: A.\n\n### OOS_2: Second\n- **Description**: B.\n")
    fake = FakeCli(tmp_path)
    monkeypatch.setattr(oos_filer, "_codex_available", lambda: False)
    rc, _payload = _run(tmp_path, fake, monkeypatch)
    assert rc == 0
    assert not any(call[:2] == ["agent", "launch-codex-exec"] for call in fake.calls)
    assert len([call for call in fake.calls if call[:2] == ["issue", "create-one"]]) == 2


def test_idempotency_sentinel_skips_create_loop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(tmp_path)
    (tmp_path / "oos-issues-created.md").write_text("| t | #3 | https://github.com/owner/repo/issues/3 |\n", encoding="utf-8")
    fake = FakeCli(tmp_path)
    rc, _payload = _run(tmp_path, fake, monkeypatch)
    assert rc == 0
    assert not any(call[:2] == ["issue", "create-one"] for call in fake.calls)
    assert any(call[:2] == ["oos", "disposition-checkpoint"] for call in fake.calls)
    assert "https://github.com/owner/repo/issues/3" in (tmp_path / "larch-logs" / "implement" / "run-1" / "oos-issues.ndjson").read_text(encoding="utf-8")
    assert any("steps_ran.step9a1=true" in " ".join(call) for call in fake.calls)


@pytest.mark.parametrize(
    "state_line",
    ["FORKED_TARGET=true\nREPO_UNAVAILABLE=false\n", "FORKED_TARGET=false\nREPO_UNAVAILABLE=true\n"],
)
def test_forked_or_repo_unavailable_skip_create_loop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, state_line: str) -> None:
    _setup(tmp_path)
    (tmp_path / "ship-pr-state.sh").write_text(f"RUN_ID=run-1\nREPO=owner/repo\n{state_line}", encoding="utf-8")
    _write_oos(tmp_path, "### OOS_1: First\n- **Description**: A.\n")
    fake = FakeCli(tmp_path)
    rc, _payload = _run(tmp_path, fake, monkeypatch)
    assert rc == 0
    assert not any(call[:2] == ["issue", "create-one"] for call in fake.calls)
    assert any(call[:2] == ["oos", "disposition-checkpoint"] for call in fake.calls)
    assert "Skipped" in (tmp_path / "larch-logs" / "implement" / "run-1" / "oos-issues.ndjson").read_text(encoding="utf-8")
    assert any("steps_ran.step9a1=true" in " ".join(call) for call in fake.calls)


def test_security_sidecar_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(tmp_path)
    (tmp_path / "security-oos-observations.md").write_text("private\n", encoding="utf-8")
    fake = FakeCli(tmp_path)
    rc = oos_filer.cmd_file(["--implement-tmpdir", str(tmp_path)])
    _ = fake, monkeypatch
    assert rc != 0


def test_already_filed_block_is_excluded_from_create_loop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(tmp_path)
    _write_oos(tmp_path, "### OOS_1: Already\n- **Description**: Done.\n- **Filed URL**: https://github.com/owner/repo/issues/44\n")
    fake = FakeCli(tmp_path)
    rc, _payload = _run(tmp_path, fake, monkeypatch)
    assert rc == 0
    assert not any(call[:2] == ["issue", "create-one"] for call in fake.calls)
    assert any(call[:2] == ["oos", "disposition-checkpoint"] for call in fake.calls)
    assert "https://github.com/owner/repo/issues/44" in (tmp_path / "larch-logs" / "implement" / "run-1" / "oos-issues.ndjson").read_text(encoding="utf-8")


def test_partial_issue_failure_returns_nonzero_without_sentinel(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(tmp_path)
    _write_oos(tmp_path, "### OOS_1: First\n- **Description**: A.\n")
    fake = FakeCli(tmp_path)
    fake.fail_create = True
    rc, _payload = _run(tmp_path, fake, monkeypatch)
    assert rc != 0
    assert not (tmp_path / "oos-issues-created.md").exists()


def test_two_item_partial_failure_cleans_up_first_issue(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OOS_ISSUES_PER_RUN_CAP", "99")
    _setup(tmp_path)
    _write_oos(
        tmp_path,
        "### OOS_1: First\n- **Description**: A.\n\n### OOS_2: Second\n- **Description**: B.\n",
    )
    fake = FakeCli(tmp_path)
    fake.fail_create_after = 2
    rc, _payload = _run(tmp_path, fake, monkeypatch)
    assert rc != 0
    assert not (tmp_path / "oos-issues-created.md").exists()
    assert any(call[:2] == ["issue", "cleanup-failed"] for call in fake.calls)
    assert len([call for call in fake.calls if call[:2] == ["issue", "create-one"]]) == 2


def test_file_conflict_deps_orders_blocker_before_blocked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OOS_ISSUES_PER_RUN_CAP", "99")
    _setup(tmp_path)
    _write_oos(
        tmp_path,
        "### OOS_1: First\n- **Description**: touches `src/a.py:1-5`\n\n### OOS_2: Second\n- **Description**: touches `src/a.py:2-6`\n",
    )
    fake = FakeCli(tmp_path)
    rc, _payload = _run(tmp_path, fake, monkeypatch)
    assert rc == 0
    create_calls = [call for call in fake.calls if call[:2] == ["issue", "create-one"]]
    assert len(create_calls) == 2
    first_title = create_calls[0][create_calls[0].index("--title") + 1].strip()
    second_title = create_calls[1][create_calls[1].index("--title") + 1].strip()
    assert first_title == "First"
    assert second_title == "Second"
    assert any(
        call[:2] == ["issue", "add-blocked-by"] and call[call.index("--client-issue") + 1] == "102" and call[call.index("--blocker-issue") + 1] == "101"
        for call in fake.calls
    )



def test_file_conflict_deps_empty_tsv_degrades_silently(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OOS_ISSUES_PER_RUN_CAP", "99")
    _setup(tmp_path)
    _write_oos(
        tmp_path,
        "### OOS_1: First\n- **Description**: A.\n\n### OOS_2: Second\n- **Description**: B.\n",
    )
    fake = FakeCli(tmp_path)
    fake.file_conflict_deps_text = ""

    rc, _payload = _run(tmp_path, fake, monkeypatch)

    assert rc == 0
    assert any(call[:2] == ["oos", "file-conflict-deps"] for call in fake.calls)
    assert not any(call[:2] == ["issue", "add-blocked-by"] for call in fake.calls)
    execution_issues = tmp_path / "execution-issues.md"
    assert not execution_issues.exists() or "Tool Failures" not in execution_issues.read_text(encoding="utf-8")
    assert not execution_issues.exists() or "oos-file-conflict pre-pass failed" not in execution_issues.read_text(encoding="utf-8")


def test_file_conflict_deps_exit_1_warns_and_unlinks_stale_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OOS_ISSUES_PER_RUN_CAP", "99")
    _setup(tmp_path)
    _write_oos(
        tmp_path,
        "### OOS_1: First\n- **Description**: A.\n\n### OOS_2: Second\n- **Description**: B.\n",
    )
    deps = tmp_path / "oos-intra-batch-deps.tsv"
    deps.write_text("1\t2\n", encoding="utf-8")
    fake = FakeCli(tmp_path)
    fake.file_conflict_deps_rc = 1

    rc, _payload = _run(tmp_path, fake, monkeypatch)

    assert rc == 0
    assert not deps.exists()
    assert not any(call[:2] == ["issue", "add-blocked-by"] for call in fake.calls)
    execution_issues = (tmp_path / "execution-issues.md").read_text(encoding="utf-8")
    assert "oos-file-conflict pre-pass failed (exit 1)" in execution_issues
    assert "Tool Failures" in execution_issues
    assert "oos file-conflict-deps exited 1" in execution_issues


def test_file_conflict_deps_exit_2_preserves_preexisting_tsv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OOS_ISSUES_PER_RUN_CAP", "99")
    _setup(tmp_path)
    _write_oos(
        tmp_path,
        "### OOS_1: First\n- **Description**: A.\n\n### OOS_2: Second\n- **Description**: B.\n",
    )
    deps = tmp_path / "oos-intra-batch-deps.tsv"
    deps.write_text("1\t2\n", encoding="utf-8")
    fake = FakeCli(tmp_path)
    fake.file_conflict_deps_rc = 2

    rc, _payload = _run(tmp_path, fake, monkeypatch)

    assert rc == 0
    assert deps.read_text(encoding="utf-8") == "1\t2\n"
    assert not any(call[:2] == ["issue", "add-blocked-by"] for call in fake.calls)
    execution_issues = (tmp_path / "execution-issues.md").read_text(encoding="utf-8")
    assert "oos-file-conflict pre-pass failed (exit 2)" in execution_issues
    assert "Tool Failures" in execution_issues
    assert "oos file-conflict-deps exited 2" in execution_issues


def test_sentinel_with_remaining_blocks_files_new_items(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(tmp_path)
    (tmp_path / "oos-issues-created.md").write_text("| t | #3 | https://github.com/owner/repo/issues/3 |\n", encoding="utf-8")
    _write_oos(tmp_path, "### OOS_1: New item\n- **Description**: Still pending.\n")
    fake = FakeCli(tmp_path)
    rc, _payload = _run(tmp_path, fake, monkeypatch)
    assert rc == 0
    assert any(call[:2] == ["issue", "create-one"] for call in fake.calls)
    sentinel = (tmp_path / "oos-issues-created.md").read_text(encoding="utf-8")
    assert "https://github.com/owner/repo/issues/3" in sentinel
    assert "https://github.com/owner/repo/issues/101" in sentinel


def test_blocked_by_failure_returns_nonzero(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(tmp_path)
    (tmp_path / "ship-pr-state.sh").write_text(
        "RUN_ID=run-1\nREPO=owner/repo\nFORKED_TARGET=false\nREPO_UNAVAILABLE=false\nISSUE_NUMBER=99\n",
        encoding="utf-8",
    )
    _write_oos(tmp_path, "### OOS_1: First\n- **Description**: A.\n")
    fake = FakeCli(tmp_path)
    fake.fail_blocked_by = True
    rc, _payload = _run(tmp_path, fake, monkeypatch)
    assert rc != 0
    assert not (tmp_path / "oos-issues-created.md").exists()


def test_sanitizes_internal_url_before_create_one(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(tmp_path)
    _write_oos(tmp_path, "### OOS_1: First\n- **Description**: See http://service.internal/path.\n")
    fake = FakeCli(tmp_path)
    rc, _payload = _run(tmp_path, fake, monkeypatch)
    assert rc == 0
    assert any("<INTERNAL-URL>" in body for body in fake.created_bodies)


def test_duplicate_of_url_is_recorded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(tmp_path)
    _write_oos(tmp_path, "### OOS_1: First\n- **Description**: A.\n")
    fake = FakeCli(tmp_path)
    fake.duplicate = True
    rc, _payload = _run(tmp_path, fake, monkeypatch)
    assert rc == 0
    sentinel = (tmp_path / "oos-issues-created.md").read_text(encoding="utf-8")
    assert "https://github.com/owner/repo/issues/101" in sentinel


def test_checkpoint_runs_before_manifest_stamp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(tmp_path)
    _write_oos(tmp_path, "### OOS_1: First\n- **Description**: A.\n")
    fake = FakeCli(tmp_path)
    rc, _payload = _run(tmp_path, fake, monkeypatch)
    assert rc == 0
    checkpoint_index = next(i for i, call in enumerate(fake.calls) if call[:2] == ["oos", "disposition-checkpoint"])
    manifest_index = next(i for i, call in enumerate(fake.calls) if call[:2] == ["run-log", "manifest"])
    assert checkpoint_index < manifest_index


def test_checkpoint_failure_preserves_evidence_without_success_markers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(tmp_path)
    _write_oos(tmp_path, "### OOS_1: First\n- **Description**: A.\n")
    fake = FakeCli(tmp_path)
    fake.checkpoint_rc = 2
    rc, _payload = _run(tmp_path, fake, monkeypatch)
    assert rc != 0
    run_dir = tmp_path / "larch-logs" / "implement" / "run-1"
    assert not (run_dir / "run-statistics.md").exists()
    assert (run_dir / "oos-issues.ndjson").is_file()
    assert "https://github.com/owner/repo/issues/101" in (tmp_path / "oos-issues-created.md").read_text(encoding="utf-8")
    flat = [arg for call in fake.calls for arg in call]
    assert "steps_ran.step9a1=false" in flat
    assert "steps_ran.step9a1=true" not in flat


def test_checkpoint_failed_retry_reuses_persisted_evidence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(tmp_path)
    _write_oos(tmp_path, "### OOS_1: First\n- **Description**: A.\n")
    first = FakeCli(tmp_path)
    first.checkpoint_rc = 2
    rc1, _payload = _run(tmp_path, first, monkeypatch)
    assert rc1 != 0
    second = FakeCli(tmp_path)
    rc2, _payload = _run(tmp_path, second, monkeypatch)
    assert rc2 == 0
    assert not any(call[:2] == ["issue", "create-one"] for call in second.calls)
    assert any(call[:2] == ["oos", "disposition-checkpoint"] for call in second.calls)
    assert (tmp_path / "larch-logs" / "implement" / "run-1" / "run-statistics.md").is_file()


def test_mixed_checkpoint_retry_files_only_unmatched_block(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(tmp_path)
    (tmp_path / "oos-issues-created.md").write_text(
        "| OOS title | Issue | URL |\n|---|---|---|\n| First rewritten | #101 | https://github.com/owner/repo/issues/101 |\n\n"
        "- **Title**: First rewritten\n- **Stable ID**: OOS_1\n- **Filed URL**: https://github.com/owner/repo/issues/101\n",
        encoding="utf-8",
    )
    run_dir = tmp_path / "larch-logs" / "implement" / "run-1"
    (run_dir / "oos-issues.ndjson").write_text(
        '{"body":"- **Filed URL**: https://github.com/owner/repo/issues/101\n- **Title**: First rewritten\n- **Stable ID**: OOS_1"}\n',
        encoding="utf-8",
    )
    _write_oos(
        tmp_path,
        "### OOS_1: First original\n- **Description**: A.\n\n### OOS_2: Second\n- **Description**: B.\n",
    )
    fake = FakeCli(tmp_path)
    rc, _payload = _run(tmp_path, fake, monkeypatch)
    assert rc == 0
    create_calls = [call for call in fake.calls if call[:2] == ["issue", "create-one"]]
    assert len(create_calls) == 1
    assert create_calls[0][create_calls[0].index("--title") + 1] == "Second"
    ndjson = (run_dir / "oos-issues.ndjson").read_text(encoding="utf-8")
    assert "https://github.com/owner/repo/issues/101" in ndjson
    assert "https://github.com/owner/repo/issues/102" in ndjson or "https://github.com/owner/repo/issues/101" in ndjson


def test_checkpoint_failed_retry_reuses_url_only_persisted_evidence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(tmp_path)
    run_dir = tmp_path / "larch-logs" / "implement" / "run-1"
    (run_dir / "oos-issues.ndjson").write_text(
        '{"body":"- **Filed URL**: https://github.com/owner/repo/issues/101\n- **Title**: Rewritten title only"}\n',
        encoding="utf-8",
    )
    _write_oos(
        tmp_path,
        "### OOS_1: Original title\n- **Description**: A.\n- **Filed URL**: https://github.com/owner/repo/issues/101\n",
    )
    fake = FakeCli(tmp_path)
    rc, _payload = _run(tmp_path, fake, monkeypatch)
    assert rc == 0
    assert not any(call[:2] == ["issue", "create-one"] for call in fake.calls)


def test_combined_issue_retry_satisfies_all_source_blocks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(tmp_path)
    (tmp_path / "oos-issues-created.md").write_text(
        "| OOS title | Issue | URL |\n|---|---|---|\n| Combined | #101 | https://github.com/owner/repo/issues/101 |\n\n"
        "- **Title**: Combined\n- **Stable ID**: OOS_1\n- **Stable ID**: OOS_2\n- **Filed URL**: https://github.com/owner/repo/issues/101\n",
        encoding="utf-8",
    )
    run_dir = tmp_path / "larch-logs" / "implement" / "run-1"
    (run_dir / "oos-issues.ndjson").write_text(
        '{"body":"- **Filed URL**: https://github.com/owner/repo/issues/101\n- **Title**: Combined\n- **Stable ID**: OOS_1\n- **Stable ID**: OOS_2"}\n',
        encoding="utf-8",
    )
    _write_oos(
        tmp_path,
        "### OOS_1: First\n- **Description**: A.\n\n### OOS_2: Second\n- **Description**: B.\n",
    )
    fake = FakeCli(tmp_path)
    rc, _payload = _run(tmp_path, fake, monkeypatch)
    assert rc == 0
    assert not any(call[:2] == ["issue", "create-one"] for call in fake.calls)


def test_multi_source_duplicate_oos_1_does_not_cross_match_retry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(tmp_path)
    (tmp_path / "oos-issues-created.md").write_text(
        "| OOS title | Issue | URL |\n|---|---|---|\n| Main item | #101 | https://github.com/owner/repo/issues/101 |\n\n"
        "- **Title**: Main item\n- **Stable ID**: OOS_1\n- **Filed URL**: https://github.com/owner/repo/issues/101\n",
        encoding="utf-8",
    )
    run_dir = tmp_path / "larch-logs" / "implement" / "run-1"
    (run_dir / "oos-issues.ndjson").write_text(
        '{"body":"- **Filed URL**: https://github.com/owner/repo/issues/101\n- **Title**: Main item\n- **Stable ID**: OOS_1"}\n',
        encoding="utf-8",
    )
    (tmp_path / "oos-accepted-main-agent.md").write_text(
        "### OOS_1: Main item\n- **Description**: Already filed from main-agent source.\n",
        encoding="utf-8",
    )
    (tmp_path / "oos-accepted-review.md").write_text(
        "### OOS_1: Review item\n- **Description**: Distinct review-source item.\n",
        encoding="utf-8",
    )
    fake = FakeCli(tmp_path)
    rc, _payload = _run(tmp_path, fake, monkeypatch)
    assert rc == 0
    create_calls = [call for call in fake.calls if call[:2] == ["issue", "create-one"]]
    assert len(create_calls) == 1
    assert create_calls[0][create_calls[0].index("--title") + 1] == "Review item"


def test_checkpoint_failure_manifest_stamp_error_still_reports_checkpoint_failed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(tmp_path)
    _write_oos(tmp_path, "### OOS_1: First\n- **Description**: A.\n")
    fake = FakeCli(tmp_path)
    fake.checkpoint_rc = 2

    def run_cli(args: list[str], *, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
        if args[:2] == ["run-log", "manifest"]:
            return _cp(args, stderr="manifest update failed", rc=1)
        return fake(args, input_text=input_text)

    monkeypatch.setattr(oos_filer, "_run_cli", run_cli)
    monkeypatch.setattr(oos_filer, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(oos_filer, "_probe_tracking_blocker", lambda **_a: True)  # type: ignore[arg-type]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = oos_filer.cmd_file(["--implement-tmpdir", str(tmp_path), "--codex-timeout", "1"])
    output = json.loads(buf.getvalue())
    assert rc != 0
    assert output["status"] == "disposition_checkpoint_failed"
    assert output["step9a1_stamped"] is False


def test_file_warns_and_continues_on_manifest_materialize_type_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _setup(tmp_path)
    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"oos_observations":["bad"]}\n', encoding="utf-8")
    with (tmp_path / "ship-pr-state.sh").open("a", encoding="utf-8") as handle:
        handle.write(f"MANIFEST_PATH={manifest}\n")
    fake = FakeCli(tmp_path)

    def fail_materialize(_manifest_path: Path, _tmpdir: Path, *, count_only: bool = False) -> int:
        _ = count_only
        raise TypeError("item must be an object")

    monkeypatch.setattr(file_oos, "materialize_manifest_oos", fail_materialize)

    rc, _payload = _run(tmp_path, fake, monkeypatch)

    assert rc == 0
    assert "manifest OOS materialization failed: item must be an object" in (
        tmp_path / "execution-issues.md"
    ).read_text(encoding="utf-8")


def test_sentinel_recovery_materializes_strict_evidence_for_real_checkpoint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _setup(tmp_path)
    (tmp_path / "oos-issues-created.md").write_text(
        "| OOS title | Issue | URL |\n|---|---|---|\n| Prior | #3 | https://github.com/owner/repo/issues/3 |\n",
        encoding="utf-8",
    )

    def fake_run(args: list[str], *, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
        _ = input_text
        if args[:2] == ["oos", "disposition-checkpoint"]:
            rc = file_oos.disposition_checkpoint_main(["--implement-tmpdir", str(tmp_path)])
            return _cp(args, rc=rc)
        fake.calls.append(args)
        if args[:2] == ["run-log", "manifest"]:
            return _cp(args)
        return _cp(args)

    def fake_subprocess_run(argv: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        if argv[:3] == ["git", "merge-base", "HEAD"]:
            return _cp(argv, stdout="base\n")
        if argv[:3] == ["git", "-C", str(tmp_path)]:
            return _cp(argv)
        if argv[:2] == ["git", "rev-parse"]:
            return _cp(argv, stdout=str(tmp_path) + "\n")
        if argv[:3] == ["git", "-C", str(tmp_path)]:
            return _cp(argv)
        if argv[:2] == ["git", "log"] or (len(argv) > 3 and argv[0] == "git" and argv[2] == "log"):
            return _cp(argv, stdout="")
        return _cp(argv)

    fake = FakeCli(tmp_path)
    monkeypatch.setattr(oos_filer, "_run_cli", fake_run)
    monkeypatch.setattr(file_oos.subprocess, "run", fake_subprocess_run)
    rc = oos_filer.cmd_file(["--implement-tmpdir", str(tmp_path), "--codex-timeout", "1"])
    assert rc == 0
    accepted = tmp_path / "oos-accepted-main-agent.md"
    assert accepted.is_file()
    assert "- **Filed URL**: https://github.com/owner/repo/issues/3" in accepted.read_text(encoding="utf-8")


def test_success_path_manifest_stamp_failure_returns_zero_with_stamped_false(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _setup(tmp_path)
    _write_oos(tmp_path, "### OOS_1: First\n- **Description**: A.\n")
    fake = FakeCli(tmp_path)

    def run_cli(args: list[str], *, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
        if args[:2] == ["run-log", "manifest"]:
            return _cp(args, stderr="manifest update failed", rc=1)
        return fake(args, input_text=input_text)

    monkeypatch.setattr(oos_filer, "_run_cli", run_cli)
    monkeypatch.setattr(oos_filer, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(oos_filer, "_probe_tracking_blocker", lambda **_a: True)  # type: ignore[arg-type]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = oos_filer.cmd_file(["--implement-tmpdir", str(tmp_path), "--codex-timeout", "1"])
    output = json.loads(buf.getvalue())
    # run-statistics must have been written (issued filed OK)
    assert (tmp_path / "larch-logs" / "implement" / "run-1" / "run-statistics.md").is_file()
    # stamp failure is handled gracefully: exit 0, step9a1_stamped=False
    assert rc == 0
    assert output["step9a1_stamped"] is False
    assert output["status"] == "filed"


def test_bare_oos_item_suffix_accepts_finding_ids() -> None:
    assert oos_filer._bare_oos_item_suffix("oos-accepted-review:FINDING_3") == "FINDING_3"
    assert oos_filer._bare_oos_item_suffix("FINDING_3") == "FINDING_3"
    assert oos_filer._bare_oos_item_suffix("oos-accepted-review:OOS_2") == "OOS_2"


def test_issue_covers_finding_stable_id_suffix() -> None:
    issue = oos_filer.FiledIssue("title", "https://github.com/o/r/issues/1", stable_id="oos-accepted-review:FINDING_3")
    assert oos_filer._issue_covers_stable_id(issue=issue, stable_id="oos-accepted-review:FINDING_3")


_THREE_OOS_BLOCKS = (
    "### OOS_1: First\n- **Description**: Alpha.\n- **Reviewer**: A\n- **Vote tally**: 2-0\n- **Phase**: implement\n\n"
    "### OOS_2: Second\n- **Description**: Beta.\n- **Reviewer**: B\n- **Vote tally**: 2-0\n- **Phase**: implement\n\n"
    "### OOS_3: Third\n- **Description**: Gamma.\n- **Reviewer**: C\n- **Vote tally**: 2-0\n- **Phase**: implement\n"
)


def test_capped_full_rollup_retains_all_source_stable_ids(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OOS_ISSUES_PER_RUN_CAP", "1")
    monkeypatch.setattr(oos_filer, "_codex_available", lambda: False)
    _setup(tmp_path)
    _write_oos(tmp_path, _THREE_OOS_BLOCKS)
    fake = FakeCli(tmp_path)
    rc, _payload = _run(tmp_path, fake, monkeypatch)
    assert rc == 0
    # cap=1 rolls all three accepted blocks into a single aggregate issue.
    assert len([call for call in fake.calls if call[:2] == ["issue", "create-one"]]) == 1
    sentinel = (tmp_path / "oos-issues-created.md").read_text(encoding="utf-8")
    # The aggregate issue must retain every source stable ID, not just the first.
    assert "oos-accepted-main-agent:OOS_1" in sentinel
    assert "oos-accepted-main-agent:OOS_2" in sentinel
    assert "oos-accepted-main-agent:OOS_3" in sentinel
    # A retry must recognize every rolled-up block as already filed (no re-filing of the remainder).
    retry = FakeCli(tmp_path)
    rc_retry, _retry_payload = _run(tmp_path, retry, monkeypatch)
    assert rc_retry == 0
    assert not [call for call in retry.calls if call[:2] == ["issue", "create-one"]]


def test_capped_partial_rollup_retains_tail_stable_ids(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OOS_ISSUES_PER_RUN_CAP", "2")
    monkeypatch.setattr(oos_filer, "_codex_available", lambda: False)
    _setup(tmp_path)
    _write_oos(tmp_path, _THREE_OOS_BLOCKS)
    fake = FakeCli(tmp_path)
    rc, _payload = _run(tmp_path, fake, monkeypatch)
    assert rc == 0
    # cap=2 keeps the first block and rolls the remaining two into one aggregate issue.
    assert len([call for call in fake.calls if call[:2] == ["issue", "create-one"]]) == 2
    sentinel = (tmp_path / "oos-issues-created.md").read_text(encoding="utf-8")
    # The aggregate (last) issue must retain the tail stable IDs, not drop everything past the first.
    assert "oos-accepted-main-agent:OOS_1" in sentinel
    assert "oos-accepted-main-agent:OOS_2" in sentinel
    assert "oos-accepted-main-agent:OOS_3" in sentinel
    # A retry must recognize every rolled-up block as already filed.
    retry = FakeCli(tmp_path)
    rc_retry, _retry_payload = _run(tmp_path, retry, monkeypatch)
    assert rc_retry == 0
    assert not [call for call in retry.calls if call[:2] == ["issue", "create-one"]]


def test_split_to_github_limit_short_body_unchanged() -> None:
    body = "Short body."
    assert oos_filer._split_to_github_limit(body) == [body]


def test_split_to_github_limit_exactly_at_byte_limit_unchanged() -> None:
    body = "x" * config.GITHUB_ISSUE_BODY_MAX_BYTES
    result = oos_filer._split_to_github_limit(body)
    assert result == [body]
    assert oos_filer._body_bytes(result[0]) == config.GITHUB_ISSUE_BODY_MAX_BYTES


def test_split_to_github_limit_over_limit_splits_without_loss() -> None:
    body = "x" * (config.GITHUB_ISSUE_BODY_MAX_BYTES + 1000)
    chunks = oos_filer._split_to_github_limit(body)
    assert len(chunks) > 1
    assert all(oos_filer._body_bytes(chunk) <= config.GITHUB_ISSUE_BODY_MAX_BYTES for chunk in chunks)
    reassembled = "".join(
        chunk.replace(oos_filer._BODY_PART_FOOTER, "").replace(oos_filer._BODY_PART_HEADER, "")
        for chunk in chunks
    )
    assert reassembled == body


def test_split_to_github_limit_multibyte_over_byte_limit() -> None:
    body = "中" * 22000
    assert len(body) < config.GITHUB_ISSUE_BODY_MAX_BYTES
    assert oos_filer._body_bytes(body) > config.GITHUB_ISSUE_BODY_MAX_BYTES
    chunks = oos_filer._split_to_github_limit(body)
    assert len(chunks) > 1
    assert all(oos_filer._body_bytes(chunk) <= config.GITHUB_ISSUE_BODY_MAX_BYTES for chunk in chunks)


def test_body_files_for_item_oversized_body_is_split(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OOS_ISSUES_PER_RUN_CAP", "99")
    _setup(tmp_path)
    large_body = "A" * (config.GITHUB_ISSUE_BODY_MAX_BYTES + 5000)
    _write_oos(tmp_path, f"### OOS_1: Big finding\n- **Description**: {large_body}\n- **Phase**: implement\n")
    fake = FakeCli(tmp_path)
    rc, _payload = _run(tmp_path, fake, monkeypatch)
    assert rc == 0
    create_calls = [call for call in fake.calls if call[:2] == ["issue", "create-one"]]
    assert len(create_calls) > 1
    assert all(oos_filer._body_bytes(body) <= config.GITHUB_ISSUE_BODY_MAX_BYTES for body in fake.created_bodies)
    reassembled = "".join(
        body.replace(oos_filer._BODY_PART_FOOTER, "").replace(oos_filer._BODY_PART_HEADER, "")
        for body in fake.created_bodies
    )
    assert large_body in reassembled


def test_multipart_retry_preserves_all_part_urls_in_ndjson(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OOS_ISSUES_PER_RUN_CAP", "99")
    _setup(tmp_path)
    large_body = "B" * (config.GITHUB_ISSUE_BODY_MAX_BYTES * 2 + 10000)
    _write_oos(tmp_path, f"### OOS_1: Oversized\n- **Description**: {large_body}\n- **Phase**: implement\n")
    fake = FakeCli(tmp_path)
    fake.urls = [
        "https://github.com/owner/repo/issues/201",
        "https://github.com/owner/repo/issues/202",
        "https://github.com/owner/repo/issues/203",
    ]
    rc, _payload = _run(tmp_path, fake, monkeypatch)
    assert rc == 0
    part_urls = fake.urls[: len(fake.created_bodies)]
    assert len(part_urls) >= 3
    run_dir = tmp_path / "larch-logs" / "implement" / "run-1"
    sentinel = (tmp_path / "oos-issues-created.md").read_text(encoding="utf-8")
    ndjson = (run_dir / "oos-issues.ndjson").read_text(encoding="utf-8")
    for url in part_urls:
        assert url in sentinel
        assert url in ndjson
    retry = FakeCli(tmp_path)
    retry.urls = fake.urls
    rc_retry, _retry_payload = _run(tmp_path, retry, monkeypatch)
    assert rc_retry == 0
    assert not [call for call in retry.calls if call[:2] == ["issue", "create-one"]]
    ndjson_retry = (run_dir / "oos-issues.ndjson").read_text(encoding="utf-8")
    for url in part_urls:
        assert url in ndjson_retry


def test_body_files_for_item_fits_body_preserved_verbatim(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OOS_ISSUES_PER_RUN_CAP", "99")
    _setup(tmp_path)
    body = "Normal sized body that fits fine."
    _write_oos(tmp_path, f"### OOS_1: Normal\n- **Description**: {body}\n- **Phase**: implement\n")
    fake = FakeCli(tmp_path)
    rc, _payload = _run(tmp_path, fake, monkeypatch)
    assert rc == 0
    assert len(fake.created_bodies) == 1
    filed_body = fake.created_bodies[0]
    assert body in filed_body
    assert oos_filer._BODY_PART_FOOTER not in filed_body


def test_stable_ids_by_combined_item_covers_every_source_on_count_reducing_combine() -> None:
    # Directly pins the dedup-safety invariant of the combine-to-stable-id mapper
    # for the Codex-combine path the OOS finding flagged: when combine yields
    # fewer output blocks than sources, every source stable id must still appear
    # across the mapping's values, or a retry's _split_persisted_matches would
    # miss a block and re-file the rolled-up remainder. Per-output attribution is
    # best-effort — the post-cap text the mapper sees carries no combine
    # source-metadata to map a non-contiguous merge by — so coverage, not exact
    # attribution, is the guaranteed property.
    blocks = [
        oos_filer.AcceptedBlock("alpha", "body a", "src:OOS_1"),
        oos_filer.AcceptedBlock("beta", "body b", "src:OOS_2"),
        oos_filer.AcceptedBlock("gamma", "body c", "src:OOS_3"),
    ]
    combined_text = "### OOS_1: merged alpha\nbody\n\n### OOS_2: tail\nbody\n"
    assert len(file_oos._parse_oos_blocks(combined_text)) == 2  # ambiguous middle branch
    mapping = oos_filer._stable_ids_by_combined_item(blocks=blocks, combined_text=combined_text)

    covered = {sid for ids in mapping.values() for sid in ids}
    assert covered == {"src:OOS_1", "src:OOS_2", "src:OOS_3"}
