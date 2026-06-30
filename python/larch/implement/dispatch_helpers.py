# pyright: reportUnusedFunction=false, reportUnusedCallResult=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportPrivateUsage=false
"""Shared primitives: I/O, git, session, rehydrate, clone-tag, telemetry."""

from __future__ import annotations

import argparse
import hashlib
import os
import shlex
import shutil
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from larch import io as larch_io
from larch.core import logging_util
from larch.implement import phantom
from larch.core import proc

_PLUGIN_ROOT = Path(__file__).resolve().parents[3]
_SAFE_CODERS = {"claude", "codex", "cursor"}
GIT_BIN = shutil.which("git") or "git"
RESUME_CAP = 5
SUMMARY_BULLETS_MAX = 5
PORCELAIN_MIN_PARTS = 2
WRAPPER_VALIDATION_RC = 2
_CLONE_TAG_ALLOWED_BYTES = frozenset(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-")


def _err(message: str) -> None:
    logging_util.diagnostic(message)


def _emit_kv(*, key: str, value: str | int) -> None:
    logging_util.emit_kv(key=key, value=str(value))


def _run(argv: Sequence[str], *, cwd: str | Path | None = None, **kwargs: Any) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(argv),
        cwd=str(cwd) if cwd is not None else None,
        text=True,
        capture_output=True,
        check=False,
        **kwargs,
    )


def _git(repo: Path, *args: str, binary: bool = False) -> subprocess.CompletedProcess[Any]:
    return subprocess.run(
        [GIT_BIN, "-C", str(repo), *args],
        capture_output=True,
        text=not binary,
        check=False,
    )


def _git_stdout(repo: Path, *args: str) -> str:
    result = _git(repo, *args)
    if result.returncode != 0:
        return ""
    return result.stdout.rstrip("\n")


def _write_text_atomic(*, path: Path, text: str) -> None:
    larch_io.atomic_write(path=path, text=text, temp_name=f"{path.name}.tmp")


