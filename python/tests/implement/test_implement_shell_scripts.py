"""Offline harness parity for implement shell helper scripts.

Adapter/bgjob behavior for Step 5/6/checks lives in python/tests/bgjob/test_bgjob_adapt.py,
python/tests/implement/test_implement_dispatch.py, test_run_step_checks.py, and
test_step_6_entry.py — this module ports only the Bash harness assertions.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from tests.support.repo_contract import repo_root

_REPO = repo_root()
_IMPLEMENT_SCRIPTS = _REPO / "skills" / "implement" / "scripts"
_STEP8_HELPER = _IMPLEMENT_SCRIPTS / "step-8-ship.sh"
_STEP8_GUARD = _IMPLEMENT_SCRIPTS / "step-8-python-guard.sh"
_STEP8_SEEDER = _IMPLEMENT_SCRIPTS / "step-8-seed-initial.sh"
_STEP18_HELPER = _IMPLEMENT_SCRIPTS / "step-18.sh"
_CLI = _REPO / "python" / "cli.py"
_REAL_PYTHON = sys.executable
_BASH = shutil.which("bash") or "/bin/bash"

_STEP5_WRAPPERS = (
    "step-5-review.sh",
    "step-5-resume.sh",
    "step-6-entry.sh",
    "run-step-checks.sh",
)

_STEP8_HELPER_STATIC_PINS: tuple[tuple[str, str, bool], ...] = (
    ("bgjob adapt", "static: foreground wrapper delegates to bgjob adapter", True),
    ('STEP="implement-step8-ship"', "static: bgjob step slug pinned", True),
    ("--budget-s 21600", "static: bgjob budget pins Step 8 timeout", True),
    ("--replace-completed-result", "static: reship replaces completed result", True),
    ('--result-env-path "$MERGE_RESULT_ENV"', "static: child passes direct result env to ship", True),
    ("bgjob start", "static: direct bgjob start retired", False),
    ("persist_handoff", "static: sidecar handoff writer retired", False),
    ("stdout-capture", "static: stdout capture retired", False),
    ("tee -a", "static: stdout tee retired", False),
    ("step-8-ship-handoff", "static: rc and JSON sidecars retired", False),
    ('python/cli.py" implement clone-tag', "static: clone-tag CLI invoked", True),
    ("step-8-python-guard.sh", "static: shared python guard invoked", True),
    (
        'python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" git phantom-probe --step 8-pre-ship >&2',
        "static: bundled phantom probe redirects stdout",
        True,
    ),
    ('python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" ship pr', "static: python ship CLI invoked", True),
    ('--state-file "$IMPLEMENT_TMPDIR/ship-pr-state.sh"', "static: state file forwarded", True),
    ("run_in_background", "static: helper prose/code no legacy background literal", False),
    ("printf 'PID=%s", "static: legacy bg-wait marker writer removed", False),
)

_STEP8_SEEDER_STATIC_PINS: tuple[tuple[str, str, bool], ...] = (
    ("ship seed-initial-state", "static: seeder wrapper delegates to Python seeder", True),
    ('session read-key --file "$file"', "static: seeder reads session keys through python cli", True),
    ("read-session-env-key.sh", "static: retired session reader absent", False),
    ('python/cli.py" implement clone-tag', "static: seeder invokes clone-tag CLI", True),
)

_STEP18_STUB_CLI = """\
#!/usr/bin/env python3
import os
import sys
from pathlib import Path


def log(message: str) -> None:
    path = os.environ.get("STEP18_STUB_LOG")
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(message + "\\n")


def read_key(args: list[str]) -> int:
    file_path = Path(args[args.index("--file") + 1])
    key = args[args.index("--key") + 1]
    default = args[args.index("--default") + 1] if "--default" in args else ""
    fail_key = os.environ.get("STEP18_STUB_READ_KEY_FAIL_KEY") or ""
    if fail_key and key == fail_key:
        return 6
    try:
        for line in file_path.read_text(encoding="utf-8").splitlines():
            if line.startswith(key + "="):
                print(line.split("=", 1)[1])
                return 0
    except OSError:
        pass
    print(default)
    return 0


def kv_get(args: list[str]) -> int:
    # Minimal stub for cli.py kv get used by step-18.sh kv_value().
    key = args[args.index("--key") + 1]
    file_path = Path(args[args.index("--file") + 1]) if "--file" in args else None
    try:
        text = file_path.read_text(encoding="utf-8") if file_path is not None else sys.stdin.read()
    except OSError:
        return 1
    for line in text.splitlines():
        if line.startswith(key + "="):
            print(line.split("=", 1)[1])
            return 0
    return 1


def step18b(args: list[str]) -> int:
    tmp = Path(args[args.index("--implement-tmpdir") + 1])
    sentinel = "true" if (tmp / ".step17-emitted").exists() else "false"
    log(f"step18b sentinel={sentinel} argv={' '.join(sys.argv[1:])}")
    if (os.environ.get("STEP18_STUB_WRITE_SUMMARY") or "true") == "true":
        (tmp / "summary-final.md").write_text((os.environ.get("STEP18_STUB_BODY") or "# Final body\\n"), encoding="utf-8")
    if (os.environ.get("STEP18_STUB_REMOVE_SUMMARY") or "false") == "true":
        with open(tmp / "summary-final.md", "w", encoding="utf-8") as handle:
            handle.write((os.environ.get("STEP18_STUB_BODY") or "# Final body\\n"))
        os.unlink(tmp / "summary-final.md")
    emit = (os.environ.get("STEP18_STUB_EMIT_BODY") or "true")
    rc = int((os.environ.get("STEP18_STUB_WFR_RC") or "0"))
    print(f"EMIT_BODY={emit}")
    print(f"WFR_RC={rc}")
    print(f"STEP17_EMITTED_PRESENT={sentinel}")
    print("SNAPSHOT_OK=true")
    return rc


def teardown(args: list[str]) -> int:
    tmp = Path(args[args.index("--implement-tmpdir") + 1])
    state = args[args.index("--state-file") + 1]
    expected = str(tmp / "finalize-state.sh")
    if Path(state) != (tmp / "finalize-state.sh"):
        print(f"bad state file {state} expected {expected}", file=sys.stderr)
        return 9
    marker = "before" if (tmp / ".step17-emitted").exists() else "missing"
    log(f"teardown sentinel={marker} argv={' '.join(sys.argv[1:])}")
    print("ISSUE_URL=https://example.test/issues/1")
    print("RENAME_BRANCH=skipped")
    print("RENAME_STATUS=ok")
    print("STASH_REF=refs/stash/test")
    print("SENTINEL_WRITTEN=true")
    print("FINALIZE_SUBCOMMAND=teardown")
    print("FINALIZE_WARNINGS=none")
    return 0


def main() -> int:
    args = sys.argv[1:]
    if args[:2] == ["session", "read-key"]:
        return read_key(args[2:])
    if args[:2] == ["kv", "get"]:
        return kv_get(args[2:])
    if args[:2] == ["final-report", "step18b"]:
        return step18b(args[2:])
    if args[:2] == ["run-log", "append-failure"]:
        log("append-failure " + " ".join(args[2:]))
        return 0
    if args[:2] == ["token", "report"]:
        log("token report")
        return 0
    if args[:2] == ["timing", "report"]:
        log("timing report")
        return 0
    if args[:2] == ["token", "mark"]:
        log("token mark " + " ".join(args[2:]))
        return 0
    if args[:2] == ["timing", "mark"]:
        log("timing mark " + " ".join(args[2:]))
        return 0
    if args[:2] == ["execution-issues", "flush-safety-net"]:
        log("flush-safety-net " + " ".join(args[2:]))
        return 0
    if args[:2] == ["run-log", "capture-transcript"]:
        log("capture-transcript " + " ".join(args[2:]))
        print("SESSION_TRANSCRIPT_STATUS=captured")
        return 0
    if args[:2] == ["session", "restore-finalize-state"]:
        log("restore-finalize-state " + " ".join(args[2:]))
        return 0
    if args[:2] == ["session", "clear-implement-pointer"]:
        log("clear-implement-pointer " + " ".join(args[2:]))
        return 0
    if args[:2] == ["implement-finalize", "teardown"]:
        return teardown(args[2:])
    print("unexpected argv: " + " ".join(args), file=sys.stderr)
    return 8


if __name__ == "__main__":
    raise SystemExit(main())
