"""Tests for oos_filer.py."""

# pyright: reportUnusedCallResult=false

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
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

    def __call__(self, args: list[str], *, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
        self.calls.append(args)
        if args[:2] == ["run-log", "manifest"]:
            return _cp(args)
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
                body = out_dir / f"item-{index}-body.txt"
                body.write_text(item.body, encoding="utf-8")
                lines.extend(
                    [
                        f"ITEM_{index}_TITLE={item.title}",
                        f"ITEM_{index}_BODY_FILE={body}",
                        f"ITEM_{index}_REVIEWER={item.reviewer}",
                        f"ITEM_{index}_VOTE_TALLY={item.vote}",
                        f"ITEM_{index}_PHASE={item.phase}",
                    ],
                )
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
    monkeypatch.setattr(oos_filer, "_probe_tracking_blocker", lambda *_a: fake.blocker_probe_rc == 0)  # type: ignore[arg-type]
    rc = oos_filer.cmd_file(["--implement-tmpdir", str(tmp_path), "--codex-timeout", "1"])
    return rc, {}


def test_empty_batch_writes_zero_statistics_and_stamps_false(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(tmp_path)
    fake = FakeCli(tmp_path)
    rc, _payload = _run(tmp_path, fake, monkeypatch)
    assert rc == 0
    assert "Run run-1: 0 OOS issue(s) filed." in (tmp_path / "larch-logs" / "implement" / "run-1" / "run-statistics.md").read_text(encoding="utf-8")
    assert any("steps_ran.step9a1=false" in call for call in fake.calls for call in call)
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
        "### OOS_1: First\n- touches `src/a.py:1-5`\n\n### OOS_2: Second\n- touches `src/a.py:2-6`\n",
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
