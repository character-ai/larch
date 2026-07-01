from __future__ import annotations
# pyright: reportUnusedCallResult=false, reportUnknownVariableType=false

import json
import os
import shutil
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
import pytest

from larch.core import config
from larch.state import finalize
from larch.core import logging_util
from larch.core import proc
from larch.state import session_env

CLI = Path(__file__).resolve().parents[2] / "cli.py"
TOOL_ENV_KEYS = ("CODEX_PRESENT", "CURSOR_PRESENT", "CODEX_AVAILABLE", "CURSOR_AVAILABLE", "CODEX_BINARY_FOUND", "CURSOR_BINARY_FOUND")


def clean_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    merged = os.environ.copy()
    for key in TOOL_ENV_KEYS:
        merged.pop(key, None)
    if extra:
        merged.update(extra)
    return merged


def run_cli(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged = clean_env()
    merged["LARCH_QUIET_DISABLE"] = "1"
    if env:
        merged.update(env)
    return subprocess.run(
        [sys.executable, str(CLI), "session", *args],
        text=True,
        capture_output=True,
        env=merged,
        check=False,
    )


def test_read_key_defaults_and_embedded_equals(tmp_path: Path) -> None:
    session = tmp_path / "session-env.sh"
    session.write_text("TOKEN=a=b=c\nEMPTY=\nTOKEN_EXTRA=wrong\n", encoding="utf-8")
    got = run_cli("read-key", "--file", str(session), "--key", "TOKEN")
    assert got.returncode == 0
    assert got.stdout == "a=b=c\n"
    empty = run_cli("read-key", "--file", str(session), "--key", "EMPTY", "--default", "fallback")
    assert empty.stdout == "fallback\n"
    missing = run_cli("read-key", "--file", str(tmp_path / "missing"), "--key", "TOKEN", "--default", "fallback")
    assert missing.returncode == 0
    assert missing.stdout == "fallback\n"
    forgotten = run_cli("read-key", "--key", "TOKEN", "--default", "fallback")
    assert forgotten.returncode == 1


def test_read_keys_batch_order_defaults_and_first_match(tmp_path: Path) -> None:
    session = tmp_path / "session-env.sh"
    session.write_text("SITE=core\nTRIGGER=\nVALUE=a=b=c\nFIRST=one\nFIRST=two\n", encoding="utf-8")
    got = run_cli(
        "read-keys",
        "--file",
        str(session),
        "--key",
        "SITE=unknown",
        "--key",
        "TRIGGER=fallback",
        "--key",
        "VALUE",
        "--key",
        "MISSING=def",
        "--key",
        "ABSENT",
        "--key",
        "FIRST",
    )
    assert got.returncode == 0, got.stderr
    # Input order preserved; embedded '=' kept; empty value -> default;
    # absent+no-default -> empty; first occurrence wins.
    assert got.stdout == "SITE=core\nTRIGGER=fallback\nVALUE=a=b=c\nMISSING=def\nABSENT=\nFIRST=one\n"


def test_read_keys_missing_file_resolves_defaults(tmp_path: Path) -> None:
    got = run_cli("read-keys", "--file", str(tmp_path / "nope"), "--key", "A=1", "--key", "B")
    assert got.returncode == 0
    assert got.stdout == "A=1\nB=\n"


def test_read_keys_requires_file_flag_and_a_key(tmp_path: Path) -> None:
    session = tmp_path / "session-env.sh"
    session.write_text("A=1\n", encoding="utf-8")
    no_file = run_cli("read-keys", "--key", "A=1")
    assert no_file.returncode == 1
    no_key = run_cli("read-keys", "--file", str(session))
    assert no_key.returncode == 1


def test_read_keys_rejects_carriage_return_injection(tmp_path: Path) -> None:
    session = tmp_path / "session-env.sh"
    session.write_text("SAFE=value\rLARCH_TOKEN_SESSION_ID=attacker\n", encoding="utf-8")
    result = run_cli("read-keys", "--file", str(session), "--key", "SAFE")
    assert result.returncode == 1
    assert "carriage return" in result.stderr


def test_write_env_writer_guard_and_plugin_root_only(tmp_path: Path) -> None:
    out = tmp_path / "session-env.sh"
    ok = run_cli(
        "write-env",
        "--output",
        str(out),
        "--repo",
        "owner/repo",
        "--repo-unavailable",
        "false",
        "--codex-present",
        "true",
        "--cursor-present",
        "false",
        "--run-id",
        "RUN_1",
        env={"CLAUDE_PLUGIN_ROOT": "/tmp/larch-plugin"},
    )
    assert ok.returncode == 0, ok.stderr
    text = out.read_text(encoding="utf-8")
    assert "REPO=owner/repo\n" in text
    assert "CODEX_AVAILABLE" not in text
    assert "CODEX_PRESENT" not in text
    assert "LARCH_RUN_ID=RUN_1\n" in text
    assert (tmp_path / "plugin-root.env").read_text(encoding="utf-8") == "CLAUDE_PLUGIN_ROOT=/tmp/larch-plugin\nexport CLAUDE_PLUGIN_ROOT\n"
    bad = run_cli("write-env", "--output", "/etc/larch-session-env", "--repo-unavailable", "false")
    assert bad.returncode == 1
    null = run_cli("write-env", "--output", "/dev/null", "--repo-unavailable", "false")
    assert null.returncode == 0
    plugin = tmp_path / "plugin-root.env"
    only = run_cli("write-env", "--plugin-root-only", "--output", str(plugin), "--value", "/tmp/plugin-root")
    assert only.returncode == 0
    assert "CLAUDE_PLUGIN_ROOT=/tmp/plugin-root" in plugin.read_text(encoding="utf-8")


def test_write_env_writer_guard_rejects_cr_lf_symlink_and_disallowed_keys(tmp_path: Path) -> None:
    out = tmp_path / "session-env.sh"
    for bad_value, flag in (("token\nid", "--token-session-id"), ("token\rid", "--token-session-id"), ("run\nid", "--run-id")):
        result = run_cli("write-env", "--output", str(out), "--repo-unavailable", "false", flag, bad_value)
        assert result.returncode == 1, (bad_value, result.stderr)
        assert "newline or carriage return" in result.stderr or "Invalid" in result.stderr
    with pytest.raises(ValueError, match="disallowed writer key"):
        session_env._validate_writer_keys(data={"EVIL_KEY": "x"}, allowed=session_env.WRITE_ENV_KEYS)  # pyright: ignore[reportPrivateUsage]
    link = tmp_path / "session-env-link"
    link.symlink_to(out)
    symlink = run_cli("write-env", "--output", str(link), "--repo-unavailable", "false")
    assert symlink.returncode == 1


def test_external_timeout_default_invalid_empty_zero_and_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(config.ENV_LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT, raising=False)
    assert session_env._external_timeout() == "60"  # pyright: ignore[reportPrivateUsage]

    monkeypatch.setenv(config.ENV_LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT, "bad")
    assert session_env._external_timeout() == "60"  # pyright: ignore[reportPrivateUsage]

    monkeypatch.setenv(config.ENV_LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT, "")
    assert session_env._external_timeout() == "60"  # pyright: ignore[reportPrivateUsage]

    monkeypatch.setenv(config.ENV_LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT, "0")
    assert session_env._external_timeout() == "0"  # pyright: ignore[reportPrivateUsage]

    monkeypatch.setenv(config.ENV_LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT, "45")
    assert session_env._external_timeout() == "45"  # pyright: ignore[reportPrivateUsage]


def test_read_key_rejects_carriage_return_injection(tmp_path: Path) -> None:
    session = tmp_path / "session-env.sh"
    session.write_text("SAFE=value\rLARCH_TOKEN_SESSION_ID=attacker\n", encoding="utf-8")
    result = run_cli("read-key", "--file", str(session), "--key", "SAFE")
    assert result.returncode == 1
    assert "carriage return" in result.stderr


def test_validate_design_tmpdir_main_accepts_allowlisted_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TMPDIR", str(tmp_path))

    rc = session_env.validate_design_tmpdir_main([str(tmp_path / "sub")])

    assert rc == 0


def test_validate_design_tmpdir_main_requires_path(capsys: pytest.CaptureFixture[str]) -> None:
    rc = session_env.validate_design_tmpdir_main([])

    assert rc == 2
    assert "path is required" in capsys.readouterr().err


def test_validate_design_tmpdir_main_rejects_disallowed_prefix(capsys: pytest.CaptureFixture[str]) -> None:
    rc = session_env.validate_design_tmpdir_main(["/var/tmp/x"])

    assert rc == 2
    assert "allowlist" in capsys.readouterr().err


def test_validate_design_tmpdir_main_writes_no_quiet_log_before_allowlist(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    disallowed = Path("/var/tmp") / f"larch-test-session-env-disallowed-{os.getpid()}"
    try:
        disallowed.mkdir()
    except OSError as exc:
        pytest.skip(f"/var/tmp unavailable for disallowed-path check: {exc}")
    try:
        monkeypatch.setenv("TMPDIR", str(tmp_path))
        monkeypatch.setenv("DESIGN_TMPDIR", str(disallowed))

        rc = session_env.validate_design_tmpdir_main([str(disallowed)])

        assert rc == 2
        assert "allowlist" in capsys.readouterr().err
        assert not list(disallowed.glob("larch-quiet-*.log"))
    finally:
        shutil.rmtree(disallowed, ignore_errors=True)


def test_write_design_env_relative_tmpdir_stderr_parity(tmp_path: Path) -> None:
    out = tmp_path / "source-env.sh"
    result = run_cli(
        "write-design-env",
        "--output",
        str(out),
        "--design-tmpdir",
        "relative/path",
        "--session-id",
        "sid-1",
        env={"HOME": str(tmp_path / "home"), "XDG_CACHE_HOME": str(tmp_path / "xdg"), "CLAUDE_PLUGIN_ROOT": "/tmp/plugin"},
    )
    assert result.returncode == 1
    assert result.stderr.count("ERROR=") == 1
    assert "ERROR=Invalid --design-tmpdir: must be an absolute path" in result.stderr


def test_write_design_env_source_safe_and_home_symlink(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    xdg = tmp_path / "xdg"
    design = tmp_path / "design dir"
    design.mkdir()
    out = tmp_path / "source-env.sh"
    env = {"HOME": str(home), "XDG_CACHE_HOME": str(xdg), "CLAUDE_PLUGIN_ROOT": "/tmp/plugin"}
    result = run_cli(
        "write-design-env",
        "--output",
        str(out),
        "--design-tmpdir",
        str(design),
        "--session-id",
        "sid-1",
        "--codex-present",
        "true",
        "--claude-pid",
        "12345",
        env=env,
    )
    assert result.returncode == 0, result.stderr
    source = subprocess.run(["bash", "-c", f"source {out}; printf '%s|%s|%s' \"$DESIGN_TMPDIR\" \"${{CODEX_PRESENT:-}}\" \"$CLAUDE_PLUGIN_ROOT\""], text=True, capture_output=True, env=clean_env(), check=False)
    assert source.stdout == f"{design}||/tmp/plugin"
    link = home / ".cache" / "larch" / "sessions" / "current-design-env-12345.sh"
    assert link.is_symlink()
    assert link.readlink() == out
    launcher = home / ".cache" / "larch" / "sessions" / "design-run-12345.sh"
    assert launcher.is_file()
    launcher_text = launcher.read_text(encoding="utf-8")
    assert launcher_text.startswith("#!/usr/bin/env bash\n")
    assert launcher.stat().st_mode & 0o111
    assert 'SESSION_ENV_PATH="$HOME/.cache/larch/sessions/current-design-env-12345.sh"' in launcher_text
    assert 'export CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT"' in launcher_text
    assert '--session-env-path "$SESSION_ENV_PATH"' in launcher_text
    assert '--claude-pid "$CLAUDE_PID"' in launcher_text
    assert "skills/design/scripts/$script" in launcher_text
    assert 'design step2b-drafter --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID" "$@"' in launcher_text
    assert 'design step2b-postplan --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID" "$@"' in launcher_text
    assert 'design step2b5 --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID" "$@"' in launcher_text
    assert 'plan validator-autofix --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID" "$@"' in launcher_text
    assert 'design stage-terminal-state "$@"' in launcher_text
    assert 'design failure-report "$@"' in launcher_text
    assert 'design step-final-summary --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID" "$@"' in launcher_text


def test_write_design_env_requires_plugin_root_with_claude_pid(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    design = tmp_path / "design"
    design.mkdir()
    out = tmp_path / "source-env.sh"
    env = {"HOME": str(home), "XDG_CACHE_HOME": str(tmp_path / "xdg"), "CLAUDE_PLUGIN_ROOT": ""}
    result = run_cli(
        "write-design-env",
        "--output",
        str(out),
        "--design-tmpdir",
        str(design),
        "--session-id",
        "sid-1",
        "--claude-pid",
        "12345",
        env=env,
    )
    assert result.returncode == 1
    assert "ERROR=" in result.stderr
    assert not (home / ".cache" / "larch" / "sessions" / "design-run-12345.sh").exists()

    invalid = run_cli(
        "write-design-env",
        "--output",
        str(out),
        "--design-tmpdir",
        str(design),
        "--session-id",
        "sid-1",
        "--claude-pid",
        "12345",
        env={**env, "CLAUDE_PLUGIN_ROOT": "relative/plugin"},
    )
    assert invalid.returncode == 1
    assert "ERROR=" in invalid.stderr
    assert not (home / ".cache" / "larch" / "sessions" / "design-run-12345.sh").exists()


def test_write_design_env_launcher_rejects_symlink_ancestor(tmp_path: Path) -> None:
    home = tmp_path / "home"
    cache = home / ".cache"
    cache.mkdir(parents=True)
    redirected = tmp_path / "redirected"
    redirected.mkdir()
    (cache / "larch").symlink_to(redirected)
    design = tmp_path / "design"
    design.mkdir()
    out = tmp_path / "source-env.sh"
    result = run_cli(
        "write-design-env",
        "--output",
        str(out),
        "--design-tmpdir",
        str(design),
        "--session-id",
        "sid-1",
        "--claude-pid",
        "12345",
        env={"HOME": str(home), "XDG_CACHE_HOME": str(tmp_path / "xdg"), "CLAUDE_PLUGIN_ROOT": "/tmp/plugin"},
    )
    assert result.returncode == 1
    assert "ERROR=" in result.stderr
    assert not (redirected / "sessions" / "design-run-12345.sh").exists()


def test_write_design_env_legacy_pid_omission_does_not_create_launcher(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    design = tmp_path / "design"
    design.mkdir()
    out = tmp_path / "source-env.sh"
    result = run_cli(
        "write-design-env",
        "--output",
        str(out),
        "--design-tmpdir",
        str(design),
        "--session-id",
        "sid-1",
        env={"HOME": str(home), "XDG_CACHE_HOME": str(tmp_path / "xdg"), "CLAUDE_PLUGIN_ROOT": "/tmp/plugin"},
    )
    assert result.returncode == 0, result.stderr
    assert (home / ".cache" / "larch" / "sessions" / "current-design-env.sh").is_symlink()
    assert not (home / ".cache" / "larch" / "sessions" / "design-run-.sh").exists()


def _write_launcher_for_test(tmp_path: Path) -> tuple[Path, Path]:
    home = tmp_path / "home"
    home.mkdir()
    plugin_root = tmp_path / "plugin"
    script_dir = plugin_root / "skills" / "design" / "scripts"
    script_dir.mkdir(parents=True)
    wrapper = script_dir / "fake-wrapper.sh"
    wrapper.write_text(
        "#!/usr/bin/env bash\n"
        "printf 'root=%s\n' \"$CLAUDE_PLUGIN_ROOT\"\n"
        "printf 'argv=%s\n' \"$*\"\n",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    cli = plugin_root / "python" / "cli.py"
    cli.parent.mkdir(parents=True)
    cli.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "print('cliargv=' + ' '.join(sys.argv[1:]))\n",
        encoding="utf-8",
    )
    cli.chmod(0o755)
    design = tmp_path / "design"
    design.mkdir()
    out = tmp_path / "source-env.sh"
    env = {"HOME": str(home), "XDG_CACHE_HOME": str(tmp_path / "xdg"), "CLAUDE_PLUGIN_ROOT": str(plugin_root)}
    result = run_cli(
        "write-design-env",
        "--output",
        str(out),
        "--design-tmpdir",
        str(design),
        "--session-id",
        "sid-1",
        "--claude-pid",
        "12345",
        env=env,
    )
    assert result.returncode == 0, result.stderr
    return home / ".cache" / "larch" / "sessions" / "design-run-12345.sh", home


def test_design_run_launcher_dispatches_wrapper(tmp_path: Path) -> None:
    launcher, home = _write_launcher_for_test(tmp_path)
    dispatch = subprocess.run(
        [str(launcher), "fake-wrapper.sh", "--example", "value"],
        text=True,
        capture_output=True,
        env={**os.environ, "HOME": str(home)},
        check=False,
    )
    assert dispatch.returncode == 0, dispatch.stderr
    assert "root=" in dispatch.stdout
    assert "argv=--session-env-path " in dispatch.stdout
    assert "current-design-env-12345.sh --claude-pid 12345 --example value" in dispatch.stdout


def test_design_run_launcher_dispatches_verb(tmp_path: Path) -> None:
    launcher, home = _write_launcher_for_test(tmp_path)
    dispatch = subprocess.run(
        [str(launcher), "step0-route", "--issue-number", "42"],
        text=True,
        capture_output=True,
        env={**os.environ, "HOME": str(home)},
        check=False,
    )
    assert dispatch.returncode == 0, dispatch.stderr
    assert "cliargv=design step0-route --session-env-path " in dispatch.stdout
    assert "current-design-env-12345.sh --claude-pid 12345 --issue-number 42" in dispatch.stdout


def test_design_run_launcher_maps_retired_step2_wrappers_to_cli_with_tail(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    plugin_root = tmp_path / "plugin"
    cli_py = plugin_root / "python" / "cli.py"
    cli_py.parent.mkdir(parents=True)
    cli_py.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "print('ARGV=' + ' '.join(sys.argv[1:]))\n",
        encoding="utf-8",
    )
    cli_py.chmod(0o755)
    design = tmp_path / "design"
    design.mkdir()
    out = tmp_path / "source-env.sh"
    env = {"HOME": str(home), "XDG_CACHE_HOME": str(tmp_path / "xdg"), "CLAUDE_PLUGIN_ROOT": str(plugin_root)}
    result = run_cli(
        "write-design-env",
        "--output",
        str(out),
        "--design-tmpdir",
        str(design),
        "--session-id",
        "sid-1",
        "--claude-pid",
        "12345",
        env=env,
    )
    assert result.returncode == 0, result.stderr
    launcher = home / ".cache" / "larch" / "sessions" / "design-run-12345.sh"
    postplan = subprocess.run(
        [str(launcher), "design-step2b-postplan.sh", "--site", "gate-b", "--snapshot-original"],
        text=True,
        capture_output=True,
        env={**os.environ, "HOME": str(home)},
        check=False,
    )
    assert postplan.returncode == 0, postplan.stderr
    assert "ARGV=design step2b-postplan --session-env-path" in postplan.stdout
    assert "--site gate-b --snapshot-original" in postplan.stdout
    validator = subprocess.run(
        [str(launcher), "design-step-validator-autofix.sh", "--validator-target-file", "target.md", "--validate-defect-count", "3"],
        text=True,
        capture_output=True,
        env={**os.environ, "HOME": str(home)},
        check=False,
    )
    assert validator.returncode == 0, validator.stderr
    assert "ARGV=plan validator-autofix --session-env-path" in validator.stdout
    assert "--validator-target-file target.md --validate-defect-count 3" in validator.stdout
    stage = subprocess.run(
        [str(launcher), "design-stage-terminal-state.sh", "--design-tmpdir", str(design), "--outcome", "failed-clarify"],
        text=True,
        capture_output=True,
        env={**os.environ, "HOME": str(home)},
        check=False,
    )
    assert stage.returncode == 0, stage.stderr
    assert "ARGV=design stage-terminal-state --design-tmpdir" in stage.stdout
    failure = subprocess.run(
        [str(launcher), "design-failure-report.sh", "--design-tmpdir", str(design), "--outcome", "approved"],
        text=True,
        capture_output=True,
        env={**os.environ, "HOME": str(home)},
        check=False,
    )
    assert failure.returncode == 0, failure.stderr
    assert "ARGV=design failure-report --design-tmpdir" in failure.stdout
    final = subprocess.run(
        [str(launcher), "design-step-final-summary.sh", "--outcome", "approved"],
        text=True,
        capture_output=True,
        env={**os.environ, "HOME": str(home)},
        check=False,
    )
    assert final.returncode == 0, final.stderr
    assert "ARGV=design step-final-summary --session-env-path" in final.stdout
    assert "--claude-pid 12345 --outcome approved" in final.stdout


def test_design_run_launcher_dispatches_non_hyphenated_verbs(tmp_path: Path) -> None:
    launcher, home = _write_launcher_for_test(tmp_path)
    for verb in ("step0c", "step1d5", "step1d7"):
        dispatch = subprocess.run([str(launcher), verb], text=True, capture_output=True, env={**os.environ, "HOME": str(home)}, check=False)
        assert dispatch.returncode == 0, dispatch.stderr
        assert f"cliargv=design {verb} --session-env-path " in dispatch.stdout


def test_design_run_launcher_rejects_invalid_script_names(tmp_path: Path) -> None:
    launcher, home = _write_launcher_for_test(tmp_path)
    bad_args = ([], ["dir/script.sh"], ["../script.sh"], ["script.py"], ["step0-route.sh"], ["not-ported"], ["bad;name.sh"])
    for args in bad_args:
        bad = subprocess.run([str(launcher), *args], text=True, capture_output=True, env={**os.environ, "HOME": str(home)}, check=False)
        assert bad.returncode == 2, args
        assert "ERROR=" in bad.stderr

def test_write_design_env_launcher_write_failure_is_fatal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    design = tmp_path / "design"
    design.mkdir()
    out = tmp_path / "source-env.sh"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg"))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", "/tmp/plugin")
    real_atomic_write = session_env._atomic_write  # pyright: ignore[reportPrivateUsage]

    def fake_atomic_write(path: Path, text: str, *, create_parent: bool = False, mode: int = 0o600) -> None:
        if path.name == "design-run-12345.sh":
            raise OSError("launcher write failed")
        real_atomic_write(path=path, text=text, create_parent=create_parent, mode=mode)

    monkeypatch.setattr(session_env, "_atomic_write", fake_atomic_write)
    rc = session_env.write_design_env_main(
        [
            "--output",
            str(out),
            "--design-tmpdir",
            str(design),
            "--session-id",
            "sid-1",
            "--claude-pid",
            "12345",
        ]
    )
    assert rc == 1
    assert not (home / ".cache" / "larch" / "sessions" / "design-run-12345.sh").exists()


def test_write_run_params(tmp_path: Path) -> None:
    out = tmp_path / "run-params.json"
    result = run_cli(
        "write-run-params",
        "--output",
        str(out),
        "--partition-requested",
        "true",
    )
    assert result.returncode == 0
    assert f"RUN_PARAMS_WRITTEN={out}" in result.stdout
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schema_version"] == 3
    assert data["partition_requested"] is True
    missing_parent = run_cli("write-run-params", "--output", str(tmp_path / "nope" / "x.json"))
    assert missing_parent.returncode == 1


def test_persist_run_flags_write_id_and_entry_gate(tmp_path: Path) -> None:
    flags = run_cli(
        "persist-run-flags",
        "--implement-tmpdir",
        str(tmp_path),
        "--no-issues",
        "false",
        "--force-requested",
        "true",
        "--self-implement-requested",
        "true",
    )
    assert flags.returncode == 0
    assert flags.stdout == "RUN_FLAGS_PERSISTED=true\n"
    run_flags_text = (tmp_path / "run-flags.sh").read_text(encoding="utf-8")
    assert "FORCE_REQUESTED=true\n" in run_flags_text
    assert "SELF_IMPLEMENT_REQUESTED=true\n" in run_flags_text
    missing = run_cli("persist-run-flags", "--implement-tmpdir", str(tmp_path))
    assert missing.returncode == 2
    sid = tmp_path / "session-id"
    first = run_cli("write-id", "--output", str(sid))
    assert first.returncode == 0
    original = sid.read_text(encoding="utf-8")
    sid.write_text("keep\n", encoding="utf-8")
    second = run_cli("write-id", "--output", str(sid))
    assert second.returncode == 0
    assert sid.read_text(encoding="utf-8") == "keep\n"
    gate = run_cli("entry-gate", "--mode", "implement", "--current-branch", "feature", "--is-main", "false", "--is-user-branch", "true", "--user-prefix", "user")
    assert gate.returncode == 0
    assert "ENTRY_GATE=continue" in gate.stdout
    assert original


def test_restore_finalize_state_raw_rhs_and_20_keys(tmp_path: Path) -> None:
    (tmp_path / "ship-pr-state.sh").write_text(
        "BRANCH_NAME=feature\nPR_TITLE=Implement $(echo x)=y\nSTALL_TRACKING=false\nBAIL_REASON=needs=user\nRUN_ID=RUN1\n",
        encoding="utf-8",
    )
    (tmp_path / "finalize-state.sh").write_text("STALL_TRACKING=true\nSTALL_STEP=18a\n", encoding="utf-8")
    result = run_cli("restore-finalize-state", "--implement-tmpdir", str(tmp_path))
    assert result.returncode == 0
    lines = (tmp_path / "finalize-state.sh").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 20
    assert "PR_TITLE=Implement $(echo x)=y" in lines
    assert "STALL_TRACKING=true" in lines
    assert "STALL_STEP=18a" in lines
    assert (tmp_path / "final-bail-reason.txt").read_text(encoding="utf-8") == "needs=user"


def test_restore_finalize_state_missing_finalize_file(tmp_path: Path) -> None:
    (tmp_path / "ship-pr-state.sh").write_text("BRANCH_NAME=feature\nBAIL_REASON=\nRUN_ID=\n", encoding="utf-8")
    result = run_cli("restore-finalize-state", "--implement-tmpdir", str(tmp_path))
    assert result.returncode == 0
    assert (tmp_path / "finalize-state.sh").is_file()


def test_write_design_env_legacy_symlink_warning(tmp_path: Path) -> None:
    home = tmp_path / "shim-home"
    home.mkdir()
    design = tmp_path / "shim" / "design"
    design.mkdir(parents=True)
    out = tmp_path / "shim" / "source-env.sh"
    env = {"HOME": str(home), "XDG_CACHE_HOME": str(tmp_path / "xdg"), "CLAUDE_PLUGIN_ROOT": "/tmp/plugin"}
    result = run_cli(
        "write-design-env",
        "--output",
        str(out),
        "--design-tmpdir",
        str(design),
        "--session-id",
        "SHIM-1",
        env=env,
    )
    assert result.returncode == 0, result.stderr
    legacy = home / ".cache" / "larch" / "sessions" / "current-design-env.sh"
    assert legacy.is_symlink()
    assert legacy.readlink() == out
    assert "claude-pid omitted" in result.stderr


def test_write_design_env_partial_codex_override_clears_binary(tmp_path: Path) -> None:
    out = tmp_path / "source-env.sh"
    env = {"HOME": str(tmp_path / "home"), "XDG_CACHE_HOME": str(tmp_path / "xdg"), "CLAUDE_PLUGIN_ROOT": "/tmp/plugin"}
    design = tmp_path / "design"
    design.mkdir()
    seed = run_cli(
        "write-design-env",
        "--output",
        str(out),
        "--design-tmpdir",
        str(design),
        "--session-id",
        "PARTIAL-SEED",
        "--codex-present",
        "true",
        "--cursor-present",
        "true",
        "--codex-available",
        "false",
        "--cursor-available",
        "true",
        "--codex-binary-found",
        "true",
        "--cursor-binary-found",
        "false",
        "--claude-pid",
        "8888881",
        env=env,
    )
    assert seed.returncode == 0, seed.stderr
    override = run_cli(
        "write-design-env",
        "--output",
        str(out),
        "--design-tmpdir",
        str(design),
        "--session-id",
        "PARTIAL-OVERRIDE",
        "--codex-present",
        "false",
        "--claude-pid",
        "8888881",
        env=env,
    )
    assert override.returncode == 0, override.stderr
    source = subprocess.run(
        ["bash", "-c", f"set -u; source {out}; printf '%s|%s|%s|%s|%s|%s' \"$SESSION_ID\" \"${{CODEX_PRESENT:-}}\" \"${{CODEX_AVAILABLE:-}}\" \"${{CURSOR_PRESENT:-}}\" \"${{CURSOR_AVAILABLE:-}}\" \"${{CURSOR_BINARY_FOUND:-}}\""],
        text=True,
        capture_output=True,
        env=clean_env(),
        check=False,
    )
    assert source.returncode == 0, source.stderr
    assert source.stdout == "PARTIAL-OVERRIDE|||||false"
    text = out.read_text(encoding="utf-8")
    assert "CODEX_PRESENT" not in text
    assert "CODEX_AVAILABLE" not in text


def test_write_design_env_strict_boolean_recovery(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    out = tmp_path / "source-env.sh"
    out.write_text(
        "#!/usr/bin/env bash\n"
        "export CODEX_PRESENT=true\n"
        "export CURSOR_PRESENT=$(touch /tmp/larch-wdce-should-not-exist)\n"
        "export CODEX_AVAILABLE=maybe\n"
        "export CURSOR_AVAILABLE=false\n",
        encoding="utf-8",
    )
    marker = Path("/tmp/larch-wdce-should-not-exist")
    marker.unlink(missing_ok=True)
    env = {"HOME": str(tmp_path / "home"), "XDG_CACHE_HOME": str(tmp_path / "xdg"), "CLAUDE_PLUGIN_ROOT": "/tmp/plugin"}
    result = run_cli(
        "write-design-env",
        "--output",
        str(out),
        "--design-tmpdir",
        str(design),
        "--session-id",
        "STRICT-RECOVERY",
        "--claude-pid",
        "42",
        env=env,
    )
    assert result.returncode == 0, result.stderr
    assert not marker.exists()
    source = subprocess.run(
        ["bash", "-c", f"set -u; source {out}; printf '%s|%s' \"${{CODEX_PRESENT:-}}\" \"${{CURSOR_AVAILABLE:-}}\""],
        text=True,
        capture_output=True,
        env=clean_env(),
        check=False,
    )
    assert source.returncode == 0, source.stderr
    assert source.stdout == "|"
    text = out.read_text(encoding="utf-8")
    assert "CURSOR_PRESENT" not in text
    assert "CODEX_AVAILABLE" not in text


def test_write_env_xdg_session_root_and_design_symlink_under_home_cache(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    xdg = tmp_path / "xdg-cache"
    xdg.mkdir()
    session_root = xdg / "larch" / "sessions" / "claude-design-test"
    session_root.mkdir(parents=True)
    design = session_root / "design"
    design.mkdir()
    session_env = session_root / "session-env.sh"
    source_env = session_root / "source-env.sh"
    env = {"HOME": str(home), "XDG_CACHE_HOME": str(xdg), "CLAUDE_PLUGIN_ROOT": "/tmp/plugin"}
    write_env = run_cli(
        "write-env",
        "--output",
        str(session_env),
        "--repo-unavailable",
        "false",
        env=env,
    )
    assert write_env.returncode == 0, write_env.stderr
    write_design = run_cli(
        "write-design-env",
        "--output",
        str(source_env),
        "--design-tmpdir",
        str(design),
        "--session-id",
        "xdg-root",
        "--claude-pid",
        "55555",
        env=env,
    )
    assert write_design.returncode == 0, write_design.stderr
    home_link = home / ".cache" / "larch" / "sessions" / "current-design-env-55555.sh"
    xdg_link = xdg / "larch" / "sessions" / "current-design-env-55555.sh"
    assert home_link.is_symlink()
    assert home_link.readlink() == source_env
    assert not xdg_link.exists()


def test_write_design_env_refresh_preserves_prior_bools(tmp_path: Path) -> None:
    out = tmp_path / "source-env.sh"
    env = {"HOME": str(tmp_path / "home"), "XDG_CACHE_HOME": str(tmp_path / "xdg"), "CLAUDE_PLUGIN_ROOT": "/tmp/plugin"}
    design = tmp_path / "design"
    design.mkdir()
    first = run_cli(
        "write-design-env",
        "--output",
        str(out),
        "--design-tmpdir",
        str(design),
        "--session-id",
        "sid-1",
        "--codex-present",
        "true",
        "--cursor-present",
        "false",
        "--claude-pid",
        "42",
        env=env,
    )
    assert first.returncode == 0, first.stderr
    second = run_cli(
        "write-design-env",
        "--output",
        str(out),
        "--design-tmpdir",
        str(design),
        "--session-id",
        "sid-1",
        "--claude-pid",
        "42",
        env=env,
    )
    assert second.returncode == 0, second.stderr
    text = out.read_text(encoding="utf-8")
    assert "CODEX_PRESENT" not in text
    assert "CURSOR_PRESENT" not in text


def test_write_env_rejects_invalid_run_id(tmp_path: Path) -> None:
    out = tmp_path / "session-env.sh"
    bad = run_cli(
        "write-env",
        "--output",
        str(out),
        "--repo-unavailable",
        "false",
        "--run-id",
        "bad id",
        env={"CLAUDE_PLUGIN_ROOT": "/tmp/larch-plugin"},
    )
    assert bad.returncode == 1


def test_repo_from_gh_or_git_falls_back_when_gh_missing() -> None:
    class MissingGhRunner:
        def run(
            self,
            argv: Sequence[str],
            *,
            timeout: float | None = None,
            cwd: str | None = None,
            env: Mapping[str, str] | None = None,
            check: bool = False,
            stdout: int | None = None,
            stderr: int | None = None,
        ) -> proc.CommandResult:
            del timeout, cwd, env, check, stdout, stderr
            if argv and argv[0] == "gh":
                raise FileNotFoundError("gh")
            if len(argv) >= 4 and list(argv[-3:]) == ["gh", "remote-repo", "origin"]:
                return proc.CommandResult(tuple(argv), 0, "owner/repo\n", "", 0.0)
            return proc.CommandResult(tuple(argv), 1, "", "", 0.0)

    assert session_env._repo_from_gh_or_git(MissingGhRunner()) == "owner/repo"  # pyright: ignore[reportPrivateUsage]


def test_setup_uses_caller_env_repo_without_gh(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    caller = tmp_path / "caller.env"
    caller.write_text("REPO=caller/repo\nREPO_UNAVAILABLE=false\n", encoding="utf-8")
    out = tmp_path / "session-env.sh"
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    result = run_cli(
        "setup",
        "--prefix",
        "pytest-",
        "--skip-preflight",
        "--skip-branch-check",
        "--write-session-env",
        str(out),
        "--caller-env",
        str(caller),
    )
    assert result.returncode == 0, result.stderr
    assert "REPO=caller/repo" in out.read_text(encoding="utf-8")


def test_setup_repo_fallback_without_gh(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = tmp_path / "session-env.sh"
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)

    def fake_run(argv: list[str], **_kwargs: object) -> proc.CommandResult:
        if argv and argv[0] == "gh":
            raise FileNotFoundError("gh")
        if len(argv) >= 4 and list(argv[-3:]) == ["gh", "remote-repo", "origin"]:
            return proc.CommandResult(tuple(argv), 0, "git-owner/repo\n", "", 0.0)
        return proc.CommandResult(tuple(argv), 0, "", "", 0.0)

    monkeypatch.setattr(session_env.proc, "run", fake_run)
    rc = session_env.setup_main(
        [
            "--prefix",
            "pytest-",
            "--skip-preflight",
            "--skip-branch-check",
            "--write-session-env",
            str(out),
        ],
    )
    assert rc == 0
    assert "REPO=git-owner/repo" in out.read_text(encoding="utf-8")


def test_setup_runs_admission_preflight_without_skip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = tmp_path / "session-env.sh"
    calls: list[tuple[str, ...]] = []
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))

    def fake_run(argv: Sequence[str], **_kwargs: object) -> proc.CommandResult:
        calls.append(tuple(argv))
        if len(argv) >= 3 and argv[-2:] == ["admission", "preflight"]:
            return proc.CommandResult(tuple(argv), 0, "PREFLIGHT=ok\n", "", 0.0)
        if argv and "check-stale-plugin.sh" in argv[0]:
            return proc.CommandResult(tuple(argv), 0, "", "", 0.0)
        if argv and argv[0] == "gh":
            return proc.CommandResult(tuple(argv), 1, "", "", 0.0)
        if len(argv) >= 4 and list(argv[-3:]) == ["gh", "remote-repo", "origin"]:
            return proc.CommandResult(tuple(argv), 0, "owner/repo\n", "", 0.0)
        if argv and argv[0] in {"codex", "cursor"}:
            return proc.CommandResult(tuple(argv), 1, "", "", 0.0)
        return proc.CommandResult(tuple(argv), 0, "", "", 0.0)

    monkeypatch.setattr(session_env.proc, "run", fake_run)
    rc = session_env.setup_main(
        [
            "--prefix",
            "pytest-",
            "--skip-branch-check",
            "--write-session-env",
            str(out),
        ],
    )
    assert rc == 0
    assert any("admission" in call and "preflight" in call for call in calls)


def test_local_cleanup_rejects_main_branch() -> None:
    result = run_cli("local-cleanup", "--branch", "main")
    assert result.returncode == 1
    assert "must not be 'main'" in result.stderr


def test_cleanup_tmpdir_allowlist_and_cache_roots(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", "relative-cache")
    monkeypatch.setenv("HOME", "")
    assert session_env.cleanup_cache_sessions_root() == Path("relative-cache/larch/sessions")
    assert finalize.cache_sessions_root().is_absolute()
    target = tmp_path / "cleanup-me"
    target.mkdir()
    result = run_cli("cleanup-tmpdir", "--dir", str(target), env={"TMPDIR": str(tmp_path)})
    assert result.returncode == 0
    assert not target.exists()
    assert (tmp_path / "larch-cleanup-audit.log").is_file()
    bad = run_cli("cleanup-tmpdir", "--dir", "/etc/not-larch")
    assert bad.returncode == 1


def test_read_key_emits_on_fd3_under_quiet_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(config.ENV_LARCH_QUIET_DISABLE, raising=False)
    monkeypatch.setenv(config.ENV_IMPLEMENT_TMPDIR, str(tmp_path))
    logging_util.reset_quiet_state()
    session = tmp_path / "session-env.sh"
    session.write_text("TOKEN=secret-value\n", encoding="utf-8")
    read_fd, write_fd = os.pipe()
    saved_stdout = os.dup(1)
    try:
        os.dup2(write_fd, 1)
        os.close(write_fd)
        rc = session_env.read_key_main(["--file", str(session), "--key", "TOKEN"])
        os.dup2(saved_stdout, 1)
        contract = os.read(read_fd, 4096).decode()
    finally:
        os.close(read_fd)
        os.close(saved_stdout)
    assert rc == 0
    assert contract == "secret-value\n"


def test_setup_writes_session_id_and_keepalive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cache = tmp_path / "cache"
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache))
    result = run_cli(
        "setup",
        "--prefix",
        "claude-implement",
        "--skip-preflight",
        "--skip-repo-check",
    )
    assert result.returncode == 0, result.stderr
    session_tmpdir = ""
    session_id = ""
    for line in result.stdout.splitlines():
        if line.startswith("SESSION_TMPDIR="):
            session_tmpdir = line.split("=", 1)[1]
        elif line.startswith("SESSION_ID="):
            session_id = line.split("=", 1)[1]
    assert session_tmpdir.startswith(str(cache / "larch" / "sessions" / "claude-implement-"))
    assert session_id
    assert "LARCH_RENDER_CACHE_DIR=" in result.stdout
    tmpdir = Path(session_tmpdir)
    session_id_file = (tmpdir / "session-id").read_text(encoding="utf-8").strip()
    assert session_id_file == session_id
    sentinel = (tmpdir / ".larch-keepalive").read_text(encoding="utf-8")
    assert "# larch session identity (hook routing)" in sentinel
    assert f"CLONE_PATH={Path.cwd()}" in sentinel
    assert f"SESSION_ID={session_id}" in sentinel
    assert not any(line.startswith(("PID=", "PPID=", "PREFIX=", "CREATED=", "NOTE=")) for line in sentinel.splitlines())


def _make_implement_candidate(
    root: Path,
    name: str,
    cwd: str,
    *,
    sentinel: str = "design-export/manifest.env",
    session_id: str = "sid-1",
    mtime: int = 1000,
    keepalive_text: str | None = None,
) -> Path:
    candidate = root / f"claude-implement-{name}"
    candidate.mkdir(parents=True)
    if keepalive_text is None:
        keepalive_text = f"# larch session identity (hook routing)\nCLONE_PATH={cwd}\nSESSION_ID={session_id}\n"
    (candidate / ".larch-keepalive").write_text(keepalive_text, encoding="utf-8")
    sentinel_path = candidate / sentinel
    sentinel_path.parent.mkdir(parents=True, exist_ok=True)
    sentinel_path.write_text("sentinel\n", encoding="utf-8")
    os.utime(sentinel_path, (mtime, mtime))
    return candidate


def test_resolve_implement_tmpdir_empty_cwd_and_roots(tmp_path: Path) -> None:
    env = {"HOME": "", "XDG_CACHE_HOME": str(tmp_path / "xdg")}
    assert session_env.implement_session_roots(env=env)[0] == tmp_path / "xdg" / "larch" / "sessions"
    assert session_env.implement_session_roots(env={"HOME": ""})[0] == Path("/tmp/.cache/larch/sessions")
    assert session_env.resolve_implement_tmpdir("", env=env, now=1000) == ""
    cli = run_cli("resolve-implement-tmpdir")
    assert cli.returncode == 0
    assert cli.stdout == ""


def test_resolve_implement_tmpdir_routes_clone_path_and_embedded_equals(tmp_path: Path) -> None:
    root = tmp_path / "cache" / "larch" / "sessions"
    cwd = str(tmp_path / "repo=name")
    other = str(tmp_path / "repo-other")
    wanted = _make_implement_candidate(root, "wanted", cwd, mtime=2000)
    _make_implement_candidate(root, "other", other, mtime=3000)
    env = {"XDG_CACHE_HOME": str(tmp_path / "cache"), "HOME": ""}
    assert session_env.resolve_implement_tmpdir(cwd, env=env, now=2500) == str(wanted)


def test_resolve_implement_tmpdir_session_id_disambiguates_and_disqualifies(tmp_path: Path) -> None:
    root = tmp_path / "cache" / "larch" / "sessions"
    cwd = str(tmp_path / "repo")
    wanted = _make_implement_candidate(root, "sid-a", cwd, session_id="sid-a", mtime=1000)
    _make_implement_candidate(root, "sid-b", cwd, session_id="sid-b", mtime=3000)
    env = {"XDG_CACHE_HOME": str(tmp_path / "cache"), "LARCH_TOKEN_SESSION_ID": "sid-a"}
    assert session_env.resolve_implement_tmpdir(cwd, env=env, now=25000) == str(wanted)
    env["LARCH_TOKEN_SESSION_ID"] = "sid-missing"
    assert session_env.resolve_implement_tmpdir(cwd, env=env, now=25000) == ""


def test_resolve_implement_tmpdir_legacy_sentinels_and_acceptance_order(tmp_path: Path) -> None:
    root = tmp_path / "cache" / "larch" / "sessions"
    cwd = str(tmp_path / "repo")
    first_order = _make_implement_candidate(root, "first-order", cwd, sentinel="design-export/manifest.env", mtime=1000)
    review = first_order / "review-round-summary.md"
    review.write_text("newer review\n", encoding="utf-8")
    os.utime(review, (5000, 5000))
    expected = _make_implement_candidate(root, "review-only", cwd, sentinel="review-round-summary.md", mtime=3000)
    _make_implement_candidate(root, "bump", cwd, sentinel=".bump-version-armed", mtime=2000)
    _make_implement_candidate(root, "release", cwd, sentinel=".release-armed", mtime=2500)
    env = {"XDG_CACHE_HOME": str(tmp_path / "cache"), "LARCH_IMPLEMENT_TMPDIR_TTL_SECONDS": "0", "LARCH_TOKEN_SESSION_ID": ""}
    assert session_env.resolve_implement_tmpdir(cwd, env=env, now=10000) == str(expected)


@pytest.mark.parametrize("sentinel", [".bump-version-armed", ".release-armed"])
def test_resolve_implement_tmpdir_legacy_sentinel_only_candidate(
    tmp_path: Path, sentinel: str
) -> None:
    root = tmp_path / "cache" / "larch" / "sessions"
    cwd = str(tmp_path / "repo")
    expected = _make_implement_candidate(root, "legacy-only", cwd, sentinel=sentinel, mtime=1000)
    env = {"XDG_CACHE_HOME": str(tmp_path / "cache"), "LARCH_IMPLEMENT_TMPDIR_TTL_SECONDS": "0", "LARCH_TOKEN_SESSION_ID": ""}
    assert session_env.resolve_implement_tmpdir(cwd, env=env, now=5000) == str(expected)


@pytest.mark.parametrize("sentinel", [".bump-version-armed", ".release-armed"])
def test_resolve_implement_tmpdir_legacy_sentinel_newest_candidate(
    tmp_path: Path, sentinel: str
) -> None:
    root = tmp_path / "cache" / "larch" / "sessions"
    cwd = str(tmp_path / "repo")
    _make_implement_candidate(root, "older", cwd, sentinel="design-export/manifest.env", mtime=1000)
    expected = _make_implement_candidate(root, "legacy-newest", cwd, sentinel=sentinel, mtime=3000)
    env = {"XDG_CACHE_HOME": str(tmp_path / "cache"), "LARCH_IMPLEMENT_TMPDIR_TTL_SECONDS": "0", "LARCH_TOKEN_SESSION_ID": ""}
    assert session_env.resolve_implement_tmpdir(cwd, env=env, now=5000) == str(expected)


def test_resolve_implement_tmpdir_ttl_and_session_bypass(tmp_path: Path) -> None:
    root = tmp_path / "cache" / "larch" / "sessions"
    cwd = str(tmp_path / "repo")
    fresh = _make_implement_candidate(root, "fresh", cwd, mtime=800)
    _make_implement_candidate(root, "equal-stale", cwd, mtime=1000 - 21600)
    env = {"XDG_CACHE_HOME": str(tmp_path / "cache")}
    assert session_env.resolve_implement_tmpdir(cwd, env=env, now=1000) == str(fresh)
    env = {"XDG_CACHE_HOME": str(tmp_path / "cache"), "LARCH_IMPLEMENT_TMPDIR_TTL_SECONDS": "200"}
    assert session_env.resolve_implement_tmpdir(cwd, env=env, now=1000) == ""
    env = {"XDG_CACHE_HOME": str(tmp_path / "cache"), "LARCH_IMPLEMENT_TMPDIR_TTL_SECONDS": "bogus"}
    assert session_env.resolve_implement_tmpdir(cwd, env=env, now=1000) == str(fresh)
    env = {"XDG_CACHE_HOME": str(tmp_path / "cache"), "LARCH_IMPLEMENT_TMPDIR_TTL_SECONDS": "0", "LARCH_TOKEN_SESSION_ID": ""}
    assert session_env.resolve_implement_tmpdir(cwd, env=env, now=1000) == str(fresh)
    env = {"XDG_CACHE_HOME": str(tmp_path / "cache"), "LARCH_TOKEN_SESSION_ID": "sid-1"}
    assert session_env.resolve_implement_tmpdir(cwd, env=env, now=0) == str(fresh)


def test_resolve_implement_tmpdir_newest_tie_and_malformed_skip(tmp_path: Path) -> None:
    root = tmp_path / "cache" / "larch" / "sessions"
    cwd = str(tmp_path / "repo")
    lex_winner = _make_implement_candidate(root, "aaa", cwd, mtime=1000)
    _make_implement_candidate(root, "bbb", cwd, mtime=1000)
    newest = _make_implement_candidate(root, "newest", cwd, mtime=2000)
    _make_implement_candidate(
        root,
        "malformed",
        cwd,
        mtime=3000,
        keepalive_text=f"CLONE_PATH={cwd}\rSESSION_ID=sid-1\n",
    )
    env = {"XDG_CACHE_HOME": str(tmp_path / "cache"), "LARCH_IMPLEMENT_TMPDIR_TTL_SECONDS": "0"}
    assert session_env.resolve_implement_tmpdir(cwd, env=env, now=4000) == str(newest)
    newest.joinpath("design-export/manifest.env").unlink()
    assert session_env.resolve_implement_tmpdir(cwd, env=env, now=4000) == str(lex_winner)


def test_resolve_implement_tmpdir_cli_output(tmp_path: Path) -> None:
    root = tmp_path / "cache" / "larch" / "sessions"
    cwd = str(tmp_path / "repo")
    wanted = _make_implement_candidate(root, "cli", cwd, mtime=1000)
    env = {"XDG_CACHE_HOME": str(tmp_path / "cache"), "LARCH_IMPLEMENT_TMPDIR_TTL_SECONDS": "0", "LARCH_TOKEN_SESSION_ID": ""}
    resolved = run_cli("resolve-implement-tmpdir", "--cwd", cwd, env=env)
    assert resolved.returncode == 0, resolved.stderr
    assert resolved.stdout == str(wanted)
    missing = run_cli("resolve-implement-tmpdir", "--cwd", str(tmp_path / "missing"), env=env)
    assert missing.returncode == 0
    assert missing.stdout == ""


def test_ignore_placeholder_run_dirs_drops_only_run_n() -> None:
    names = ["run-1", "run-22", "run-abc", "shared", "run", "0199F1E2-2238-403D-89F3-AAAAAAAAAAAA"]
    assert session_env._ignore_placeholder_run_dirs(_="/x", names=names) == {"run-1", "run-22"}  # pyright: ignore[reportPrivateUsage]


def test_setup_carry_forward_drops_placeholder_run_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # A fresh session must not inherit a previous session's non-unique run-1 dir
    # (issue #4397), but real UUID run dirs and shared/ are carried for resume.
    cache = tmp_path / "cache"
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache))
    prev = tmp_path / "prev"
    uuid_dir = "0199F1E2-2238-403D-89F3-F37CA6989999"
    for rel in (f"implement/{uuid_dir}", "implement/run-1", "shared"):
        (prev / "larch-logs" / rel).mkdir(parents=True)
    _ = (prev / "larch-logs" / "implement" / uuid_dir / "manifest.json").write_text("{}", encoding="utf-8")
    _ = (prev / "larch-logs" / "implement" / "run-1" / "manifest.json").write_text("{}", encoding="utf-8")
    _ = (prev / "larch-logs" / "shared" / "state.json").write_text("{}", encoding="utf-8")
    caller_env = tmp_path / "caller.env"
    _ = caller_env.write_text(f"PREV_IMPLEMENT_TMPDIR={prev}\n", encoding="utf-8")
    result = run_cli(
        "setup",
        "--prefix",
        "claude-implement",
        "--skip-preflight",
        "--skip-repo-check",
        "--caller-env",
        str(caller_env),
    )
    assert result.returncode == 0, result.stderr
    session_tmpdir = ""
    for line in result.stdout.splitlines():
        if line.startswith("SESSION_TMPDIR="):
            session_tmpdir = line.split("=", 1)[1]
    assert session_tmpdir
    carried = Path(session_tmpdir) / "larch-logs"
    assert (carried / "implement" / uuid_dir / "manifest.json").is_file()
    assert (carried / "shared" / "state.json").is_file()
    assert not (carried / "implement" / "run-1").exists()


def test_setup_presence_defaults_with_check_reviewers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    stub_bin = tmp_path / "bin"
    stub_bin.mkdir()
    (stub_bin / "codex").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    (stub_bin / "cursor").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    (stub_bin / "codex").chmod(0o755)
    (stub_bin / "cursor").chmod(0o755)
    cache = tmp_path / "cache"
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache))
    reviewer_env = {
        "PATH": f"{stub_bin}:{os.environ.get('PATH', '')}",
        "LARCH_LIB_CURSOR_AUTH_TEST_MODE": "1",
        "LIB_CURSOR_AUTH_TEST_UNAME": "Linux",
    }

    env1 = tmp_path / "env1.txt"
    env1.write_text("", encoding="utf-8")
    out1 = tmp_path / "session-env1.txt"
    result1 = run_cli(
        "setup",
        "--prefix",
        "test-presence-1",
        "--skip-preflight",
        "--skip-repo-check",
        "--caller-env",
        str(env1),
        "--check-reviewers",
        "--write-session-env",
        str(out1),
        env=reviewer_env,
    )
    assert result1.returncode == 0, result1.stderr
    for key in ("CODEX_PRESENT=true", "CURSOR_PRESENT=true", "CODEX_BINARY_FOUND=true", "CURSOR_BINARY_FOUND=true"):
        assert key in result1.stdout
    assert "CODEX_AVAILABLE" not in result1.stdout
    text1 = out1.read_text(encoding="utf-8")
    assert "CODEX_PRESENT" not in text1
    assert "CURSOR_PRESENT" not in text1
    assert "CODEX_BINARY_FOUND=true\n" in text1
    assert "CURSOR_BINARY_FOUND=true\n" in text1

    env2 = tmp_path / "env2.txt"
    env2.write_text("CODEX_PRESENT=false\nCURSOR_PRESENT=true\n", encoding="utf-8")
    out2 = tmp_path / "session-env2.txt"
    result2 = run_cli(
        "setup",
        "--prefix",
        "test-presence-2",
        "--skip-preflight",
        "--skip-repo-check",
        "--caller-env",
        str(env2),
        "--check-reviewers",
        "--write-session-env",
        str(out2),
        env=reviewer_env,
    )
    assert result2.returncode == 0, result2.stderr
    assert "CODEX_PRESENT=true" in result2.stdout
    assert "CURSOR_PRESENT=true" in result2.stdout
    text2 = out2.read_text(encoding="utf-8")
    assert "CODEX_PRESENT" not in text2
    assert "CURSOR_PRESENT" not in text2
    assert "CODEX_BINARY_FOUND=true\n" in text2

    env3 = tmp_path / "env3.txt"
    env3.write_text(
        "CODEX_PRESENT=true\nCURSOR_PRESENT=false\nLARCH_DYNAMIC_ARCHETYPES_MAX=1\n",
        encoding="utf-8",
    )
    out3 = tmp_path / "session-env3.txt"
    result3 = run_cli(
        "setup",
        "--prefix",
        "test-presence-3",
        "--skip-preflight",
        "--skip-repo-check",
        "--caller-env",
        str(env3),
        "--check-reviewers",
        "--write-session-env",
        str(out3),
        env=reviewer_env,
    )
    assert result3.returncode == 0, result3.stderr
    assert "LARCH_DYNAMIC_ARCHETYPES_MAX=1\n" in out3.read_text(encoding="utf-8")

    env4 = tmp_path / "env4.txt"
    env4.write_text(
        "CODEX_PRESENT=true\nCURSOR_PRESENT=false\nLARCH_DYNAMIC_ARCHETYPES_MAX=9\n",
        encoding="utf-8",
    )
    out4 = tmp_path / "session-env4.txt"
    result4 = run_cli(
        "setup",
        "--prefix",
        "test-presence-4",
        "--skip-preflight",
        "--skip-repo-check",
        "--caller-env",
        str(env4),
        "--check-reviewers",
        "--write-session-env",
        str(out4),
        env=reviewer_env,
    )
    assert result4.returncode == 0, result4.stderr
    assert "LARCH_DYNAMIC_ARCHETYPES_MAX=" not in out4.read_text(encoding="utf-8")
    assert "ignoring invalid LARCH_DYNAMIC_ARCHETYPES_MAX" in result4.stderr