"""

_REVIEW_CORE_STUB = """\
#!/usr/bin/env bash
set -euo pipefail
: "${CORE_CAPTURE_FILE:?}"
printf 'REVIEW_CORE_ARGV' >> "$CORE_CAPTURE_FILE"
printf ' %q' "$@" >> "$CORE_CAPTURE_FILE"
printf '\\n' >> "$CORE_CAPTURE_FILE"
out=""
session_env=""
round="1"
panel=""
tier=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output-dir) out="$2"; shift 2 ;;
        --session-env-path) session_env="$2"; shift 2 ;;
        --round-num) round="$2"; shift 2 ;;
        --panel) panel="$2"; shift 2 ;;
        --tier) tier="$2"; shift 2 ;;
        --mode|--diff-file|--plan-file|--feature-file|--run-id|--commit-count|--dynamic-archetypes|--codex-available|--cursor-available|--escalated-round|--prune-ledger|--site) shift 2 ;;
        *) shift; [[ $# -gt 0 && "$1" != --* ]] && shift || true ;;
    esac
done
case "$tier" in
    TRIVIAL) panel_shape="singles"; effective_cap="2" ;;
    MODERATE) panel_shape="pairs"; effective_cap="2" ;;
    HARD) panel_shape="pairs"; effective_cap="2" ;;
    *) panel_shape="unknown"; effective_cap="0" ;;
esac
mkdir -p "$out"
printf 'SESSION_ENV_PATH=%s\\n' "$session_env" >> "$CORE_CAPTURE_FILE"
printf 'PANEL_ARG=%s\\n' "$panel" >> "$CORE_CAPTURE_FILE"
printf 'TIER_ARG=%s\\n' "$tier" >> "$CORE_CAPTURE_FILE"
printf 'ROUND_ARG=%s\\n' "$round" >> "$CORE_CAPTURE_FILE"
printf 'LARCH_TOKEN_SESSION_ID=%s\\n' "${LARCH_TOKEN_SESSION_ID:-}" >> "$CORE_CAPTURE_FILE"
printf 'LARCH_CLAUDE_SOURCE_FILE=%s\\n' "${LARCH_CLAUDE_SOURCE_FILE:-}" >> "$CORE_CAPTURE_FILE"
printf 'LARCH_TIMING_LEDGER=%s\\n' "${LARCH_TIMING_LEDGER:-}" >> "$CORE_CAPTURE_FILE"
: > "$out/accepted-findings.md"
: > "$out/rejected-findings.md"
: > "$out/oos-accepted-review.md"
printf '# Review Round %s\\n' "$round" > "$out/review-round-summary.md"
printf '{"schema_version":1,"rounds_completed":%s,"accepted_count":0,"rejected_count":0}\\n' "$round" > "$out/review-summary.json"
printf 'REVIEW_CORE_STATUS=zero-findings\\nROUND_NUM=%s\\nACCEPTED_COUNT=0\\nREJECTED_COUNT=0\\nACCEPTED_FINDINGS_FILE=%s/accepted-findings.md\\nREJECTED_FINDINGS_FILE=%s/rejected-findings.md\\nPANEL_MODE=normal\\nPANEL_SHAPE=%s\\nPANEL_TIER=%s\\nEFFECTIVE_ROUND_CAP=%s\\n' "$round" "$out" "$out" "$panel_shape" "$tier" "$effective_cap"
"""


def _wrapper_source(name: str) -> str:
    return (_IMPLEMENT_SCRIPTS / name).read_text(encoding="utf-8")


def _run_bash(
    script: Path,
    *,
    env: Mapping[str, str] | None = None,
    args: Sequence[str] = (),
) -> subprocess.CompletedProcess[str]:
    run_env = os.environ.copy()
    if env is not None:
        run_env.update(env)
    return subprocess.run(
        [_BASH, str(script), *args],
        env=run_env,
        text=True,
        capture_output=True,
        check=False,
    )


def _kv(key: str, text: str) -> str:
    prefix = f"{key}="
    for line in text.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :]
    return ""


def _line_no(needle: str, text: str) -> int | None:
    for index, line in enumerate(text.splitlines(), start=1):
        if needle in line:
            return index
    return None


def _count_literal(needle: str, text: str) -> int:
    return sum(1 for line in text.splitlines() if needle in line)


def _write_executable(path: Path, body: str) -> None:
    _ = path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


def _prepend_path(env: dict[str, str], stub_bin: Path) -> None:
    system_path = os.pathsep.join(
        part for part in (str(stub_bin), "/bin", "/usr/bin", env.get("PATH", "")) if part
    )
    env["PATH"] = system_path


def _make_step8_impl(tmp_path: Path, name: str = "implement") -> Path:
    impl = tmp_path / name
    bgjob = impl / "bgjob"
    bgjob.mkdir(parents=True)
    _ = (impl / "ship-pr-state.sh").write_text(
        "BRANCH_NAME=test-branch\n"
        "ISSUE_NUMBER=42\n"
        "RUN_ID=run-ship-guard\n"
        "REPO=owner/repo\n"
        "MANIFEST_PATH=/tmp/manifest.json\n"
        "NO_ADMIN_FALLBACK=true\n"
        "NO_LOGS_COMMIT=true\n",
        encoding="utf-8",
    )
    _ = (impl / "plugin-root.env").write_text(
        f"export CLAUDE_PLUGIN_ROOT={_REPO}\n",
        encoding="utf-8",
    )
    _ = (impl / "session-id").write_text("session-id\n", encoding="utf-8")
    order_file = tmp_path / "order.txt"
    larch_run = impl / "larch-run.sh"
    _write_executable(
        larch_run,
        f"""#!/usr/bin/env bash
set -euo pipefail
case "$1" in
  skills/implement/scripts/step-8-python-guard.sh) printf '%s\\n' guard >> "{order_file}"; exit 0 ;;
  *) exec bash "{_REPO}/$1" "${{@:2}}" ;;
esac
""",
    )
    return impl


def _step8_env(impl: Path) -> dict[str, str]:
    return {
        "IMPLEMENT_TMPDIR": str(impl),
        "CLAUDE_PLUGIN_ROOT": str(_REPO),
        "PYTHONPATH": str(_REPO / "python"),
    }


def _write_python3_stub(stub_bin: Path, body: str) -> None:
    _write_executable(stub_bin / "python3", body)


def _run_step8(
    impl: Path,
    stub_bin: Path,
    *,
    args: Sequence[str] = (),
) -> subprocess.CompletedProcess[str]:
    env = _step8_env(impl)
    _prepend_path(env, stub_bin)
    return _run_bash(_STEP8_HELPER, env=env, args=args)


@pytest.mark.parametrize("wrapper", _STEP5_WRAPPERS, ids=_STEP5_WRAPPERS)
def test_step5_wrapper_shape_set_euo_pipefail(wrapper: str) -> None:
    assert "set -euo pipefail" in _wrapper_source(wrapper)


@pytest.mark.parametrize("wrapper", _STEP5_WRAPPERS, ids=_STEP5_WRAPPERS)
def test_step5_wrapper_shape_exec_python_implement(wrapper: str) -> None:
    assert 'exec python3 "$PLUGIN_ROOT/python/cli.py" implement' in _wrapper_source(wrapper)


@pytest.mark.parametrize("wrapper", _STEP5_WRAPPERS, ids=_STEP5_WRAPPERS)
def test_step5_wrapper_shape_no_bgjob_start(wrapper: str) -> None:
    assert "bgjob start" not in _wrapper_source(wrapper)


@pytest.mark.parametrize("wrapper", _STEP5_WRAPPERS, ids=_STEP5_WRAPPERS)
def test_step5_wrapper_shape_no_registry(wrapper: str) -> None:
    assert "registry" not in _wrapper_source(wrapper)


@pytest.mark.parametrize(
    ("needle", "label", "should_contain"),
    _STEP8_HELPER_STATIC_PINS,
    ids=[label for _needle, label, _should in _STEP8_HELPER_STATIC_PINS],
)
def test_step8_helper_static_pin(needle: str, label: str, should_contain: bool) -> None:
    text = _STEP8_HELPER.read_text(encoding="utf-8")
    if should_contain:
        assert needle in text, label
    else:
        assert needle not in text, label


@pytest.mark.parametrize(
    ("needle", "label", "should_contain"),
    _STEP8_SEEDER_STATIC_PINS,
    ids=[label for _needle, label, _should in _STEP8_SEEDER_STATIC_PINS],
)
def test_step8_seeder_static_pin(needle: str, label: str, should_contain: bool) -> None:
    text = _STEP8_SEEDER.read_text(encoding="utf-8")
    if should_contain:
        assert needle in text, label
    else:
        assert needle not in text, label


def test_step8_dynamic_foreground_launcher_fresh_start(tmp_path: Path) -> None:
    impl = _make_step8_impl(tmp_path)
    stub_bin = tmp_path / "bin"
    stub_bin.mkdir()
    capture = tmp_path / "bgjob-adapt-argv.txt"
    _write_python3_stub(
        stub_bin,
        f"""#!/usr/bin/env bash
