"""Offline harness parity for implement shell helper scripts.

Adapter/bgjob behavior for Step 5/6/checks lives in the Rust adapter tests and
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

from larch.core import config
from tests.support.repo_contract import repo_root

_REPO = repo_root()
_IMPLEMENT_SCRIPTS = _REPO / "skills" / "implement" / "scripts"
_STEP8_HELPER = _IMPLEMENT_SCRIPTS / "step-8-ship.sh"
_STEP8_GUARD = _IMPLEMENT_SCRIPTS / "step-8-python-guard.sh"
_STEP8_SEEDER = _IMPLEMENT_SCRIPTS / "step-8-seed-initial.sh"
_STEP18_HELPER = _IMPLEMENT_SCRIPTS / "step-18.sh"
_STEP19_HELPER = _IMPLEMENT_SCRIPTS / "step-19.sh"
_CLI = _REPO / "python" / "cli.py"
_REAL_PYTHON = sys.executable
_BASH = shutil.which("bash") or "/bin/bash"

_STEP5_WRAPPERS: tuple[str, ...] = ()

_STEP5_RUST_WRAPPERS = (
    "run-step-checks.sh",
    "step-5-review.sh",
    "step-5-resume.sh",
    "step-6-entry.sh",
)

_STEP8_HELPER_STATIC_PINS: tuple[tuple[str, str, bool], ...] = (
    ('implement step-8-ship "$@"', "static: thin wrapper delegates to Python", True),
    ("bgjob adapt", "static: bash wrapper no longer owns bgjob adapt", False),
    ("bgjob start", "static: direct bgjob start retired", False),
    ("persist_handoff", "static: sidecar handoff writer retired", False),
    ("stdout-capture", "static: stdout capture retired", False),
    ("tee -a", "static: stdout tee retired", False),
    ("step-8-ship-handoff", "static: rc and JSON sidecars retired", False),
    ("run_in_background", "static: helper prose/code no legacy background literal", False),
    ("printf 'PID=%s", "static: legacy bg-wait marker writer removed", False),
    ("rehydrate_plugin_root", "static: rehydrate helpers moved to Python", False),
)

_STEP8_SEEDER_STATIC_PINS: tuple[tuple[str, str, bool], ...] = (
    ('implement step-8-seed-initial "$@"', "static: thin wrapper delegates to Python", True),
    ("ship seed-initial-state", "static: bash wrapper no longer calls seeder directly", False),
    ("read-session-env-key.sh", "static: retired session reader absent", False),
    ("rehydrate_plugin_root", "static: rehydrate helpers moved to Python", False),
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
    # Minimal stub for the legacy-compatible kv get used by step-18.sh kv_value(). Mirrors
    # larch.io.read_kv always exits 0 through the CLI, printing
    # the default when the key (or file) is absent.
    key = args[args.index("--key") + 1]
    default = args[args.index("--default") + 1] if "--default" in args else ""
    file_path = Path(args[args.index("--file") + 1]) if "--file" in args else None
    try:
        text = file_path.read_text(encoding="utf-8") if file_path is not None else sys.stdin.read()
    except OSError:
        print(default)
        return 0
    for line in text.splitlines():
        if line.startswith(key + "="):
            print(line.split("=", 1)[1])
            return 0
    print(default)
    return 0


def step18b(args: list[str]) -> int:
    tmp = Path(args[args.index("--implement-tmpdir") + 1])
    sentinel = "true" if (tmp / ".step17-emitted").exists() else "false"
    log(f"step18b sentinel={sentinel} argv={' '.join(sys.argv[1:])}")
    summary = tmp / "summary-final.md"
    if (os.environ.get("STEP18_STUB_WRITE_SUMMARY") or "true") == "true":
        summary.write_text((os.environ.get("STEP18_STUB_BODY") or "# Final body\\n"), encoding="utf-8")
    if (os.environ.get("STEP18_STUB_REMOVE_SUMMARY") or "false") == "true":
        with open(summary, "w", encoding="utf-8") as handle:
            handle.write((os.environ.get("STEP18_STUB_BODY") or "# Final body\\n"))
        os.unlink(summary)
    # Python finalize reads summary via Path.read_text (not cat). Simulate a
    # mid-marker read failure by making the file unreadable after write.
    if (os.environ.get("STEP18_STUB_CAT_FAIL") or "false") == "true" and summary.is_file():
        os.chmod(summary, 0o000)
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


def implement_step18(args: list[str]) -> int:
    # Delegate to real Python step-18; nested verbs stay on this stub cli.
    real_python = Path(os.environ["STEP18_REAL_REPO"]) / "python"
    if str(real_python) not in sys.path:
        sys.path.insert(0, str(real_python))
    from larch.implement.implement_dispatch import step_18_main

    return step_18_main(args)


def implement_step19(args: list[str]) -> int:
    # Delegate to real Python step-19; nested verbs stay on this stub cli.
    real_python = Path(os.environ["STEP18_REAL_REPO"]) / "python"
    if str(real_python) not in sys.path:
        sys.path.insert(0, str(real_python))
    from larch.implement.implement_dispatch import step_19_main

    return step_19_main(args)


def prepare_terminal_snapshot(args: list[str]) -> int:
    log("prepare-terminal-snapshot " + " ".join(args))
    rc = int(os.environ.get("STEP18_STUB_SNAPSHOT_RC") or "0")
    if rc != 0:
        print("SESSION_TRANSCRIPT_STATUS=failed")
        print("TERMINAL_SNAPSHOT_STATUS=failed")
        print("TERMINAL_SNAPSHOT_ERROR=stub snapshot failure")
        return rc
    print("SESSION_TRANSCRIPT_STATUS=captured")
    print("TERMINAL_SNAPSHOT_STATUS=prepared")
    print("TERMINAL_SNAPSHOT_ERROR=")
    return 0


def main() -> int:
    args = sys.argv[1:]
    if args[:2] == ["implement", "step-18"]:
        return implement_step18(args[2:])
    if args[:2] == ["implement", "step-19"]:
        return implement_step19(args[2:])
    if args[:2] == ["session", "read-key"]:
        return read_key(args[2:])
    if args[:2] == ["kv", "get"]:
        return kv_get(args[2:])
    if args[:2] == ["final-report", "step18b"]:
        return step18b(args[2:])
    if args[:2] == ["run-log", "append-failure"]:
        log("append-failure " + " ".join(args[2:]))
        return 0
    if args[:2] == ["run-log", "prepare-terminal-snapshot"]:
        return prepare_terminal_snapshot(args[2:])
    if len(args) >= 2 and args[0] == "run-log" and args[1] in {
        "lifecycle-cancel",
        "lifecycle-failure",
        "lifecycle-finalize",
    }:
        log("run-log " + args[1] + " " + " ".join(args[2:]))
        publish_rc = int(os.environ.get("STEP18_STUB_PUBLISH_RC") or "0")
        if publish_rc != 0:
            print("publication failed: stub upload failure", file=sys.stderr)
            return publish_rc
        if os.environ.get("STEP18_STUB_STORAGE_DISABLED") == "true":
            print("RUN_LOG_STORAGE=disabled")
            print("RUN_LOG_STORAGE_REASON=config-file-missing")
            print("RUN_LOG_PUBLICATION=skipped-disabled")
            print("LIFECYCLE_FLUSHED=false")
            print("LIFECYCLE_TERMINALIZED=true")
            return 0
        cache = Path(os.environ["IMPLEMENT_TMPDIR"]) / "published-cache"
        cache.mkdir(parents=True, exist_ok=True)
        print("REMOTE_KEY=run-logs/implement/RUN1.tar.gz")
        print("ARCHIVE_SHA256=" + "a" * 64)
        print(f"CACHE_DIR={cache}")
        print("RUN_LOG_STORAGE=enabled")
        print("RUN_LOG_STORAGE_REASON=repository-config")
        print("RUN_LOG_PUBLICATION=published")
        print("LIFECYCLE_FLUSHED=true")
        print("LIFECYCLE_TERMINALIZED=true")
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
        return int(os.environ.get("STEP18_STUB_FLUSH_RC") or "0")
    if args[:2] == ["run-log", "capture-transcript"]:
        log("capture-transcript " + " ".join(args[2:]))
        print("SESSION_TRANSCRIPT_STATUS=captured")
        return 0
    if args[:2] == ["session", "restore-finalize-state"]:
        log("restore-finalize-state " + " ".join(args[2:]))
        return int(os.environ.get("STEP18_STUB_RESTORE_RC") or "0")
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


_STEP8_HYBRID_CLI = """\
#!/usr/bin/env python3
import os
import sys
from pathlib import Path


