"""Tests for design_oos.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from collections.abc import Sequence

import pytest

from larch.design import design_lifecycle
from larch.design import design_step5b
from larch.design import design_oos
from larch.design import design_pause
from test_design_cli_ports import test_design_port_registry_entries_are_machine_stdout  # noqa: F401  # pylint: disable=unused-import,import-error  # pyright: ignore[reportUnusedImport]


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
    _ = cache.with_name("cache.accepted-design.md").write_text(
        "### OOS_3: title\n- desc\n- **Filed URL**: https://github.com/acme/repo/issues/123\n",
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


def test_prepare_ignores_stale_cross_session_cache_when_block_identity_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    accepted = tmp_path / "oos-accepted-design.md"
    _ = accepted.write_text(
        "### OOS_1: gamma\n- **Description**: current one\n\n"
        "### OOS_2: delta\n- **Description**: current two\n",
        encoding="utf-8",
    )
    cache = tmp_path / "44.md"
    _ = cache.write_text(
        "OOS_FILE_MAP\t1\thttps://github.com/acme/repo/issues/123\n"
        "OOS_FILE_MAP\t2\thttps://github.com/acme/repo/issues/124\n",
        encoding="utf-8",
    )
    _ = cache.with_name("44.accepted-design.md").write_text(
        "### OOS_1: alpha\n- **Description**: previous one\n- **Filed URL**: https://github.com/acme/repo/issues/123\n\n"
        "### OOS_2: beta\n- **Description**: previous two\n- **Filed URL**: https://github.com/acme/repo/issues/124\n",
        encoding="utf-8",
    )

    def _stub_cache(_issue: str) -> Path:
        return cache

    monkeypatch.setattr(design_oos, "_cross_session_cache_path", _stub_cache)

    rc = design_oos.file_oos_prepare_main(["--design-tmpdir", str(tmp_path), "--issue-number", "44"])
    out = _kv(capsys.readouterr().out)

    assert rc == 0
    assert out["FILE_DESIGN_OOS_STATUS"] == "ready"
    assert not (tmp_path / "oos-issues-created.md").exists()
    assert (tmp_path / "oos-combined.md").is_file()


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
    return str(Path(__file__).resolve().parents[3])


def _step5b_argv() -> list[str]:
    return ["--plugin-root", _plugin_root()]


def test_step5b_prepare_ready_orchestration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setattr(design_step5b, "_maybe_timing_mark", _noop_timing_mark)

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
    assert "NEXT_ACTION=file-issues" in out
    assert "STEP5B_NEEDS_ANNOTATE=true" in out
    assert "OOS_SKIP_BREADCRUMB=" not in out
    assert not (tmp_path / ".completed" / "step-5b").exists()


@pytest.mark.parametrize(
    ("status", "breadcrumb"),
    [
        ("skip-sentinel", "⏩ 5b: oos filing; sentinel recovery (skip pipeline)"),
        ("skip-no-items", "⏩ 5b: oos filing; no accepted-OOS items"),
        ("skip-all-security", "⏩ 5b: oos filing; no non-security OOS items"),
    ],
)
def test_step5b_prepare_skip_marks_complete(
    status: str,
    breadcrumb: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setattr(design_step5b, "_maybe_timing_mark", _noop_timing_mark)

    def fake_prepare(_argv: Sequence[str]) -> int:
        print(f"FILE_DESIGN_OOS_STATUS={status}")
        return 0

    monkeypatch.setattr(design_lifecycle.design_oos, "file_oos_prepare_main", fake_prepare)

    rc = design_lifecycle.step5b_prepare_main(_step5b_argv())
    out = capsys.readouterr().out

    assert rc == 0
    assert f"STEP5B_STATUS={status}" in out
    assert "NEXT_ACTION=skip-pipeline" in out
    assert f"OOS_SKIP_BREADCRUMB={breadcrumb}" in out
    assert "STEP5B_NEEDS_ANNOTATE=true" not in out
    assert (tmp_path / ".completed" / "step-5b").is_file()


@pytest.mark.parametrize("issue_stdout_text", ["", "ISSUE_1_URL=https://github.com/acme/repo/issues/101\n"])
def test_step5b_prepare_already_filed_sentinel_routes_annotation_by_issue_stdout(
    issue_stdout_text: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setattr(design_step5b, "_maybe_timing_mark", _noop_timing_mark)
    if issue_stdout_text:
        _ = (tmp_path / "oos-issue.stdout.txt").write_text(issue_stdout_text, encoding="utf-8")

    def fake_prepare(_argv: Sequence[str]) -> int:
        print("FILE_DESIGN_OOS_STATUS=skip-already-filed-sentinel")
        print("WARN=already filed recovery warning")
        return 0

    monkeypatch.setattr(design_lifecycle.design_oos, "file_oos_prepare_main", fake_prepare)

    rc = design_lifecycle.step5b_prepare_main(_step5b_argv())
    out = capsys.readouterr().out

    assert rc == 0
    assert "NEXT_ACTION=skip-pipeline" in out
    assert "OOS_SKIP_BREADCRUMB=⏩ 5b: oos filing; oos-issue-sentinel present (already filed); skip pipeline" in out
    assert "WARN=already filed recovery warning" in out
    if issue_stdout_text:
        assert "STEP5B_NEEDS_ANNOTATE=true" in out
        assert not (tmp_path / ".completed" / "step-5b").exists()
    else:
        assert "STEP5B_NEEDS_ANNOTATE=true" not in out
        assert (tmp_path / ".completed" / "step-5b").is_file()


def test_step5b_prepare_unknown_status_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setattr(design_step5b, "_maybe_timing_mark", _noop_timing_mark)

    def fake_prepare(_argv: Sequence[str]) -> int:
        print("FILE_DESIGN_OOS_STATUS=unrecognized-future-status")
        return 0

    monkeypatch.setattr(design_lifecycle.design_oos, "file_oos_prepare_main", fake_prepare)

    rc = design_lifecycle.step5b_prepare_main(_step5b_argv())
    out = capsys.readouterr().out

    assert rc == 2
    assert "STEP5B_STATUS=unknown-oos-status" in out
    assert "NEXT_ACTION=unknown-oos-status" in out
    assert "unrecognized OOS prepare status" in out
    assert "stop for repair" in out
    assert "STEP5B_NEEDS_ANNOTATE=true" not in out
    assert not (tmp_path / ".completed" / "step-5b").exists()


def test_step5b_prepare_unknown_status_env_parseable_on_nonzero_rc(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Orchestrator must read NEXT_ACTION from env even when prepare wrapper exits rc=2."""
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setattr(design_step5b, "_maybe_timing_mark", _noop_timing_mark)

    def fake_prepare(_argv: Sequence[str]) -> int:
        print("FILE_DESIGN_OOS_STATUS=legacy-unmapped-status")
        return 0

    monkeypatch.setattr(design_lifecycle.design_oos, "file_oos_prepare_main", fake_prepare)

    rc = design_lifecycle.step5b_prepare_main(_step5b_argv())
    _ = capsys.readouterr()
    env_text = (tmp_path / "oos-filing-prepare.env").read_text(encoding="utf-8")

    assert rc == 2
    assert _kv(env_text)["NEXT_ACTION"] == "unknown-oos-status"
    assert _kv(env_text)["STEP5B_STATUS"] == "unknown-oos-status"