if [ "$1" = "{_CLI}" ] && [ "$2" = "bgjob" ] && [ "$3" = "adapt" ]; then
  printf '%s\\n' "$@" > "{capture}"
  printf '%s\\n' 'BGJOB_STATUS=STARTED STEP=implement-step8-ship PGID=12345'
  exit 0
fi
exec "{_REAL_PYTHON}" "$@"
""",
    )
    result = _run_step8(impl, stub_bin)
    argv = capture.read_text(encoding="utf-8")
    assert result.returncode == 0, "dynamic: foreground launcher exits 0 on bgjob adapt"
    assert result.stdout == "BGJOB_STATUS=STARTED STEP=implement-step8-ship PGID=12345\n", (
        "dynamic: foreground launcher stdout is exact bgjob adapter line"
    )
    assert "--step\nimplement-step8-ship" in argv, "dynamic: bgjob adapter step forwarded"
    assert "--replace-completed-result" in argv, "dynamic: adapter replaces result for a reship"
    assert "--bgjob-child" not in argv, "dynamic: adapter owns child control arguments"


def test_step8_dynamic_child_guard_phantom_driver_order(tmp_path: Path) -> None:
    impl = _make_step8_impl(tmp_path)
    stub_bin = tmp_path / "bin"
    stub_bin.mkdir()
    order_file = tmp_path / "order.txt"
    ship_argv = tmp_path / "ship-argv.txt"
    merge_env = impl / "bgjob" / "implement-step8-ship.merge.env"
    merge_env.unlink(missing_ok=True)
    _ = order_file.write_text("", encoding="utf-8")
    _write_python3_stub(
        stub_bin,
        f"""#!/usr/bin/env bash
if [ "$1" = "{_CLI}" ] && [ "$2" = "implement" ] && [ "$3" = "clone-tag" ]; then
  printf '%s\\n' 'CLONE_TAG_FULL=stub'
  printf '%s\\n' 'EXPECTED_TMPDIR_BASENAME_PREFIX=claude-implement-stub-'
  exit 0
fi
if [ "$1" = "{_CLI}" ] && [ "$2" = "git" ] && [ "$3" = "phantom-probe" ]; then
  printf '%s\\n' phantom >> "{order_file}"
  printf '%s\\n' 'PHANTOM_STATUS=clean'
  exit 0
fi
if [ "$1" = "{_CLI}" ] && [ "$2" = "ship" ] && [ "$3" = "pr" ]; then
  printf '%s\\n' driver >> "{order_file}"
  printf '%s\\n' "$@" > "{ship_argv}"
  printf '%s\\n' '{{"outcome":"NEEDS_USER_INPUT","needs_user_reason":"oos-filing"}}'
  exit 3
fi
exec "{_REAL_PYTHON}" "$@"
""",
    )
    result = _run_step8(
        impl,
        stub_bin,
        args=["--bgjob-child", "--merge-result-env", str(merge_env)],
    )
    assert result.returncode == 3, "dynamic: child preserves the ship driver's route rc"
    assert order_file.read_text(encoding="utf-8") == "guard\nphantom\ndriver\n", (
        "dynamic: child runs guard then phantom then driver"
    )
    assert "PHANTOM_STATUS=clean" in result.stderr, "dynamic: phantom stdout redirected to stderr"
    assert '"needs_user_reason":"oos-filing"' in result.stdout, "dynamic: child forwards driver JSON"
    ship_text = ship_argv.read_text(encoding="utf-8")
    assert "--branch" in ship_text, "dynamic: child forwards branch flag"
    assert "test-branch" in ship_text, "dynamic: child forwards branch value"
    assert "--result-env-path" in ship_text, "dynamic: child forwards direct result env flag"
    assert str(merge_env) in ship_text, "dynamic: child forwards adapter merge-result env"
    assert not (impl / ".step-8-ship-handoff.rc").exists(), "dynamic: retired rc sidecar remains absent"
    assert not (impl / ".step-8-ship-handoff.json").exists(), "dynamic: retired JSON sidecar remains absent"


def test_step8_guard_stale_python(tmp_path: Path) -> None:
    impl = _make_step8_impl(tmp_path)
    stub_bin = tmp_path / "bin"
    stub_bin.mkdir()
    _write_python3_stub(
        stub_bin,
        f"""#!/usr/bin/env bash
if [ "$1" = "-c" ]; then exit 1; fi
exec "{_REAL_PYTHON}" "$@"
""",
    )
    env = _step8_env(impl)
    _prepend_path(env, stub_bin)
    result = _run_bash(_STEP8_GUARD, env=env)
    assert result.returncode == 4, "guard: stale python exits 4"
    assert "ERROR: Python ship driver requires Python 3.11 or newer" in result.stderr, (
        "guard: stale python emits stderr"
    )
    assert '"outcome":"STALLED"' in result.stdout, "guard: stale python emits STALLED JSON"


def test_step8_guard_new_python(tmp_path: Path) -> None:
    impl = _make_step8_impl(tmp_path)
    stub_bin = tmp_path / "bin"
    stub_bin.mkdir()
    _write_python3_stub(
        stub_bin,
        f"""#!/usr/bin/env bash
if [ "$1" = "-c" ]; then exit 0; fi
exec "{_REAL_PYTHON}" "$@"
""",
    )
    env = _step8_env(impl)
    _prepend_path(env, stub_bin)
    result = _run_bash(_STEP8_GUARD, env=env)
    assert result.returncode == 0, "guard: new python exits 0"
    assert result.stdout == "", "guard: new python stdout empty"


def test_step8_child_setup_failure_does_not_write_handoff_sidecars(tmp_path: Path) -> None:
    impl = _make_step8_impl(tmp_path)
    stub_bin = tmp_path / "bin"
    stub_bin.mkdir()
    merge_env = impl / "bgjob" / "implement-step8-ship.merge.env"
    _ = (impl / "ship-pr-state.sh").write_text(
        "RUN_ID=run-ship-guard\nREPO=owner/repo\n",
        encoding="utf-8",
    )
    _write_python3_stub(
        stub_bin,
        f"""#!/usr/bin/env bash
if [ "$1" = "-c" ]; then exit 0; fi
exec "{_REAL_PYTHON}" "$@"
""",
    )
    result = _run_step8(
        impl,
        stub_bin,
        args=["--bgjob-child", "--merge-result-env", str(merge_env)],
    )
    assert result.returncode == 2, "child: require_value setup failure exits 2"
    assert not (impl / ".step-8-ship-handoff.rc").exists(), "child: rc sidecar is retired"
    assert not (impl / ".step-8-ship-handoff.json").exists(), "child: JSON sidecar is retired"
    assert result.stdout == "", "child: setup failure stdout empty"


def test_step8_clone_cli_derives_sanitized_prefix_from_pwd(tmp_path: Path) -> None:
    spaced = tmp_path / "repo with spaces"
    spaced.mkdir()
    pwd = str(spaced.resolve())
    result = subprocess.run(
        [_REAL_PYTHON, str(_CLI), "implement", "clone-tag"],
        cwd=spaced,
        env={
            **os.environ,
            "PYTHONPATH": str(_REPO / "python"),
            "CLAUDE_PLUGIN_ROOT": str(_REPO),
            "CLONE_TAG": "",
            "PWD": pwd,
        },
        text=True,
        capture_output=True,
        check=False,
    )
    assert "EXPECTED_TMPDIR_BASENAME_PREFIX=claude-implement-repo_with_spaces-" in result.stdout, (
        "clone CLI: derives sanitized prefix from PWD"
    )


def test_step8_seeder_argv_forwarding(tmp_path: Path) -> None:
    seed_tmp = tmp_path / "seed"
    codex_out = seed_tmp / "codex-step2-out"
    codex_out.mkdir(parents=True)
    _ = (seed_tmp / "plugin-root.env").write_text(
        f"export CLAUDE_PLUGIN_ROOT={_REPO}\n",
        encoding="utf-8",
    )
    _ = (seed_tmp / "bootstrap-routing.env").write_text(
        "coder=codex\nBRANCH_NAME=seed-branch\nISSUE_NUMBER=77\nRUN_ID=run-seed\nREPO=owner/repo\nDEFERRED=true\n",
        encoding="utf-8",
    )
    _ = (seed_tmp / "session-env.sh").write_text(
        "LARCH_RUN_ID=run-session\nREPO=owner/session\nFORKED_TARGET=false\n",
        encoding="utf-8",
    )
    _ = (seed_tmp / "ship-seed-input.env").write_text(
        f"MERGE=true\nDRAFT=true\nNO_ADMIN_FALLBACK=true\nNO_LOGS_COMMIT=true\nMANIFEST_PATH={codex_out}/manifest.json\n",
        encoding="utf-8",
    )
    _ = (codex_out / "manifest.json").write_text('{"summary_bullets":["x"]}\n', encoding="utf-8")
    _ = (seed_tmp / "session-id").write_text("seed-session\n", encoding="utf-8")
    stub_bin = tmp_path / "bin"
    stub_bin.mkdir()
    seed_argv = tmp_path / "seed-argv.txt"
    _write_python3_stub(
        stub_bin,
        f"""#!/usr/bin/env bash