def _order(message: str) -> None:
    path = os.environ.get("STEP8_ORDER_FILE")
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(message + "\\n")


def _capture(env_key: str) -> None:
    path = os.environ.get(env_key)
    if path:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("\\n".join(sys.argv[1:]) + "\\n")


def _delegate(main_name: str, args: list[str]) -> int:
    real_python = Path(os.environ["STEP8_REAL_REPO"]) / "python"
    if str(real_python) not in sys.path:
        sys.path.insert(0, str(real_python))
    from larch.implement import implement_dispatch

    return getattr(implement_dispatch, main_name)(args)


def main() -> int:
    args = sys.argv[1:]
    if args[:2] == ["implement", "step-8-ship"]:
        return _delegate("step8_ship_main", args[2:])
    if args[:2] == ["implement", "step-8-seed-initial"]:
        return _delegate("step8_seed_initial_main", args[2:])
    if args[:2] == ["implement", "clone-tag"]:
        print("CLONE_TAG_FULL=stub")
        print("EXPECTED_TMPDIR_BASENAME_PREFIX=claude-implement-stub-")
        return 0
    if args[:2] == ["git", "phantom-probe"]:
        _order("phantom")
        print("PHANTOM_STATUS=clean")
        return 0
    if args[:2] == ["ship", "pr"]:
        _order("driver")
        _capture("STEP8_SHIP_ARGV")
        print('{"outcome":"NEEDS_USER_INPUT","needs_user_reason":"oos-filing"}')
        return 3
    if args[:2] == ["ship", "seed-initial-state"]:
        _capture("STEP8_SEED_ARGV")
        return 0
    if args[:2] == ["session", "read-key"]:
        file_path = Path(args[args.index("--file") + 1])
        key = args[args.index("--key") + 1]
        default = args[args.index("--default") + 1] if "--default" in args else ""
        try:
            for line in file_path.read_text(encoding="utf-8").splitlines():
                if line.startswith(key + "="):
                    print(line.split("=", 1)[1])
                    return 0
        except OSError:
            pass
        print(default)
        return 0
    print("unexpected argv: " + " ".join(args), file=sys.stderr)
    return 8