def _write_bytes_atomic(*, path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(path)


def _parse_kv(text: str) -> dict[str, str]:
    return larch_io.parse_kv(text, first_wins=True, key_pattern=r"^[A-Z0-9_]+$")


def _session_get(*, file: Path, key: str, default: str = "") -> str:
    return larch_io.read_kv(path=file, key=key, default=default, first_match=True, cr_strip="none")


def _binary_available(*, session_env: Path, key: str, binary: str) -> str:
    value = _session_get(file=session_env, key=key, default="")
    if value in {"true", "false"}:
        return value
    return "true" if shutil.which(binary) is not None else "false"


def _current_cli_path() -> Path:
    root = Path(os.environ.get("LARCH_CLAUDE_PLUGIN_ROOT") or os.environ.get("CLAUDE_PLUGIN_ROOT") or _PLUGIN_ROOT)
    return root / "python" / "cli.py"


def _invoke_cli(args: Sequence[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return _run([sys.executable, str(_current_cli_path()), *args], cwd=cwd)


def _resolve_repo_root() -> Path | None:
    result = _run([GIT_BIN, "rev-parse", "--show-toplevel"])
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return Path(result.stdout.strip()).resolve()


def _capture_git_porcelain(*, repo_root: Path, out_file: Path) -> int:
    result = _git(repo_root, "status", "--porcelain=v1", "-z", "--untracked-files=all", binary=True)
    if result.returncode != 0:
        return result.returncode or 1
    _write_bytes_atomic(path=out_file, data=cast("bytes", result.stdout))
    return 0


def _capture_postlaunch_porcelain(*, repo_root: Path, implement_tmpdir: Path) -> int:
    return _capture_git_porcelain(
        repo_root=repo_root,
        out_file=implement_tmpdir / "step2-postlaunch-porcelain.nul",
    )


@dataclass(frozen=True)
class RecoveryParse:
    tuples: set[tuple[str, str]]
    paths: set[str]


def _parse_porcelain_z(path: Path) -> RecoveryParse:
    raw = path.read_bytes() if path.exists() else b""
    items = raw.split(b"\0")
    tuples: set[tuple[str, str]] = set()
    paths: set[str] = set()
    idx = 0
    while idx < len(items):
        rec = items[idx]
        idx += 1
        if not rec:
            continue
        status = rec[:2].decode("ascii", "replace")
        rel = rec[3:].decode("utf-8", "surrogateescape")
        if ("R" in status or "C" in status) and idx < len(items):
            old_item = items[idx]
            idx += 1
            if old_item:
                old_rel = old_item.decode("utf-8", "surrogateescape")
                tuples.add(("D ", old_rel))
                paths.add(old_rel)
        tuples.add((status, rel))
        paths.add(rel)
    return RecoveryParse(tuples, paths)


def _write_prelaunch_digests(*, repo_root: Path, porcelain_file: Path, digests_file: Path) -> None:
    parsed = _parse_porcelain_z(porcelain_file)
    lines: list[str] = []
    for rel in sorted(parsed.paths):
        full = repo_root / rel
        try:
            digest = hashlib.sha256(full.read_bytes()).hexdigest()
        except OSError:
            digest = "missing"
        lines.append(f"{digest}\t{rel}")
    _write_text_atomic(path=digests_file, text="\n".join(lines) + ("\n" if lines else ""))


def _capture_prelaunch_porcelain(*, repo_root: Path, implement_tmpdir: Path) -> int:
    prelaunch_porcelain = implement_tmpdir / "step2-prelaunch-porcelain.nul"
    if prelaunch_porcelain.exists():
        return 0
    rc = _capture_git_porcelain(repo_root=repo_root, out_file=prelaunch_porcelain)
    if rc != 0:
        return rc
    index_probe = _git(repo_root, "diff", "--cached", "--quiet", "--no-ext-diff")
    if index_probe.returncode not in {0, 1}:
        return index_probe.returncode or 1
    index_nonempty = index_probe.returncode != 0
    _write_text_atomic(
        path=implement_tmpdir / "step2-prelaunch-index.env",
        text=f"PRELAUNCH_INDEX_NONEMPTY={str(index_nonempty).lower()}\n",
    )
    _write_prelaunch_digests(
        repo_root=repo_root,
        porcelain_file=prelaunch_porcelain,
        digests_file=implement_tmpdir / "step2-prelaunch-content-digests.txt",
    )
    return 0


def _child_stdout_is_claude_fallback(stdout: str) -> bool:
    status = False
    edit_authority = False
    for line in stdout.splitlines():
        if line == "STATUS=claude_fallback":
            status = True
        elif line == "ORCHESTRATOR_EDIT_AUTHORITY=allowed":
            edit_authority = True
    return status and edit_authority


def _step2_token_mark_eligible(*, coder: str, codex_binary_found: str, cursor_binary_found: str) -> bool:
    return (
        coder == "claude"
        or (coder == "codex" and codex_binary_found != "true")
        or (coder == "cursor" and cursor_binary_found != "true")
    )


def _maybe_mark_step2_telemetry(
    *,
    tmpdir: Path,
    plugin_root: Path,
    env: dict[str, str],
    coder: str,
    codex_binary_found: str,
    cursor_binary_found: str,
    write_sentinel: bool = True,
) -> bool:
    telemetry_marker = tmpdir / ".step2-telemetry-marked"
    if telemetry_marker.exists():
        return True
    if _step2_token_mark_eligible(
        coder=coder,
        codex_binary_found=codex_binary_found,
        cursor_binary_found=cursor_binary_found,
    ):
        token_result = _invoke_cli(["token", "mark", "Step 2 — implementation"])
        if token_result.returncode != 0:
            return False
    timing_result = _run(
        [sys.executable, str(Path(plugin_root) / "python" / "cli.py"), "timing", "mark", "Step 2 — implementation"],
        env={**env, "DESIGN_TMPDIR": "", "LARCH_TIMING_SKILL": "implement"},
    )
    if timing_result.returncode != 0:
        return False
    if write_sentinel:
        _write_text_atomic(path=telemetry_marker, text="true\n")
    return True


def _write_step2_telemetry_sentinel(tmpdir: Path) -> None:
    _write_text_atomic(path=tmpdir / ".step2-telemetry-marked", text="true\n")


def _derive_pathspec_via_recovery_paths(
    *,
    implement_tmpdir: Path,
    repo_root: Path,
    out_file: Path,
) -> int:
    rc = _capture_postlaunch_porcelain(repo_root=repo_root, implement_tmpdir=implement_tmpdir)
    if rc != 0:
        return rc
    result = _invoke_cli(
        [
            "implement",
            "recovery-paths",
            "--repo-root",
            str(repo_root),
            "--tmpdir",
            str(implement_tmpdir),
            "--prelaunch-porcelain",
            str(implement_tmpdir / "step2-prelaunch-porcelain.nul"),
            "--postlaunch-porcelain",
            str(implement_tmpdir / "step2-postlaunch-porcelain.nul"),
            "--prelaunch-digests",
            str(implement_tmpdir / "step2-prelaunch-content-digests.txt"),
            "--out-file",
            str(out_file),
        ],
        cwd=repo_root,
    )
    _forward_child_output_to_stderr(result)
    return result.returncode


def _forward_result(result: subprocess.CompletedProcess[str]) -> int:
    if result.stdout:
        sys.stdout.write(result.stdout)
        sys.stdout.flush()
    if result.stderr:
        sys.stderr.write(result.stderr)
        sys.stderr.flush()
    return result.returncode


def _forward_child_output_to_stderr(result: subprocess.CompletedProcess[str]) -> None:
    if result.stdout:
        sys.stderr.write(result.stdout)
        sys.stderr.flush()
    if result.stderr:
        sys.stderr.write(result.stderr)
        sys.stderr.flush()


def _tmpdir_from_env() -> Path:
    raw = os.environ.get("IMPLEMENT_TMPDIR", "")
    if not raw:
        print("IMPLEMENT_TMPDIR required", file=sys.stderr)
        raise SystemExit(2)
    return Path(raw)


def _rehydrate_plugin_root(implement_tmpdir: Path | None = None) -> Path:
    root = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    if not root and implement_tmpdir:
        plugin_env = implement_tmpdir / "plugin-root.env"
        if plugin_env.is_file():
            value = _session_get(file=plugin_env, key="CLAUDE_PLUGIN_ROOT", default="")
            if value:
                root = value
        if not root:
            value = _session_get(file=implement_tmpdir / "session-env.sh", key="LARCH_CLAUDE_PLUGIN_ROOT", default="")
            if value:
                root = value
    if not root:
        root = str(_PLUGIN_ROOT)
    os.environ["CLAUDE_PLUGIN_ROOT"] = root
    return Path(root)


def _read_session_key_default(*, implement_tmpdir: Path, key: str, default: str = "") -> str:
    return _session_get(file=implement_tmpdir / "session-env.sh", key=key, default=default)


def _rehydrate_larch_triplet(implement_tmpdir: Path) -> None:
    for key in ("LARCH_TOKEN_SESSION_ID", "LARCH_CLAUDE_SOURCE_FILE", "LARCH_TIMING_LEDGER"):
        if not os.environ.get(key):
            value = _read_session_key_default(implement_tmpdir=implement_tmpdir, key=key, default="")
            if value:
                os.environ[key] = value


def _read_kv_file(*, path: Path, key: str, default: str = "") -> str:
    return larch_io.read_kv(path=path, key=key, default=default, first_match=True)


def _tracking_sentinel_values(sentinel: Path) -> dict[str, str]:
    if not sentinel.is_file():
        return {}
    result = _invoke_cli(["tracking-issue", "read", "--sentinel", str(sentinel)])
    return _parse_kv(result.stdout if result.returncode == 0 else "")


def _first_nonempty(*values: str) -> str:
    return next((value for value in values if value), "")


def _pwd_basename(pwd: str) -> str:
    r"""Match bash ``basename \"$PWD\"`` byte behavior on the logical PWD string."""
    path_bytes = os.fsencode(pwd)
    if path_bytes in (b"", b"/"):
        return "/"
    trimmed = path_bytes.rstrip(b"/")
    if not trimmed:
        return "/"
    return os.fsdecode(trimmed.rsplit(b"/", 1)[-1])


def _derive_clone_tag_full(env: Mapping[str, str] | None = None) -> str:
    source_env = os.environ if env is None else env
    clone_tag = source_env.get("CLONE_TAG", "")
    if clone_tag:
        return clone_tag
    basename = _pwd_basename(source_env["PWD"])
    translated = bytes(byte if byte in _CLONE_TAG_ALLOWED_BYTES else ord("_") for byte in os.fsencode(basename))[:32]
    if not translated:
        return "_"
    return translated.decode("ascii")


def _clone_expected_tmpdir_prefix() -> str:
    return f"claude-implement-{_derive_clone_tag_full()}-"


def clone_tag_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py implement clone-tag")
    parser.parse_args(argv)
    clone_tag_full = _derive_clone_tag_full()
    expected_prefix = f"claude-implement-{clone_tag_full}-"
    print(f"CLONE_TAG_FULL={shlex.quote(clone_tag_full)}")
    print(f"EXPECTED_TMPDIR_BASENAME_PREFIX={shlex.quote(expected_prefix)}")
    return 0


def _run_cli_forward(args: Sequence[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> int:
    result = subprocess.run(
        [sys.executable, str(_current_cli_path()), *args],
        cwd=str(cwd) if cwd else None,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    return _forward_result(result)


def _env_value(*, name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def _emit_phantom_probe_with_warn(step: str) -> None:
    result = phantom.probe_with_warn(proc, step=step)
    _emit_kv(key="PHANTOM_STATUS", value=result.dirty.status)
    if result.dirty.reason:
        _emit_kv(key="PHANTOM_REASON", value=result.dirty.reason)
    if result.dirty.status == "phantom":
        _emit_kv(key="PHANTOM_COUNT", value=result.dirty.count)
        _emit_kv(key="PHANTOM_PATHS_FILE", value=result.dirty.paths_file)
    if result.append_warn_error:
        _emit_kv(key="PHANTOM_APPEND_WARN_ERROR", value=result.append_warn_error)
