# pyright: reportUnusedFunction=false, reportUnusedCallResult=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportPrivateUsage=false
"""Ship seed context management.

`implement step-2-post-dispatch` is Rust-owned (#8623); only the seed-file
helpers its Python siblings still read live here.
"""

from __future__ import annotations

from pathlib import Path

from larch.implement.dispatch_helpers import (
    _read_kv_file,
    _write_text_atomic,
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