if [ "$1" = "{_CLI}" ] && [ "$2" = "implement" ] && [ "$3" = "clone-tag" ]; then
  printf '%s\\n' 'CLONE_TAG_FULL=seedstub'
  printf '%s\\n' 'EXPECTED_TMPDIR_BASENAME_PREFIX=claude-implement-seedstub-'
  exit 0
fi
if [ "$1" = "{_CLI}" ] && [ "$2" = "session" ] && [ "$3" = "read-key" ]; then
  file=""; key=""; default=""
  while [ "$#" -gt 0 ]; do
    case "$1" in --file) file=$2; shift 2 ;; --key) key=$2; shift 2 ;; --default) default=$2; shift 2 ;; *) shift ;; esac
  done
  value=$(grep "^${{key}}=" "$file" 2>/dev/null | head -n 1 | cut -d= -f2- || true)
  printf '%s\\n' "${{value:-$default}}"
  exit 0
fi
if [ "$1" = "{_CLI}" ] && [ "$2" = "ship" ] && [ "$3" = "seed-initial-state" ]; then
  printf '%s\\n' "$@" > "{seed_argv}"
  exit 0
fi
exec "{_REAL_PYTHON}" "$@"
""",
    )
    env = {
        "IMPLEMENT_TMPDIR": str(seed_tmp),
        "CLAUDE_PLUGIN_ROOT": str(_REPO),
        "PYTHONPATH": str(_REPO / "python"),
    }
    _prepend_path(env, stub_bin)
    result = _run_bash(_STEP8_SEEDER, env=env, args=["--merge", "false", "--draft", "false"])
    assert result.returncode == 0
    argv = seed_argv.read_text(encoding="utf-8")
    assert "--branch\nseed-branch" in argv, "seeder: branch from bootstrap routing"
    assert "--issue\n77" in argv, "seeder: issue from bootstrap routing"
    assert "--run-id\nrun-seed" in argv, "seeder: run id from bootstrap routing"
    assert "--manifest-path" in argv, "seeder: manifest path forwarded"
    assert "--no-admin-fallback\ntrue" in argv, "seeder: no-admin from ship-seed-input"
    assert "--no-logs-commit\ntrue" in argv, "seeder: no-logs from ship-seed-input"
    assert "--merge\nfalse" in argv, "seeder: stall/argv merge override precedence"
    assert "--draft\nfalse" in argv, "seeder: stall/argv draft override precedence"
    assert "--expected-tmpdir-basename-prefix" in argv, "seeder: shared prefix forwarded"
    assert "claude-implement-seedstub-" in argv, "seeder: clone-tag CLI prefix forwarded"


def test_step8_symlinked_bgjob_directory_rejected(tmp_path: Path) -> None:
    impl = tmp_path / "implement-symlink-bgjob"
    real_bgjob = tmp_path / "real-bgjob"
    real_bgjob.mkdir()
    impl.mkdir()
    (impl / "bgjob").symlink_to(real_bgjob)
    _ = (impl / "ship-pr-state.sh").write_text("RUN_ID=r\nREPO=o/r\n", encoding="utf-8")
    stub_bin = tmp_path / "bin"
    stub_bin.mkdir()
    _write_python3_stub(stub_bin, f'#!/usr/bin/env bash\nexec "{_REAL_PYTHON}" "$@"\n')
    result = _run_step8(impl, stub_bin)
    assert result.returncode == 2
    assert result.stdout == "BGJOB_ERROR=invalid-input\n"


def test_step8_symlinked_result_env_rejected(tmp_path: Path) -> None:
    impl = _make_step8_impl(tmp_path, "implement-symlink-result")
    target = tmp_path / "result-target.env"
    _ = target.write_text("BGJOB_RC=0\n", encoding="utf-8")
    result_env = impl / "bgjob" / "implement-step8-ship.result.env"
    result_env.symlink_to(target)
    stub_bin = tmp_path / "bin"
    stub_bin.mkdir()
    _write_python3_stub(stub_bin, f'#!/usr/bin/env bash\nexec "{_REAL_PYTHON}" "$@"\n')
    result = _run_step8(impl, stub_bin)
    assert result.returncode == 2
    assert result.stdout == "BGJOB_ERROR=unsafe-path\n"


def test_step8_child_passes_merge_result_env_to_ship(tmp_path: Path) -> None:
    impl = _make_step8_impl(tmp_path, "implement-symlink-merge")
    merge_target = tmp_path / "merge-target.env"
    _ = merge_target.write_text("old\n", encoding="utf-8")
    merge_env = impl / "bgjob" / "implement-step8-ship.merge.env"
    merge_env.symlink_to(merge_target)
    stub_bin = tmp_path / "bin"
    stub_bin.mkdir()
    _write_python3_stub(
        stub_bin,
        f"""#!/usr/bin/env bash
if [ "$1" = "{_CLI}" ] && [ "$2" = "implement" ] && [ "$3" = "clone-tag" ]; then
  printf '%s\\n' 'CLONE_TAG_FULL=stub'
  printf '%s\\n' 'EXPECTED_TMPDIR_BASENAME_PREFIX=claude-implement-stub-'
  exit 0
fi
if [ "$1" = "{_CLI}" ] && [ "$2" = "git" ] && [ "$3" = "phantom-probe" ]; then
  printf '%s\\n' 'PHANTOM_STATUS=clean'
  exit 0
fi
if [ "$1" = "{_CLI}" ] && [ "$2" = "ship" ] && [ "$3" = "pr" ]; then
  printf '%s\\n' '{{"outcome":"NEEDS_USER_INPUT"}}'
  exit 3
fi
exec "{_REAL_PYTHON}" "$@"
""",
    )
    result = _run_step8(
        impl,
        stub_bin,
        args=["--bgjob-child", "--merge-result-env", str(merge_env)],
    )
    assert result.returncode == 3
    assert merge_target.read_text(encoding="utf-8") == "old\n"


def _make_step18_plugin(tmp_path: Path) -> Path:
    plugin = tmp_path / "plugin"
    python_dir = plugin / "python"
    python_dir.mkdir(parents=True)
    cli = python_dir / "cli.py"
    _write_executable(cli, _STEP18_STUB_CLI)
    return plugin


def _make_step18_impl(tmp_path: Path, name: str) -> Path:
    impl = tmp_path / name
    impl.mkdir()
    _ = (impl / "session-env.sh").write_text(
        f"LARCH_RUN_ID=RUN1\nLARCH_TOKEN_SESSION_ID=tok\n"
        f"LARCH_CLAUDE_SOURCE_FILE=source.jsonl\n"
        f"LARCH_TIMING_LEDGER={impl}/timing-ledger.tsv\n"
        "STALL_TRACKING=false\n",
        encoding="utf-8",
    )
    _ = (impl / "ship-pr-state.sh").write_text(
        "STALL_TRACKING=false\nBAIL_NEEDS_USER_INPUT=false\nSTALL_STEP=\n",
        encoding="utf-8",
    )
    _ = (impl / "finalize-state.sh").write_text(
        "STALL_TRACKING=false\nSTALL_STEP=\n",
        encoding="utf-8",
    )
    return impl


def _run_step18(
    tmp_path: Path,
    impl: Path,
    plugin: Path,
    *,
    out_path: Path,
    log_path: Path,
    args: Sequence[str],
    extra_env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    fakebin = tmp_path / "fakebin"
    fakebin.mkdir(exist_ok=True)
    cat_stub = fakebin / "cat"
    _write_executable(
        cat_stub,
        """#!/usr/bin/env bash