if __name__ == "__main__":
    raise SystemExit(main())
"""


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
    return impl


def _make_step8_plugin(tmp_path: Path) -> Path:
    plugin = tmp_path / "step8-plugin"
    python_dir = plugin / "python"
    python_dir.mkdir(parents=True)
    cli = python_dir / "cli.py"
    _write_executable(cli, _STEP8_HYBRID_CLI)
    return plugin


def _step8_env(impl: Path, *, plugin: Path | None = None) -> dict[str, str]:
    root = plugin if plugin is not None else _REPO
    return {
        "IMPLEMENT_TMPDIR": str(impl),
        "CLAUDE_PLUGIN_ROOT": str(root),
        "STEP8_REAL_REPO": str(_REPO),
        "PYTHONPATH": str(_REPO / "python"),
    }


def _write_python3_stub(stub_bin: Path, body: str) -> None:
    _write_executable(stub_bin / "python3", body)


def _run_step8(
    impl: Path,
    stub_bin: Path | None = None,
    *,
    args: Sequence[str] = (),
    plugin: Path | None = None,
    extra_env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = _step8_env(impl, plugin=plugin)
    if extra_env:
        env.update(extra_env)
    if stub_bin is not None:
        _prepend_path(env, stub_bin)
    return _run_bash(_STEP8_HELPER, env=env, args=args)


@pytest.mark.parametrize("wrapper", _STEP5_WRAPPERS + _STEP5_RUST_WRAPPERS, ids=_STEP5_WRAPPERS + _STEP5_RUST_WRAPPERS)
def test_step5_wrapper_shape_set_euo_pipefail(wrapper: str) -> None:
    assert "set -euo pipefail" in _wrapper_source(wrapper)


@pytest.mark.parametrize("wrapper", _STEP5_RUST_WRAPPERS, ids=_STEP5_RUST_WRAPPERS)
def test_step5_wrapper_shape_exec_larch_implement(wrapper: str) -> None:
    assert 'exec "$PLUGIN_ROOT/scripts/larch.sh" implement' in _wrapper_source(wrapper)


@pytest.mark.parametrize("wrapper", _STEP5_WRAPPERS + _STEP5_RUST_WRAPPERS, ids=_STEP5_WRAPPERS + _STEP5_RUST_WRAPPERS)
def test_step5_wrapper_shape_no_bgjob_start(wrapper: str) -> None:
    assert "bgjob start" not in _wrapper_source(wrapper)


@pytest.mark.parametrize("wrapper", _STEP5_WRAPPERS + _STEP5_RUST_WRAPPERS, ids=_STEP5_WRAPPERS + _STEP5_RUST_WRAPPERS)
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
    capture = tmp_path / "step8-ship-argv.txt"
    _write_python3_stub(
        stub_bin,
        f"""#!/usr/bin/env bash
