"""Parity coverage for python/collect_results.py."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING

import collect_results
import logging_util

if TYPE_CHECKING:
    import pytest


def _reset(monkeypatch: pytest.MonkeyPatch) -> None:
    logging_util.reset_quiet_state()
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    monkeypatch.setenv("WAIT_FOR_REVIEWERS_POLL_INTERVAL", "0.01")
    monkeypatch.setenv("RUN_EXTERNAL_AGENT_POLL_INTERVAL", "0.01")
    monkeypatch.setenv("LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT", "0")
    monkeypatch.setattr(collect_results, "_RETRY_WAIT_FLOOR", 5)
    monkeypatch.setattr(collect_results, "_RETRY_WAIT_GRACE", 5)


def _parse_blocks(stdout: str) -> list[dict[str, str]]:
    blocks: list[dict[str, str]] = []
    for raw in stdout.strip().split("\n\n"):
        if not raw.strip():
            continue
        item: dict[str, str] = {}
        for line in raw.splitlines():
            key, _, value = line.partition("=")
            item[key] = value
        blocks.append(item)
    return blocks


def _write_done(path: Path, code: str = "0\n") -> None:
    _ = path.with_suffix(path.suffix + ".done").write_text(code, encoding="utf-8")


def _write_meta(path: Path, *, tool: str = "cursor", timeout: str = "60", cmd: list[str] | None = None, capture_stdout_only: bool = True) -> None:
    lines = [
        f"TOOL={tool}",
        f"TIMEOUT={timeout}",
        "CAPTURE_STDOUT=false",
        f"CAPTURE_STDOUT_ONLY={str(capture_stdout_only).lower()}",
        f"OUTPUT_FILE={path}",
    ]
    if cmd is not None:
        lines.append(f"CMD_JSON={json.dumps(cmd, separators=(',', ':'))}")
    _ = path.with_suffix(path.suffix + ".meta").write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_arg_validation_precedes_quiet(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _reset(monkeypatch)
    assert collect_results.collect_results_main(["--timeout", "0", str(tmp_path / "x.txt")]) == 1
    assert "must be a positive integer" in capsys.readouterr().err
    assert collect_results.collect_results_main(["--timeout", "abc", str(tmp_path / "x.txt")]) == 1
    assert "must be a positive integer" in capsys.readouterr().err
    assert collect_results.collect_results_main(["--timeout", "1"]) == 1
    assert "at least one output file" in capsys.readouterr().err


def test_ok_timeout_duplicate_basename_and_paths_file(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _reset(monkeypatch)
    a_dir = tmp_path / "a"
    b_dir = tmp_path / "b"
    a_dir.mkdir()
    b_dir.mkdir()
    out_a = a_dir / "same.txt"
    out_b = b_dir / "same.txt"
    _ = out_a.write_text("NO_ISSUES_FOUND\n", encoding="utf-8")
    _ = out_b.write_text("will time out\n", encoding="utf-8")
    _write_done(out_a)
    paths_file = tmp_path / "paths.txt"
    _ = paths_file.write_text(f"{out_a}\n\n{out_b}\n", encoding="utf-8")

    assert collect_results.collect_results_main(["--timeout", "1", "--paths-file", str(paths_file)]) == 0
    blocks = _parse_blocks(capsys.readouterr().out)
    assert blocks[0]["REVIEWER_FILE"] == str(out_a)
    assert blocks[0]["STATUS"] == "OK"
    assert blocks[1]["REVIEWER_FILE"] == str(out_b)
    assert blocks[1]["STATUS"] == "SENTINEL_TIMEOUT"
    assert blocks[1]["EXIT_CODE"] == "124"


def test_paths_file_errors(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _reset(monkeypatch)
    empty = tmp_path / "empty.txt"
    _ = empty.write_text(" \n\t\n", encoding="utf-8")
    assert collect_results.collect_results_main(["--timeout", "1", "--paths-file", str(empty)]) == 1
    assert "paths-file contains no entries" in capsys.readouterr().err
    out = tmp_path / "out.txt"
    assert collect_results.collect_results_main(["--timeout", "1", "--paths-file", str(empty), str(out)]) == 1
    assert "mutually exclusive" in capsys.readouterr().err


def test_retry_success_and_metadata_fail_closed(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _reset(monkeypatch)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    cursor = bin_dir / "cursor"
    _ = cursor.write_text("#!/usr/bin/env bash\nprintf 'NO_ISSUES_FOUND\\n'\n", encoding="utf-8")
    cursor.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")

    ok_out = tmp_path / "cursor-ok.txt"
    bad_out = tmp_path / "cursor-bad.txt"
    _ = ok_out.write_text("", encoding="utf-8")
    _ = bad_out.write_text("", encoding="utf-8")
    _write_done(ok_out)
    _write_done(bad_out)
    _write_meta(ok_out, cmd=[str(cursor), "agent", "--workspace", str(tmp_path), "retry prompt"])
    _write_meta(bad_out, cmd=None)

    assert collect_results.collect_results_main(["--timeout", "2", str(ok_out), str(bad_out)]) == 0
    blocks = _parse_blocks(capsys.readouterr().out)
    assert blocks[0]["REVIEWER_FILE"] == str(tmp_path / "cursor-ok-retry.txt")
    assert blocks[0]["STATUS"] == "OK"
    assert blocks[1]["STATUS"] == "EMPTY_OUTPUT"
    assert blocks[1]["EXIT_CODE"] == "99"
    assert blocks[1]["FAILURE_REASON"] == "Retry metadata invalid: missing CMD_JSON"


def test_transient_retry_requires_diag(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _reset(monkeypatch)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    cursor = bin_dir / "cursor"
    _ = cursor.write_text("#!/usr/bin/env bash\nprintf 'NO_ISSUES_FOUND\\n'\n", encoding="utf-8")
    cursor.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")

    transient = tmp_path / "cursor-transient.txt"
    non_diag = tmp_path / "cursor-no-diag.txt"
    for output in (transient, non_diag):
        _ = output.write_text("", encoding="utf-8")
        _write_done(output, "1\n")
        _write_meta(output, cmd=[str(cursor), "agent", "--workspace", str(tmp_path), "retry prompt"])
    _ = transient.with_suffix(transient.suffix + ".diag").write_text("Could not resolve host: example.invalid\n", encoding="utf-8")

    assert collect_results.collect_results_main(["--timeout", "2", str(transient), str(non_diag)]) == 0
    blocks = _parse_blocks(capsys.readouterr().out)
    assert blocks[0]["STATUS"] == "OK"
    assert blocks[0]["REVIEWER_FILE"].endswith("-retry.txt")
    assert blocks[1]["STATUS"] == "FAILED"


def test_substantive_structured_summary_and_cursor_response(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _reset(monkeypatch)
    structured = tmp_path / "cursor-structured.txt"
    _ = structured.write_text(
        "schema_version\tscope\tseverity\tfocus_area\tlocation\twhat\tscenario_or_breakage\tsuggested_fix\n"
        "1\tin_scope\tImportant\tcorrectness\tfoo.sh:7\tbad branch\tinput fails\tadd guard\n",
        encoding="utf-8",
    )
    _write_done(structured)
    cursor_empty = tmp_path / "cursor-empty.txt"
    _ = cursor_empty.write_text("CURSOR_DEGRADED_RESPONSE\n", encoding="utf-8")
    _write_done(cursor_empty)

    assert collect_results.collect_results_main(["--timeout", "1", "--structured-reviewer-validation", str(structured), str(cursor_empty)]) == 0
    blocks = _parse_blocks(capsys.readouterr().out)
    assert blocks[0]["STATUS"] == "OK"
    assert blocks[0]["STRUCTURED_SIDECAR"] == f"{structured}.tsv"
    assert (tmp_path / "cursor-structured.txt.tsv").read_text(encoding="utf-8").splitlines()[1].split("\t")[2] == "important"
    assert blocks[1]["STATUS"] == "CURSOR_EMPTY_RESPONSE"

    assert collect_results.collect_results_main(["--timeout", "1", "--structured-reviewer-validation", "--summary-only", str(structured)]) == 0
    summary = capsys.readouterr().out
    assert "STATUS=OK" in summary
    assert "STRUCTURED_SIDECAR=" not in summary
    assert "FAILURE_REASON=" not in summary


def test_structured_validation_recovers_no_issues_after_preamble(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _reset(monkeypatch)
    preamble = tmp_path / "cursor-preamble.txt"
    _ = preamble.write_text('Everything looks fine.\n{"no_issues_found": true}\n', encoding="utf-8")
    _write_done(preamble)
    assert collect_results.collect_results_main(["--timeout", "1", "--structured-reviewer-validation", str(preamble)]) == 0
    captured = capsys.readouterr()
    block = _parse_blocks(captured.out)[0]
    assert block["STATUS"] == "OK"
    assert block["STRUCTURED_SIDECAR"] == f"{preamble}.tsv"
    assert (tmp_path / "cursor-preamble.txt.tsv").read_text(encoding="utf-8") == ""
    assert block.get("FAILURE_REASON", "") == ""
    assert "NOT_SUBSTANTIVE" not in captured.out
    assert "recovered a no-issues sentinel after preamble" in (captured.out + captured.err)


def test_launch_outer_retry_threads_meta_site(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _reset(monkeypatch)
    orig = tmp_path / "codex-review.txt"
    prompt = tmp_path / "codex-review.txt.prompt"
    _ = prompt.write_text("prompt\n", encoding="utf-8")
    captured: dict[str, list[str]] = {}

    class _Proc:
        def wait(self, timeout: float = 0) -> int:
            _ = timeout
            return 0

    def fake_popen(args: list[str], **_kwargs: object) -> object:
        captured["argv"] = [str(a) for a in args]
        return _Proc()

    monkeypatch.setattr(collect_results.subprocess, "Popen", fake_popen)
    plan = collect_results.RetryPlan(index=0, orig_output=str(orig), retry_output=str(tmp_path / "codex-review-retry.txt"), timeout=2)
    meta = collect_results.RetryMeta(
        tool="codex",
        outer_launcher="agent launch-review",
        outer_launcher_prompt_file=str(prompt),
        outer_launcher_workdir=str(tmp_path),
        outer_launcher_site="design Step 3",
    )
    assert collect_results._launch_outer_retry(plan=plan, meta=meta, records=[]) is True  # type: ignore[reportPrivateUsage]
    argv = captured["argv"]
    assert "launch-review" in argv
    assert argv[argv.index("--site") + 1] == "design Step 3"


def test_parse_meta_reads_outer_launcher_site(tmp_path: Path) -> None:
    # Both preflight-written and success-path metas carry OUTER_LAUNCHER_SITE through this parser.
    meta = tmp_path / "out.txt.meta"
    _ = meta.write_text("TOOL=cursor\nOUTER_LAUNCHER=agent launch-review\nOUTER_LAUNCHER_SITE=design Step 3\n", encoding="utf-8")
    assert collect_results._parse_meta(meta).outer_launcher_site == "design Step 3"  # type: ignore[reportPrivateUsage]
    bare = tmp_path / "bare.meta"
    _ = bare.write_text("TOOL=cursor\n", encoding="utf-8")
    assert collect_results._parse_meta(bare).outer_launcher_site == ""  # type: ignore[reportPrivateUsage]


def test_non_substantive_validation_warns_without_retry(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _reset(monkeypatch)
    output = tmp_path / "cursor-specialist-output.txt"
    first_pass = "Reading files and preparing a response.\n"
    _ = output.write_text(first_pass, encoding="utf-8")
    _write_done(output)

    assert collect_results.collect_results_main(["--timeout", "2", "--substantive-validation", "--validation-mode", str(output)]) == 0
    captured = capsys.readouterr()
    blocks = _parse_blocks(captured.out)
    assert blocks[0]["REVIEWER_FILE"] == str(output)
    assert blocks[0]["STATUS"] == "NOT_SUBSTANTIVE"
    assert blocks[0]["NS_RETRY_MODE"] == "substantive"
    assert blocks[0]["NS_RETRY_REASON"] == "NO_ISSUES_FOUND_TOO_THIN"
    assert output.read_text(encoding="utf-8") == first_pass
    assert not (tmp_path / "cursor-specialist-output-ns-retry.txt").exists()
    assert not (tmp_path / "cursor-specialist-output-first-pass.txt").exists()
    assert "dropping NOT_SUBSTANTIVE reviewer" in captured.err
    assert "basename=cursor-specialist-output.txt" in captured.err


def test_structured_validation_not_substantive_no_retry(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _reset(monkeypatch)
    output = tmp_path / "codex-plan-generic-output.txt"
    narrative = "I reviewed the plan and found one important issue, but this is narrative prose.\n"
    _ = output.write_text(narrative, encoding="utf-8")
    _write_done(output)

    assert collect_results.collect_results_main(["--timeout", "2", "--structured-reviewer-validation", str(output)]) == 0
    captured = capsys.readouterr()
    blocks = _parse_blocks(captured.out)
    assert blocks[0]["REVIEWER_FILE"] == str(output)
    assert blocks[0]["STATUS"] == "NOT_SUBSTANTIVE"
    assert blocks[0]["NS_RETRY_MODE"] == "structured"
    assert blocks[0]["NS_RETRY_REASON"] in {"JSON_PARSE_FAIL", "UNKNOWN"}
    assert output.read_text(encoding="utf-8") == narrative
    assert not (tmp_path / "codex-plan-generic-output-ns-retry.txt").exists()
    assert not (tmp_path / "codex-plan-generic-output-first-pass.txt").exists()
    assert "dropping NOT_SUBSTANTIVE reviewer" in captured.err


def test_stderr_tail_resolution_prefers_retry_and_dedupes(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _reset(monkeypatch)
    a = tmp_path / "cursor-a.txt"
    b = tmp_path / "cursor-b.txt"
    _ = a.write_text("failed\n", encoding="utf-8")
    _ = b.write_text("failed\n", encoding="utf-8")
    _write_done(a, "7\n")
    _write_done(b, "7\n")
    _ = (tmp_path / "cursor-a-retry.txt.stderr-tail").write_text("same failure at /tmp/path/123 line 9\n", encoding="utf-8")
    ns_retry_tail = tmp_path / "cursor-a-ns-retry.txt.stderr-tail"
    _ = ns_retry_tail.write_text("stale ns retry failure\n", encoding="utf-8")
    _ = b.with_suffix(b.suffix + ".stderr-tail").write_text("same failure at /tmp/path/456 line 10\n", encoding="utf-8")

    resolved_tail = collect_results.resolve_collector_stderr_tail_file(str(a))
    assert resolved_tail.endswith("cursor-a-retry.txt.stderr-tail")
    assert resolved_tail != str(ns_retry_tail)
    assert collect_results.collect_results_main(["--timeout", "1", str(a), str(b)]) == 0
    err = capsys.readouterr().err
    assert "--- failed agent stderr tail ---" in err
    assert "stderr tail suppressed" in err


def test_retry_output_path_non_txt_uses_txt_suffix() -> None:
    assert collect_results._retry_output_path("/tmp/foo.out") == "/tmp/foo.out-retry.txt"  # type: ignore[reportPrivateUsage]
    assert collect_results.resolve_collector_stderr_tail_file("/tmp/foo.out") == ""


def test_stderr_tail_resolution_uses_ns_retry_when_retry_absent(tmp_path: Path) -> None:
    reviewer = tmp_path / "cursor-a.txt"
    _ = reviewer.write_text("failed\n", encoding="utf-8")
    ns_retry_tail = tmp_path / "cursor-a-ns-retry.txt.stderr-tail"
    _ = ns_retry_tail.write_text("ns retry failure\n", encoding="utf-8")

    resolved_tail = collect_results.resolve_collector_stderr_tail_file(str(reviewer))
    assert resolved_tail == str(ns_retry_tail)


def test_stderr_tail_resolution_uses_phase2_ns_retry_for_phase3(tmp_path: Path) -> None:
    reviewer = tmp_path / "cursor-a-phase3.txt"
    _ = reviewer.write_text("failed\n", encoding="utf-8")
    phase2_ns = tmp_path / "cursor-a-phase2-ns-retry.txt.stderr-tail"
    _ = phase2_ns.write_text("phase2 ns retry failure\n", encoding="utf-8")

    resolved_tail = collect_results.resolve_collector_stderr_tail_file(str(reviewer))
    assert resolved_tail == str(phase2_ns)


def test_stderr_tail_resolution_uses_base_ns_retry_for_phase2(tmp_path: Path) -> None:
    reviewer = tmp_path / "cursor-a-phase2.txt"
    _ = reviewer.write_text("failed\n", encoding="utf-8")
    base_ns = tmp_path / "cursor-a-ns-retry.txt.stderr-tail"
    _ = base_ns.write_text("base ns retry failure\n", encoding="utf-8")

    resolved_tail = collect_results.resolve_collector_stderr_tail_file(str(reviewer))
    assert resolved_tail == str(base_ns)


def test_stderr_tail_resolution_phase_retry_tails_beat_launch_stderr(tmp_path: Path) -> None:
    reviewer = tmp_path / "cursor-a-phase3.txt"
    _ = reviewer.write_text("failed\n", encoding="utf-8")
    phase2_ns = tmp_path / "cursor-a-phase2-ns-retry.txt.stderr-tail"
    _ = phase2_ns.write_text("phase2 ns retry failure\n", encoding="utf-8")
    _ = (tmp_path / "cursor-a-phase2.txt.launch-stderr").write_text("launch stderr\n", encoding="utf-8")

    resolved_tail = collect_results.resolve_collector_stderr_tail_file(str(reviewer))
    assert resolved_tail == str(phase2_ns)


def test_stderr_tail_resolution_primary_retry_beats_primary_ns_retry(tmp_path: Path) -> None:
    reviewer = tmp_path / "cursor-a.txt"
    _ = reviewer.write_text("failed\n", encoding="utf-8")
    retry = tmp_path / "cursor-a-retry.txt.stderr-tail"
    ns_retry = tmp_path / "cursor-a-ns-retry.txt.stderr-tail"
    _ = retry.write_text("retry failure\n", encoding="utf-8")
    _ = ns_retry.write_text("ns retry failure\n", encoding="utf-8")

    resolved_tail = collect_results.resolve_collector_stderr_tail_file(str(reviewer))
    assert resolved_tail == str(retry)


def test_stderr_tail_resolution_renders_retry_launch_stderr_after_tails_absent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reviewer = tmp_path / "cursor-a.txt"
    _ = reviewer.write_text("failed\n", encoding="utf-8")
    _ = (tmp_path / "cursor-a-retry.txt.launch-stderr").write_text("launch stderr\n", encoding="utf-8")

    def fake_render(_path: Path) -> str:
        return "rendered retry launch\n"

    monkeypatch.setattr(collect_results.agents, "render_failed_agent_stderr_tail", fake_render)

    resolved_tail = collect_results.resolve_collector_stderr_tail_file(str(reviewer))
    assert Path(resolved_tail).read_text(encoding="utf-8") == "rendered retry launch\n"


def test_stderr_tail_resolution_ignores_empty_launch_stderr(tmp_path: Path) -> None:
    reviewer = tmp_path / "cursor-a.txt"
    _ = reviewer.write_text("failed\n", encoding="utf-8")
    _ = (tmp_path / "cursor-a.txt.launch-stderr").write_text("", encoding="utf-8")
    tail = tmp_path / "cursor-a.txt.stderr-tail"
    _ = tail.write_text("plain stderr tail\n", encoding="utf-8")

    resolved_tail = collect_results.resolve_collector_stderr_tail_file(str(reviewer))
    assert resolved_tail == str(tail)


def test_coerced_invalid_sentinel_empty_output_retries(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _reset(monkeypatch)
    output = tmp_path / "cursor-bad-sentinel.txt"
    _write_done(output, "abc\n")
    _write_meta(output, timeout="2", cmd=None)
    assert collect_results.collect_results_main(["--timeout", "1", str(output)]) == 0
    block = _parse_blocks(capsys.readouterr().out)[0]
    assert block["STATUS"] == "EMPTY_OUTPUT"
    assert block["EXIT_CODE"] == "99"


def test_cmd_json_outer_launcher_uses_last_mode_flag(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _reset(monkeypatch)
    output = tmp_path / "cursor-review.txt"
    cmd = ["cursor", "agent", "--mode", "ask", "--mode", "plan", "--workspace", str(tmp_path), "go"]
    assert not collect_results._cmd_json_requires_outer_launcher(orig_output=str(output), tool="cursor", cmd=cmd)  # type: ignore[reportPrivateUsage]
    codex_cmd = ["codex", "exec", "--sandbox", "read-only", "--sandbox", "full-auto", "-C", str(tmp_path), "--add-dir", str(tmp_path), "--output-last-message", str(tmp_path / "out.txt"), "go"]
    assert not collect_results._cmd_json_requires_outer_launcher(orig_output=str(output), tool="codex", cmd=codex_cmd)  # type: ignore[reportPrivateUsage]
    assert collect_results._cmd_json_requires_outer_launcher(orig_output=str(output), tool="cursor", cmd=["cursor", "agent", "--mode", "ask", "--workspace", str(tmp_path), "go"])  # type: ignore[reportPrivateUsage]


def test_env_without_test_hooks_strips_collect_results_vars(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _reset(monkeypatch)
    monkeypatch.setenv("LARCH_COLLECT_RESULTS_TRAP", "1")
    captured: dict[str, str] = {}

    def fake_popen(args: list[str], **kwargs: object) -> object:
        _ = args
        captured["env"] = json.dumps(dict(kwargs.get("env", {})))  # type: ignore[reportCallIssue, reportArgumentType]
        class _Proc:
            def wait(self, timeout: float = 0) -> int:
                _ = timeout
                return 0
        return _Proc()

    output = tmp_path / "cursor-retry-env.txt"
    _ = output.write_text("", encoding="utf-8")
    _write_done(output)
    _write_meta(output, cmd=["cursor", "agent", "--workspace", str(tmp_path), "retry prompt"])
    monkeypatch.setattr(collect_results.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(collect_results, "_wait_retry_plans", lambda _plans: None)  # type: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    monkeypatch.setattr(collect_results, "_apply_empty_retry_results", lambda records, plans: None)  # type: ignore[reportUnknownArgumentType, reportUnknownLambdaType]  # noqa: ARG005
    assert collect_results.collect_results_main(["--timeout", "2", str(output)]) == 0
    assert "LARCH_COLLECT_RESULTS_TRAP" not in captured.get("env", "")


def test_ns_retry_fields_emitted_on_not_substantive(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _reset(monkeypatch)
    output = tmp_path / "cursor-thin.txt"
    _ = output.write_text("Reading files and preparing a response.\n", encoding="utf-8")
    _write_done(output)
    assert collect_results.collect_results_main(["--timeout", "1", "--substantive-validation", "--validation-mode", str(output)]) == 0
    block = _parse_blocks(capsys.readouterr().out)[0]
    assert block["STATUS"] == "NOT_SUBSTANTIVE"
    assert block["NS_RETRY_MODE"] == "substantive"
    assert block["NS_RETRY_REASON"] == "NO_ISSUES_FOUND_TOO_THIN"


def test_failed_agent_stderr_signature_returns_stable_value(tmp_path: Path) -> None:
    tail = tmp_path / "sig.stderr-tail"
    _ = tail.write_text("error in /tmp/foo123/bar.txt exit 2\n", encoding="utf-8")
    assert collect_results.failed_agent_stderr_signature(str(tail))


def test_derive_tool_uses_registry_allowlist(tmp_path: Path) -> None:
    output = tmp_path / "cursor-specialist-output.txt"
    meta = output.with_suffix(output.suffix + ".meta")
    _ = meta.write_text("TOOL=sanitized-empty\nOUTPUT_FILE=\n", encoding="utf-8")
    assert collect_results.derive_tool(str(output)) == "cursor"
    bogus = tmp_path / "bogus-output.txt"
    _ = bogus.with_suffix(bogus.suffix + ".meta").write_text("TOOL=not-a-tool\nOUTPUT_FILE=\n", encoding="utf-8")
    assert collect_results.derive_tool(str(bogus)) == "unknown"


def test_retired_outer_launcher_fail_closed(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _reset(monkeypatch)
    output = tmp_path / "cursor-retired.txt"
    _ = output.write_text("", encoding="utf-8")
    _write_done(output)
    meta = output.with_suffix(output.suffix + ".meta")
    _ = meta.write_text(
        "\n".join(
            [
                "TOOL=cursor",
                "TIMEOUT=2",
                f"OUTPUT_FILE={output}",
                "OUTER_LAUNCHER=launch-review.sh",
                f"OUTER_LAUNCHER_PROMPT_FILE={output}.prompt",
                f"OUTER_LAUNCHER_WORKDIR={tmp_path}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    _ = output.with_suffix(output.suffix + ".prompt").write_text("prompt\n", encoding="utf-8")
    assert collect_results.collect_results_main(["--timeout", "2", str(output)]) == 0
    block = _parse_blocks(capsys.readouterr().out)[0]
    assert block["STATUS"] == "EMPTY_OUTPUT"
    assert "retired review OUTER_LAUNCHER" in block["FAILURE_REASON"]


def test_cap_hit_status(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _reset(monkeypatch)
    output = tmp_path / "cursor-cap.txt"
    _ = output.write_text("STATUS=cap_hit\n", encoding="utf-8")
    _write_done(output)
    assert collect_results.collect_results_main(["--timeout", "1", str(output)]) == 0
    block = _parse_blocks(capsys.readouterr().out)[0]
    assert block["STATUS"] == "cap_hit"
