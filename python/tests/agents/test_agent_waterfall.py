# pyright: reportUnusedCallResult=false
from __future__ import annotations

from collections.abc import Mapping, Sequence
import contextlib
import io
import json
import os
import signal
import subprocess
import sys
import time
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest

from larch.agents import agent_waterfall
from larch.core import logging_util
from larch.core import proc as proc_module
from test_support import ROOT

CLI = Path(__file__).resolve().parents[2] / "cli.py"


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    path.chmod(0o755)
    return path


@pytest.fixture()
def stub_env(tmp_path: Path) -> dict[str, str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write(
        path=bin_dir / "codex",
        text="""#!/usr/bin/env bash
out=""
last=""
log="${CODEX_STUB_LOG:-}"
for arg in "$@"; do
  if [[ "$last" == "--output-last-message" ]]; then out="$arg"; fi
  last="$arg"
done
[[ -n "$log" ]] && printf '%s\n' "$*" >> "$log"
[[ -n "$out" ]] || exit 9
if [[ -n "${CODEX_STUB_COUNTER:-}" ]]; then
  n=0; [[ -f "$CODEX_STUB_COUNTER" ]] && n=$(cat "$CODEX_STUB_COUNTER" 2>/dev/null || echo 0)
  case "$n" in ''|*[!0-9]*) n=0 ;; esac
  printf '%s\n' "$((n + 1))" > "$CODEX_STUB_COUNTER"
fi
if [[ -n "${CODEX_STUB_FAIL_OUTPUT_CONTAINS:-}" && "$out" == *"${CODEX_STUB_FAIL_OUTPUT_CONTAINS}"* ]]; then exit 7; fi
if [[ "${CODEX_STUB_FAIL:-false}" == "true" ]]; then exit 7; fi
if [[ -n "${CODEX_STUB_EMPTY_OUTPUT_CONTAINS:-}" && "$out" == *"${CODEX_STUB_EMPTY_OUTPUT_CONTAINS}"* ]]; then : > "$out"; exit 0; fi
if [[ -n "${CODEX_STUB_ALT_OUTPUT_CONTAINS:-}" && "$out" == *"${CODEX_STUB_ALT_OUTPUT_CONTAINS}"* ]]; then
  printf '%s\n' "${CODEX_STUB_ALT_RESULT_CONTENT:-codex alt}" > "$out"
else
  printf '%s\n' "${CODEX_STUB_RESULT_CONTENT:-codex ok}" > "$out"
fi
""",
    )
    _write(
        path=bin_dir / "cursor",
        text="""#!/usr/bin/env bash
if [[ -n "${CURSOR_STUB_PID_FILE:-}" ]]; then printf '%s\n' "$$" > "$CURSOR_STUB_PID_FILE"; fi
if [[ -n "${CURSOR_STUB_DELAY:-}" ]]; then sleep "$CURSOR_STUB_DELAY"; fi
log="${CURSOR_STUB_LOG:-}"
[[ -n "$log" ]] && printf '%s\n' "$*" >> "$log"
if [[ -n "${CURSOR_STUB_FAIL_OUTPUT_CONTAINS:-}" && "$*" == *"${CURSOR_STUB_FAIL_OUTPUT_CONTAINS}"* ]]; then exit 8; fi
if [[ "${CURSOR_STUB_FAIL:-false}" == "true" ]]; then exit 8; fi
python3 - <<'PY_CURSOR'
import json, os
print(json.dumps({"result": os.environ.get("CURSOR_STUB_RESULT_CONTENT", "cursor ok"), "usage": {"inputTokens": 1, "outputTokens": int(os.environ.get("CURSOR_STUB_OUTPUT_TOKENS", "1")), "cacheReadTokens": 0, "cacheWriteTokens": 0}}))
PY_CURSOR
""",
    )
    _write(
        path=bin_dir / "claude",
        text="""#!/usr/bin/env bash
cat >/dev/null
if [[ "${CLAUDE_STUB_FAIL:-false}" == "true" ]]; then exit 9; fi
printf '{"type":"result","subtype":"success","is_error":false,"result":"%s","usage":{"input_tokens":1,"output_tokens":1,"cache_read_input_tokens":0,"cache_creation_input_tokens":0}}\\n' "${CLAUDE_STUB_RESULT_CONTENT:-claude ok}"
""",
    )
    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
            "CLAUDE_PLUGIN_ROOT": str(ROOT),
            "LARCH_QUIET_DISABLE": "1",
            "WAIT_FOR_REVIEWERS_POLL_INTERVAL": "0.05",
            "RUN_EXTERNAL_AGENT_POLL_INTERVAL": "0.05",
            "LARCH_TRANSIENT_RETRY_DELAY": "0",
            "LARCH_CURSOR_LAUNCH_JITTER_MS": "0",
            "LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT": "0",
            "LARCH_EXTERNAL_STARTUP_LOCK_FORCE_UNAME": "Linux",
            "LARCH_LIB_CURSOR_AUTH_TEST_MODE": "1",
            "LIB_CURSOR_AUTH_TEST_UNAME": "Linux",
        }
    )
    return env


def _slot(tmp_path: Path, *, name: str = "s1", tool: str = "codex", output_name: str = "out.txt") -> tuple[Path, Path]:
    prompt = tmp_path / f"{name}.prompt"
    prompt.write_text("review\n", encoding="utf-8")
    manifest = tmp_path / f"{name}.ndjson"
    output = tmp_path / output_name
    manifest.write_text(json.dumps({"slot": name, "tool": tool, "output": str(output), "prompt_file": str(prompt)}) + "\n", encoding="utf-8")
    return manifest, output


def _slots_manifest(tmp_path: Path, rows: Sequence[tuple[str, str, str]]) -> Path:
    prompt = tmp_path / "multi.prompt"
    prompt.write_text("review\n", encoding="utf-8")
    manifest = tmp_path / "multi.ndjson"
    manifest.write_text(
        "\n".join(
            json.dumps({"slot": name, "tool": tool, "output": str(tmp_path / output_name), "prompt_file": str(prompt)})
            for name, tool, output_name in rows
        )
        + "\n",
        encoding="utf-8",
    )
    return manifest


def _run(manifest: Path, env: dict[str, str], *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), "agent", "dispatch-waterfall", "--slots-file", str(manifest), "--codex-present", "true", "--cursor-present", "true", "--mode", "description", "--timeout", "5", *extra],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


