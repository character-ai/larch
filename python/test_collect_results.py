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
    path.with_suffix(path.suffix + ".done").write_text(code, encoding="utf-8")


def _write_meta(path: Path, *, tool: str = "cursor", timeout: str = "2", cmd: list[str] | None = None, capture_stdout_only: bool = True) -> None:
    lines = [
        f"TOOL={tool}",
        f"TIMEOUT={timeout}",
        "CAPTURE_STDOUT=false",
        f"CAPTURE_STDOUT_ONLY={str(capture_stdout_only).lower()}",
        f"OUTPUT_FILE={path}",
    ]
    if cmd is not None:
        lines.append(f"CMD_JSON={json.dumps(cmd, separators=(',', ':'))}")
    path.with_suffix(path.suffix + ".meta").write_text("\n".join(lines) + "\n", encoding="utf-8")


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
    out_a.write_text("NO_ISSUES_FOUND\n", encoding="utf-8")
    out_b.write_text("will time out\n", encoding="utf-8")
    _write_done(out_a)
    paths_file = tmp_path / "paths.txt"
    paths_file.write_text(f"{out_a}\n\n{out_b}\n", encoding="utf-8")

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
    empty.write_text(" \n\t\n", encoding="utf-8")
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
    cursor.write_text("#!/usr/bin/env bash\nprintf 'NO_ISSUES_FOUND\\n'\n", encoding="utf-8")
    cursor.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")

    ok_out = tmp_path / "cursor-ok.txt"
    bad_out = tmp_path / "cursor-bad.txt"
    ok_out.write_text("", encoding="utf-8")
    bad_out.write_text("", encoding="utf-8")
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
    cursor.write_text("#!/usr/bin/env bash\nprintf 'NO_ISSUES_FOUND\\n'\n", encoding="utf-8")
    cursor.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")

    transient = tmp_path / "cursor-transient.txt"
    non_diag = tmp_path / "cursor-no-diag.txt"
    for output in (transient, non_diag):
        output.write_text("", encoding="utf-8")
        _write_done(output, "1\n")
        _write_meta(output, cmd=[str(cursor), "agent", "--workspace", str(tmp_path), "retry prompt"])
    transient.with_suffix(transient.suffix + ".diag").write_text("Could not resolve host: example.invalid\n", encoding="utf-8")

    assert collect_results.collect_results_main(["--timeout", "2", str(transient), str(non_diag)]) == 0
    blocks = _parse_blocks(capsys.readouterr().out)
    assert blocks[0]["STATUS"] == "OK"
    assert blocks[0]["REVIEWER_FILE"].endswith("-retry.txt")
    assert blocks[1]["STATUS"] == "FAILED"


def test_substantive_structured_summary_and_cursor_response(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _reset(monkeypatch)
    structured = tmp_path / "cursor-structured.txt"
    structured.write_text(
        "schema_version\tscope\tseverity\tfocus_area\tlocation\twhat\tscenario_or_breakage\tsuggested_fix\n"
        "1\tin_scope\tImportant\tcorrectness\tfoo.sh:7\tbad branch\tinput fails\tadd guard\n",
        encoding="utf-8",
    )
    _write_done(structured)
    cursor_empty = tmp_path / "cursor-empty.txt"
    cursor_empty.write_text("CURSOR_DEGRADED_RESPONSE\n", encoding="utf-8")
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


def test_non_substantive_retry_publishes_first_pass(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _reset(monkeypatch)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    cursor = bin_dir / "cursor"
    cursor.write_text("#!/usr/bin/env bash\nprintf 'NO_ISSUES_FOUND\\n'\n", encoding="utf-8")
    cursor.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    output = tmp_path / "cursor-specialist-output.txt"
    first_pass = "Reading files and preparing a response.\n"
    output.write_text(first_pass, encoding="utf-8")
    _write_done(output)
    _write_meta(output, cmd=[str(cursor), "agent", "--workspace", str(tmp_path), "retry prompt"])

    assert collect_results.collect_results_main(["--timeout", "2", "--substantive-validation", "--validation-mode", str(output)]) == 0
    blocks = _parse_blocks(capsys.readouterr().out)
    assert blocks[0]["REVIEWER_FILE"] == str(output)
    assert blocks[0]["STATUS"] == "OK"
    assert output.read_text(encoding="utf-8") == "NO_ISSUES_FOUND\n"
    assert (tmp_path / "cursor-specialist-output-first-pass.txt").read_text(encoding="utf-8") == first_pass
    assert "NS_RETRY_REASON=NO_ISSUES_FOUND_TOO_THIN" in (tmp_path / "cursor-specialist-output-ns-retry.txt.meta").read_text(encoding="utf-8")


def test_stderr_tail_resolution_prefers_retry_and_dedupes(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _reset(monkeypatch)
    a = tmp_path / "cursor-a.txt"
    b = tmp_path / "cursor-b.txt"
    a.write_text("failed\n", encoding="utf-8")
    b.write_text("failed\n", encoding="utf-8")
    _write_done(a, "7\n")
    _write_done(b, "7\n")
    (tmp_path / "cursor-a-retry.txt.stderr-tail").write_text("same failure at /tmp/path/123 line 9\n", encoding="utf-8")
    b.with_suffix(b.suffix + ".stderr-tail").write_text("same failure at /tmp/path/456 line 10\n", encoding="utf-8")

    assert collect_results.resolve_collector_stderr_tail_file(str(a)).endswith("cursor-a-retry.txt.stderr-tail")
    assert collect_results.collect_results_main(["--timeout", "1", str(a), str(b)]) == 0
    err = capsys.readouterr().err
    assert "--- failed agent stderr tail ---" in err
    assert "stderr tail suppressed" in err
