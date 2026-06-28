# pyright: reportUnusedFunction=false, reportUnusedCallResult=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportPrivateUsage=false
"""Ship seed context management and step 2 post-dispatch."""

from __future__ import annotations

import argparse
from pathlib import Path

from larch.implement.dispatch_helpers import (
    _emit_kv,
    _emit_phantom_probe_with_warn,
    _err,
    _read_kv_file,
    _rehydrate_plugin_root,
    _run,
    _tmpdir_from_env,
    _write_text_atomic,
    GIT_BIN,
)


def _seed_kv_nonempty(*, lines: list[str], key: str) -> bool:
    prefix = f"{key}="
    for line in lines:
        if line.startswith(prefix):
            return bool(line[len(prefix):].strip())
    return False


def _upsert_seed_kv(*, lines: list[str], key: str, value: str) -> None:
    prefix = f"{key}="
    for index, line in enumerate(lines):
        if line.startswith(prefix):
            lines[index] = f"{prefix}{value}"
            return
    lines.append(f"{prefix}{value}")


def _read_ship_seed_lines(implement_tmpdir: Path) -> list[str]:
    seed_file = implement_tmpdir / "ship-seed-input.env"
    if seed_file.is_file() and not seed_file.is_symlink():
        return seed_file.read_text(encoding="utf-8", errors="replace").splitlines()
    return []


def _write_ship_seed_lines(*, implement_tmpdir: Path, lines: list[str]) -> None:
    seed_file = implement_tmpdir / "ship-seed-input.env"
    _write_text_atomic(path=seed_file, text="\n".join(lines) + ("\n" if lines else ""))


def _persist_ship_seed_context(implement_tmpdir: Path) -> None:
    lines = _read_ship_seed_lines(implement_tmpdir)
    if not _seed_kv_nonempty(lines=lines, key="MANIFEST_PATH"):
        manifest = ""
        if (implement_tmpdir / "codex-step2-out" / "manifest.json").is_file():
            manifest = str(implement_tmpdir / "codex-step2-out" / "manifest.json")
        elif (implement_tmpdir / "manifest.json").is_file():
            manifest = str(implement_tmpdir / "manifest.json")
        _upsert_seed_kv(lines=lines, key="MANIFEST_PATH", value=manifest)
    if not _seed_kv_nonempty(lines=lines, key="TOOL_LABEL"):
        coder_value = _read_kv_file(path=implement_tmpdir / "bootstrap-routing.env", key="coder", default="")
        tool_label = "Codex" if coder_value == "codex" else "Cursor" if coder_value == "cursor" else "claude"
        _upsert_seed_kv(lines=lines, key="TOOL_LABEL", value=tool_label)
    _write_ship_seed_lines(implement_tmpdir=implement_tmpdir, lines=lines)


def _mark_dispatcher_committed(implement_tmpdir: Path) -> None:
    lines = _read_ship_seed_lines(implement_tmpdir)
    _upsert_seed_kv(lines=lines, key="DISPATCHER_COMMITTED", value="true")
    _write_ship_seed_lines(implement_tmpdir=implement_tmpdir, lines=lines)


def _clear_external_dispatch_seed(implement_tmpdir: Path) -> None:
    lines = _read_ship_seed_lines(implement_tmpdir)
    _upsert_seed_kv(lines=lines, key="MANIFEST_PATH", value="")
    _upsert_seed_kv(lines=lines, key="DISPATCHER_COMMITTED", value="")
    _write_ship_seed_lines(implement_tmpdir=implement_tmpdir, lines=lines)


def step2_post_dispatch_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py implement step-2-post-dispatch")
    parser.add_argument("--expected-branch", required=True)
    args = parser.parse_args(argv)
    implement_tmpdir = _tmpdir_from_env()
    _rehydrate_plugin_root(implement_tmpdir)
    _emit_phantom_probe_with_warn("2-post-dispatch")
    branch = _run([GIT_BIN, "symbolic-ref", "--short", "HEAD"])
    if branch.returncode != 0 or not branch.stdout.strip():
        _err("step-2-post-dispatch: not on a named branch (detached HEAD or not a git repo)")
        _emit_kv(key="POST_DISPATCH_NEXT", value="bail")
        _emit_kv(key="BAIL_REASON", value="main-branch-post-dispatch")
        return 0
    current_branch = branch.stdout.strip()
    _emit_kv(key="BRANCH", value=current_branch)
    commit = _run([GIT_BIN, "rev-parse", "--short", "HEAD"])
    if commit.returncode == 0 and commit.stdout.strip():
        _emit_kv(key="COMMIT_SHA", value=commit.stdout.strip())
    _persist_ship_seed_context(implement_tmpdir)
    if not args.expected_branch or current_branch != args.expected_branch:
        _emit_kv(key="POST_DISPATCH_NEXT", value="bail")
        _emit_kv(key="BAIL_REASON", value="main-branch-post-dispatch")
        return 0
    _mark_dispatcher_committed(implement_tmpdir)
    _emit_kv(key="POST_DISPATCH_NEXT", value="continue")
    return 0