if [ "${STEP18_STUB_CAT_FAIL:-false}" = true ]; then
  case "${1:-}" in
    *summary-final.md) exit 1 ;;
  esac
fi
exec /bin/cat "$@"
""",
    )
    env = {
        "IMPLEMENT_TMPDIR": str(impl),
        "CLAUDE_PLUGIN_ROOT": str(plugin),
        "STEP18_STUB_LOG": str(log_path),
        "PATH": f"{fakebin}{os.pathsep}{os.environ.get('PATH', '')}",
    }
    if extra_env:
        env.update(extra_env)
    result = _run_bash(_STEP18_HELPER, env=env, args=args)
    _ = out_path.write_text(result.stdout, encoding="utf-8")
    _ = (out_path.with_suffix(".out.err")).write_text(result.stderr, encoding="utf-8")
    return result


def test_step18_gate_clear(tmp_path: Path) -> None:
    plugin = _make_step18_plugin(tmp_path)
    impl = _make_step18_impl(tmp_path, "gate-clear")
    out = tmp_path / "gate-clear.out"
    log = tmp_path / "gate-clear.log"
    result = _run_step18(
        tmp_path,
        impl,
        plugin,
        out_path=out,
        log_path=log,
        args=["--phase", "gate", "--stall-tracking-memory", "false"],
    )
    assert result.returncode == 0
    text = result.stdout
    assert "STALL_TRACKING_MEMORY=false" in text, "gate clear memory KV"
    assert "STALL_TRACKING_DISK=false" in text, "gate clear disk KV"
    assert "STALL_TRACKING_FINALIZE=false" in text, "gate clear finalize KV"
    assert "STALL_TRACKING_SESSION=false" in text, "gate clear session KV"
    assert "STALL_RECOVERY_REQUIRED=false" in text, "gate clear recovery KV"
    assert "⏩ 18a: stall recovery — no stall detected" in text, "gate clear breadcrumb"
    assert not log.exists(), "gate clear should not invoke finalize stubs"


def test_step18_gate_stall(tmp_path: Path) -> None:
    plugin = _make_step18_plugin(tmp_path)
    impl = _make_step18_impl(tmp_path, "gate-stall")
    _ = (impl / "ship-pr-state.sh").write_text("STALL_TRACKING=maybe\n", encoding="utf-8")
    out = tmp_path / "gate-stall.out"
    log = tmp_path / "gate-stall.log"
    result = _run_step18(
        tmp_path,
        impl,
        plugin,
        out_path=out,
        log_path=log,
        args=["--phase", "gate", "--stall-tracking-memory", "false"],
    )
    assert result.returncode == 0
    text = result.stdout
    assert "STALL_TRACKING_DISK=maybe" in text, "gate stall disk KV"
    assert "STALL_RECOVERY_REQUIRED=true" in text, "gate stall recovery KV"
    assert not log.exists(), "gate stall should not invoke finalize stubs"


@pytest.mark.parametrize("value", ["", "false"], ids=["empty", "false"])
def test_step18_gate_predicate_inactive(tmp_path: Path, value: str) -> None:
    plugin = _make_step18_plugin(tmp_path)
    name = f"pred-inactive-{value or 'empty'}"
    impl = _make_step18_impl(tmp_path, name)
    out = tmp_path / f"{name}.out"
    log = tmp_path / f"{name}.log"
    result = _run_step18(
        tmp_path,
        impl,
        plugin,
        out_path=out,
        log_path=log,
        args=["--phase", "gate", "--stall-tracking-memory", value],
    )
    assert result.returncode == 0
    assert _kv("STALL_RECOVERY_REQUIRED", result.stdout) == "false", f"predicate inactive {value}"


@pytest.mark.parametrize("value", ["true", "1", "yes", "arbitrary"], ids=["true", "1", "yes", "arbitrary"])
def test_step18_gate_predicate_active(tmp_path: Path, value: str) -> None:
    plugin = _make_step18_plugin(tmp_path)
    impl = _make_step18_impl(tmp_path, f"pred-active-{value}")
    out = tmp_path / f"pred-active-{value}.out"
    log = tmp_path / f"pred-active-{value}.log"
    result = _run_step18(
        tmp_path,
        impl,
        plugin,
        out_path=out,
        log_path=log,
        args=["--phase", "gate", "--stall-tracking-memory", value],
    )
    assert result.returncode == 0
    assert _kv("STALL_RECOVERY_REQUIRED", result.stdout) == "true", f"predicate active {value}"


def test_step18_finalize_body_and_teardown(tmp_path: Path) -> None:
    plugin = _make_step18_plugin(tmp_path)
    impl = _make_step18_impl(tmp_path, "finalize-body")
    out = tmp_path / "finalize-body.out"
    log = tmp_path / "finalize-body.log"
    result = _run_step18(
        tmp_path,
        impl,
        plugin,
        out_path=out,
        log_path=log,
        args=["--phase", "finalize", "--step17-emitted", "false"],
        extra_env={"STEP18_STUB_BODY": "# Final body\nDetails\n"},
    )
    assert result.returncode == 0
    text = result.stdout
    assert "STALL_RECOVERY_REQUIRED" not in text, "finalize body stdout"
    assert _count_literal("---LARCH-SUMMARY-FINAL-BEGIN---", text) == 1, (
        "finalize body begin marker count"
    )
    assert _count_literal("---LARCH-SUMMARY-FINAL-END---", text) == 1, (
        "finalize body end marker count"
    )
    assert "# Final body" in text, "finalize body marker content"
    assert _count_literal("# Final body", text) == 1, "finalize body raw duplicate check"
    assert "ISSUE_URL=https://example.test/issues/1" in text, "teardown issue tail relay"
    assert "RENAME_BRANCH=skipped" in text, "teardown rename tail relay"
    assert "RENAME_STATUS=ok" in text, "teardown rename status relay"
    assert "STASH_REF=refs/stash/test" in text, "teardown stash relay"
    assert "SENTINEL_WRITTEN=true" in text, "teardown sentinel relay"
    assert "FINALIZE_SUBCOMMAND=teardown" in text, "teardown subcommand relay"
    assert "FINALIZE_WARNINGS=none" in text, "teardown warnings relay"
    log_text = log.read_text(encoding="utf-8")
    assert "step18b sentinel=false argv=final-report step18b --implement-tmpdir" in log_text, (
        "finalize step18b invocation"
    )
    assert "--step17-emitted false" in log_text, "finalize false step17 flag forwarding"
    assert "flush-safety-net --log-root" in log_text, "finalize flush safety net"
    assert "--run-id RUN1" in log_text, "finalize safety net run id"
    assert "capture-transcript --source-file source.jsonl --log-root" in log_text, (
        "finalize transcript capture"
    )
    assert "--skill implement --run-id RUN1 --defer-commit true" in log_text, (
        "finalize transcript capture argv"
    )
    assert "teardown sentinel=before argv=implement-finalize teardown --state-file" in log_text, (
        "finalize teardown invocation"
    )
    assert "SESSION_TRANSCRIPT_STATUS=captured" in text, "finalize transcript status relay"


def test_step18_step7a_complete_skips_transcript_recapture(tmp_path: Path) -> None:
    plugin = _make_step18_plugin(tmp_path)
    impl = _make_step18_impl(tmp_path, "step7a-complete")
    (impl / "bgjob").mkdir()
    _ = (impl / "bgjob" / "implement-step7a.result.env").write_text("", encoding="utf-8")
    out = tmp_path / "step7a-complete.out"
    log = tmp_path / "step7a-complete.log"
    result = _run_step18(
        tmp_path,
        impl,
        plugin,
        out_path=out,
        log_path=log,
        args=["--phase", "finalize", "--step17-emitted", "false"],
        extra_env={"STEP18_STUB_EMIT_BODY": "false"},
    )
    assert result.returncode == 0
    log_text = log.read_text(encoding="utf-8")
    assert "flush-safety-net" in log_text, "step7a-complete still flushes execution issues"
    assert "capture-transcript" not in log_text, "step7a-complete skips transcript recapture"


def test_step18_step17_present_suppresses_body(tmp_path: Path) -> None:
    plugin = _make_step18_plugin(tmp_path)
    impl = _make_step18_impl(tmp_path, "step17-present")
    out = tmp_path / "step17-present.out"
    log = tmp_path / "step17-present.log"
    result = _run_step18(
        tmp_path,
        impl,
        plugin,
        out_path=out,
        log_path=log,
        args=["--phase", "finalize", "--step17-emitted", "true"],
        extra_env={"STEP18_STUB_EMIT_BODY": "false"},
    )
    assert result.returncode == 0
    assert _kv("EMIT_BODY", result.stdout) == "false", "step17-present EMIT_BODY"
    log_text = log.read_text(encoding="utf-8")
    assert "step18b sentinel=true" in log_text, "step17-present pre-step18b sentinel"
    assert "--step17-emitted true" in log_text, "finalize true step17 flag forwarding"
    assert _count_literal("---LARCH-SUMMARY-FINAL-BEGIN---", result.stdout) == 0, (
        "step17-present marker suppressed"
    )


def test_step18_step18b_failure_tolerance(tmp_path: Path) -> None:
    plugin = _make_step18_plugin(tmp_path)
    impl = _make_step18_impl(tmp_path, "step18b-failure")
    out = tmp_path / "step18b-failure.out"
    log = tmp_path / "step18b-failure.log"
    result = _run_step18(
        tmp_path,
        impl,
        plugin,
        out_path=out,
        log_path=log,
        args=["--phase", "finalize", "--step17-emitted", "false"],
        extra_env={"STEP18_STUB_WFR_RC": "7", "STEP18_STUB_EMIT_BODY": "true"},
    )
    assert result.returncode == 0
    assert _kv("WFR_RC", result.stdout) == "7", "step18b failure WFR_RC relay"
    assert _count_literal("---LARCH-SUMMARY-FINAL-BEGIN---", result.stdout) == 0, (
        "step18b failure markers suppressed"
    )
    log_text = log.read_text(encoding="utf-8")
    assert "append-failure" in log_text, "step18b failure append log"
    assert "token mark Step 18 — done" in log_text, "step18b failure closing mark"
    assert "teardown sentinel=" in log_text, "step18b failure teardown"


def test_step18_marker_cat_failure_tolerance(tmp_path: Path) -> None:
    plugin = _make_step18_plugin(tmp_path)
    impl = _make_step18_impl(tmp_path, "marker-failure")
    out = tmp_path / "marker-failure.out"
    log = tmp_path / "marker-failure.log"
    result = _run_step18(
        tmp_path,
        impl,
        plugin,
        out_path=out,
        log_path=log,
        args=["--phase", "finalize", "--step17-emitted", "false"],
        extra_env={"STEP18_STUB_CAT_FAIL": "true", "STEP18_STUB_EMIT_BODY": "true"},
    )
    assert result.returncode == 0
    assert _count_literal("---LARCH-SUMMARY-FINAL-BEGIN---", result.stdout) == 1, (
        "marker failure begin marker appears before cat failure"
    )
    assert _count_literal("---LARCH-SUMMARY-FINAL-END---", result.stdout) == 0, (
        "marker failure lacks balanced end marker"
    )
    log_text = log.read_text(encoding="utf-8")
    assert "token mark Step 18 — done" in log_text, "marker failure closing mark"
    assert "teardown sentinel=" in log_text, "marker failure teardown"


def test_step18_restore_missing_finalize_state(tmp_path: Path) -> None:
    plugin = _make_step18_plugin(tmp_path)
    impl = _make_step18_impl(tmp_path, "restore-missing")
    (impl / "finalize-state.sh").unlink()
    out = tmp_path / "restore-missing.out"
    log = tmp_path / "restore-missing.log"
    result = _run_step18(
        tmp_path,
        impl,
        plugin,
        out_path=out,
        log_path=log,
        args=["--phase", "finalize", "--step17-emitted", "false"],
        extra_env={"STEP18_STUB_EMIT_BODY": "false"},
    )
    assert result.returncode == 0
    assert "restore-finalize-state --implement-tmpdir" in log.read_text(encoding="utf-8"), (
        "restore missing finalize state"
    )


def test_step18_restore_ship_stall_truthy(tmp_path: Path) -> None:
    plugin = _make_step18_plugin(tmp_path)
    impl = _make_step18_impl(tmp_path, "restore-stall")
    _ = (impl / "ship-pr-state.sh").write_text(
        "STALL_TRACKING=yes\nBAIL_NEEDS_USER_INPUT=false\nSTALL_STEP=\n",
        encoding="utf-8",
    )
    out = tmp_path / "restore-stall.out"
    log = tmp_path / "restore-stall.log"
    result = _run_step18(
        tmp_path,
        impl,
        plugin,
        out_path=out,
        log_path=log,
        args=["--phase", "finalize", "--step17-emitted", "false"],
        extra_env={"STEP18_STUB_EMIT_BODY": "false"},
    )
    assert result.returncode == 0
    assert "restore-finalize-state --implement-tmpdir" in log.read_text(encoding="utf-8"), (
        "restore ship stall truthy"
    )


def test_step18_restore_ship_bail_truthy(tmp_path: Path) -> None:
    plugin = _make_step18_plugin(tmp_path)
    impl = _make_step18_impl(tmp_path, "restore-bail")
    _ = (impl / "ship-pr-state.sh").write_text(
        "STALL_TRACKING=false\nBAIL_NEEDS_USER_INPUT=ON\nSTALL_STEP=\n",
        encoding="utf-8",
    )
    out = tmp_path / "restore-bail.out"
    log = tmp_path / "restore-bail.log"
    result = _run_step18(
        tmp_path,
        impl,
        plugin,
        out_path=out,
        log_path=log,
        args=["--phase", "finalize", "--step17-emitted", "false"],
        extra_env={"STEP18_STUB_EMIT_BODY": "false"},
    )
    assert result.returncode == 0
    assert "restore-finalize-state --implement-tmpdir" in log.read_text(encoding="utf-8"), (
        "restore ship bail truthy"
    )


def test_step18_restore_stall_step_mismatch(tmp_path: Path) -> None:
    plugin = _make_step18_plugin(tmp_path)
    impl = _make_step18_impl(tmp_path, "restore-mismatch")
    _ = (impl / "ship-pr-state.sh").write_text(
        "STALL_TRACKING=false\nBAIL_NEEDS_USER_INPUT=false\nSTALL_STEP=ship\n",
        encoding="utf-8",
    )
    _ = (impl / "finalize-state.sh").write_text(
        "STALL_TRACKING=false\nSTALL_STEP=final\n",
        encoding="utf-8",
    )
    out = tmp_path / "restore-mismatch.out"
    log = tmp_path / "restore-mismatch.log"
    result = _run_step18(
        tmp_path,
        impl,
        plugin,
        out_path=out,
        log_path=log,
        args=["--phase", "finalize", "--step17-emitted", "false"],
        extra_env={"STEP18_STUB_EMIT_BODY": "false"},
    )
    assert result.returncode == 0
    log_text = log.read_text(encoding="utf-8")
    assert "restore-finalize-state --implement-tmpdir" in log_text, "restore stall step mismatch"
    mark_line = _line_no("token mark Step 18 — done", log_text)
    flush_line = _line_no("flush-safety-net", log_text)
    capture_line = _line_no("capture-transcript", log_text)
    restore_line = _line_no("restore-finalize-state", log_text)
    teardown_line = _line_no("teardown sentinel=", log_text)
    assert all(line is not None for line in (mark_line, flush_line, capture_line, restore_line, teardown_line)), (
        "ordering log missing expected rows"
    )
    assert mark_line < flush_line, "closing mark must precede execution-issues safety net"  # type: ignore[operator]  # pyright cannot narrow int | None across an all(...is not None...) assertion boundary
    assert flush_line < capture_line, "execution-issues safety net must precede transcript safety net"  # type: ignore[operator]  # pyright cannot narrow int | None across an all(...is not None...) assertion boundary
    assert capture_line < restore_line, "transcript safety net must precede restore-finalize-state"  # type: ignore[operator]  # pyright cannot narrow int | None across an all(...is not None...) assertion boundary
    assert restore_line < teardown_line, "restore-finalize-state must precede teardown"  # type: ignore[operator]  # pyright cannot narrow int | None across an all(...is not None...) assertion boundary


def test_step18_restore_aligned_skips(tmp_path: Path) -> None:
    plugin = _make_step18_plugin(tmp_path)
    impl = _make_step18_impl(tmp_path, "restore-aligned")
    _ = (impl / "ship-pr-state.sh").write_text(
        "STALL_TRACKING=false\nBAIL_NEEDS_USER_INPUT=false\nSTALL_STEP=same\n",
        encoding="utf-8",
    )
    _ = (impl / "finalize-state.sh").write_text(
        "STALL_TRACKING=false\nSTALL_STEP=same\n",
        encoding="utf-8",
    )
    out = tmp_path / "restore-aligned.out"
    log = tmp_path / "restore-aligned.log"
    result = _run_step18(
        tmp_path,
        impl,
        plugin,
        out_path=out,
        log_path=log,
        args=["--phase", "finalize", "--step17-emitted", "false"],
        extra_env={"STEP18_STUB_EMIT_BODY": "false"},
    )
    assert result.returncode == 0
    assert "restore-finalize-state" not in log.read_text(encoding="utf-8"), (
        "restore aligned should skip"
    )


def test_step18_restore_read_key_failure_still_teardown(tmp_path: Path) -> None:
    plugin = _make_step18_plugin(tmp_path)
    impl = _make_step18_impl(tmp_path, "restore-read-key-failure")
    _ = (impl / "ship-pr-state.sh").write_text(
        "STALL_TRACKING=yes\nBAIL_NEEDS_USER_INPUT=true\nSTALL_STEP=ship\n",
        encoding="utf-8",
    )
    _ = (impl / "finalize-state.sh").write_text(
        "STALL_TRACKING=false\nSTALL_STEP=ship\n",
        encoding="utf-8",
    )
    out = tmp_path / "restore-read-key-failure.out"
    log = tmp_path / "restore-read-key-failure.log"
    result = _run_step18(
        tmp_path,
        impl,
        plugin,
        out_path=out,
        log_path=log,
        args=["--phase", "finalize", "--step17-emitted", "false"],
        extra_env={
            "STEP18_STUB_EMIT_BODY": "false",
            "STEP18_STUB_READ_KEY_FAIL_KEY": "STALL_TRACKING",
        },
    )
    assert result.returncode == 0
    log_text = log.read_text(encoding="utf-8")
    assert "teardown sentinel=" in log_text, "restore read-key failure still tears down"
    assert "restore-finalize-state --implement-tmpdir" in log_text, (
        "restore read-key failure uses default and continues"
    )


def test_step18_no_run_id_skips_safety_nets(tmp_path: Path) -> None:
    plugin = _make_step18_plugin(tmp_path)
    impl = _make_step18_impl(tmp_path, "no-run-id")
    session = (impl / "session-env.sh").read_text(encoding="utf-8")
    _ = (impl / "session-env.sh").write_text(
        "\n".join(line for line in session.splitlines() if not line.startswith("LARCH_RUN_ID=")),
        encoding="utf-8",
    )
    out = tmp_path / "no-run-id.out"
    log = tmp_path / "no-run-id.log"
    result = _run_step18(
        tmp_path,
        impl,
        plugin,
        out_path=out,
        log_path=log,
        args=["--phase", "finalize", "--step17-emitted", "false"],
        extra_env={"STEP18_STUB_EMIT_BODY": "false", "RUN_ID": ""},
    )
    assert result.returncode == 0
    log_text = log.read_text(encoding="utf-8")
    assert "flush-safety-net" not in log_text, "no run id flush safety net skip"
    assert "capture-transcript" not in log_text, "no run id transcript safety net skip"
    assert "teardown sentinel=" in log_text, "no run id teardown"


def test_step18_post_terminal_finalize(tmp_path: Path) -> None:
    plugin = _make_step18_plugin(tmp_path)
    impl = _make_step18_impl(tmp_path, "post-terminal")
    _ = (impl / "ship-pr-state.sh").write_text(
        "STALL_TRACKING=true\nBAIL_NEEDS_USER_INPUT=false\nSTALL_STEP=terminal\n",
        encoding="utf-8",
    )
    _ = (impl / "stall-recovery-terminal-report.env").write_text(
        "terminal report\n",
        encoding="utf-8",
    )
    out = tmp_path / "post-terminal.out"
    log = tmp_path / "post-terminal.log"
    result = _run_step18(
        tmp_path,
        impl,
        plugin,
        out_path=out,
        log_path=log,
        args=["--phase", "finalize", "--step17-emitted", "false"],
        extra_env={"STEP18_STUB_EMIT_BODY": "false"},
    )
    assert result.returncode == 0
    assert "STALL_RECOVERY_REQUIRED" not in result.stdout, (
        "post-terminal finalize must not re-run gate"
    )
    assert "FINALIZE_SUBCOMMAND=teardown" in result.stdout, "post-terminal teardown tail relay"


def _token_prop_env() -> dict[str, str]:
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(_REPO)
    env["PYTHONPATH"] = str(_REPO / "python")
    for key in list(env):
        if key.startswith("LARCH_QUIET"):
            del env[key]
    return env


def _read_session_key(env_file: Path, key: str, default: str = "") -> str:
    result = subprocess.run(
        [_REAL_PYTHON, str(_CLI), "session", "read-key", "--file", str(env_file), "--key", key, "--default", default],
        env={**os.environ, "PYTHONPATH": str(_REPO / "python"), "CLAUDE_PLUGIN_ROOT": str(_REPO)},
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout.rstrip("\n")


def test_token_propagation_session_setup_forwarding(tmp_path: Path) -> None:
    env = _token_prop_env()
    timing_ledger = tmp_path / "timing-ledger.tsv"
    implement_env = tmp_path / "implement-session-env.sh"
    review_env = tmp_path / "review-session-env.sh"
    claude_source = tmp_path / "claude-source.env"
    _ = claude_source.write_text("SOURCE_FILE=/tmp/mock-transcript.jsonl\n", encoding="utf-8")
    _ = implement_env.write_text(
        f"REPO=owner/repo\nREPO_UNAVAILABLE=false\n"
        f"LARCH_TIMING_LEDGER={timing_ledger}\n"
        f"LARCH_TOKEN_SESSION_ID=parent-implement-session\n"
        f"LARCH_CLAUDE_SOURCE_FILE={claude_source}\n",
        encoding="utf-8",
    )
    setup = subprocess.run(
        [
            _REAL_PYTHON,
            str(_CLI),
            "session",
            "setup",
            "--prefix",
            "claude-review-token-test",
            "--skip-preflight",
            "--skip-repo-check",
            "--caller-env",
            str(implement_env),
            "--write-session-env",
            str(review_env),
        ],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert setup.returncode == 0
    assert "LARCH_TOKEN_SESSION_ID=parent-implement-session" in setup.stdout
    assert "LARCH_TIMING_LEDGER=" not in setup.stdout
    assert _read_session_key(review_env, "LARCH_TOKEN_SESSION_ID") == "parent-implement-session"
    assert _read_session_key(review_env, "LARCH_CLAUDE_SOURCE_FILE") == str(claude_source)
    assert _read_session_key(review_env, "LARCH_TIMING_LEDGER") == str(timing_ledger)


def test_token_propagation_unsafe_ledger_rejection(tmp_path: Path) -> None:
    env = _token_prop_env()
    claude_source = tmp_path / "claude-source.env"
    _ = claude_source.write_text("SOURCE_FILE=/tmp/mock-transcript.jsonl\n", encoding="utf-8")
    unsafe_env = tmp_path / "unsafe-implement-session-env.sh"
    unsafe_review = tmp_path / "unsafe-review-session-env.sh"
    unsafe_err = tmp_path / "unsafe-session-setup.err"
    _ = unsafe_env.write_text(
        f"REPO=owner/repo\nREPO_UNAVAILABLE=false\n"
        f"LARCH_TIMING_LEDGER=/etc/passwd\n"
        f"LARCH_TOKEN_SESSION_ID=parent-implement-session\n"
        f"LARCH_CLAUDE_SOURCE_FILE={claude_source}\n",
        encoding="utf-8",
    )
    setup = subprocess.run(
        [
            _REAL_PYTHON,
            str(_CLI),
            "session",
            "setup",
            "--prefix",
            "claude-review-token-test",
            "--skip-preflight",
            "--skip-repo-check",
            "--caller-env",
            str(unsafe_env),
            "--write-session-env",
            str(unsafe_review),
        ],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert setup.returncode == 0
    _ = unsafe_err.write_text(setup.stderr, encoding="utf-8")
    assert _read_session_key(unsafe_review, "LARCH_TIMING_LEDGER") == ""
    assert (
        "session-setup.sh: warning: ignoring unsafe LARCH_TIMING_LEDGER from caller-env (not under accepted root)"
        in setup.stderr
    )


def _write_review_core_stub(tmp_path: Path) -> Path:
    stub = tmp_path / "review-core-stub.sh"
    _write_executable(stub, _REVIEW_CORE_STUB)
    return stub


def test_token_propagation_review_and_fix_step5_default_moderate(tmp_path: Path) -> None:
    env = _token_prop_env()
    timing_ledger = tmp_path / "timing-ledger.tsv"
    review_env = tmp_path / "review-session-env.sh"
    claude_source = tmp_path / "claude-source.env"
    _ = claude_source.write_text("SOURCE_FILE=/tmp/mock-transcript.jsonl\n", encoding="utf-8")
    implement_env = tmp_path / "implement-session-env.sh"
    _ = implement_env.write_text(
        f"REPO=owner/repo\nREPO_UNAVAILABLE=false\n"
        f"LARCH_TIMING_LEDGER={timing_ledger}\n"
        f"LARCH_TOKEN_SESSION_ID=parent-implement-session\n"
        f"LARCH_CLAUDE_SOURCE_FILE={claude_source}\n",
        encoding="utf-8",
    )
    setup = subprocess.run(
        [
            _REAL_PYTHON,
            str(_CLI),
            "session",
            "setup",
            "--prefix",
            "claude-review-token-test",
            "--skip-preflight",
            "--skip-repo-check",
            "--caller-env",
            str(implement_env),
            "--write-session-env",
            str(review_env),
        ],
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    token_session_id = _read_session_key(review_env, "LARCH_TOKEN_SESSION_ID")
    claude_source_file = _read_session_key(review_env, "LARCH_CLAUDE_SOURCE_FILE")
    timing_ledger_value = _read_session_key(review_env, "LARCH_TIMING_LEDGER")

    implement_tmpdir = tmp_path / "claude-implement-token-test"
    implement_tmpdir.mkdir()
    _ = shutil.copy(review_env, implement_tmpdir / "session-env.sh")
    session_env = implement_tmpdir / "session-env.sh"
    with session_env.open("a", encoding="utf-8") as handle:
        _ = handle.write("RUN_ID=token-test-run\nCODEX_BINARY_FOUND=false\nCURSOR_BINARY_FOUND=false\n")
    _ = (implement_tmpdir / "plan.txt").write_text("plan\n", encoding="utf-8")
    _ = (implement_tmpdir / "feature-description.txt").write_text("feature\n", encoding="utf-8")
    core_stub = _write_review_core_stub(tmp_path)
    capture = tmp_path / "review-core-capture.env"
    review_env_vars = {
        **env,
        "CORE_CAPTURE_FILE": str(capture),
        "LARCH_TOKEN_SESSION_ID": token_session_id,
        "LARCH_CLAUDE_SOURCE_FILE": claude_source_file,
        "LARCH_TIMING_LEDGER": timing_ledger_value,
        "LARCH_TEST_REVIEW_CORE_OVERRIDE": "1",
        "REVIEW_AND_FIX_REVIEW_CORE_SH": str(core_stub),
    }
    result = subprocess.run(
        [
            _REAL_PYTHON,
            str(_CLI),
            "review-and-fix",
            "step5",
            "--implement-tmpdir",
            str(implement_tmpdir),
            "--mode",
            "single",
            "--round-num",
            "1",
            "--session-env-path",
            str(session_env),
            "--codex-available",
            "false",
            "--cursor-available",
            "false",
        ],
        env=review_env_vars,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    expected_session_env = os.path.normpath(str(session_env))
    capture_text = capture.read_text(encoding="utf-8")
    assert f"SESSION_ENV_PATH={expected_session_env}" in capture_text
    assert "REVIEW_CORE_ARGV" in capture_text
    argv_line = next(line for line in capture_text.splitlines() if line.startswith("REVIEW_CORE_ARGV"))
    assert "--panel" in argv_line
    assert "hard" in argv_line
    assert "LARCH_TOKEN_SESSION_ID=parent-implement-session" in capture_text
    assert f"LARCH_CLAUDE_SOURCE_FILE={claude_source}" in capture_text
    assert f"LARCH_TIMING_LEDGER={timing_ledger}" in capture_text
    review_core_env = (implement_tmpdir / "round-1" / "review-core.env").read_text(encoding="utf-8")
    assert "PANEL_TIER=MODERATE" in review_core_env
    assert "PANEL_SHAPE=pairs" in review_core_env
    assert "EFFECTIVE_ROUND_CAP=2" in review_core_env
    _ = setup  # session setup exercised above


@pytest.mark.parametrize(
    ("tier", "expected_panel", "expected_shape", "expected_cap"),
    [
        ("TRIVIAL", "simple", "singles", "2"),
        ("MODERATE", "hard", "pairs", "2"),
        ("HARD", "hard", "pairs", "2"),
    ],
    ids=["TRIVIAL", "MODERATE", "HARD"],
)
def test_token_propagation_difficulty_routing(
    tmp_path: Path,
    tier: str,
    expected_panel: str,
    expected_shape: str,
    expected_cap: str,
) -> None:
    env = _token_prop_env()
    timing_ledger = tmp_path / "timing-ledger.tsv"
    review_env = tmp_path / "review-session-env.sh"
    claude_source = tmp_path / "claude-source.env"
    _ = claude_source.write_text("SOURCE_FILE=/tmp/mock-transcript.jsonl\n", encoding="utf-8")
    implement_env = tmp_path / "implement-session-env.sh"
    _ = implement_env.write_text(
        f"REPO=owner/repo\nREPO_UNAVAILABLE=false\n"
        f"LARCH_TIMING_LEDGER={timing_ledger}\n"
        f"LARCH_TOKEN_SESSION_ID=parent-implement-session\n"
        f"LARCH_CLAUDE_SOURCE_FILE={claude_source}\n",
        encoding="utf-8",
    )
    _ = subprocess.run(
        [
            _REAL_PYTHON,
            str(_CLI),
            "session",
            "setup",
            "--prefix",
            "claude-review-token-test",
            "--skip-preflight",
            "--skip-repo-check",
            "--caller-env",
            str(implement_env),
            "--write-session-env",
            str(review_env),
        ],
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    token_session_id = _read_session_key(review_env, "LARCH_TOKEN_SESSION_ID")
    claude_source_file = _read_session_key(review_env, "LARCH_CLAUDE_SOURCE_FILE")
    timing_ledger_value = _read_session_key(review_env, "LARCH_TIMING_LEDGER")

    lower = tier.lower()
    case_tmp = tmp_path / f"claude-implement-difficulty-{lower}"
    case_tmp.mkdir()
    _ = shutil.copy(review_env, case_tmp / "session-env.sh")
    session_env = case_tmp / "session-env.sh"
    with session_env.open("a", encoding="utf-8") as handle:
        _ = handle.write(f"RUN_ID=token-test-run-{lower}\nCODEX_BINARY_FOUND=false\nCURSOR_BINARY_FOUND=false\n")
    _ = (case_tmp / "plan.txt").write_text("plan\n", encoding="utf-8")
    _ = (case_tmp / "feature-description.txt").write_text("feature\n", encoding="utf-8")
    core_stub = _write_review_core_stub(tmp_path)
    capture = tmp_path / f"review-core-capture-{lower}.env"
    review_env_vars = {
        **env,
        "CORE_CAPTURE_FILE": str(capture),
        "LARCH_TOKEN_SESSION_ID": token_session_id,
        "LARCH_CLAUDE_SOURCE_FILE": claude_source_file,
        "LARCH_TIMING_LEDGER": timing_ledger_value,
        "LARCH_TEST_REVIEW_CORE_OVERRIDE": "1",
        "REVIEW_AND_FIX_REVIEW_CORE_SH": str(core_stub),
    }
    result = subprocess.run(
        [
            _REAL_PYTHON,
            str(_CLI),
            "review-and-fix",
            "step5",
            "--implement-tmpdir",
            str(case_tmp),
            "--mode",
            "single",
            "--round-num",
            "1",
            "--session-env-path",
            str(session_env),
            "--codex-available",
            "false",
            "--cursor-available",
            "false",
            "--difficulty",
            tier,
        ],
        env=review_env_vars,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    capture_text = capture.read_text(encoding="utf-8")
    argv_line = next(line for line in capture_text.splitlines() if line.startswith("REVIEW_CORE_ARGV"))
    assert "--panel" in argv_line
    assert expected_panel in argv_line
    assert "--tier" in argv_line
    assert tier in argv_line
    assert f"PANEL_ARG={expected_panel}" in capture_text
    assert f"TIER_ARG={tier}" in capture_text
    review_core_env = (case_tmp / "round-1" / "review-core.env").read_text(encoding="utf-8")
    assert f"PANEL_SHAPE={expected_shape}" in review_core_env
    assert f"PANEL_TIER={tier}" in review_core_env
    assert f"EFFECTIVE_ROUND_CAP={expected_cap}" in review_core_env