def test_step5b_prepare_next_action_disagreement_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setattr(design_step5b, "_maybe_timing_mark", _noop_timing_mark)

    def fake_prepare(_argv: Sequence[str]) -> int:
        # status says ready (file-issues) but upstream NEXT_ACTION says skip-pipeline
        print("FILE_DESIGN_OOS_STATUS=ready")
        print("NEXT_ACTION=skip-pipeline")
        return 0

    monkeypatch.setattr(design_lifecycle.design_oos, "file_oos_prepare_main", fake_prepare)

    rc = design_lifecycle.step5b_prepare_main(_step5b_argv())
    out = capsys.readouterr().out
    env_text = (tmp_path / "oos-filing-prepare.env").read_text(encoding="utf-8")

    assert rc == 2
    assert "STEP5B_STATUS=unknown-oos-status" in out
    assert "NEXT_ACTION=unknown-oos-status" in out
    assert _kv(env_text)["FILE_DESIGN_OOS_STATUS"] == "ready"
    assert _kv(env_text)["NEXT_ACTION"] == "unknown-oos-status"
    assert _kv(env_text)["STEP5B_STATUS"] == "unknown-oos-status"
    assert not (tmp_path / ".completed" / "step-5b").exists()


def test_step5b_prepare_failure_continues_and_marks_complete(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setattr(design_step5b, "_maybe_timing_mark", _noop_timing_mark)
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
    monkeypatch.setattr(design_step5b, "_append_failure", fake_append)

    rc = design_lifecycle.step5b_prepare_main(_step5b_argv())
    out = capsys.readouterr().out

    assert rc == 0
    assert "OOS filing prepare failed" in out
    assert "continuing to Step 5b.5" in out
    assert "Step 5c" not in out
    assert "STEP5B_STATUS=prepare-failed-continue" in out
    assert "NEXT_ACTION=skip-pipeline" in out
    assert "OOS_PREP_RC=2" in out
    assert "OOS_SKIP_BREADCRUMB=" not in out
    assert appended == [("file-design-oos.sh prepare", 2, tmp_path / "oos-filing-prepare.stderr.log")]
    assert (tmp_path / ".completed" / "step-5b").is_file()


def test_step5b_prepare_allows_relative_missing_tmpdir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DESIGN_TMPDIR", "relative-missing")
    monkeypatch.setattr(design_step5b, "_maybe_timing_mark", _noop_timing_mark)
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
    monkeypatch.setattr(design_step5b, "_call_pause_save", fake_pause)

    rc = design_lifecycle.step5b_prepare_main(_step5b_argv())

    assert rc == 7
    assert not called


def test_step5b_prepare_callable_crash_continues(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setattr(design_step5b, "_maybe_timing_mark", _noop_timing_mark)
    monkeypatch.setattr(design_step5b, "_append_failure", _fake_append_success)

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
    monkeypatch.setattr(design_step5b, "_append_failure", _fake_append_success)

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
    monkeypatch.setattr(design_step5b, "_append_failure", _fake_append_success)
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
    monkeypatch.setattr(design_step5b, "_append_failure", _fake_append_success)
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


def test_step5b_annotate_empty_stdout_retries_once_then_stops(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setattr(design_step5b, "_append_failure", _fake_append_success)
    attempts = {"count": 0}

    def fake_annotate(_argv: Sequence[str]) -> int:
        attempts["count"] += 1
        if attempts["count"] == 3:
            print("FILE_DESIGN_OOS_STATUS=annotate-complete")
            return 0
        print("FILE_DESIGN_OOS_STATUS=annotate-failed-empty-stdout")
        print("NEXT_ACTION=retry-file-and-annotate")
        print("WARN=empty issue stdout")
        return 1

    monkeypatch.setattr(design_lifecycle.design_oos, "file_oos_annotate_main", fake_annotate)

    rc_first = design_lifecycle.step5b_annotate_main(_step5b_argv())
    first = capsys.readouterr().out

    assert rc_first == 1
    assert "FILE_DESIGN_OOS_STATUS=annotate-failed-empty-stdout" in first
    assert "NEXT_ACTION=retry-file-and-annotate" in first
    assert (tmp_path / ".oos-issue-retry-used").is_file()
    assert not (tmp_path / ".completed" / "step-5b").exists()
    assert "status unclear" in first

    rc_second = design_lifecycle.step5b_annotate_main(_step5b_argv())
    second = capsys.readouterr().out

    assert rc_second == 1
    assert not (tmp_path / ".completed" / "step-5b").exists()
    assert "after retry sentinel" in second

    _ = (tmp_path / "oos-issue.stdout.txt").write_text("ISSUES_CREATED=1\nISSUES_FAILED=0\n", encoding="utf-8")
    rc_third = design_lifecycle.step5b_annotate_main(_step5b_argv())
    third = capsys.readouterr().out

    assert rc_third == 0
    assert (tmp_path / ".completed" / "step-5b").is_file()
    assert "STEP5B_STATUS=annotate-complete" in third


def test_prepare_promotes_important_pool_item(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _stub_design_oos_prepare_commands(monkeypatch)
    _ = (tmp_path / "oos-aggregate-pool.md").write_text(
        """### FINDING_1: important one
- **Severity**: important
- **Concern**: one.
""",
        encoding="utf-8",
    )

    rc = design_oos.file_oos_prepare_main(["--design-tmpdir", str(tmp_path)])

    assert rc == 0
    kv = _kv(capsys.readouterr().out)
    assert kv["FILE_DESIGN_OOS_STATUS"] == "ready"
    accepted = (tmp_path / "oos-accepted-design.md").read_text(encoding="utf-8")
    combined = (tmp_path / "oos-combined.md").read_text(encoding="utf-8")
    assert "### OOS_1: important one" in accepted
    assert "### OOS_1: important one" in combined


def test_prepare_promotes_pool_before_skip_sentinel(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _stub_design_oos_prepare_commands(monkeypatch)
    _ = (tmp_path / "oos-accepted-design.md").write_text(
        "### OOS_1: already filed\n- **Severity**: latent\n- **Filed URL**: https://github.com/acme/repo/issues/11\n",
        encoding="utf-8",
    )
    _ = (tmp_path / "oos-issues-created.md").write_text(
        "OOS_FILE_MAP\t1\thttps://github.com/acme/repo/issues/11\n",
        encoding="utf-8",
    )
    _ = (tmp_path / "oos-aggregate-pool.md").write_text(
        """### FINDING_1: pool item
- **Severity**: important
- **Concern**: promote before skip.
""",
        encoding="utf-8",
    )

    rc = design_oos.file_oos_prepare_main(["--design-tmpdir", str(tmp_path)])

    assert rc == 0
    kv = _kv(capsys.readouterr().out)
    assert kv["FILE_DESIGN_OOS_STATUS"] == "ready"
    accepted = (tmp_path / "oos-accepted-design.md").read_text(encoding="utf-8")
    combined = (tmp_path / "oos-combined.md").read_text(encoding="utf-8")
    assert "https://github.com/acme/repo/issues/11" in accepted
    assert "### OOS_2: pool item" in accepted
    assert "### OOS_2: pool item" in combined


def test_prepare_counts_accepted_and_pool_latent_items(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _stub_design_oos_prepare_commands(monkeypatch)
    _ = (tmp_path / "oos-accepted-design.md").write_text(
        """### OOS_1: latent one
- **Severity**: latent
- **Concern**: one.

### OOS_2: latent two
- **Severity**: latent
- **Concern**: two.
""",
        encoding="utf-8",
    )
    _ = (tmp_path / "oos-aggregate-pool.md").write_text(
        """### FINDING_1: latent three
- **Severity**: latent
- **Concern**: three.
""",
        encoding="utf-8",
    )

    rc = design_oos.file_oos_prepare_main(["--design-tmpdir", str(tmp_path)])

    assert rc == 0
    kv = _kv(capsys.readouterr().out)
    assert kv["FILE_DESIGN_OOS_STATUS"] == "ready"
    accepted = (tmp_path / "oos-accepted-design.md").read_text(encoding="utf-8")
    combined = (tmp_path / "oos-combined.md").read_text(encoding="utf-8")
    assert accepted.count("### OOS_") == 3
    assert combined.count("### OOS_") == 3
    assert "latent three" in accepted


def test_prepare_multi_round_pool_accumulates_latent_items(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _stub_design_oos_prepare_commands(monkeypatch)
    pool = tmp_path / "oos-aggregate-pool.md"
    _ = pool.write_text(
        """### FINDING_1: latent one
- **Severity**: latent
- **Concern**: one.

### FINDING_2: latent two
- **Severity**: latent
- **Concern**: two.
""",
        encoding="utf-8",
    )

    rc_first = design_oos.file_oos_prepare_main(["--design-tmpdir", str(tmp_path)])
    first = _kv(capsys.readouterr().out)

    assert rc_first == 0
    assert first["FILE_DESIGN_OOS_STATUS"] == "skip-no-items"
    assert not (tmp_path / "oos-accepted-design.md").exists()

    _ = pool.write_text(
        """### FINDING_1: latent one
- **Severity**: latent
- **Concern**: one.

### FINDING_2: latent two
- **Severity**: latent
- **Concern**: two.

### FINDING_3: latent three
- **Severity**: latent
- **Concern**: three.

### FINDING_4: latent four
- **Severity**: latent
- **Concern**: four.
""",
        encoding="utf-8",
    )

    rc_second = design_oos.file_oos_prepare_main(["--design-tmpdir", str(tmp_path)])
    second = _kv(capsys.readouterr().out)

    assert rc_second == 0
    assert second["FILE_DESIGN_OOS_STATUS"] == "ready"
    accepted = (tmp_path / "oos-accepted-design.md").read_text(encoding="utf-8")
    assert accepted.count("### OOS_") == 4
    assert "latent four" in accepted


def test_step5b_annotate_partial_failure_routes_to_step5b5_and_step5c(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setattr(design_step5b, "_append_failure", _fake_append_success)
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
    monkeypatch.setattr(design_step5b, "_call_pause_save", fake_pause)

    rc = design_lifecycle.step5b_annotate_main(_step5b_argv())

    assert rc == 9
    assert not called


def test_step5b_annotate_callable_crash_fails_without_completion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setattr(design_step5b, "_append_failure", _fake_append_success)

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


def _write_design_priority_fixture(tmp_path: Path, focus: str = "correctness") -> Path:
    accepted = tmp_path / "oos-accepted-design.md"
    _ = accepted.write_text(
        f"### OOS_1: alpha\n- **Focus area**: {focus}\n- **Description**: risky\n\n"
        "### OOS_2: beta\n- **Focus area**: risk-integration\n- **Description**: safe\n",
        encoding="utf-8",
    )
    _ = (tmp_path / "oos-combined.md").write_text(accepted.read_text(encoding="utf-8"), encoding="utf-8")
    _ = (tmp_path / "oos-design-filing-order.txt").write_text("1\n2\n", encoding="utf-8")
    stdout_file = tmp_path / "oos-issue.stdout.txt"
    _ = stdout_file.write_text(
        "ISSUE_1_URL=https://github.com/acme/repo/issues/101\n"
        "ISSUE_2_URL=https://github.com/acme/repo/issues/102\n"
        "ISSUES_FAILED=0\n",
        encoding="utf-8",
    )
    _ = (tmp_path / "oos-filing-prepare.env").write_text("REPO=acme/repo\n", encoding="utf-8")
    return stdout_file


def test_design_annotate_labels_only_high_risk_url_with_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stdout_file = _write_design_priority_fixture(tmp_path)
    gh_calls: list[list[str]] = []

    def fake_gh(*, repo: str, argv: list[str]) -> subprocess.CompletedProcess[str]:
        gh_calls.append([*argv, "--repo", repo])
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(design_oos, "_run_gh", fake_gh)

    rc = design_oos.file_oos_annotate_main(["--design-tmpdir", str(tmp_path), "--issue-stdout-file", str(stdout_file), "--issue-number", "44"])

    assert rc == 0
    assert gh_calls[0][:4] == ["gh", "label", "create", "oos-correctness"]
    edit_calls = [call for call in gh_calls if call[:3] == ["gh", "issue", "edit"]]
    assert edit_calls == [["gh", "issue", "edit", "101", "--add-label", "oos-correctness", "--repo", "acme/repo"]]
    assert not (tmp_path / ".oos-priority-label-pending").exists()


def test_design_annotate_label_failure_preserves_pending_retry_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    stdout_file = _write_design_priority_fixture(tmp_path)
    cache = tmp_path / "cache" / "44.md"

    def fake_cache(_issue: str) -> Path:
        return cache

    def fake_gh(*, repo: str, argv: list[str]) -> subprocess.CompletedProcess[str]:
        _ = repo
        if argv[:2] == ["gh", "label"]:
            return subprocess.CompletedProcess(argv, 0, "", "")
        return subprocess.CompletedProcess(argv, 1, "", "edit failed")

    monkeypatch.setattr(design_oos, "_cross_session_cache_path", fake_cache)
    monkeypatch.setattr(design_oos, "_run_gh", fake_gh)

    rc = design_oos.file_oos_annotate_main(["--design-tmpdir", str(tmp_path), "--issue-stdout-file", str(stdout_file), "--issue-number", "44"])
    captured = capsys.readouterr()

    assert rc == 1
    assert _kv(captured.out)["FILE_DESIGN_OOS_STATUS"] == "annotate-label-failed"
    assert (tmp_path / ".oos-priority-label-pending").is_file()
    assert "OOS_FILE_MAP\t1\thttps://github.com/acme/repo/issues/101" in (tmp_path / "oos-issues-created.md").read_text(encoding="utf-8")
    assert cache.is_file()
    assert cache.with_name("44.priority-pending").is_file()
    assert cache.with_name("44.combined.md").is_file()
    assert "priority label application failed" in captured.err


def test_design_prepare_routes_durable_pending_to_label_only_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    cache = tmp_path / "cache" / "44.md"
    cache.parent.mkdir()
    _ = cache.write_text("OOS_FILE_MAP\t1\thttps://github.com/acme/repo/issues/101\n", encoding="utf-8")
    _ = cache.with_name("44.priority-pending").write_text("pending\n", encoding="utf-8")
    _ = cache.with_name("44.combined.md").write_text("### OOS_1: alpha\n- **Focus area**: correctness\n", encoding="utf-8")
    _ = cache.with_name("44.filing-order.txt").write_text("1\n", encoding="utf-8")

    def fake_cache(_issue: str) -> Path:
        return cache

    monkeypatch.setattr(design_oos, "_cross_session_cache_path", fake_cache)

    rc = design_oos.file_oos_prepare_main(["--design-tmpdir", str(tmp_path), "--issue-number", "44"])
    kv = _kv(capsys.readouterr().out)

    assert rc == 0
    assert kv["FILE_DESIGN_OOS_STATUS"] == "label-only-retry"
    assert kv["NEXT_ACTION"] == "label-only"
    assert (tmp_path / "oos-issues-created.md").is_file()
    assert (tmp_path / "oos-combined.md").is_file()


def test_label_only_mapping_preserves_partial_failure_slot_gaps(tmp_path: Path) -> None:
    sentinel = tmp_path / "oos-issues-created.md"
    _ = sentinel.write_text(
        "OOS_FILE_MAP\t1\thttps://github.com/acme/repo/issues/101\n"
        "OOS_FILE_MAP\t3\thttps://github.com/acme/repo/issues/103\n",
        encoding="utf-8",
    )
    combined = tmp_path / "oos-combined.md"
    _ = combined.write_text(
        "### OOS_1: one\n- **Focus area**: correctness\n\n"
        "### OOS_2: two\n- **Focus area**: risk-integration\n\n"
        "### OOS_3: three\n- **Focus area**: regression\n",
        encoding="utf-8",
    )
    stdout_file = tmp_path / "oos-issue.stdout.txt"
    _ = stdout_file.write_text(
        "ISSUE_1_URL=https://github.com/acme/repo/issues/101\n"
        "ISSUE_2_FAILED=true\n"
        "ISSUE_3_URL=https://github.com/acme/repo/issues/103\n"
        "ISSUES_FAILED=1\n",
        encoding="utf-8",
    )

    mapping = design_oos._label_only_url_priority_map(  # pyright: ignore[reportPrivateUsage]
        sentinel_path=sentinel,
        combined_path=combined,
        order_file=None,
        issue_stdout_path=stdout_file,
    )

    assert mapping == {
        "https://github.com/acme/repo/issues/101": True,
        "https://github.com/acme/repo/issues/103": True,
    }


def test_step5b_label_only_retry_forwards_label_only_and_waits_for_completion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setattr(design_step5b, "_maybe_timing_mark", _noop_timing_mark)

    def fake_prepare(_argv: Sequence[str]) -> int:
        print("FILE_DESIGN_OOS_STATUS=label-only-retry")
        print("NEXT_ACTION=label-only")
        return 0

    monkeypatch.setattr(design_lifecycle.design_oos, "file_oos_prepare_main", fake_prepare)
    rc = design_lifecycle.step5b_prepare_main(_step5b_argv())
    out = capsys.readouterr().out

    assert rc == 0
    assert "NEXT_ACTION=label-only" in out
    assert "STEP5B_NEEDS_ANNOTATE=true" in out
    assert not (tmp_path / ".completed" / "step-5b").exists()

    seen_label_only = False

    def fake_annotate(argv: Sequence[str]) -> int:
        nonlocal seen_label_only
        seen_label_only = "--label-only" in argv
        print("FILE_DESIGN_OOS_STATUS=annotate-label-complete")
        return 0

    monkeypatch.setattr(design_lifecycle.design_oos, "file_oos_annotate_main", fake_annotate)
    rc_annotate = design_lifecycle.step5b_annotate_main(_step5b_argv())

    assert rc_annotate == 0
    assert seen_label_only
    assert (tmp_path / ".completed" / "step-5b").is_file()


def test_step5b_annotate_label_failed_does_not_mark_complete(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setattr(design_step5b, "_append_failure", _fake_append_success)
    _ = (tmp_path / "oos-issue.stdout.txt").write_text("ISSUES_FAILED=0\nISSUES_CREATED=1\n", encoding="utf-8")

    def fake_annotate(_argv: Sequence[str]) -> int:
        print("FILE_DESIGN_OOS_STATUS=annotate-label-failed")
        return 1

    monkeypatch.setattr(design_lifecycle.design_oos, "file_oos_annotate_main", fake_annotate)
    rc = design_lifecycle.step5b_annotate_main(_step5b_argv())
    out = capsys.readouterr().out

    assert rc == 1
    assert "STEP5B_STATUS=annotate-label-failed" in out
    assert not (tmp_path / ".completed" / "step-5b").exists()
    assert design_pause._determine_step(design_tmpdir=tmp_path, plugin_root=Path.cwd()) != "5b.5"  # pyright: ignore[reportPrivateUsage]
    assert not (tmp_path / ".completed" / "step-5b.5").exists()


def test_design_annotate_label_failure_without_repo_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    stdout_file = _write_design_priority_fixture(tmp_path)
    gh_calls: list[list[str]] = []

    def fake_gh(*, repo: str, argv: list[str]) -> subprocess.CompletedProcess[str]:
        _ = repo
        gh_calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(design_oos, "_resolve_filing_repo", lambda **_a: "")  # type: ignore[arg-type]
    monkeypatch.setattr(design_oos, "_run_gh", fake_gh)

    rc = design_oos.file_oos_annotate_main(["--design-tmpdir", str(tmp_path), "--issue-stdout-file", str(stdout_file), "--issue-number", "44"])
    captured = capsys.readouterr()

    assert rc == 1
    assert _kv(captured.out)["FILE_DESIGN_OOS_STATUS"] == "annotate-label-failed"
    assert not gh_calls


def test_label_only_mapping_uses_oos_file_map_without_stdout(tmp_path: Path) -> None:
    sentinel = tmp_path / "oos-issues-created.md"
    _ = sentinel.write_text(
        "OOS_FILE_MAP\t1\thttps://github.com/acme/repo/issues/101\n"
        "OOS_FILE_MAP\t2\thttps://github.com/acme/repo/issues/102\n",
        encoding="utf-8",
    )
    combined = tmp_path / "oos-combined.md"
    _ = combined.write_text(
        "### OOS_1: one\n- **Focus area**: correctness\n\n"
        "### OOS_2: two\n- **Focus area**: risk-integration\n",
        encoding="utf-8",
    )
    order_file = tmp_path / "oos-design-filing-order.txt"
    _ = order_file.write_text("1\n2\n", encoding="utf-8")

    mapping = design_oos._label_only_url_priority_map(  # pyright: ignore[reportPrivateUsage]
        sentinel_path=sentinel,
        combined_path=combined,
        order_file=order_file,
        issue_stdout_path=None,
    )

    assert mapping == {
        "https://github.com/acme/repo/issues/101": True,
        "https://github.com/acme/repo/issues/102": False,
    }
# pyright: reportUnknownArgumentType=false, reportUnknownLambdaType=false


def _stub_design_oos_prepare_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run_cli(*args: str, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if args[:2] == ("oos", "issue-cap"):
            input_file = Path(args[args.index("--input-file") + 1])
            output = Path(args[args.index("--output") + 1])
            _ = output.write_text(input_file.read_text(encoding="utf-8"), encoding="utf-8")
            return subprocess.CompletedProcess(list(args), 0, "", "")
        if args[:2] == ("oos", "file-conflict-deps"):
            output = Path(args[args.index("--output") + 1])
            _ = output.write_text("", encoding="utf-8")
            return subprocess.CompletedProcess(list(args), 0, "", "")
        return subprocess.CompletedProcess(list(args), 0, "", "")

    monkeypatch.setattr(design_oos, "_run_cli", fake_run_cli)


def test_prepare_promotes_three_latent_pool_items(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    _stub_design_oos_prepare_commands(monkeypatch)
    _ = (tmp_path / "oos-aggregate-pool.md").write_text(
        """### FINDING_1: latent one
- **Severity**: latent
- **Concern**: one.

### FINDING_2: latent two
- **Severity**: latent
- **Concern**: two.

### FINDING_3: latent three
- **Severity**: latent
- **Concern**: three.
""",
        encoding="utf-8",
    )

    rc = design_oos.file_oos_prepare_main(["--design-tmpdir", str(tmp_path)])

    assert rc == 0
    kv = _kv(capsys.readouterr().out)
    assert kv["FILE_DESIGN_OOS_STATUS"] == "ready"
    accepted = (tmp_path / "oos-accepted-design.md").read_text(encoding="utf-8")
    combined = (tmp_path / "oos-combined.md").read_text(encoding="utf-8")
    assert accepted.count("### OOS_") == 3
    assert "### FINDING_" not in combined
    assert "latent three" in combined


def test_prepare_two_latent_pool_items_do_not_trigger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    _stub_design_oos_prepare_commands(monkeypatch)
    _ = (tmp_path / "oos-aggregate-pool.md").write_text(
        """### FINDING_1: latent one
- **Severity**: latent
- **Concern**: one.

### FINDING_2: latent two
- **Severity**: latent
- **Concern**: two.
""",
        encoding="utf-8",
    )

    rc = design_oos.file_oos_prepare_main(["--design-tmpdir", str(tmp_path)])

    assert rc == 0
    assert _kv(capsys.readouterr().out)["FILE_DESIGN_OOS_STATUS"] == "skip-no-items"
    assert not (tmp_path / "oos-accepted-design.md").exists()