def _kv(stdout: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in stdout.splitlines():
        key, sep, value = line.partition("=")
        if sep:
            out[key] = value
    return out


def _record_collect_calls(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    calls: list[list[str]] = []
    real_run = proc_module.run

    def recording_run(
        argv: Sequence[str],
        *,
        timeout: float | None = None,
        cwd: str | None = None,
        env: Mapping[str, str] | None = None,
        check: bool = False,
        stdout: int | None = None,
        stderr: int | None = None,
    ) -> proc_module.CommandResult:
        argv_list = list(argv)
        if "collect-results" in argv_list:
            calls.append(argv_list)
        return real_run(
            argv,
            timeout=timeout,
            cwd=cwd,
            env=env,
            check=check,
            stdout=stdout,
            stderr=stderr,
        )

    monkeypatch.setattr(agent_waterfall.proc, "run", recording_run)
    return calls


def _run_direct(
    manifest: Path,
    env: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    *extra: str,
) -> tuple[int, str]:
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    logging_util.reset_quiet_state()
    argv = [
        "--slots-file",
        str(manifest),
        "--codex-present",
        "true",
        "--cursor-present",
        "true",
        "--mode",
        "description",
        "--timeout",
        "5",
        *extra,
    ]
    out = io.StringIO()
    err = io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = agent_waterfall.dispatch_waterfall_main(argv)
    return rc, out.getvalue()


def test_phase2_and_phase3_fallbacks(tmp_path: Path, stub_env: dict[str, str], monkeypatch: pytest.MonkeyPatch) -> None:
    manifest, _output = _slot(tmp_path)
    rc, stdout = _run_direct(manifest, {**stub_env, "CODEX_STUB_FAIL": "true"}, monkeypatch)
    assert rc == 0
    kvs = _kv(stdout)
    assert kvs["ALL_OUTPUT_TOOLS"] == "cursor"
    assert (tmp_path / "out-phase2.txt").read_text(encoding="utf-8").strip() == "cursor ok"

    rc, stdout = _run_direct(manifest, {**stub_env, "CODEX_STUB_FAIL": "true", "CURSOR_STUB_FAIL": "true"}, monkeypatch)
    assert rc == 0
    kvs = _kv(stdout)
    assert kvs["FALLBACK_COUNT"] == "1"
    assert kvs["ALL_OUTPUT_TOOLS"] == "claude"
    assert (tmp_path / "out-phase3.txt").read_text(encoding="utf-8").strip() == "claude ok"


def test_phase3_hard_fail_still_emits_final_path(tmp_path: Path, stub_env: dict[str, str], monkeypatch: pytest.MonkeyPatch) -> None:
    collect_calls = _record_collect_calls(monkeypatch)
    manifest, _ = _slot(tmp_path, output_name="hard.txt")
    env = {**stub_env, "CODEX_STUB_FAIL": "true", "CURSOR_STUB_FAIL": "true", "CLAUDE_STUB_FAIL": "true"}
    rc, stdout = _run_direct(manifest, env, monkeypatch)
    assert rc == 0
    kvs = _kv(stdout)
    final = str(tmp_path / "hard-phase3.txt")
    assert kvs["DISPATCH_OK"] == "false"
    assert kvs["ALL_OUTPUT_FILES"] == final
    assert Path(kvs["ALL_OUTPUT_FILES_PATH"]).read_text(encoding="utf-8") == final + "\n"
    assert Path(final + ".launch-stderr").exists()
    tail_calls = [call for call in collect_calls if "--summary-only" not in call]
    assert len(tail_calls) == 1
    assert final in tail_calls[0]


def test_validation_errors_exit_two_and_do_not_launch(tmp_path: Path, stub_env: dict[str, str]) -> None:
    manifest, _ = _slot(tmp_path)
    codex_log = tmp_path / "codex.log"
    proc = _run(manifest, {**stub_env, "CODEX_STUB_LOG": str(codex_log)}, "--require-result-pattern", "[")
    assert proc.returncode == 2
    assert "--require-result-pattern is not a valid ERE" in proc.stderr
    assert not codex_log.exists() or codex_log.read_text(encoding="utf-8") == ""

    cursor_log = tmp_path / "cursor-invalid.log"
    proc = _run(manifest, {**stub_env, "CURSOR_STUB_LOG": str(cursor_log)}, "--require-first-line-pattern", "[")
    assert proc.returncode == 2
    assert "--require-first-line-pattern is not a valid ERE" in proc.stderr
    assert not cursor_log.exists() or cursor_log.read_text(encoding="utf-8") == ""

    empty = tmp_path / "empty.ndjson"
    empty.write_text("", encoding="utf-8")
    proc = _run(empty, stub_env)
    assert proc.returncode == 2
    assert "no slot rows" in proc.stderr
    assert not Path(str(empty) + ".output-files").exists()


def test_posix_ere_result_gate_and_caphit_bypass(tmp_path: Path, stub_env: dict[str, str], monkeypatch: pytest.MonkeyPatch) -> None:
    manifest, _ = _slot(tmp_path, tool="cursor", output_name="pattern.txt")
    rc, stdout = _run_direct(
        manifest,
        {**stub_env, "CURSOR_STUB_RESULT_CONTENT": "narration", "CODEX_STUB_RESULT_CONTENT": "## Recommendation\nsplit"},
        monkeypatch,
        "--require-result-pattern",
        "^[[:space:]]*## Recommendation",
    )
    assert rc == 0
    assert _kv(stdout)["ALL_OUTPUT_TOOLS"] == "codex"

    codex_log = tmp_path / "codex-caphit.log"
    rc, stdout = _run_direct(
        manifest,
        {**stub_env, "CURSOR_STUB_RESULT_CONTENT": "STATUS=cap_hit\nbudget", "CODEX_STUB_LOG": str(codex_log)},
        monkeypatch,
        "--require-result-pattern",
        "^[[:space:]]*## Recommendation",
    )
    assert rc == 0
    assert _kv(stdout)["ALL_OUTPUT_TOOLS"] == "cursor"
    assert not codex_log.exists() or codex_log.read_text(encoding="utf-8") == ""


@pytest.mark.parametrize(
    ("content", "expected_tool"),
    [
        ("### FINDING_1:\nbody", "cursor"),
        ("   LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED   \n", "cursor"),
        ("unrelated body", "codex"),
    ],
)
def test_aggregate_findings_posix_alternation(tmp_path: Path, stub_env: dict[str, str], content: str, expected_tool: str) -> None:
    manifest, _ = _slot(tmp_path, tool="cursor", output_name="agg.txt")
    pattern = r"^(### FINDING_[0-9]+:|[[:space:]]*LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED[[:space:]]*$)"
    proc = _run(
        manifest,
        {**stub_env, "CURSOR_STUB_RESULT_CONTENT": content, "CODEX_STUB_RESULT_CONTENT": "### FINDING_2:\nbody"},
        "--require-result-pattern",
        pattern,
    )
    assert proc.returncode == 0, proc.stderr
    assert _kv(proc.stdout)["ALL_OUTPUT_TOOLS"] == expected_tool


def test_first_line_salvage_and_no_fallback_drop_file(tmp_path: Path, stub_env: dict[str, str]) -> None:
    manifest, output = _slot(tmp_path, tool="cursor", output_name="first.txt")
    proc = _run(
        manifest,
        {**stub_env, "CURSOR_STUB_RESULT_CONTENT": "preamble\nschema_version\tscope\n1\tx"},
        "--require-first-line-pattern",
        r"^[[:space:]]*schema_version",
    )
    assert proc.returncode == 0, proc.stderr
    assert _kv(proc.stdout)["ALL_OUTPUT_TOOLS"] == "cursor"
    assert output.read_text(encoding="utf-8").startswith("schema_version")

    manifest, _ = _slot(tmp_path, tool="cursor", output_name="drop.txt")
    proc = _run(
        manifest,
        {**stub_env, "CURSOR_STUB_RESULT_CONTENT": "narration only"},
        "--no-fallback",
        "--require-first-line-pattern",
        r"^[[:space:]]*schema_version",
    )
    assert proc.returncode == 0, proc.stderr
    kvs = _kv(proc.stdout)
    assert kvs["ALL_SLOTS_DROPPED"] == "true"
    drop_file = Path(kvs["DROPPED_SLOTS_FILE"])
    fields = drop_file.read_text(encoding="utf-8").split("\t")
    assert fields[:3] == ["s1", "cursor", "format-gate-miss"]


def test_fallback_counter_and_paths_file_override(tmp_path: Path, stub_env: dict[str, str]) -> None:
    manifest, _ = _slot(tmp_path)
    counter = tmp_path / "counter.txt"
    counter.write_text("2\n", encoding="utf-8")
    paths = tmp_path / "outputs.list"
    proc = _run(
        manifest,
        {**stub_env, "CODEX_STUB_FAIL": "true", "CURSOR_STUB_FAIL": "true"},
        "--fallback-counter-file",
        str(counter),
        "--paths-file",
        str(paths),
    )
    assert proc.returncode == 0, proc.stderr
    assert counter.read_text(encoding="utf-8") == "3\n"
    assert _kv(proc.stdout)["ALL_OUTPUT_FILES_PATH"] == str(paths)
    assert paths.read_text(encoding="utf-8").strip().endswith("out-phase3.txt")


def test_rejects_newline_output_path(tmp_path: Path, stub_env: dict[str, str]) -> None:
    prompt = tmp_path / "p"
    prompt.write_text("x\n", encoding="utf-8")
    manifest = tmp_path / "bad.ndjson"
    manifest.write_text(json.dumps({"slot": "bad", "tool": "codex", "output": "x\ny", "prompt_file": str(prompt)}) + "\n", encoding="utf-8")
    proc = _run(manifest, stub_env)
    assert proc.returncode == 2
    assert "newline or carriage return" in proc.stderr


def test_two_slot_phase1_order_and_default_paths_file(tmp_path: Path, stub_env: dict[str, str]) -> None:
    manifest = tmp_path / "two.ndjson"
    out1 = tmp_path / "phase1-codex.txt"
    out2 = tmp_path / "phase1-cursor.txt"
    prompt = tmp_path / "two.prompt"
    prompt.write_text("review\n", encoding="utf-8")
    manifest.write_text(
        "\n".join(
            [
                json.dumps({"slot": "s1", "tool": "codex", "output": str(out1), "prompt_file": str(prompt)}),
                json.dumps({"slot": "s2", "tool": "cursor", "output": str(out2), "prompt_file": str(prompt)}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    proc = _run(manifest, stub_env)
    assert proc.returncode == 0, proc.stderr
    kvs = _kv(proc.stdout)
    paths_file = Path(f"{manifest}.output-files")
    assert kvs["ALL_OUTPUT_FILES_PATH"] == str(paths_file)
    lines = paths_file.read_text(encoding="utf-8").splitlines()
    assert lines == [str(out1), str(out2)]
    assert kvs["ALL_OUTPUT_TOOLS"] == "codex cursor"


@pytest.mark.parametrize("no_fallback", [False, True])
def test_straggler_cutoff_drops_slow_slot_without_fallback(
    tmp_path: Path,
    stub_env: dict[str, str],
    no_fallback: bool,
) -> None:
    manifest = _slots_manifest(
        tmp_path,
        [
            ("fast-one", "codex", "fast-one.txt"),
            ("slow", "cursor", "slow.txt"),
        ],
    )
    args = ["--straggler-cutoff"]
    if no_fallback:
        args.append("--no-fallback")
    proc = _run(
        manifest,
        {
            **stub_env,
            "CODEX_STUB_RESULT_CONTENT": "ACCEPT fast",
            "CURSOR_STUB_DELAY": "5",
            "CURSOR_STUB_RESULT_CONTENT": "ACCEPT slow",
            "LARCH_REVIEWER_STRAGGLER_MULTIPLE": "0.01",
            "LARCH_REVIEWER_STRAGGLER_FLOOR_SECONDS": "0",
        },
        *args,
    )
    assert proc.returncode == 0, proc.stderr
    kvs = _kv(proc.stdout)
    assert kvs["STRAGGLER_DROPPED_COUNT"] == "1"
    assert kvs["WARN"] == "reviewer-straggler-dropped"
    assert str(tmp_path / "fast-one.txt") in kvs["ALL_OUTPUT_FILES"]
    assert str(tmp_path / "slow.txt") not in kvs["ALL_OUTPUT_FILES"]
    assert Path(kvs["ALL_OUTPUT_FILES_PATH"]).read_text(encoding="utf-8").splitlines() == [str(tmp_path / "fast-one.txt")]
    # The dropped-slots file is written whenever a slot is straggler-dropped,
    # regardless of fallback mode, so the coverage gate can excuse the dropped
    # archetype instead of producing a spurious panel-failed stall (issue #5047).
    drop_file = Path(kvs["DROPPED_SLOTS_FILE"])
    assert drop_file.read_text(encoding="utf-8").split("\t")[:3] == ["slow", "cursor", "straggler-dropped"]
    assert not (tmp_path / "slow-phase2.txt").exists()
    assert not (tmp_path / "slow-phase3.txt").exists()


def test_dropped_slot_diagnostic_carrier_copies_launch_stderr(tmp_path: Path) -> None:
    output = tmp_path / "dyn-dyn-lint-escalation-output.txt"
    Path(str(output) + ".launch-stderr").write_text("vendor hung before output\n", encoding="utf-8")
    slot = agent_waterfall.Slot(
        name="dyn-dyn-lint-escalation",
        tool="cursor",
        output=str(output),
        agent="agents/reviewer.md",
        prompt_file="",
    )

    dropped = agent_waterfall._write_drops(  # pyright: ignore[reportPrivateUsage]
        path=str(tmp_path / "panel.output-files"),
        slots=[slot],
        final_outputs=[""],
        drops=[agent_waterfall.DropState("straggler-dropped", "cut")],
    )

    assert Path(dropped).is_file()
    diag = tmp_path / "dropped-dyn-dyn-lint-escalation-cursor-straggler-dropped.txt"
    assert "vendor hung before output" in diag.read_text(encoding="utf-8")
    assert not list(tmp_path.glob("dropped-*.json"))
    assert not list(tmp_path.glob("dropped-*.meta"))


def test_straggler_anchor_requires_collector_validated_half_mark(tmp_path: Path, stub_env: dict[str, str]) -> None:
    manifest = _slots_manifest(
        tmp_path,
        [
            ("good", "codex", "good.txt"),
            ("empty", "codex", "empty.txt"),
            ("crash", "codex", "crash.txt"),
            ("malformed", "codex", "malformed.txt"),
            ("slow", "cursor", "slow.txt"),
        ],
    )
    proc = _run(
        manifest,
        {
            **stub_env,
            "CODEX_STUB_RESULT_CONTENT": "ACCEPT good",
            "CODEX_STUB_EMPTY_OUTPUT_CONTAINS": "empty",
            "CODEX_STUB_FAIL_OUTPUT_CONTAINS": "crash",
            "CODEX_STUB_ALT_OUTPUT_CONTAINS": "malformed",
            "CODEX_STUB_ALT_RESULT_CONTENT": "narration only",
            "CURSOR_STUB_DELAY": "0.2",
            "CURSOR_STUB_RESULT_CONTENT": "ACCEPT slow",
            "LARCH_REVIEWER_STRAGGLER_MULTIPLE": "0.01",
            "LARCH_REVIEWER_STRAGGLER_FLOOR_SECONDS": "0",
        },
        "--straggler-cutoff",
        "--no-fallback",
        "--require-result-pattern",
        "ACCEPT",
    )
    assert proc.returncode == 0, proc.stderr
    kvs = _kv(proc.stdout)
    assert kvs["STRAGGLER_DROPPED_COUNT"] == "0"
    assert "DROPPED_SLOTS_FILE" in kvs
    drop_text = Path(kvs["DROPPED_SLOTS_FILE"]).read_text(encoding="utf-8")
    assert "empty\tcodex\tcollector-failure" in drop_text
    assert "crash\tcodex\tcollector-failure" in drop_text
    assert "malformed\tcodex\tresult-gate-miss" in drop_text
    assert "slow\tcursor\tstraggler-dropped" not in drop_text
    assert str(tmp_path / "slow.txt") in kvs["ALL_OUTPUT_FILES"]


def test_caphit_counts_toward_straggler_half_mark(tmp_path: Path, stub_env: dict[str, str]) -> None:
    manifest = _slots_manifest(tmp_path, [("cap", "codex", "cap.txt"), ("slow", "cursor", "slow.txt")])
    proc = _run(
        manifest,
        {
            **stub_env,
            "CODEX_STUB_RESULT_CONTENT": "STATUS=cap_hit\nbudget",
            "CURSOR_STUB_DELAY": "5",
            "LARCH_REVIEWER_STRAGGLER_MULTIPLE": "0.01",
            "LARCH_REVIEWER_STRAGGLER_FLOOR_SECONDS": "0",
        },
        "--straggler-cutoff",
    )
    assert proc.returncode == 0, proc.stderr
    kvs = _kv(proc.stdout)
    assert kvs["STRAGGLER_DROPPED_COUNT"] == "1"
    assert str(tmp_path / "cap.txt") in kvs["ALL_OUTPUT_FILES"]
    assert str(tmp_path / "slow.txt") not in kvs["ALL_OUTPUT_FILES"]


@pytest.mark.parametrize(
    ("extra_args", "env_overrides"),
    [
        ([], {}),
        (["--straggler-cutoff"], {"LARCH_REVIEWER_STRAGGLER_MULTIPLE": "0"}),
    ],
)
def test_straggler_cutoff_disabled_paths_wait_for_slow_slot(
    tmp_path: Path,
    stub_env: dict[str, str],
    extra_args: list[str],
    env_overrides: dict[str, str],
) -> None:
    manifest = _slots_manifest(tmp_path, [("fast", "codex", "fast.txt"), ("slow", "cursor", "slow.txt")])
    proc = _run(
        manifest,
        {
            **stub_env,
            **env_overrides,
            "CODEX_STUB_RESULT_CONTENT": "fast",
            "CURSOR_STUB_DELAY": "0.2",
            "CURSOR_STUB_RESULT_CONTENT": "slow",
            "LARCH_REVIEWER_STRAGGLER_FLOOR_SECONDS": "0",
        },
        *extra_args,
    )
    assert proc.returncode == 0, proc.stderr
    kvs = _kv(proc.stdout)
    assert kvs["STRAGGLER_DROPPED_COUNT"] == "0"
    assert str(tmp_path / "slow.txt") in kvs["ALL_OUTPUT_FILES"]


def test_straggler_floor_prevents_early_cut(tmp_path: Path, stub_env: dict[str, str]) -> None:
    manifest = _slots_manifest(tmp_path, [("fast", "codex", "fast.txt"), ("slow", "cursor", "slow.txt")])
    proc = _run(
        manifest,
        {
            **stub_env,
            "CURSOR_STUB_DELAY": "0.2",
            "LARCH_REVIEWER_STRAGGLER_MULTIPLE": "0.01",
            # Floor dominates the tiny multiple, so the slow slot is never cut. Keep the
            # floor (and the --timeout ceiling it is clamped against) far above the slow
            # slot's real subprocess-chain latency so saturated parallel CI cannot force a
            # false straggler cut. The happy path still exits on slot completion (~0.3s).
            "LARCH_REVIEWER_STRAGGLER_FLOOR_SECONDS": "30",
        },
        "--timeout",
        "30",
        "--straggler-cutoff",
        "--timeout",
        "60",
    )
    assert proc.returncode == 0, proc.stderr
    kvs = _kv(proc.stdout)
    assert kvs["STRAGGLER_DROPPED_COUNT"] == "0"
    assert str(tmp_path / "slow.txt") in kvs["ALL_OUTPUT_FILES"]


def test_straggler_floor_clamps_negative_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_REVIEWER_STRAGGLER_FLOOR_SECONDS", "-50")

    assert agent_waterfall._straggler_floor() == 0  # pyright: ignore[reportPrivateUsage]


def test_straggler_deadline_clamps_to_timeout_ceiling(tmp_path: Path, stub_env: dict[str, str]) -> None:
    manifest = _slots_manifest(tmp_path, [("fast", "codex", "fast.txt"), ("slow", "cursor", "slow.txt")])
    proc = _run(
        manifest,
        {
            **stub_env,
            "CURSOR_STUB_DELAY": "5",
            "LARCH_REVIEWER_STRAGGLER_MULTIPLE": "100",
            "LARCH_REVIEWER_STRAGGLER_FLOOR_SECONDS": "999",
        },
        "--timeout",
        "1",
        "--straggler-cutoff",
    )
    assert proc.returncode == 0, proc.stderr
    assert _kv(proc.stdout)["STRAGGLER_DROPPED_COUNT"] == "1"


def test_single_slot_phase_never_uses_straggler_cutoff(tmp_path: Path, stub_env: dict[str, str]) -> None:
    manifest, output = _slot(tmp_path, tool="cursor", output_name="single-slow.txt")
    proc = _run(
        manifest,
        {
            **stub_env,
            "CURSOR_STUB_DELAY": "0.2",
            "LARCH_REVIEWER_STRAGGLER_MULTIPLE": "0.01",
            "LARCH_REVIEWER_STRAGGLER_FLOOR_SECONDS": "0",
        },
        "--straggler-cutoff",
    )
    assert proc.returncode == 0, proc.stderr
    kvs = _kv(proc.stdout)
    assert kvs["STRAGGLER_DROPPED_COUNT"] == "0"
    assert str(output) in kvs["ALL_OUTPUT_FILES"]


def test_warn_threshold_emits_cost_fallback_warning(tmp_path: Path, stub_env: dict[str, str]) -> None:
    manifest, _ = _slot(tmp_path, tool="cursor", output_name="warn.txt")
    proc = _run(
        manifest,
        {**stub_env, "LARCH_FALLBACK_CLAUDE_WARN_THRESHOLD": "0", "CURSOR_STUB_FAIL": "true"},
        "--codex-present",
        "false",
        "--cursor-present",
        "false",
    )
    assert proc.returncode == 0, proc.stderr
    kvs = _kv(proc.stdout)
    assert kvs["WARN"] == "cost-fallback-exceeded-threshold"
    assert kvs["FALLBACK_COUNT"] == "1"


def test_competition_notice_forwarded_to_codex_prompt(tmp_path: Path, stub_env: dict[str, str]) -> None:
    agent = ROOT / "agents" / "reviewer-structure.md"
    prompt = tmp_path / "comp.prompt"
    prompt.write_text("vote\n", encoding="utf-8")
    output = tmp_path / "competition-slot.txt"
    manifest = tmp_path / "competition.ndjson"
    manifest.write_text(
        json.dumps({"slot": "s1", "tool": "codex", "output": str(output), "agent": str(agent)}) + "\n",
        encoding="utf-8",
    )
    notice = tmp_path / "competition-notice.md"
    notice.write_text("Custom notice text\n", encoding="utf-8")
    scope = tmp_path / "scope.txt"
    scope.write_text("python/larch/agents/agent_waterfall.py\n", encoding="utf-8")
    codex_log = tmp_path / "codex-competition.log"
    proc = _run(
        manifest,
        {**stub_env, "CODEX_STUB_LOG": str(codex_log)},
        "--competition-notice",
        "--competition-notice-file",
        str(notice),
        "--description-text",
        "competition review context",
        "--scope-files",
        str(scope),
    )
    assert proc.returncode == 0, proc.stderr
    prompt_sidecar = Path(f"{output}.prompt")
    prompt_text = prompt_sidecar.read_text(encoding="utf-8")
    assert "Structure, KISS, and Maintainability" in prompt_text
    log = codex_log.read_text(encoding="utf-8")
    assert "Structure, KISS, and Maintainability" in log
    assert "Competition notice" in log
    assert "Custom notice text" in log


def test_embedded_space_output_paths(tmp_path: Path, stub_env: dict[str, str]) -> None:
    prompt = tmp_path / "space.prompt"
    prompt.write_text("vote\n", encoding="utf-8")
    output = tmp_path / "with space out.txt"
    manifest = tmp_path / "slots space.ndjson"
    manifest.write_text(
        json.dumps({"slot": "s-space", "tool": "codex", "output": str(output), "prompt_file": str(prompt)}) + "\n",
        encoding="utf-8",
    )
    proc = _run(
        manifest,
        stub_env,
        "--codex-present",
        "false",
        "--cursor-present",
        "false",
    )
    assert proc.returncode == 0, proc.stderr
    kvs = _kv(proc.stdout)
    expected = str(tmp_path / "with space out-phase3.txt")
    assert kvs["ALL_OUTPUT_FILES"] == expected
    assert Path(kvs["ALL_OUTPUT_FILES_PATH"]).read_text(encoding="utf-8").strip() == expected


def test_load_slots_validation_rejects_bad_rows(tmp_path: Path, stub_env: dict[str, str]) -> None:
    prompt = tmp_path / "p.prompt"
    prompt.write_text("review\n", encoding="utf-8")
    codex_log = tmp_path / "codex-val.log"
    env = {**stub_env, "CODEX_STUB_LOG": str(codex_log)}
    cases: list[tuple[str, str]] = [
        ("bad-json.ndjson", "not json\n"),
        ("bad-tool.ndjson", json.dumps({"slot": "s1", "tool": "claude", "output": str(tmp_path / "o.txt"), "prompt_file": str(prompt)}) + "\n"),
        ("empty-slot.ndjson", json.dumps({"slot": "", "tool": "codex", "output": str(tmp_path / "o.txt"), "prompt_file": str(prompt)}) + "\n"),
        ("both-agent-prompt.ndjson", json.dumps({"slot": "s1", "tool": "codex", "output": str(tmp_path / "o.txt"), "agent": "a.md", "prompt_file": str(prompt)}) + "\n"),
        ("neither-agent-prompt.ndjson", json.dumps({"slot": "s1", "tool": "codex", "output": str(tmp_path / "o.txt")}) + "\n"),
        ("non-string-agent.ndjson", json.dumps({"slot": "bad", "tool": "codex", "output": str(tmp_path / "invalid.txt"), "agent": 1}) + "\n"),
    ]
    for name, body in cases:
        manifest = tmp_path / name
        manifest.write_text(body, encoding="utf-8")
        proc = _run(manifest, env)
        assert proc.returncode == 2, name
        assert "invalid slot row" in proc.stderr or "no slot rows" in proc.stderr or "must set either agent or prompt_file" in proc.stderr or "must not set both agent and prompt_file" in proc.stderr, name
        assert not codex_log.exists() or codex_log.read_text(encoding="utf-8") == "", name
        assert not Path(str(manifest) + ".output-files").exists(), name


def test_skip_invalid_slots_launches_valid_rows_and_writes_sidecar(tmp_path: Path, stub_env: dict[str, str]) -> None:
    prompt = tmp_path / "valid.prompt"
    prompt.write_text("review\n", encoding="utf-8")
    valid_out = tmp_path / "valid.txt"
    invalid_out = tmp_path / "invalid.txt"
    manifest = tmp_path / "mixed-invalid.ndjson"
    manifest.write_text(
        "\n".join(
            [
                json.dumps({"slot": "valid-slot", "tool": "codex", "output": str(valid_out), "prompt_file": str(prompt)}),
                json.dumps({"slot": "bad-slot", "tool": "codex", "output": str(invalid_out)}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    codex_log = tmp_path / "codex-skip-invalid.log"

    proc = _run(manifest, {**stub_env, "CODEX_STUB_LOG": str(codex_log)}, "--skip-invalid-slots")

    assert proc.returncode == 0, proc.stderr
    assert valid_out.read_text(encoding="utf-8").strip() == "codex ok"
    assert not invalid_out.exists()
    kvs = _kv(proc.stdout)
    assert kvs["INVALID_SLOT_DROP_COUNT"] == "1"
    assert kvs["WARN"] == "invalid-slots-dropped"
    sidecar = Path(kvs["INVALID_SLOT_DROPS_FILE"])
    assert sidecar.is_file()
    sidecar_text = sidecar.read_text(encoding="utf-8")
    assert "bad-slot" in sidecar_text
    assert "must set either agent or prompt_file" in sidecar_text
    assert str(valid_out) in Path(kvs["ALL_OUTPUT_FILES_PATH"]).read_text(encoding="utf-8")
    assert str(invalid_out) not in codex_log.read_text(encoding="utf-8")


def test_waterfall_warning_tokens_merge_for_fallback_and_invalid_slot(tmp_path: Path, stub_env: dict[str, str]) -> None:
    prompt = tmp_path / "valid.prompt"
    prompt.write_text("review\n", encoding="utf-8")
    valid_out = tmp_path / "valid.txt"
    manifest = tmp_path / "mixed-warn.ndjson"
    manifest.write_text(
        json.dumps({"slot": "valid-slot", "tool": "codex", "output": str(valid_out), "prompt_file": str(prompt)})
        + "\n"
        + json.dumps({"slot": "bad-slot", "tool": "codex", "output": str(tmp_path / "invalid.txt")})
        + "\n",
        encoding="utf-8",
    )

    proc = _run(
        manifest,
        {**stub_env, "CODEX_STUB_FAIL": "true", "CURSOR_STUB_FAIL": "true", "LARCH_FALLBACK_CLAUDE_WARN_THRESHOLD": "0"},
        "--skip-invalid-slots",
    )

    assert proc.returncode == 0, proc.stderr
    assert _kv(proc.stdout)["WARN"] == "cost-fallback-exceeded-threshold;invalid-slots-dropped"


def test_skip_invalid_slots_all_invalid_fails_before_launch(tmp_path: Path, stub_env: dict[str, str]) -> None:
    manifest = tmp_path / "all-invalid.ndjson"
    output = tmp_path / "invalid.txt"
    manifest.write_text(json.dumps({"slot": "bad-slot", "tool": "codex", "output": str(output)}) + "\n", encoding="utf-8")
    codex_log = tmp_path / "codex-all-invalid.log"

    proc = _run(manifest, {**stub_env, "CODEX_STUB_LOG": str(codex_log)}, "--skip-invalid-slots")

    assert proc.returncode == 2
    assert "contains no valid slot rows" in proc.stderr
    assert not codex_log.exists()
    assert not output.exists()
    assert not Path(str(manifest) + ".output-files").exists()


def test_skip_invalid_slots_sidecar_failure_happens_before_launch(
    tmp_path: Path,
    stub_env: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompt = tmp_path / "valid.prompt"
    prompt.write_text("review\n", encoding="utf-8")
    valid_out = tmp_path / "valid.txt"
    manifest = tmp_path / "sidecar-failure.ndjson"
    manifest.write_text(
        "\n".join(
            [
                json.dumps({"slot": "valid-slot", "tool": "codex", "output": str(valid_out), "prompt_file": str(prompt)}),
                json.dumps({"slot": "bad-slot", "tool": "codex", "output": str(tmp_path / "bad.txt")}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    real_mkstemp = agent_waterfall.tempfile.mkstemp
    launch_argv: list[Sequence[str]] = []

    def failing_invalid_sidecar_mkstemp(*args: object, **kwargs: object) -> tuple[int, str]:
        prefix = str(kwargs.get("prefix") or (args[0] if args else ""))
        if prefix.startswith(".dispatch-waterfall-invalid-slots."):
            raise OSError("sidecar denied")
        return real_mkstemp(*args, **kwargs)  # type: ignore[arg-type]

    def recording_popen(argv: Sequence[str], **_kwargs: object) -> subprocess.Popen[bytes]:
        launch_argv.append(argv)
        raise AssertionError("sidecar failure must happen before launch")

    monkeypatch.setattr(agent_waterfall.tempfile, "mkstemp", failing_invalid_sidecar_mkstemp)
    monkeypatch.setattr(agent_waterfall.subprocess, "Popen", recording_popen)

    rc, _stdout = _run_direct(manifest, stub_env, monkeypatch, "--skip-invalid-slots")

    assert rc == 2
    assert not launch_argv
    assert not valid_out.exists()
    assert not Path(str(manifest) + ".output-files").exists()


def test_skip_invalid_slots_drops_bad_payload_rows(tmp_path: Path, stub_env: dict[str, str]) -> None:
    prompt = tmp_path / "valid.prompt"
    prompt.write_text("review\n", encoding="utf-8")
    valid_out = tmp_path / "valid.txt"
    invalid_out = tmp_path / "invalid.txt"
    manifest = tmp_path / "payload-invalid.ndjson"
    manifest.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "slot": "valid-slot",
                        "tool": "codex",
                        "output": str(valid_out),
                        "prompt_file": str(prompt),
                        "payload_bytes": 7,
                    }
                ),
                json.dumps(
                    {
                        "slot": "bad-payload",
                        "tool": "codex",
                        "output": str(invalid_out),
                        "prompt_file": str(prompt),
                        "payload_files": {"codex": -1},
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    proc = _run(manifest, stub_env, "--skip-invalid-slots")

    assert proc.returncode == 0, proc.stderr
    assert valid_out.read_text(encoding="utf-8").strip() == "codex ok"
    assert not invalid_out.exists()
    kvs = _kv(proc.stdout)
    assert kvs["INVALID_SLOT_DROP_COUNT"] == "1"
    assert "payload_files.codex" in Path(kvs["INVALID_SLOT_DROPS_FILE"]).read_text(encoding="utf-8")


def test_load_slots_accepts_missing_prompt_file_until_launch_time(tmp_path: Path) -> None:
    manifest = tmp_path / "missing-prompt.ndjson"
    missing_prompt = tmp_path / "does-not-exist.prompt"
    output = tmp_path / "out.txt"
    manifest.write_text(
        json.dumps({"slot": "missing-prompt", "tool": "codex", "output": str(output), "prompt_file": str(missing_prompt)}) + "\n",
        encoding="utf-8",
    )

    slots = agent_waterfall._load_slots(str(manifest))  # pyright: ignore[reportPrivateUsage]

    assert len(slots) == 1
    assert slots[0].prompt_file == str(missing_prompt)


def test_static_dynamic_dispatch_ok_split_on_partial_failure(tmp_path: Path, stub_env: dict[str, str]) -> None:
    manifest = tmp_path / "mixed.ndjson"
    static_out = tmp_path / "static.txt"
    dyn_out = tmp_path / "dyn.txt"
    prompt = tmp_path / "mixed.prompt"
    prompt.write_text("review\n", encoding="utf-8")
    manifest.write_text(
        "\n".join(
            [
                json.dumps({"slot": "static-slot", "tool": "codex", "output": str(static_out), "prompt_file": str(prompt)}),
                json.dumps({"slot": "dyn-cursor-plan-x", "tool": "cursor", "output": str(dyn_out), "prompt_file": str(prompt)}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    proc = _run(
        manifest,
        {
            **stub_env,
            "CODEX_STUB_RESULT_CONTENT": "## Recommendation\ncodex ok",
            "CURSOR_STUB_RESULT_CONTENT": "narration only",
        },
        "--no-fallback",
        "--require-result-pattern",
        r"^[[:space:]]*## Recommendation",
    )
    assert proc.returncode == 0, proc.stderr
    kvs = _kv(proc.stdout)
    assert kvs["STATIC_DISPATCH_OK"] == "true"
    assert kvs["DYNAMIC_DISPATCH_OK"] == "false"


def test_metadata_passthrough_on_launcher_argv(tmp_path: Path, stub_env: dict[str, str], monkeypatch: pytest.MonkeyPatch) -> None:
    manifest, _output = _slot(tmp_path, output_name="meta.txt")
    diff = tmp_path / "diff.patch"
    diff.write_text("diff\n", encoding="utf-8")
    plan = tmp_path / "plan.txt"
    plan.write_text("plan\n", encoding="utf-8")
    launch_argv: list[list[str]] = []
    real_popen = subprocess.Popen

    def recording_popen(argv: Sequence[str], **kwargs: object) -> subprocess.Popen[bytes]:
        argv_list = list(argv)
        if "launch-review" in argv_list or "launch-claude-review" in argv_list:
            launch_argv.append(argv_list)
        return real_popen(argv, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(agent_waterfall.subprocess, "Popen", recording_popen)
    for key, value in stub_env.items():
        monkeypatch.setenv(key, value)
    logging_util.reset_quiet_state()
    argv = [
        "--slots-file",
        str(manifest),
        "--codex-present",
        "true",
        "--cursor-present",
        "true",
        "--mode",
        "diff",
        "--timeout",
        "5",
        "--diff-file",
        str(diff),
        "--commit-count",
        "3",
        "--plan-file",
        str(plan),
    ]
    out = io.StringIO()
    with redirect_stdout(out), redirect_stderr(io.StringIO()):
        rc = agent_waterfall.dispatch_waterfall_main(argv)
    assert rc == 0
    assert launch_argv
    joined = " ".join(launch_argv[0])
    assert "--diff-file" in joined
    assert str(diff) in joined
    assert "--commit-count" in joined
    assert "3" in joined
    assert "--plan-file" in joined
    assert str(plan) in joined


def test_claude_read_tools_add_dir_reaches_phase3_claude_only_when_set(tmp_path: Path, stub_env: dict[str, str], monkeypatch: pytest.MonkeyPatch) -> None:
    # issue #5837 Mode B: the opt-in --claude-read-tools-add-dir grants the terminal
    # Claude voter tier ballot read access. It must reach the phase3 claude launch
    # argv only when set; callers (reviewers) that omit it are unaffected.
    for key, value in stub_env.items():
        monkeypatch.setenv(key, value)

    def _claude_launch_argv(*extra: str, tag: str) -> list[str]:
        manifest, _output = _slot(tmp_path, name=tag, tool="codex", output_name=f"{tag}.txt")
        launched: list[list[str]] = []
        real_popen = subprocess.Popen

        def recording_popen(argv: Sequence[str], **kwargs: object) -> subprocess.Popen[bytes]:
            argv_list = list(argv)
            if "launch-claude-review" in argv_list:
                launched.append(argv_list)
            return real_popen(argv, **kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr(agent_waterfall.subprocess, "Popen", recording_popen)
        logging_util.reset_quiet_state()
        # Both externals absent -> the single codex-primary slot cascades to phase3 Claude.
        argv = ["--slots-file", str(manifest), "--codex-present", "false", "--cursor-present", "false", "--mode", "diff", "--timeout", "5", *extra]
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(io.StringIO()):
            rc = agent_waterfall.dispatch_waterfall_main(argv)
        assert rc == 0
        assert launched, "expected a phase3 claude launch"
        return launched[0]

    with_grant = _claude_launch_argv("--claude-read-tools-add-dir", str(tmp_path), tag="grant")
    assert "--read-tools-add-dir" in with_grant
    assert str(tmp_path) in with_grant

    without_grant = _claude_launch_argv(tag="nogrant")
    assert "--read-tools-add-dir" not in without_grant


def test_dropped_slots_tab_cr_flattening(tmp_path: Path, stub_env: dict[str, str]) -> None:
    manifest = tmp_path / "tab-cr.ndjson"
    out = tmp_path / "nf-tab.txt"
    prompt = tmp_path / "tab.prompt"
    prompt.write_text("review\n", encoding="utf-8")
    manifest.write_text(
        json.dumps({"slot": "dyn-cursor-plan-a\tb", "tool": "cursor", "output": str(out), "prompt_file": str(prompt)}) + "\n",
        encoding="utf-8",
    )
    proc = _run(
        manifest,
        {**stub_env, "CURSOR_STUB_FAIL": "true"},
        "--no-fallback",
        "--codex-present",
        "false",
    )
    assert proc.returncode == 0, proc.stderr
    drop_file = Path(_kv(proc.stdout)["DROPPED_SLOTS_FILE"])
    lines = drop_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    fields = lines[0].split("\t")
    assert len(fields) == 4
    assert fields[2] == "collector-failure"
    assert "\t" not in fields[0]
    assert "\r" not in fields[0]


def test_aggregate_alternation_invalid_ere_exits_two(tmp_path: Path, stub_env: dict[str, str]) -> None:
    manifest, _ = _slot(tmp_path)
    codex_log = tmp_path / "codex-agg-invalid.log"
    cursor_log = tmp_path / "cursor-agg-invalid.log"
    pattern = r"^(### FINDING_[0-9]+:|[[:space:]]*LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED[[:space:]]*$"
    proc = _run(
        manifest,
        {**stub_env, "CODEX_STUB_LOG": str(codex_log), "CURSOR_STUB_LOG": str(cursor_log)},
        "--require-result-pattern",
        pattern,
    )
    assert proc.returncode == 2
    assert "--require-result-pattern is not a valid ERE" in proc.stderr
    assert not codex_log.exists() or codex_log.read_text(encoding="utf-8") == ""
    assert not cursor_log.exists() or cursor_log.read_text(encoding="utf-8") == ""
    assert not Path(str(manifest) + ".output-files").exists()


def test_phase2_launches_all_before_single_collect(tmp_path: Path, stub_env: dict[str, str], monkeypatch: pytest.MonkeyPatch) -> None:
    collect_calls = _record_collect_calls(monkeypatch)
    manifest = tmp_path / "phase2-concurrency.ndjson"
    out1 = tmp_path / "p2a.txt"
    out2 = tmp_path / "p2b.txt"
    prompt = tmp_path / "p2.prompt"
    prompt.write_text("review\n", encoding="utf-8")
    manifest.write_text(
        "\n".join(
            [
                json.dumps({"slot": "s1", "tool": "codex", "output": str(out1), "prompt_file": str(prompt)}),
                json.dumps({"slot": "s2", "tool": "codex", "output": str(out2), "prompt_file": str(prompt)}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    env = {**stub_env, "CODEX_STUB_FAIL": "true"}
    rc, _stdout = _run_direct(manifest, env, monkeypatch)
    assert rc == 0
    summary_calls = [call for call in collect_calls if "--summary-only" in call]
    assert len(summary_calls) == 2
    phase2_call = summary_calls[1]
    outputs = phase2_call[phase2_call.index("--summary-only") + 1 :]
    assert outputs == [str(out1).replace(".txt", "-phase2.txt"), str(out2).replace(".txt", "-phase2.txt")]


def test_phase3_launches_all_before_single_collect(tmp_path: Path, stub_env: dict[str, str], monkeypatch: pytest.MonkeyPatch) -> None:
    collect_calls = _record_collect_calls(monkeypatch)
    manifest = tmp_path / "phase3-concurrency.ndjson"
    out1 = tmp_path / "p3a.txt"
    out2 = tmp_path / "p3b.txt"
    prompt = tmp_path / "p3.prompt"
    prompt.write_text("review\n", encoding="utf-8")
    manifest.write_text(
        "\n".join(
            [
                json.dumps({"slot": "s1", "tool": "codex", "output": str(out1), "prompt_file": str(prompt)}),
                json.dumps({"slot": "s2", "tool": "codex", "output": str(out2), "prompt_file": str(prompt)}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    env = {**stub_env, "CODEX_STUB_FAIL": "true", "CURSOR_STUB_FAIL": "true"}
    rc, _stdout = _run_direct(manifest, env, monkeypatch)
    assert rc == 0
    summary_calls = [call for call in collect_calls if "--summary-only" in call]
    assert len(summary_calls) == 3
    phase3_call = summary_calls[2]
    outputs = phase3_call[phase3_call.index("--summary-only") + 1 :]
    assert outputs == [str(out1).replace(".txt", "-phase3.txt"), str(out2).replace(".txt", "-phase3.txt")]


def test_phase1_launches_all_before_single_collect(tmp_path: Path, stub_env: dict[str, str], monkeypatch: pytest.MonkeyPatch) -> None:
    collect_calls = _record_collect_calls(monkeypatch)
    manifest = tmp_path / "concurrency.ndjson"
    out1 = tmp_path / "c1.txt"
    out2 = tmp_path / "c2.txt"
    prompt = tmp_path / "c.prompt"
    prompt.write_text("review\n", encoding="utf-8")
    manifest.write_text(
        "\n".join(
            [
                json.dumps({"slot": "s1", "tool": "codex", "output": str(out1), "prompt_file": str(prompt)}),
                json.dumps({"slot": "s2", "tool": "cursor", "output": str(out2), "prompt_file": str(prompt)}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    rc, _stdout = _run_direct(manifest, stub_env, monkeypatch)
    assert rc == 0
    summary_calls = [call for call in collect_calls if "--summary-only" in call]
    assert len(summary_calls) == 1
    outputs = summary_calls[0][summary_calls[0].index("--summary-only") + 1 :]
    assert outputs == [str(out1), str(out2)]


def test_degraded_cursor_falls_back_to_claude(tmp_path: Path, stub_env: dict[str, str]) -> None:
    manifest, _ = _slot(tmp_path, tool="cursor", output_name="cursor-deg.txt")
    narration = "Exploring the design skill...Creating the architectural review plan from codebase alignment."
    proc = _run(
        manifest,
        {
            **stub_env,
            "CURSOR_STUB_OUTPUT_TOKENS": "5000",
            "CURSOR_STUB_RESULT_CONTENT": narration,
            "CODEX_STUB_FAIL": "true",
        },
        "--codex-present",
        "false",
    )
    assert proc.returncode == 0, proc.stderr
    kvs = _kv(proc.stdout)
    assert kvs["ALL_OUTPUT_TOOLS"] == "claude"
    assert kvs["FALLBACK_COUNT"] == "1"
    assert (tmp_path / "cursor-deg-phase3.txt").read_text(encoding="utf-8").strip() == "claude ok"


def test_no_fallback_tool_absent_drop(tmp_path: Path, stub_env: dict[str, str]) -> None:
    manifest, _ = _slot(tmp_path, name="absent", output_name="no-fallback-absent.txt")
    proc = _run(
        manifest,
        stub_env,
        "--no-fallback",
        "--codex-present",
        "false",
        "--cursor-present",
        "false",
    )
    assert proc.returncode == 0, proc.stderr
    kvs = _kv(proc.stdout)
    assert kvs["ALL_SLOTS_DROPPED"] == "true"
    drop_file = Path(kvs["DROPPED_SLOTS_FILE"])
    fields = drop_file.read_text(encoding="utf-8").split("\t")
    assert fields[2] == "tool-absent"


def test_paths_file_directory_target_exits_two_without_success_kvs(tmp_path: Path, stub_env: dict[str, str]) -> None:
    manifest, _ = _slot(tmp_path)
    paths_dir = tmp_path / "is-a-dir"
    paths_dir.mkdir()
    proc = _run(manifest, stub_env, "--paths-file", str(paths_dir))
    assert proc.returncode == 2
    assert "paths-file not writable" in proc.stderr
    assert "DISPATCH_OK" not in proc.stdout


def test_paths_file_unwritable_parent_exits_two_without_success_kvs(tmp_path: Path, stub_env: dict[str, str]) -> None:
    manifest, _ = _slot(tmp_path)
    unreadable = tmp_path / "no-write"
    unreadable.mkdir()
    unreadable.chmod(0o555)
    try:
        proc = _run(manifest, stub_env, "--paths-file", str(unreadable / "outputs.list"))
        assert proc.returncode == 2
        assert "paths-file not writable" in proc.stderr
        assert "DISPATCH_OK" not in proc.stdout
    finally:
        unreadable.chmod(0o755)


def test_no_fallback_result_gate_miss_drop(tmp_path: Path, stub_env: dict[str, str]) -> None:
    manifest, _ = _slot(tmp_path, tool="cursor", output_name="gate-miss.txt")
    proc = _run(
        manifest,
        {**stub_env, "CURSOR_STUB_RESULT_CONTENT": "narration only"},
        "--no-fallback",
        "--require-result-pattern",
        r"^[[:space:]]*## Recommendation",
    )
    assert proc.returncode == 0, proc.stderr
    kvs = _kv(proc.stdout)
    assert kvs["ALL_SLOTS_DROPPED"] == "true"
    fields = Path(kvs["DROPPED_SLOTS_FILE"]).read_text(encoding="utf-8").split("\t")
    assert fields[:3] == ["s1", "cursor", "result-gate-miss"]


def test_no_fallback_empty_drop(tmp_path: Path, stub_env: dict[str, str]) -> None:
    manifest, _ = _slot(tmp_path, tool="cursor", output_name="empty.txt")
    proc = _run(
        manifest,
        {**stub_env, "CURSOR_STUB_RESULT_CONTENT": "   \n\t\n  "},
        "--no-fallback",
        "--require-first-line-pattern",
        r"^[[:space:]]*schema_version",
    )
    assert proc.returncode == 0, proc.stderr
    kvs = _kv(proc.stdout)
    assert kvs["ALL_SLOTS_DROPPED"] == "true"
    fields = Path(kvs["DROPPED_SLOTS_FILE"]).read_text(encoding="utf-8").split("\t")
    assert fields[:3] == ["s1", "cursor", "empty"]


def test_no_fallback_collector_failure_drop(tmp_path: Path, stub_env: dict[str, str]) -> None:
    manifest, _ = _slot(tmp_path, output_name="collector-fail.txt")
    proc = _run(manifest, {**stub_env, "CODEX_STUB_FAIL": "true"}, "--no-fallback")
    assert proc.returncode == 0, proc.stderr
    kvs = _kv(proc.stdout)
    assert kvs["ALL_SLOTS_DROPPED"] == "true"
    fields = Path(kvs["DROPPED_SLOTS_FILE"]).read_text(encoding="utf-8").split("\t")
    assert fields[2] == "collector-failure"


def test_no_fallback_result_unreadable_drop(tmp_path: Path, stub_env: dict[str, str], monkeypatch: pytest.MonkeyPatch) -> None:
    manifest, _ = _slot(tmp_path, tool="cursor", output_name="unreadable.txt")
    missing = tmp_path / "missing-reviewer.txt"
    real_run = proc_module.run

    def fake_run(
        argv: Sequence[str],
        *,
        timeout: float | None = None,
        cwd: str | None = None,
        env: Mapping[str, str] | None = None,
        check: bool = False,
        stdout: int | None = None,
        stderr: int | None = None,
    ) -> proc_module.CommandResult:
        if "collect-results" in argv:
            return proc_module.CommandResult(
                tuple(argv),
                0,
                f"STATUS=OK\nREVIEWER_FILE={missing}\n",
                "",
                0.0,
            )
        return real_run(
            argv,
            timeout=timeout,
            cwd=cwd,
            env=env,
            check=check,
            stdout=stdout,
            stderr=stderr,
        )

    monkeypatch.setattr(agent_waterfall.proc, "run", fake_run)
    rc, stdout = _run_direct(
        manifest,
        stub_env,
        monkeypatch,
        "--no-fallback",
        "--require-result-pattern",
        r"^[[:space:]]*## Recommendation",
    )
    assert rc == 0
    kvs = _kv(stdout)
    assert kvs["ALL_SLOTS_DROPPED"] == "true"
    fields = Path(kvs["DROPPED_SLOTS_FILE"]).read_text(encoding="utf-8").split("\t")
    assert fields[:3] == ["s1", "cursor", "result-unreadable"]


def test_no_fallback_partial_drop_emits_dropped_file_not_all_slots_dropped(tmp_path: Path, stub_env: dict[str, str]) -> None:
    manifest = tmp_path / "partial.ndjson"
    out_ok = tmp_path / "ok.txt"
    out_drop = tmp_path / "drop.txt"
    prompt = tmp_path / "partial.prompt"
    prompt.write_text("review\n", encoding="utf-8")
    manifest.write_text(
        "\n".join(
            [
                json.dumps({"slot": "ok", "tool": "codex", "output": str(out_ok), "prompt_file": str(prompt)}),
                json.dumps({"slot": "drop", "tool": "cursor", "output": str(out_drop), "prompt_file": str(prompt)}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    proc = _run(
        manifest,
        {
            **stub_env,
            "CURSOR_STUB_RESULT_CONTENT": "narration only",
            "CODEX_STUB_RESULT_CONTENT": "## Recommendation\ncodex ok",
        },
        "--no-fallback",
        "--require-result-pattern",
        r"^[[:space:]]*## Recommendation",
    )
    assert proc.returncode == 0, proc.stderr
    kvs = _kv(proc.stdout)
    assert "ALL_SLOTS_DROPPED" not in kvs
    assert "DROPPED_SLOTS_FILE" in kvs
    drop_lines = Path(kvs["DROPPED_SLOTS_FILE"]).read_text(encoding="utf-8").splitlines()
    assert len(drop_lines) == 1
    assert drop_lines[0].split("\t")[2] == "result-gate-miss"


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def test_sigterm_kills_launcher_subtree(tmp_path: Path, stub_env: dict[str, str]) -> None:
    manifest, _ = _slot(tmp_path, tool="cursor", output_name="term-trap-slot.txt")
    stub_pid_file = tmp_path / "term-trap-stub.pid"
    env = {**stub_env, "CURSOR_STUB_DELAY": "30", "CURSOR_STUB_PID_FILE": str(stub_pid_file)}
    with subprocess.Popen(
        [
            sys.executable,
            str(CLI),
            "agent",
            "dispatch-waterfall",
            "--slots-file",
            str(manifest),
            "--codex-present",
            "false",
            "--cursor-present",
            "true",
            "--mode",
            "description",
            "--timeout",
            "60",
        ],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ) as dispatcher:
        deadline = time.monotonic() + 10
        pid_text = ""
        while not pid_text:
            if stub_pid_file.is_file():
                pid_text = stub_pid_file.read_text(encoding="utf-8").strip()
            if not pid_text:
                if time.monotonic() >= deadline:
                    dispatcher.kill()
                    dispatcher.wait()
                    pytest.fail("cursor stub PID file not created within 10s")
                time.sleep(0.05)
        stub_pid = int(pid_text)
        time.sleep(0.2)
        os.kill(dispatcher.pid, signal.SIGTERM)
        rc = dispatcher.wait(timeout=10)
        assert rc == 143
        gone_deadline = time.monotonic() + 5
        while _pid_alive(stub_pid):
            if time.monotonic() >= gone_deadline:
                with contextlib.suppress(ProcessLookupError):
                    os.kill(stub_pid, signal.SIGKILL)
                pytest.fail("cursor stub launcher still alive after dispatcher SIGTERM")
            time.sleep(0.05)


def test_grouped_reuse_guard() -> None:
    dispatcher = (ROOT / "python" / "larch" / "agents" / "agent_waterfall.py").read_text(encoding="utf-8")
    symbols = [
        "reuse_slot_result",
        "find_group_ok_for_tool",
        "append_group_ledger_ok",
        "GROUP_LEDGER",
        "REUSED_INDICES",
        "idx_was_reused",
        "has_fallback_groups",
        "waterfall-" + "group-results",
        "DEDUPE_REUSED",
        "slot_" + "fallback_" + "groups",
        "REUSED_INDICES_FILE",
        "phase2_grouped",
    ]
    for symbol in symbols:
        assert symbol not in dispatcher
    for needle in ("fallback_" + "group", "." + "dedup", "waterfall-" + "group-results"):
        assert needle not in dispatcher
    token = "fallback_" + "group"
    hits: list[str] = []
    for root_name in ("skills", "scripts"):
        for path in (ROOT / root_name).rglob("*"):
            if not path.is_file() or path.suffix == ".md" or (path.name.startswith("test-") and path.suffix == ".sh"):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if token in text:
                hits.append(str(path.relative_to(ROOT)))
    assert not hits


def test_parse_args_accepts_and_validates_site(tmp_path: Path) -> None:
    slots = _write(path=tmp_path / "slots.ndjson", text=json.dumps({"slot": "s1", "tool": "codex", "output": str(tmp_path / "o.txt"), "agent": "agents/code-reviewer.md"}) + "\n")
    base = ["--slots-file", str(slots), "--codex-present", "true", "--cursor-present", "true", "--mode", "diff"]
    default_opts = agent_waterfall._parse_args(base)  # pyright: ignore[reportPrivateUsage]
    assert isinstance(default_opts, agent_waterfall.Options)
    assert default_opts.site == "review Step 2"
    explicit = agent_waterfall._parse_args([*base, "--site", "design Step 3"])  # pyright: ignore[reportPrivateUsage]
    assert isinstance(explicit, agent_waterfall.Options)
    assert explicit.site == "design Step 3"
    for bad in ("", "--flagish"):
        with pytest.raises(agent_waterfall.ValidationError):
            agent_waterfall._parse_args([*base, "--site", bad])  # pyright: ignore[reportPrivateUsage]


def test_launch_slot_threads_site_to_launch_review_not_claude(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[list[str]] = []

    class _FakePopen:
        def __init__(self, argv: Sequence[str], **_kwargs: object) -> None:
            captured.append([str(a) for a in argv])
            self.pid = 4321

    monkeypatch.setattr(agent_waterfall.subprocess, "Popen", _FakePopen)
    monkeypatch.setattr(agent_waterfall, "_ACTIVE_LAUNCHES", [])
    monkeypatch.setattr(agent_waterfall, "_DISPATCH_LAUNCHES", [])
    opts = agent_waterfall.Options(
        slots_file=str(tmp_path / "slots.ndjson"),
        codex_present=True,
        cursor_present=True,
        mode="diff",
        site="design Step 3",
    )
    codex_slot = agent_waterfall.Slot(name="r1", tool="codex", output=str(tmp_path / "o1.txt"), agent="agents/code-reviewer.md", prompt_file="")
    claude_slot = agent_waterfall.Slot(name="r2", tool="claude", output=str(tmp_path / "o2.txt"), agent="agents/code-reviewer.md", prompt_file="")
    codex_launch = agent_waterfall._launch_slot(idx=0, phase="phase1", tool="codex", output=str(tmp_path / "o1.txt"), slots=[codex_slot], opts=opts)  # pyright: ignore[reportPrivateUsage]
    claude_launch = agent_waterfall._launch_slot(idx=0, phase="phase1", tool="claude", output=str(tmp_path / "o2.txt"), slots=[claude_slot], opts=opts)  # pyright: ignore[reportPrivateUsage]
    for launch in (codex_launch, claude_launch):
        handle = launch.stderr_handle
        if isinstance(handle, io.IOBase):
            handle.close()
    codex_argv, claude_argv = captured[0], captured[1]
    assert "launch-review" in codex_argv
    assert codex_argv[codex_argv.index("--site") + 1] == "design Step 3"
    assert "launch-claude-review" in claude_argv
    assert "--site" not in claude_argv


def test_bind_manifest_slot_outputs_uses_slot_identity_for_compressed_success(tmp_path: Path) -> None:
    manifest = tmp_path / "slots.ndjson"
    output2 = tmp_path / "voter-2.txt"
    output3 = tmp_path / "voter-3.txt"
    manifest.write_text(
        json.dumps({"slot": "voter-2", "tool": "codex", "output": str(output2), "prompt_file": str(tmp_path / "p2")}) + "\n"
        + json.dumps({"slot": "voter-3", "tool": "codex", "output": str(output3), "prompt_file": str(tmp_path / "p3")}) + "\n",
        encoding="utf-8",
    )
    paths_file = tmp_path / "paths.txt"
    paths_file.write_text(str(output3) + "\n", encoding="utf-8")
    drops = tmp_path / "paths.txt.dropped-slots"
    drops.write_text("voter-2\tcodex\tempty\t\n", encoding="utf-8")

    bindings = agent_waterfall.bind_manifest_slot_outputs(
        manifest_path=manifest,
        wf_kv={"ALL_OUTPUT_FILES_PATH": str(paths_file), "ALL_OUTPUT_TOOLS": "cursor", "DROPPED_SLOTS_FILE": str(drops)},
    )

    assert bindings["voter-2"].path == ""
    assert bindings["voter-2"].dropped is True
    assert bindings["voter-3"].path == str(output3)
    assert bindings["voter-3"].tool == "cursor"


def test_dispatch_waterfall_model_role_parser_forwards_to_codex(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    launches: list[list[str]] = []

    class FakeProcess:
        def __init__(self, argv: list[str], stdout: object = None, stderr: object = None, start_new_session: bool = False, env: object = None) -> None:
            _ = (stdout, stderr, start_new_session, env)
            launches.append([str(item) for item in argv])
            output = argv[argv.index("--output") + 1]
            Path(output).write_text("OK\n", encoding="utf-8")
            Path(str(output) + ".done").write_text("0\n", encoding="utf-8")
            self.pid = 999999
            self.returncode = 0

        def poll(self) -> int:
            return 0

        def wait(self, timeout: float | None = None) -> int:
            _ = timeout
            return 0

    def fake_slot_collector_accepted(**_kwargs: object) -> bool:
        return True

    def fake_collect_phase(**_kwargs: object) -> list[int]:
        return []

    monkeypatch.setattr(agent_waterfall.subprocess, "Popen", FakeProcess)
    monkeypatch.setattr(agent_waterfall, "_slot_collector_accepted", fake_slot_collector_accepted)
    monkeypatch.setattr(agent_waterfall, "_collect_phase", fake_collect_phase)
    manifest = tmp_path / "slots.ndjson"
    manifest.write_text(json.dumps({"slot": "s", "tool": "codex", "output": str(tmp_path / "out.txt"), "prompt_file": str(tmp_path / "p")}) + "\n", encoding="utf-8")
    opts = agent_waterfall.Options(slots_file=str(manifest), codex_present=True, cursor_present=True, mode="description", model_role="vote")

    assert agent_waterfall.dispatch_waterfall(opts) == 0
    assert any("--model-role" in call and call[call.index("--model-role") + 1] == "vote" for call in launches)


def test_dispatch_waterfall_slot_model_role_overrides_global_for_codex(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    launches: list[list[str]] = []

    class FakeProcess:
        def __init__(self, argv: list[str], stdout: object = None, stderr: object = None, start_new_session: bool = False, env: object = None) -> None:
            _ = (stdout, stderr, start_new_session, env)
            launches.append([str(item) for item in argv])
            output = argv[argv.index("--output") + 1]
            Path(output).write_text("OK\n", encoding="utf-8")
            Path(str(output) + ".done").write_text("0\n", encoding="utf-8")
            self.pid = 999999
            self.returncode = 0

        def poll(self) -> int:
            return 0

        def wait(self, timeout: float | None = None) -> int:
            _ = timeout
            return 0

    def fake_slot_collector_accepted(**_kwargs: object) -> bool:
        return True

    def fake_collect_phase(**_kwargs: object) -> list[int]:
        return []

    monkeypatch.setattr(agent_waterfall.subprocess, "Popen", FakeProcess)
    monkeypatch.setattr(agent_waterfall, "_slot_collector_accepted", fake_slot_collector_accepted)
    monkeypatch.setattr(agent_waterfall, "_collect_phase", fake_collect_phase)
    manifest = tmp_path / "slots.ndjson"
    manifest.write_text(
        json.dumps(
            {
                "slot": "generalist",
                "tool": "codex",
                "output": str(tmp_path / "out.txt"),
                "prompt_file": str(tmp_path / "p"),
                "model_role": "default",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    opts = agent_waterfall.Options(
        slots_file=str(manifest), codex_present=True, cursor_present=True, mode="description", model_role="vote"
    )

    assert agent_waterfall.dispatch_waterfall(opts) == 0
    assert any("--model-role" in call and call[call.index("--model-role") + 1] == "default" for call in launches)


def test_parse_slot_row_accepts_prompt_files_only(tmp_path: Path) -> None:
    output = tmp_path / "out.txt"
    slot = agent_waterfall._parse_slot_row(  # pyright: ignore[reportPrivateUsage]
        json.dumps({"slot": "s1", "tool": "codex", "output": str(output), "prompt_files": {"codex": "codex.prompt", "cursor": "cursor.prompt"}})
    )
    assert slot.prompt_file == ""
    assert slot.prompt_files == {"codex": "codex.prompt", "cursor": "cursor.prompt"}
    assert agent_waterfall._prompt_file_for_tool(slot=slot, tool="cursor") == "cursor.prompt"  # pyright: ignore[reportPrivateUsage]
    assert agent_waterfall._prompt_file_for_tool(slot=slot, tool="claude") is None  # pyright: ignore[reportPrivateUsage]




def test_parse_slot_row_accepts_payload_bytes_and_payload_files(tmp_path: Path) -> None:
    output = tmp_path / "out.txt"
    slot = agent_waterfall._parse_slot_row(  # pyright: ignore[reportPrivateUsage]
        json.dumps({
            "slot": "s1",
            "tool": "codex",
            "output": str(output),
            "prompt_files": {"codex": "codex.prompt", "cursor": "cursor.prompt"},
            "payload_bytes": "5",
            "payload_files": {"codex": "7", "cursor": 11},
        })
    )

    assert slot.payload_bytes == 5
    assert slot.payload_files == {"codex": 7, "cursor": 11}
    assert agent_waterfall._payload_bytes_for_tool(slot=slot, tool="cursor") == 11  # pyright: ignore[reportPrivateUsage]
    assert agent_waterfall._payload_bytes_for_tool(slot=slot, tool="claude") == 0  # pyright: ignore[reportPrivateUsage]


def test_parse_slot_row_rejects_invalid_payload_fields(tmp_path: Path) -> None:
    output = tmp_path / "out.txt"
    with pytest.raises(agent_waterfall.ValidationError):
        agent_waterfall._parse_slot_row(  # pyright: ignore[reportPrivateUsage]
            json.dumps({"slot": "s1", "tool": "codex", "output": str(output), "prompt_file": "p", "payload_bytes": "bad"})
        )
    with pytest.raises(agent_waterfall.ValidationError):
        agent_waterfall._parse_slot_row(  # pyright: ignore[reportPrivateUsage]
            json.dumps({"slot": "s1", "tool": "codex", "output": str(output), "prompt_file": "p", "payload_files": {"codex": -1}})
        )

def test_parse_slot_row_rejects_invalid_prompt_files(tmp_path: Path) -> None:
    output = tmp_path / "out.txt"
    with pytest.raises(agent_waterfall.ValidationError):
        agent_waterfall._parse_slot_row(  # pyright: ignore[reportPrivateUsage]
            json.dumps({"slot": "s1", "tool": "codex", "output": str(output), "prompt_files": {"bad": "x"}})
        )
    with pytest.raises(agent_waterfall.ValidationError):
        agent_waterfall._parse_slot_row(  # pyright: ignore[reportPrivateUsage]
            json.dumps({"slot": "s1", "tool": "codex", "output": str(output), "prompt_files": {"codex": ""}})
        )


def test_phase3_prompt_missing_records_drop_not_synthetic_output(tmp_path: Path, stub_env: dict[str, str], monkeypatch: pytest.MonkeyPatch) -> None:
    codex_prompt = tmp_path / "codex.prompt"
    cursor_prompt = tmp_path / "cursor.prompt"
    codex_prompt.write_text("codex review\n", encoding="utf-8")
    cursor_prompt.write_text("cursor review\n", encoding="utf-8")
    output = tmp_path / "out.txt"
    manifest = tmp_path / "slots.ndjson"
    manifest.write_text(
        json.dumps(
            {
                "slot": "s1",
                "tool": "codex",
                "output": str(output),
                "prompt_files": {"codex": str(codex_prompt), "cursor": str(cursor_prompt)},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    env = {**stub_env, "CODEX_STUB_FAIL": "true", "CURSOR_STUB_FAIL": "true"}
    rc, stdout = _run_direct(manifest, env, monkeypatch)
    assert rc == 0
    kvs = _kv(stdout)
    assert kvs["DISPATCH_OK"] == "false"
    assert kvs.get("ALL_OUTPUT_FILES", "") == ""
    assert not (tmp_path / "out-phase3.txt").exists()
    dropped = Path(kvs["ALL_OUTPUT_FILES_PATH"] + ".dropped-slots")
    assert dropped.is_file()
    assert "prompt-missing" in dropped.read_text(encoding="utf-8")


def test_waterfall_per_tool_prompt_files_phase2_uses_cursor_prompt(tmp_path: Path, stub_env: dict[str, str], monkeypatch: pytest.MonkeyPatch) -> None:
    codex_prompt = tmp_path / "codex.prompt"
    cursor_prompt = tmp_path / "cursor.prompt"
    codex_prompt.write_text("CODEX_MARKER\n", encoding="utf-8")
    cursor_prompt.write_text("CURSOR_MARKER\n", encoding="utf-8")
    output = tmp_path / "out.txt"
    manifest = tmp_path / "slots.ndjson"
    manifest.write_text(
        json.dumps(
            {
                "slot": "s1",
                "tool": "codex",
                "output": str(output),
                "prompt_files": {"codex": str(codex_prompt), "cursor": str(cursor_prompt)},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    cursor_log = tmp_path / "cursor.log"
    env = {**stub_env, "CODEX_STUB_FAIL": "true", "CURSOR_STUB_LOG": str(cursor_log)}
    rc, stdout = _run_direct(manifest, env, monkeypatch)
    assert rc == 0
    assert "CURSOR_MARKER" in cursor_log.read_text(encoding="utf-8")
    assert "CODEX_MARKER" not in cursor_log.read_text(encoding="utf-8")
    assert _kv(stdout)["ALL_OUTPUT_TOOLS"] == "cursor"


def test_launch_slot_threads_panel_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    captured_env: dict[str, str] = {}

    class _FakePopen:
        def __init__(self, _argv: Sequence[str], **kwargs: object) -> None:
            env = kwargs.get("env")
            if isinstance(env, dict):
                captured_env.update({str(k): str(v) for k, v in env.items()})
            self.pid = 1234

    monkeypatch.setattr(agent_waterfall.subprocess, "Popen", _FakePopen)
    monkeypatch.setattr(agent_waterfall, "_ACTIVE_LAUNCHES", [])
    monkeypatch.setattr(agent_waterfall, "_DISPATCH_LAUNCHES", [])
    artifact_dir = tmp_path / "round-7"
    opts = agent_waterfall.Options(
        slots_file=str(tmp_path / "slots.ndjson"),
        codex_present=True,
        cursor_present=True,
        mode="description",
        site="review Step 2",
        panel_artifact_dir=str(artifact_dir),
    )
    slot = agent_waterfall.Slot("correctness", "cursor", str(tmp_path / "out.txt"), "", str(tmp_path / "prompt.txt"), payload_bytes=9)

    agent_waterfall._launch_slot(idx=0, phase="phase1", tool="cursor", output=str(tmp_path / "out.txt"), slots=[slot], opts=opts)  # pyright: ignore[reportPrivateUsage]

    assert captured_env["LARCH_PANEL_ARTIFACT_DIR"] == str(artifact_dir)
    assert captured_env["LARCH_PANEL_SLOT"] == "correctness"
    assert captured_env["LARCH_PANEL_ROUND_NUM"] == "7"
    assert captured_env["LARCH_PANEL_PAYLOAD_BYTES"] == "9"


def test_launch_slot_threads_payload_files_by_tool(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    captured_envs: list[dict[str, str]] = []

    class _FakePopen:
        def __init__(self, _argv: Sequence[str], **kwargs: object) -> None:
            env = kwargs.get("env")
            captured_envs.append({str(k): str(v) for k, v in env.items()})  # type: ignore[union-attr]
            self.pid = 1234

    monkeypatch.setattr(agent_waterfall.subprocess, "Popen", _FakePopen)
    monkeypatch.setattr(agent_waterfall, "_ACTIVE_LAUNCHES", [])
    monkeypatch.setattr(agent_waterfall, "_DISPATCH_LAUNCHES", [])
    artifact_dir = tmp_path / "round-7"
    opts = agent_waterfall.Options(
        slots_file=str(tmp_path / "slots.ndjson"),
        codex_present=True,
        cursor_present=True,
        mode="description",
        site="review Step 2",
        panel_artifact_dir=str(artifact_dir),
    )
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("prompt\n", encoding="utf-8")
    slot = agent_waterfall.Slot(
        "correctness",
        "cursor",
        str(tmp_path / "out.txt"),
        "",
        str(prompt),
        payload_bytes=99,
        payload_files={"codex": 3, "cursor": 11},
    )

    agent_waterfall._launch_slot(idx=0, phase="phase1", tool="codex", output=str(tmp_path / "out-codex.txt"), slots=[slot], opts=opts)  # pyright: ignore[reportPrivateUsage]
    agent_waterfall._launch_slot(idx=0, phase="phase1", tool="cursor", output=str(tmp_path / "out-cursor.txt"), slots=[slot], opts=opts)  # pyright: ignore[reportPrivateUsage]

    assert [env["LARCH_PANEL_PAYLOAD_BYTES"] for env in captured_envs] == ["3", "11"]


def _tsv_rows(path: Path) -> list[dict[str, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    header = lines[0].split("\t")
    return [dict(zip(header, line.split("\t"), strict=False)) for line in lines[1:]]


def test_waterfall_dispatch_materializes_panel_prompt_sizes(tmp_path: Path, stub_env: dict[str, str]) -> None:
    artifact_dir = tmp_path / "round-3"
    artifact_dir.mkdir()
    manifest = _slots_manifest(tmp_path, [("correctness", "cursor", "cursor-correctness-output.txt")])
    env = {**stub_env, "CURSOR_API_KEY": "test-key"}
    result = _run(
        manifest,
        env,
        "--panel-artifact-dir",
        str(artifact_dir),
        "--site",
        "review Step 2",
        "--model-role",
        "review",
    )
    assert result.returncode == 0, result.stderr
    tsv = artifact_dir / "panel-prompt-sizes.tsv"
    assert tsv.is_file()
    rows = _tsv_rows(tsv)
    assert len(rows) >= 1
    assert rows[0]["slot_kind"] == "specialist"
    assert "review\n" not in tsv.read_text(encoding="utf-8")


def test_waterfall_voter_dispatch_materializes_panel_prompt_sizes(tmp_path: Path, stub_env: dict[str, str]) -> None:
    artifact_dir = tmp_path / "round-2"
    artifact_dir.mkdir()
    manifest = _slots_manifest(tmp_path, [("voter-1", "cursor", "cursor-vote-output.txt")])
    env = {**stub_env, "CURSOR_API_KEY": "test-key"}
    result = _run(
        manifest,
        env,
        "--panel-artifact-dir",
        str(artifact_dir),
        "--site",
        "implement Step 5",
        "--model-role",
        "vote",
        "--codex-present",
        "false",
        "--cursor-present",
        "true",
    )
    assert result.returncode == 0, result.stderr
    tsv = artifact_dir / "panel-prompt-sizes.tsv"
    assert tsv.is_file()
    rows = _tsv_rows(tsv)
    assert len(rows) >= 1
    assert rows[0]["slot_kind"] == "voter"
# pyright: reportUnknownArgumentType=false, reportUnknownVariableType=false