def test_entry_gate_accepts_explicit_empty_current_branch() -> None:
    gate = run_cli(
        "entry-gate",
        "--mode",
        "implement",
        "--current-branch",
        "",
        "--is-main",
        "true",
        "--is-user-branch",
        "false",
        "--user-prefix",
        "sergey",
    )
    assert gate.returncode == 0
    assert "ENTRY_GATE=strict" in gate.stdout
    assert "SKIP_BRANCH_CHECK=false" in gate.stdout
    design = run_cli(
        "entry-gate",
        "--mode",
        "design",
        "--current-branch",
        "",
        "--is-main",
        "true",
        "--is-user-branch",
        "false",
        "--user-prefix",
        "sergey",
        "--branch-info-supplied",
        "true",
    )
    assert design.returncode == 0
    assert "ENTRY_GATE=continue" in design.stdout


def test_entry_gate_failure_matrix() -> None:
    base = ("--mode", "implement", "--current-branch", "main", "--is-main", "true", "--is-user-branch", "false", "--user-prefix", "sergey")

    def expect_success(expected_gate: str, expected_skip: str, *args: str) -> None:
        result = run_cli("entry-gate", *args)
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == f"ENTRY_GATE={expected_gate}\nSKIP_BRANCH_CHECK={expected_skip}"
        assert result.stderr == ""

    def expect_failure(substring: str, *args: str) -> None:
        result = run_cli("entry-gate", *args)
        assert result.returncode == 4, (result.stdout, result.stderr)
        assert result.stdout == ""
        assert "GATE_ERROR=" in result.stderr or "error:" in result.stderr.lower()
        assert substring in result.stderr

    expect_success("strict", "false", *base)
    expect_success("continue", "true", "--mode", "implement", "--current-branch", "sergey/foo", "--is-main", "false", "--is-user-branch", "true", "--user-prefix", "sergey")
    expect_success("strict", "false", "--mode", "implement", "--current-branch", "random-branch", "--is-main", "false", "--is-user-branch", "false", "--user-prefix", "sergey")
    expect_success("strict", "false", "--mode", "implement", "--current-branch", "", "--is-main", "true", "--is-user-branch", "false", "--user-prefix", "sergey")
    expect_success("continue", "true", "--mode", "design", "--current-branch", "sergey/foo", "--is-main", "false", "--is-user-branch", "true", "--user-prefix", "sergey", "--branch-info-supplied", "false")
    expect_success("continue", "true", "--mode", "design", "--current-branch", "main", "--is-main", "true", "--is-user-branch", "false", "--user-prefix", "sergey", "--branch-info-supplied", "true")
    expect_success("strict", "false", "--mode", "design", "--current-branch", "main", "--is-main", "true", "--is-user-branch", "false", "--user-prefix", "sergey", "--branch-info-supplied", "false")
    expect_success("strict", "false", "--mode", "design", "--current-branch", "random-branch", "--is-main", "false", "--is-user-branch", "false", "--user-prefix", "sergey", "--branch-info-supplied", "false")
    expect_success("continue", "true", "--mode", "design", "--current-branch", "", "--is-main", "true", "--is-user-branch", "false", "--user-prefix", "sergey", "--branch-info-supplied", "true")

    expect_failure("invalid mode", "--mode", "foo", "--current-branch", "main", "--is-main", "true", "--is-user-branch", "false", "--user-prefix", "sergey")
    expect_failure("missing required flag --mode", "--current-branch", "main", "--is-main", "true", "--is-user-branch", "false", "--user-prefix", "sergey")
    expect_failure("expected one argument", "--mode")
    expect_failure("invalid value for --is-main", "--mode", "implement", "--current-branch", "main", "--is-main", "yes", "--is-user-branch", "false", "--user-prefix", "sergey")
    expect_failure("invalid value for --is-user-branch", "--mode", "implement", "--current-branch", "main", "--is-main", "true", "--is-user-branch", "", "--user-prefix", "sergey")
    expect_failure("expected one argument", "--mode", "implement", "--current-branch", "main", "--is-main")
    expect_failure("missing required flag --current-branch", "--mode", "implement", "--is-main", "true", "--is-user-branch", "false", "--user-prefix", "sergey")
    expect_failure("--user-prefix must be non-empty", "--mode", "implement", "--current-branch", "main", "--is-main", "true", "--is-user-branch", "false", "--user-prefix", "")
    expect_failure("missing required flag --user-prefix", "--mode", "implement", "--current-branch", "main", "--is-main", "true", "--is-user-branch", "false")
    expect_failure("--branch-info-supplied not allowed for mode=implement", *base, "--branch-info-supplied", "true")
    expect_failure("--branch-info-supplied not allowed for mode=implement", *base, "--branch-info-supplied", "false")
    expect_failure("unknown argument", *base, "--bogus")


