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

from tests.support.repo_contract import repo_root

_REPO = repo_root()
_IMPLEMENT_SCRIPTS = _REPO / "skills" / "implement" / "scripts"
_STEP8_HELPER = _IMPLEMENT_SCRIPTS / "step-8-ship.sh"
_STEP8_GUARD = _IMPLEMENT_SCRIPTS / "step-8-python-guard.sh"
_STEP8_SEEDER = _IMPLEMENT_SCRIPTS / "step-8-seed-initial.sh"
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

