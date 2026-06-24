"""Tests for design_oos.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from collections.abc import Sequence

import pytest  # noqa: TC002

import design_lifecycle
import design_oos
import design_pause
from test_design_cli_ports import test_design_port_registry_entries_are_machine_stdout  # noqa: F401  # pylint: disable=unused-import  # pyright: ignore[reportUnusedImport]


def _kv(stdout: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in stdout.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key] = value
    return out


def test_count_non_security_blocks_delegates_to_file_oos(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []

    def fake_count(text: str) -> int:
        seen.append(text)
        return 7

    monkeypatch.setattr(design_oos.file_oos, "_count_non_security_markdown", fake_count)

    text = "### OOS_1: public\n- **Description**: body\n"
    assert design_oos._count_non_security_blocks(text) == 7  # pyright: ignore[reportPrivateUsage]
    assert seen == [text]


def test_prepare_ready_emits_expected_contract(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    accepted = tmp_path / "oos-accepted-design.md"
    _ = accepted.write_text(
        "### OOS_7: first\n- body\n\n"
        "### OOS_9: second\n- body\n",
        encoding="utf-8",
    )
    seen: list[tuple[str, ...]] = []

    def fake_run_cli(*args: str, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        seen.append(args)
        if args[:2] == ("oos", "issue-cap"):
            output = Path(args[args.index("--output") + 1])
            _ = output.write_text("### OOS_1: capped\n", encoding="utf-8")
            return subprocess.CompletedProcess(list(args), 0, "", "")
        if args[:2] == ("oos", "file-conflict-deps"):
            output = Path(args[args.index("--output") + 1])
            _ = output.write_text("1\t2\n", encoding="utf-8")
            return subprocess.CompletedProcess(list(args), 0, "", "")
        return subprocess.CompletedProcess(list(args), 0, "", "")

    def _stub_count(_text: str) -> int:
        return 2

    monkeypatch.setattr(design_oos, "_run_cli", fake_run_cli)
    monkeypatch.setattr(design_oos, "_count_non_security_blocks", _stub_count)

    rc = design_oos.file_oos_prepare_main(["--design-tmpdir", str(tmp_path)])
    assert rc == 0
    kv = _kv(capsys.readouterr().out)
    assert kv["FILE_DESIGN_OOS_STATUS"] == "ready"
    assert kv["FILE_DESIGN_OOS_DEPS_AVAILABLE"] == "true"
    assert kv["FILE_DESIGN_OOS_COMBINED"] == str(tmp_path / "oos-combined.md")
    assert kv["FILE_DESIGN_OOS_DEPS_TSV"] == str(tmp_path / "oos-intra-batch-deps.tsv")
    assert kv["FILE_DESIGN_OOS_ORDER"] == str(tmp_path / "oos-design-filing-order.txt")
    assert (tmp_path / "oos-design-filing-order.txt").read_text(encoding="utf-8") == "7\n9\n"
    assert ("oos", "issue-cap") in [call[:2] for call in seen]
    assert ("oos", "file-conflict-deps") in [call[:2] for call in seen]
    cap_call = next(call for call in seen if call[:2] == ("oos", "issue-cap"))
    assert "--input-file" in cap_call
    assert "--output" in cap_call
    assert "--design-tmpdir" not in cap_call


def test_prepare_all_security_skips_without_filing_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    accepted = tmp_path / "oos-accepted-design.md"
    _ = accepted.write_text(
        "### OOS_4: hardening\n"
        "- **focus-area**: security-hardening\n"
        "- **Phase**: design\n",
        encoding="utf-8",
    )

    def unexpected_run_cli(*_args: str, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        raise AssertionError("_run_cli should not run for all-security design OOS")

    monkeypatch.setattr(design_oos, "_run_cli", unexpected_run_cli)

    rc = design_oos.file_oos_prepare_main(["--design-tmpdir", str(tmp_path)])
    assert rc == 0
    kv = _kv(capsys.readouterr().out)
    assert kv["FILE_DESIGN_OOS_STATUS"] == "skip-all-security"
    assert not (tmp_path / "oos-combined.md").exists()
    assert not (tmp_path / "oos-intra-batch-deps.tsv").exists()
    assert not (tmp_path / "oos-design-filing-order.txt").exists()


def test_prepare_uses_cross_session_cache_and_recovers_accepted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    accepted = tmp_path / "oos-accepted-design.md"
    _ = accepted.write_text("### OOS_3: title\n- desc\n", encoding="utf-8")
    cache = tmp_path / "cache.md"
    _ = cache.write_text(
        "OOS_FILE_MAP\t3\thttps://github.com/acme/repo/issues/123\n"
        "https://github.com/acme/repo/issues/123\n",
        encoding="utf-8",
    )
    def _stub_cache1(_issue: str) -> Path:
        return cache

    monkeypatch.setattr(design_oos, "_cross_session_cache_path", _stub_cache1)

    rc = design_oos.file_oos_prepare_main(["--design-tmpdir", str(tmp_path), "--issue-number", "44"])
    assert rc == 0
    kv = _kv(capsys.readouterr().out)
    assert kv["FILE_DESIGN_OOS_STATUS"] == "skip-sentinel"
    assert "Filed URL" in accepted.read_text(encoding="utf-8")
    assert (tmp_path / "oos-issues-created.md").is_file()


def test_annotate_updates_accepted_and_returns_nonzero_on_reported_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    accepted = tmp_path / "oos-accepted-design.md"
    _ = accepted.write_text(
        "### OOS_1: alpha\n- desc\n\n"
        "### OOS_2: beta\n- desc\n",
        encoding="utf-8",
    )
    _ = (tmp_path / "oos-design-filing-order.txt").write_text("1\n2\n", encoding="utf-8")
    stdout_file = tmp_path / "oos-issue.stdout.txt"
    _ = stdout_file.write_text(
        "ISSUE_1_URL=https://github.com/acme/repo/issues/101\n"
        "ISSUE_2_DUPLICATE_OF_URL=https://github.com/acme/repo/issues/102\n"
        "ISSUE_2_FAILED=true\n"
        "ISSUES_FAILED=1\n",
        encoding="utf-8",
    )
    cache = tmp_path / "cache.md"

    def _stub_cache2(_issue: str) -> Path:
        return cache

    monkeypatch.setattr(design_oos, "_cross_session_cache_path", _stub_cache2)

    rc = design_oos.file_oos_annotate_main(["--design-tmpdir", str(tmp_path), "--issue-stdout-file", str(stdout_file), "--issue-number", "44"])
    assert rc == 1
    kv = _kv(capsys.readouterr().out)
    assert kv["FILE_DESIGN_OOS_STATUS"] == "annotate-partial-failed"
    accepted_text = accepted.read_text(encoding="utf-8")
    assert "### OOS_1: alpha" in accepted_text
    assert "- **Filed URL**: https://github.com/acme/repo/issues/101" in accepted_text
    assert "### OOS_2: beta" in accepted_text
    assert "- **Filed URL**: https://github.com/acme/repo/issues/102" not in accepted_text
    assert not (tmp_path / "oos-issues-created.md").exists()
    partial_text = (tmp_path / "oos-issues-created.partial.md").read_text(encoding="utf-8")
    assert "OOS_FILE_MAP\t1\thttps://github.com/acme/repo/issues/101" in partial_text
    assert "https://github.com/acme/repo/issues/101" in partial_text
    assert not cache.exists()

    rc_prepare = design_oos.file_oos_prepare_main(["--design-tmpdir", str(tmp_path), "--issue-number", "44"])
    assert rc_prepare == 0
    kv_prepare = _kv(capsys.readouterr().out)
    assert kv_prepare["FILE_DESIGN_OOS_STATUS"] != "skip-sentinel"


def test_annotate_empty_stdout_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = design_oos.file_oos_annotate_main(
        ["--design-tmpdir", str(tmp_path), "--issue-stdout-file", str(tmp_path / "missing.txt")],
    )
    assert rc == 1
    kv = _kv(capsys.readouterr().out)
    assert kv["FILE_DESIGN_OOS_STATUS"] == "annotate-failed-empty-stdout"


def _plugin_root() -> str:
    return str(Path(__file__).resolve().parents[1])


def _step5b_argv() -> list[str]:
    return ["--plugin-root", _plugin_root()]


def test_step5b_prepare_ready_orchestration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setattr(design_lifecycle, "_maybe_timing_mark", _noop_timing_mark)

    def fake_prepare(argv: Sequence[str]) -> int:
        assert argv[:2] == ["--design-tmpdir", str(tmp_path)]
        print("FILE_DESIGN_OOS_DEPS_AVAILABLE=true")
        print("FILE_DESIGN_OOS_STATUS=ready")
        print(f"FILE_DESIGN_OOS_COMBINED={tmp_path / 'oos-combined.md'}")
        print(f"FILE_DESIGN_OOS_DEPS_TSV={tmp_path / 'oos-intra-batch-deps.tsv'}")
        return 0

    monkeypatch.setattr(design_lifecycle.design_oos, "file_oos_prepare_main", fake_prepare)

    rc = design_lifecycle.step5b_prepare_main(_step5b_argv())
    out = capsys.readouterr().out

    assert rc == 0
    assert (tmp_path / "oos-filing-prepare.env").is_file()
    assert "STEP5B_STATUS=ready" in out
    assert "STEP5B_NEEDS_ANNOTATE=true" in out
    assert not (tmp_path / ".completed" / "step-5b").exists()


def test_step5b_prepare_skip_marks_complete(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setattr(design_lifecycle, "_maybe_timing_mark", _noop_timing_mark)

    def fake_prepare(_argv: Sequence[str]) -> int:
        print("FILE_DESIGN_OOS_STATUS=skip-no-items")
        return 0

    monkeypatch.setattr(design_lifecycle.design_oos, "file_oos_prepare_main", fake_prepare)

    rc = design_lifecycle.step5b_prepare_main(_step5b_argv())
    out = capsys.readouterr().out

    assert rc == 0
    assert "STEP5B_STATUS=skip-no-items" in out
    assert (tmp_path / ".completed" / "step-5b").is_file()


def test_step5b_prepare_failure_continues_and_marks_complete(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setattr(design_lifecycle, "_maybe_timing_mark", _noop_timing_mark)
    appended: list[tuple[str, int, Path]] = []

    def fake_prepare(_argv: Sequence[str]) -> int:
        print("prepare failed", file=sys.stderr)
        return 2

    def fake_append(
        *,
        plugin_root: Path,
        design_tmpdir: Path,
        site: str,
        tool: str,
        exit_code: int,
        category: str,
        output_file: Path,
    ) -> bool:
        _ = plugin_root, design_tmpdir, site, category
        appended.append((tool, exit_code, output_file))
        return True

    monkeypatch.setattr(design_lifecycle.design_oos, "file_oos_prepare_main", fake_prepare)
    monkeypatch.setattr(design_lifecycle, "_append_failure", fake_append)

    rc = design_lifecycle.step5b_prepare_main(_step5b_argv())
    out = capsys.readouterr().out

    assert rc == 0
    assert "OOS filing prepare failed" in out
    assert "continuing to Step 5b.5" in out
    assert "Step 5c" not in out
    assert "STEP5B_STATUS=prepare-failed-continue" in out
    assert "OOS_PREP_RC=2" in out
    assert appended == [("file-design-oos.sh prepare", 2, tmp_path / "oos-filing-prepare.stderr.log")]
    assert (tmp_path / ".completed" / "step-5b").is_file()


def test_step5b_prepare_allows_relative_missing_tmpdir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DESIGN_TMPDIR", "relative-missing")
    monkeypatch.setattr(design_lifecycle, "_maybe_timing_mark", _noop_timing_mark)
    seen_step4b = False

    def fake_prepare(_argv: Sequence[str]) -> int:
        nonlocal seen_step4b
        seen_step4b = (tmp_path / "relative-missing" / ".completed" / "step-4b").is_file()
        print("FILE_DESIGN_OOS_STATUS=skip-no-items")
        return 0

    monkeypatch.setattr(design_lifecycle.design_oos, "file_oos_prepare_main", fake_prepare)

    rc = design_lifecycle.step5b_prepare_main(_step5b_argv())
    out = capsys.readouterr().out

    assert rc == 0
    assert "STEP5B_STATUS=skip-no-items" in out
    assert seen_step4b
    assert (tmp_path / "relative-missing" / ".completed").is_dir()


def test_step5b_prepare_pause_returns_pause_save_rc(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    _ = (tmp_path / ".pause-requested").write_text("", encoding="utf-8")
    called = False

    def fake_prepare(_argv: Sequence[str]) -> int:
        nonlocal called
        called = True
        return 0

    def fake_pause(*, design_tmpdir: Path, ctx: object = None) -> int:
        _ = design_tmpdir, ctx
        return 7

    monkeypatch.setattr(design_lifecycle.design_oos, "file_oos_prepare_main", fake_prepare)
    monkeypatch.setattr(design_lifecycle, "_call_pause_save", fake_pause)

    rc = design_lifecycle.step5b_prepare_main(_step5b_argv())

    assert rc == 7
    assert not called


def test_step5b_prepare_callable_crash_continues(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setattr(design_lifecycle, "_maybe_timing_mark", _noop_timing_mark)
    monkeypatch.setattr(design_lifecycle, "_append_failure", _fake_append_success)

    def fake_prepare(_argv: Sequence[str]) -> int:
        raise RuntimeError("prepare boom")

    monkeypatch.setattr(design_lifecycle.design_oos, "file_oos_prepare_main", fake_prepare)

    rc = design_lifecycle.step5b_prepare_main(_step5b_argv())
    out = capsys.readouterr().out

    assert rc == 0
    assert "STEP5B_STATUS=prepare-failed-continue" in out
    assert "RuntimeError: prepare boom" in (tmp_path / "oos-filing-prepare.stderr.log").read_text(encoding="utf-8")
    assert (tmp_path / ".completed" / "step-5b").is_file()


def test_step5b_annotate_success_marks_complete(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))

    def fake_annotate(_argv: Sequence[str]) -> int:
        print("FILE_DESIGN_OOS_STATUS=annotate-complete")
        return 0

    monkeypatch.setattr(design_lifecycle.design_oos, "file_oos_annotate_main", fake_annotate)

    rc = design_lifecycle.step5b_annotate_main(_step5b_argv())
    out = capsys.readouterr().out

    assert rc == 0
    assert (tmp_path / "oos-filing-annotate.stdout.txt").is_file()
    assert (tmp_path / ".completed" / "step-5b").is_file()
    assert "STEP5B_STATUS=annotate-complete" in out


def test_step5b_annotate_failure_does_not_mark_complete(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setattr(design_lifecycle, "_append_failure", _fake_append_success)

    def fake_annotate(_argv: Sequence[str]) -> int:
        print("annotate failed", file=sys.stderr)
        return 3

    monkeypatch.setattr(design_lifecycle.design_oos, "file_oos_annotate_main", fake_annotate)

    rc = design_lifecycle.step5b_annotate_main(_step5b_argv())
    out = capsys.readouterr().out

    assert rc == 3
    assert "STEP5B_STATUS=annotate-failed" in out
    assert not (tmp_path / ".completed" / "step-5b").exists()


def test_step5b_annotate_failure_with_partial_issue_stdout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setattr(design_lifecycle, "_append_failure", _fake_append_success)
    issue_stdout = tmp_path / "oos-issue.stdout.txt"
    _ = issue_stdout.write_text("ISSUES_FAILED=1\n", encoding="utf-8")
    seen_stdout_file = ""

    def fake_annotate(argv: Sequence[str]) -> int:
        nonlocal seen_stdout_file
        seen_stdout_file = argv[argv.index("--issue-stdout-file") + 1]
        print("annotate failed", file=sys.stderr)
        return 4

    monkeypatch.setattr(design_lifecycle.design_oos, "file_oos_annotate_main", fake_annotate)

    rc = design_lifecycle.step5b_annotate_main(_step5b_argv())
    out = capsys.readouterr().out

    assert rc == 4
    assert "OOS filing completed with ISSUES_FAILED>0" in out
    assert seen_stdout_file == str(issue_stdout)
    assert (tmp_path / ".completed" / "step-5b").is_file()


def test_step5b_annotate_failure_with_issue_stdout_marks_complete_for_step5b5(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setattr(design_lifecycle, "_append_failure", _fake_append_success)
    issue_stdout = tmp_path / "oos-issue.stdout.txt"
    _ = issue_stdout.write_text("ISSUES_FAILED=0\nISSUES_CREATED=1\n", encoding="utf-8")

    def fake_annotate(_argv: Sequence[str]) -> int:
        print("annotate failed", file=sys.stderr)
        return 3

    monkeypatch.setattr(design_lifecycle.design_oos, "file_oos_annotate_main", fake_annotate)

    rc = design_lifecycle.step5b_annotate_main(_step5b_argv())
    out = capsys.readouterr().out

    assert rc == 3
    assert "STEP5B_STATUS=annotate-failed" in out
    assert (tmp_path / ".completed" / "step-5b").is_file()


def test_step5b_annotate_partial_failure_routes_to_step5b5_and_step5c(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setattr(design_lifecycle, "_append_failure", _fake_append_success)
    issue_stdout = tmp_path / "oos-issue.stdout.txt"
    _ = issue_stdout.write_text("ISSUES_FAILED=1\n", encoding="utf-8")

    def fake_annotate(_argv: Sequence[str]) -> int:
        print("annotate failed", file=sys.stderr)
        return 4

    monkeypatch.setattr(design_lifecycle.design_oos, "file_oos_annotate_main", fake_annotate)

    _ = design_lifecycle.step5b_annotate_main(_step5b_argv())

    assert (tmp_path / ".completed" / "step-5b").is_file()
    assert design_pause._determine_step(design_tmpdir=tmp_path, plugin_root=Path.cwd()) == "5b.5"  # pyright: ignore[reportPrivateUsage]
    _ = (tmp_path / ".completed" / "step-5b.5").write_text("", encoding="utf-8")
    assert design_pause._determine_step(design_tmpdir=tmp_path, plugin_root=Path.cwd()) == "5c"  # pyright: ignore[reportPrivateUsage]


def test_step5b_annotate_pause_returns_pause_save_rc(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    _ = (tmp_path / ".pause-requested").write_text("", encoding="utf-8")
    called = False

    def fake_annotate(_argv: Sequence[str]) -> int:
        nonlocal called
        called = True
        return 0

    def fake_pause(*, design_tmpdir: Path, ctx: object = None) -> int:
        _ = design_tmpdir, ctx
        return 9

    monkeypatch.setattr(design_lifecycle.design_oos, "file_oos_annotate_main", fake_annotate)
    monkeypatch.setattr(design_lifecycle, "_call_pause_save", fake_pause)

    rc = design_lifecycle.step5b_annotate_main(_step5b_argv())

    assert rc == 9
    assert not called


def test_step5b_annotate_callable_crash_fails_without_completion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setattr(design_lifecycle, "_append_failure", _fake_append_success)

    def fake_annotate(_argv: Sequence[str]) -> int:
        raise RuntimeError("annotate boom")

    monkeypatch.setattr(design_lifecycle.design_oos, "file_oos_annotate_main", fake_annotate)

    rc = design_lifecycle.step5b_annotate_main(_step5b_argv())
    out = capsys.readouterr().out

    assert rc == 1
    assert "STEP5B_STATUS=annotate-failed" in out
    assert "RuntimeError: annotate boom" in (tmp_path / "oos-filing-annotate.stderr.log").read_text(encoding="utf-8")
    assert not (tmp_path / ".completed" / "step-5b").exists()


def _noop_timing_mark(*, label: str, ctx: object = None) -> None:
    _ = label, ctx


def _fake_append_success(
    *,
    plugin_root: Path,
    design_tmpdir: Path,
    site: str,
    tool: str,
    exit_code: int,
    category: str,
    output_file: Path,
) -> bool:
    _ = plugin_root, design_tmpdir, site, tool, exit_code, category, output_file
    return True