def test_write_run_params_rejects_empty_boolean_flags(tmp_path: Path) -> None:
    out = tmp_path / "run-params.json"
    invalid = run_cli(
        "write-run-params",
        "--output",
        str(out),
        "--partition-requested",
        "",
    )
    assert invalid.returncode == 2
    assert "requires a value" in invalid.stderr


def test_cleanup_tmpdir_fails_when_removal_blocked(tmp_path: Path) -> None:
    target = tmp_path / "cleanup-me"
    target.mkdir()
    (target / "keep").write_text("x", encoding="utf-8")
    if os.name != "nt":
        target.chmod(0o555)
        try:
            result = run_cli("cleanup-tmpdir", "--dir", str(target), env={"TMPDIR": str(tmp_path)})
            assert result.returncode == 1
            assert target.exists()
            assert "cleanup-tmpdir failed" in result.stderr
        finally:
            target.chmod(0o755)


def test_cleanup_tmpdir_succeeds_when_target_already_absent(tmp_path: Path) -> None:
    target = tmp_path / "already-gone"
    result = run_cli("cleanup-tmpdir", "--dir", str(target), env={"TMPDIR": str(tmp_path)})
    assert result.returncode == 0
    assert result.stderr == ""


def _git(args: list[str], *, cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)
    if check and completed.returncode != 0:
        msg = f"git {' '.join(args)} failed: {completed.stderr}"
        raise RuntimeError(msg)
    return completed