if [ "$1" = "{_CLI}" ] && [ "$2" = "implement" ] && [ "$3" = "step-8-ship" ]; then
  printf '%s\\n' "$@" > "{capture}"
  for arg in "$@"; do
    if [ "$arg" = "--bgjob-child" ]; then
      exec "{_REAL_PYTHON}" "$@"
    fi
  done
  printf '%s\\n' 'BGJOB_STATUS=STARTED STEP=implement-step8-ship PGID=12345'
  exit 0
fi
exec "{_REAL_PYTHON}" "$@"
""",
    )
    result = _run_step8(impl, stub_bin)
    argv = capture.read_text(encoding="utf-8")
    assert result.returncode == 0, "dynamic: foreground launcher exits 0 on step-8-ship"
    assert result.stdout == "BGJOB_STATUS=STARTED STEP=implement-step8-ship PGID=12345\n", (
        "dynamic: foreground launcher stdout is exact bgjob adapter line"
    )
    assert "implement\nstep-8-ship" in argv, "dynamic: thin wrapper reaches implement step-8-ship"
    assert "--bgjob-child" not in argv, "dynamic: outer launch does not pass child flags"


def test_step8_dynamic_child_guard_phantom_driver_order(tmp_path: Path) -> None:
    impl = _make_step8_impl(tmp_path)
    plugin = _make_step8_plugin(tmp_path)
    # Keep plugin-root.env aligned with the hybrid plugin so rehydrate does not
    # flip nested CLI resolution back to the real repo cli.py.
    _ = (impl / "plugin-root.env").write_text(
        f"export CLAUDE_PLUGIN_ROOT={plugin}\n",
        encoding="utf-8",
    )
    order_file = tmp_path / "order.txt"
    ship_argv = tmp_path / "ship-argv.txt"
    merge_env = impl / "bgjob" / "implement-step8-ship.merge.env"
    merge_env.unlink(missing_ok=True)
    _ = order_file.write_text("", encoding="utf-8")
    result = _run_step8(
        impl,
        plugin=plugin,
        args=["--bgjob-child", "--merge-result-env", str(merge_env)],
        extra_env={
            "STEP8_ORDER_FILE": str(order_file),
            "STEP8_SHIP_ARGV": str(ship_argv),
        },
    )
    assert result.returncode == 3, "dynamic: child preserves the ship driver's route rc"
    # Guard and phantom-probe now run in-process; only the ship driver is CLI-ordered.
    assert order_file.read_text(encoding="utf-8") == "driver\n", (
        "dynamic: child forwards to ship pr driver"
    )
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
    plugin = _make_step8_plugin(tmp_path)
    _ = (impl / "plugin-root.env").write_text(
        f"export CLAUDE_PLUGIN_ROOT={plugin}\n",
        encoding="utf-8",
    )
    merge_env = impl / "bgjob" / "implement-step8-ship.merge.env"
    _ = (impl / "ship-pr-state.sh").write_text(
        "RUN_ID=run-ship-guard\nREPO=owner/repo\n",
        encoding="utf-8",
    )
    result = _run_step8(
        impl,
        plugin=plugin,
        args=["--bgjob-child", "--merge-result-env", str(merge_env)],
    )
    assert result.returncode == 2, "child: require_value setup failure exits 2"
    assert not (impl / ".step-8-ship-handoff.rc").exists(), "child: rc sidecar is retired"
    assert not (impl / ".step-8-ship-handoff.json").exists(), "child: JSON sidecar is retired"
    assert result.stdout == "", "child: setup failure stdout empty"


def test_step8_seeder_argv_forwarding(tmp_path: Path) -> None:
    seed_tmp = tmp_path / "seed"
    codex_out = seed_tmp / "codex-step2-out"
    codex_out.mkdir(parents=True)
    plugin = _make_step8_plugin(tmp_path)
    seed_argv = tmp_path / "seed-argv.txt"
    _ = (seed_tmp / "plugin-root.env").write_text(
        f"export CLAUDE_PLUGIN_ROOT={plugin}\n",
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
    env = _step8_env(seed_tmp, plugin=plugin)
    env["STEP8_SEED_ARGV"] = str(seed_argv)
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
    assert "claude-implement-" in argv, "seeder: clone-tag prefix forwarded"


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


def test_step8_child_passes_merge_result_env_to_ship(tmp_path: Path) -> None:
    impl = _make_step8_impl(tmp_path, "implement-symlink-merge")
    plugin = _make_step8_plugin(tmp_path)
    _ = (impl / "plugin-root.env").write_text(
        f"export CLAUDE_PLUGIN_ROOT={plugin}\n",
        encoding="utf-8",
    )
    merge_target = tmp_path / "merge-target.env"
    _ = merge_target.write_text("old\n", encoding="utf-8")
    merge_env = impl / "bgjob" / "implement-step8-ship.merge.env"
    merge_env.symlink_to(merge_target)
    result = _run_step8(
        impl,
        plugin=plugin,
        args=["--bgjob-child", "--merge-result-env", str(merge_env)],
        extra_env={"STEP8_SHIP_ARGV": str(tmp_path / "ship-argv.txt")},
    )
    assert result.returncode == 3
    assert merge_target.read_text(encoding="utf-8") == "old\n"


def _make_step18_plugin(tmp_path: Path) -> Path:
    plugin = tmp_path / "plugin"
    python_dir = plugin / "python"
    python_dir.mkdir(parents=True)
    cli = python_dir / "cli.py"
    _write_executable(cli, _STEP18_STUB_CLI)
    # Step 19 reaches the Rust-owned session verbs through the verified bootstrap
    # script (issue #8058); forwarding to the stub keeps one recorded argv log.
    (plugin / "scripts").mkdir(parents=True, exist_ok=True)
    _write_executable(
        plugin / "scripts" / "larch.sh",
        f'#!/usr/bin/env bash\nexec python3 "{cli}" "$@"\n',
    )
    return plugin


def _make_step18_impl(tmp_path: Path, name: str) -> Path:
    impl = tmp_path / name
    impl.mkdir()
    _ = (impl / "session-env.sh").write_text(
        f"LARCH_RUN_ID=RUN1\nLARCH_TOKEN_SESSION_ID=tok\n"
        f"LARCH_CLAUDE_SOURCE_FILE=source.jsonl\n"
        f"LARCH_TIMING_LEDGER={impl}/timing-ledger.tsv\n"
        f"REPO_ROOT={_REPO}\n"
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
        "STEP18_REAL_REPO": str(_REPO),
        "PYTHONPATH": str(_REPO / "python"),
        "PATH": f"{fakebin}{os.pathsep}{os.environ.get('PATH', '')}",
    }
    if extra_env:
        env.update(extra_env)
    result = _run_bash(_STEP18_HELPER, env=env, args=args)
    _ = out_path.write_text(result.stdout, encoding="utf-8")
    _ = (out_path.with_suffix(".out.err")).write_text(result.stderr, encoding="utf-8")
    return result


def _run_step19(
    impl: Path, plugin: Path, *, log_path: Path, extra_env: Mapping[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    env = {
        "IMPLEMENT_TMPDIR": str(impl),
        "CLAUDE_PLUGIN_ROOT": str(plugin),
        "STEP18_STUB_LOG": str(log_path),
        "STEP18_REAL_REPO": str(_REPO),
        "PYTHONPATH": str(_REPO / "python"),
    }
    if extra_env:
        env.update(extra_env)
    return _run_bash(_STEP19_HELPER, env=env, args=["--implement-tmpdir", str(impl)])


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
    assert "⏩ 18a: stall recovery; no stall detected" in text, "gate clear breadcrumb"
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


def test_step18_logs_flush_body_then_step19_teardown(tmp_path: Path) -> None:
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
        args=["--phase", "logs-flush", "--step17-emitted", "false"],
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
    assert "FINALIZE_SUBCOMMAND=teardown" not in text
    assert (impl / ".run-log-terminalized").is_file()
    log_text = log.read_text(encoding="utf-8")
    assert "step18b sentinel=false argv=final-report step18b --implement-tmpdir" in log_text, (
        "finalize step18b invocation"
    )
    assert "--step17-emitted false" in log_text, "finalize false step17 flag forwarding"
    assert "prepare-terminal-snapshot --implement-tmpdir" in log_text
    assert "--run-id RUN1 --no-logs-commit false" in log_text
    assert "teardown sentinel=" not in log_text
    assert "SESSION_TRANSCRIPT_STATUS=captured" in text, "finalize transcript status relay"
    assert log_text.index("prepare-terminal-snapshot") < log_text.index("run-log lifecycle-")

    cleanup = _run_step19(impl, plugin, log_path=log)
    assert cleanup.returncode == 0
    assert "ISSUE_URL=https://example.test/issues/1" in cleanup.stdout
    assert "RENAME_BRANCH=skipped" in cleanup.stdout
    assert "RENAME_STATUS=ok" in cleanup.stdout
    assert "STASH_REF=refs/stash/test" in cleanup.stdout
    assert "SENTINEL_WRITTEN=true" in cleanup.stdout
    assert "FINALIZE_SUBCOMMAND=teardown" in cleanup.stdout
    assert "FINALIZE_WARNINGS=none" in cleanup.stdout
    assert "teardown sentinel=before argv=implement-finalize teardown --state-file" in log.read_text(encoding="utf-8")


def test_step18_accepts_disabled_terminalization_without_remote_fields(tmp_path: Path) -> None:
    plugin = _make_step18_plugin(tmp_path)
    impl = _make_step18_impl(tmp_path, "disabled-terminalization")
    out = tmp_path / "disabled-terminalization.out"
    log = tmp_path / "disabled-terminalization.log"
    result = _run_step18(
        tmp_path,
        impl,
        plugin,
        out_path=out,
        log_path=log,
        args=["--phase", "logs-flush", "--step17-emitted", "false"],
        extra_env={"STEP18_STUB_STORAGE_DISABLED": "true", "STEP18_STUB_BODY": "# Final body\n"},
    )

    assert result.returncode == 0
    assert "RUN_LOG_PUBLICATION=skipped-disabled" in result.stdout
    assert "LIFECYCLE_FLUSHED=false" in result.stdout
    assert "LIFECYCLE_TERMINALIZED=true" in result.stdout
    assert "RUN_LOG_PUBLISH_OK=true" in result.stdout
    assert "REMOTE_KEY=" not in result.stdout
    assert "CACHE_DIR=" not in result.stdout
    assert "durable pending state" not in result.stderr


@pytest.mark.parametrize(
    ("failure_env", "returncode", "status_kv", "stderr_text", "published"),
    [
        ("STEP18_STUB_PUBLISH_RC", 9, "RUN_LOG_PUBLISH_OK=false", "durable pending state", True),
        ("STEP18_STUB_SNAPSHOT_RC", 7, "RUN_LOG_FINAL_FLUSH_OK=false", "terminal snapshot preparation failed", False),
    ],
)
def test_step18_terminal_log_failure_preserves_session(
    tmp_path: Path, failure_env: str, returncode: int, status_kv: str, stderr_text: str, published: bool
) -> None:
    plugin = _make_step18_plugin(tmp_path)
    impl = _make_step18_impl(tmp_path, "terminal-log-failure")
    out = tmp_path / "terminal-log-failure.out"
    log = tmp_path / "terminal-log-failure.log"

    result = _run_step18(
        tmp_path,
        impl,
        plugin,
        out_path=out,
        log_path=log,
        args=["--phase", "logs-flush", "--step17-emitted", "false"],
        extra_env={failure_env: str(returncode)},
    )

    assert result.returncode == returncode
    assert status_kv in result.stdout
    assert "---LARCH-SUMMARY-FINAL-BEGIN---" not in result.stdout
    assert stderr_text in result.stderr
    log_text = log.read_text(encoding="utf-8")
    assert ("run-log lifecycle-" in log_text) is published
    assert "prepare-terminal-snapshot" in log_text
    assert "teardown" not in log_text
    assert impl.is_dir()


def test_step18_no_logs_commit_skips_archive_publication(tmp_path: Path) -> None:
    plugin = _make_step18_plugin(tmp_path)
    impl = _make_step18_impl(tmp_path, "publish-suppressed")
    _ = (impl / "run-flags.sh").write_text("NO_LOGS_COMMIT=true\n", encoding="utf-8")
    out = tmp_path / "publish-suppressed.out"
    log = tmp_path / "publish-suppressed.log"

    result = _run_step18(
        tmp_path,
        impl,
        plugin,
        out_path=out,
        log_path=log,
        args=["--phase", "logs-flush", "--step17-emitted", "false"],
        extra_env={"STEP18_STUB_EMIT_BODY": "false"},
    )

    assert result.returncode == 0
    assert "RUN_LOG_PUBLISH_SKIPPED=no-logs-commit" in result.stdout
    log_text = log.read_text(encoding="utf-8")
    assert "prepare-terminal-snapshot" in log_text
    assert "--run-id RUN1 --no-logs-commit true" in log_text
    assert "run-log lifecycle-" not in log_text
    assert "teardown" not in log_text
    assert (impl / ".run-log-terminalized").is_file()

    cleanup = _run_step19(impl, plugin, log_path=log)
    assert cleanup.returncode == 0
    assert "teardown sentinel=" in log.read_text(encoding="utf-8")


def test_step18_step7a_complete_still_prepares_terminal_snapshot(tmp_path: Path) -> None:
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
        args=["--phase", "logs-flush", "--step17-emitted", "false"],
        extra_env={"STEP18_STUB_EMIT_BODY": "false"},
    )
    assert result.returncode == 0
    log_text = log.read_text(encoding="utf-8")
    assert "prepare-terminal-snapshot" in log_text
    assert "SESSION_TRANSCRIPT_STATUS=captured" in result.stdout


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
        args=["--phase", "logs-flush", "--step17-emitted", "true"],
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
        args=["--phase", "logs-flush", "--step17-emitted", "false"],
        extra_env={"STEP18_STUB_WFR_RC": "7", "STEP18_STUB_EMIT_BODY": "true"},
    )
    assert result.returncode == 0
    assert _kv("WFR_RC", result.stdout) == "7", "step18b failure WFR_RC relay"
    assert _count_literal("---LARCH-SUMMARY-FINAL-BEGIN---", result.stdout) == 0, (
        "step18b failure markers suppressed"
    )
    log_text = log.read_text(encoding="utf-8")
    assert "append-failure" in log_text, "step18b failure append log"
    assert "token mark Step 18 — logs flush" in log_text
    assert "prepare-terminal-snapshot" in log_text
    assert "teardown sentinel=" not in log_text


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
        args=["--phase", "logs-flush", "--step17-emitted", "false"],
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
    assert "token mark Step 18 — logs flush" in log_text
    assert "teardown sentinel=" not in log_text


def test_step19_restore_missing_finalize_state(tmp_path: Path) -> None:
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
        args=["--phase", "logs-flush", "--step17-emitted", "false"],
        extra_env={"STEP18_STUB_EMIT_BODY": "false"},
    )
    assert result.returncode == 0
    assert "restore-finalize-state" not in log.read_text(encoding="utf-8")
    cleanup = _run_step19(impl, plugin, log_path=log)
    assert cleanup.returncode == 0
    assert "restore-finalize-state --implement-tmpdir" in log.read_text(encoding="utf-8"), (
        "restore missing finalize state"
    )


def test_step19_restore_ship_stall_truthy(tmp_path: Path) -> None:
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
        args=["--phase", "logs-flush", "--step17-emitted", "false"],
        extra_env={"STEP18_STUB_EMIT_BODY": "false"},
    )
    assert result.returncode == 0
    assert "restore-finalize-state" not in log.read_text(encoding="utf-8")
    cleanup = _run_step19(impl, plugin, log_path=log)
    assert cleanup.returncode == 0
    assert "restore-finalize-state --implement-tmpdir" in log.read_text(encoding="utf-8"), (
        "restore ship stall truthy"
    )


def test_step19_restore_ship_bail_truthy(tmp_path: Path) -> None:
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
        args=["--phase", "logs-flush", "--step17-emitted", "false"],
        extra_env={"STEP18_STUB_EMIT_BODY": "false"},
    )
    assert result.returncode == 0
    assert "restore-finalize-state" not in log.read_text(encoding="utf-8")
    cleanup = _run_step19(impl, plugin, log_path=log)
    assert cleanup.returncode == 0
    assert "restore-finalize-state --implement-tmpdir" in log.read_text(encoding="utf-8"), (
        "restore ship bail truthy"
    )


def test_step19_restore_stall_step_mismatch(tmp_path: Path) -> None:
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
        args=["--phase", "logs-flush", "--step17-emitted", "false"],
        extra_env={"STEP18_STUB_EMIT_BODY": "false"},
    )
    assert result.returncode == 0
    cleanup = _run_step19(impl, plugin, log_path=log)
    assert cleanup.returncode == 0
    log_text = log.read_text(encoding="utf-8")
    assert "restore-finalize-state --implement-tmpdir" in log_text, "restore stall step mismatch"
    mark_line = _line_no("token mark Step 18 — logs flush", log_text)
    snapshot_line = _line_no("prepare-terminal-snapshot", log_text)
    publish_line = _line_no("run-log lifecycle-", log_text)
    restore_line = _line_no("restore-finalize-state", log_text)
    teardown_line = _line_no("teardown sentinel=", log_text)
    assert all(line is not None for line in (mark_line, snapshot_line, publish_line, restore_line, teardown_line)), (
        "ordering log missing expected rows"
    )
    assert mark_line < snapshot_line  # type: ignore[operator]  # pyright cannot narrow int | None across an all(...is not None...) assertion boundary
    assert snapshot_line < publish_line  # type: ignore[operator]  # pyright cannot narrow int | None across an all(...is not None...) assertion boundary
    assert publish_line < restore_line  # type: ignore[operator]  # pyright cannot narrow int | None across an all(...is not None...) assertion boundary
    assert restore_line < teardown_line, "restore-finalize-state must precede teardown"  # type: ignore[operator]  # pyright cannot narrow int | None across an all(...is not None...) assertion boundary


def test_step19_restore_aligned_skips(tmp_path: Path) -> None:
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
        args=["--phase", "logs-flush", "--step17-emitted", "false"],
        extra_env={"STEP18_STUB_EMIT_BODY": "false"},
    )
    assert result.returncode == 0
    cleanup = _run_step19(impl, plugin, log_path=log)
    assert cleanup.returncode == 0
    assert "restore-finalize-state" not in log.read_text(encoding="utf-8"), (
        "restore aligned should skip"
    )


def test_step19_restore_command_failure_still_tears_down(tmp_path: Path) -> None:
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
        args=["--phase", "logs-flush", "--step17-emitted", "false"],
        extra_env={"STEP18_STUB_EMIT_BODY": "false"},
    )
    assert result.returncode == 0
    cleanup = _run_step19(impl, plugin, log_path=log, extra_env={"STEP18_STUB_RESTORE_RC": "7"})
    assert cleanup.returncode == 0
    assert "restore-finalize-state failed" in cleanup.stderr
    log_text = log.read_text(encoding="utf-8")
    assert "teardown sentinel=" in log_text
    assert "restore-finalize-state --implement-tmpdir" in log_text, (
        "restore command failure should be attempted before teardown"
    )


def test_step18_no_run_id_fails_before_safety_nets_and_teardown(tmp_path: Path) -> None:
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
        args=["--phase", "logs-flush", "--step17-emitted", "false"],
        extra_env={"STEP18_STUB_EMIT_BODY": "false", "RUN_ID": ""},
    )
    assert result.returncode == config.EXIT_INTERNAL_ERROR
    assert "RUN_LOG_PUBLISH_OK=false" in result.stdout
    assert "LARCH_RUN_ID is unavailable" in result.stderr
    log_text = log.read_text(encoding="utf-8")
    assert "flush-safety-net" not in log_text, "no run id flush safety net skip"
    assert "capture-transcript" not in log_text, "no run id transcript safety net skip"
    assert "run-log lifecycle-" not in log_text, "no run id publication skip"
    assert "teardown sentinel=" not in log_text, "no run id preserves the session"
    assert impl.is_dir()


def test_step18_post_terminal_logs_flush(tmp_path: Path) -> None:
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
        args=["--phase", "logs-flush", "--step17-emitted", "false"],
        extra_env={"STEP18_STUB_EMIT_BODY": "false"},
    )
    assert result.returncode == 0
    assert "STALL_RECOVERY_REQUIRED" not in result.stdout, "post-terminal logs flush must not re-run gate"
    assert "FINALIZE_SUBCOMMAND=teardown" not in result.stdout
    cleanup = _run_step19(impl, plugin, log_path=log)
    assert cleanup.returncode == 0
    assert "FINALIZE_SUBCOMMAND=teardown" in cleanup.stdout