def _config_git_identity(repo: Path) -> None:
    _git(["config", "user.email", "ci@test"], cwd=repo)
    _git(["config", "user.name", "Test CI"], cwd=repo)


def _commit_path(repo: Path, rel: str, content: str, subject: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content + "\n", encoding="utf-8")
    _git(["add", "--", rel], cwd=repo)
    _git(["commit", "-q", "-m", subject], cwd=repo)


def _setup_remote_repo(tmp_path: Path, label: str) -> Path:
    remote = tmp_path / f"{label}-origin.git"
    seed = tmp_path / f"{label}-seed"
    repo = tmp_path / f"{label}-repo"
    _git(["init", "-q", "--bare", str(remote)], cwd=tmp_path)
    seed.mkdir()
    _git(["init", "-q"], cwd=seed)
    _git(["symbolic-ref", "HEAD", "refs/heads/main"], cwd=seed)
    _config_git_identity(seed)
    _commit_path(seed, "README.md", "initial", "init")
    _git(["remote", "add", "origin", str(remote)], cwd=seed)
    _git(["push", "-q", "-u", "origin", "main"], cwd=seed)
    _git(["symbolic-ref", "HEAD", "refs/heads/main"], cwd=remote)
    _git(["clone", "-q", str(remote), str(repo)], cwd=tmp_path)
    _git(["checkout", "-q", "main"], cwd=repo)
    _config_git_identity(repo)
    _git(["branch", "feature"], cwd=repo)
    return repo


def _run_local_cleanup(repo: Path, *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    merged["LARCH_QUIET_DISABLE"] = "1"
    if env:
        merged.update(env)
    return subprocess.run(
        [sys.executable, str(CLI), "session", "local-cleanup", "--branch", "feature"],
        cwd=repo,
        text=True,
        capture_output=True,
        env=merged,
        check=False,
    )


@pytest.mark.skipif(shutil.which("git") is None, reason="git required for local-cleanup integration tests")
def test_local_cleanup_flush_orphan_non_flush_and_squash_gap(tmp_path: Path) -> None:
    prefix = config.FLUSH_COMMIT_SUBJECT_PREFIX

    flush_repo = _setup_remote_repo(tmp_path, "flush-orphan")
    _commit_path(
        flush_repo,
        "larch-logs/implement/prior-run/session-transcript.jsonl",
        '{"type":"message","text":"prior"}',
        f"{prefix}implement run prior-run",
    )
    flush_origin = _git(["rev-parse", "origin/main"], cwd=flush_repo).stdout.strip()
    flush_result = _run_local_cleanup(flush_repo)
    assert "CLEANUP_SUCCESS=true" in flush_result.stdout
    assert "BRANCH_DELETED=true" in flush_result.stdout
    assert "Dropping 1 prior-run larch-log flush commit(s)" in flush_result.stderr
    assert _git(["rev-parse", "HEAD"], cwd=flush_repo).stdout.strip() == flush_origin

    non_flush_repo = _setup_remote_repo(tmp_path, "non-flush-ahead")
    _commit_path(non_flush_repo, "operator-note.txt", "keep me", "operator local note")
    non_flush_origin = _git(["rev-parse", "origin/main"], cwd=non_flush_repo).stdout.strip()
    non_flush_result = _run_local_cleanup(non_flush_repo)
    assert "CLEANUP_SUCCESS=true" in non_flush_result.stdout
    assert "Dropping" not in non_flush_result.stderr
    assert _git(["rev-parse", "HEAD"], cwd=non_flush_repo).stdout.strip() != non_flush_origin
    assert (non_flush_repo / "operator-note.txt").is_file()

    squash_repo = _setup_remote_repo(tmp_path, "squash-gap")
    remote_url = _git(["remote", "get-url", "origin"], cwd=squash_repo).stdout.strip()
    _commit_path(
        squash_repo,
        "larch-logs/implement/squash-gap/session-transcript.jsonl",
        '{"type":"message","text":"flush-only"}',
        f"{prefix}implement run squash-gap",
    )
    pusher = tmp_path / "squash-gap-pusher"
    _git(["clone", "-q", remote_url, str(pusher)], cwd=tmp_path)
    _config_git_identity(pusher)
    _commit_path(pusher, "landed-from-pr.txt", "squash simulation", "feat: simulate post-merge remote advance")
    _git(["push", "-q", "origin", "main"], cwd=pusher)
    expected = _git(["rev-parse", "HEAD"], cwd=pusher).stdout.strip()
    squash_result = _run_local_cleanup(squash_repo)
    assert "CLEANUP_SUCCESS=true" in squash_result.stdout
    assert "BRANCH_DELETED=true" in squash_result.stdout
    assert "Dropping 1 prior-run larch-log flush commit(s)" in squash_result.stderr
    assert _git(["rev-parse", "HEAD"], cwd=squash_repo).stdout.strip() == expected


def test_write_and_clear_implement_env_pointer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    impl = tmp_path / "sessions" / "impl"
    impl.mkdir(parents=True)
    cwd = tmp_path / "repo"
    cwd.mkdir()

    rc = session_env.write_implement_env_main(
        ["--claude-pid", "12345", "--implement-tmpdir", str(impl), "--cwd", str(cwd)]
    )

    pointer = home / ".cache" / "larch" / "sessions" / "current-implement-env-12345.sh"
    assert rc == 0
    assert pointer.read_text(encoding="utf-8") == (
        f"IMPLEMENT_TMPDIR={impl}\nREPO_CWD={cwd}\nSKILL_KIND=implement\n"
    )

    clear_rc = session_env.clear_implement_pointer_main(["--claude-pid", "12345"])

    assert clear_rc == 0
    assert not pointer.exists()


def test_write_implement_env_rejects_bad_pid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    impl = tmp_path / "impl"
    impl.mkdir()
    cwd = tmp_path / "repo"
    cwd.mkdir()

    rc = session_env.write_implement_env_main(
        ["--claude-pid", "0", "--implement-tmpdir", str(impl), "--cwd", str(cwd)]
    )

    assert rc == 1
    assert not (home / ".cache" / "larch" / "sessions").exists()


def test_write_design_env_persists_claude_source_file(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    design = tmp_path / "design"
    design.mkdir()
    out = tmp_path / "source-env.sh"
    source_file = design / "claude-source.env"
    result = run_cli(
        "write-design-env",
        "--output",
        str(out),
        "--design-tmpdir",
        str(design),
        "--session-id",
        "sid-1",
        "--claude-pid",
        "12345",
        "--claude-source-file",
        str(source_file),
        env={"HOME": str(home), "XDG_CACHE_HOME": str(tmp_path / "xdg"), "CLAUDE_PLUGIN_ROOT": "/tmp/plugin"},
    )
    assert result.returncode == 0, result.stderr
    assert f"LARCH_CLAUDE_SOURCE_FILE={source_file}\n" in out.read_text(encoding="utf-8")
