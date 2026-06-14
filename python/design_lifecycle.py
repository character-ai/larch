"""Python CLI entrypoints and shared helpers for /design lifecycle phases."""

from __future__ import annotations

import argparse
import contextlib
import os
import sys
import tempfile
from pathlib import Path
from collections.abc import Iterable, Sequence

import design_legacy


def _valid_var_name(value: str) -> bool:
    if not value or value[0].isdigit():
        return False
    return all(ch.isalnum() or ch == "_" for ch in value)


def _quote_single(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def phase_driver_read_result_env(path: str | Path, allow_keys: Iterable[str]) -> list[tuple[str, str]]:
    """Read allowlisted KEY=VALUE records from a result-env file.

    Blank and malformed lines are skipped. Values containing CR or LF are
    refused, matching the shell phase-driver trust boundary.
    """
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise OSError(f"result env is not a regular file: {source}")
    allow = set(allow_keys)
    pairs: list[tuple[str, str]] = []
    for raw in source.read_bytes().decode("utf-8", errors="replace").split("\n"):
        if raw == "":
            continue
        if "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        if key not in allow:
            continue
        if "\n" in value or "\r" in value:
            continue
        pairs.append((key, value))
    return pairs


def _replay_warn_error(path: Path) -> None:
    for raw in path.read_bytes().decode("utf-8", errors="replace").split("\n"):
        if raw == "":
            continue
        if "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        if key in {"WARN", "ERROR"}:
            print(f"{key}={value}")


def _classify_input(path: Path) -> str:
    if path.is_symlink():
        return "symlink"
    if not path.exists():
        return "missing"
    if not path.is_file():
        return "nonregular"
    return "regular"


def read_result_env_main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="cli.py design read-result-env",
        add_help=False,
    )
    parser.add_argument("--input", dest="input_path")  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--fallback-input", dest="fallback_input", default="")  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--allow", dest="allow", action="append", default=[])  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--output", dest="output_path")  # pyright: ignore[reportUnusedCallResult]
    try:
        ns, extra = parser.parse_known_args(list(argv))
    except SystemExit:
        _usage()
        return 1
    if extra or not ns.input_path or not ns.output_path or any(not _valid_var_name(k) for k in ns.allow):
        _usage()
        return 1

    input_path = Path(ns.input_path)
    fallback_path = Path(ns.fallback_input) if ns.fallback_input else None
    source_path: Path
    primary_kind = _classify_input(input_path)
    if primary_kind == "regular":
        source_path = input_path
    else:
        if fallback_path is None:
            return 1
        if primary_kind == "symlink":
            if str(input_path).endswith(".design-init-runparams-result.env"):
                print("**⚠ Step 0b: design-init-runparams result env is a symlink; refusing to source**")
            else:
                print(f"WARN=read-result-env input is a symlink; refusing primary path: {input_path}")
        if fallback_path.is_symlink() or not fallback_path.is_file():
            return 1
        source_path = fallback_path

    output_path = Path(ns.output_path)
    if not output_path.parent.is_dir():
        return 1

    def write_pairs(from_path: Path, tmp_path: Path) -> int:
        _replay_warn_error(from_path)
        try:
            pairs = phase_driver_read_result_env(from_path, ns.allow)
        except OSError:
            return 1
        with tmp_path.open("w", encoding="utf-8") as handle:
            for key, value in pairs:
                handle.write(f"{key}={_quote_single(value)}\n")  # pyright: ignore[reportUnusedCallResult]
        return 0

    fd = -1
    tmp_name = ""
    try:
        fd, tmp_name = tempfile.mkstemp(prefix=f".{output_path.name}.", dir=str(output_path.parent))
        os.close(fd)
        fd = -1
        tmp_path = Path(tmp_name)
        if write_pairs(source_path, tmp_path) != 0:
            return 1
        if tmp_path.stat().st_size == 0 and primary_kind == "regular" and fallback_path is not None and fallback_path.is_file() and not fallback_path.is_symlink():
            source_path = fallback_path
            if write_pairs(source_path, tmp_path) != 0:
                return 1
        tmp_path.replace(output_path)  # pyright: ignore[reportUnusedCallResult]
        tmp_name = ""
        return 0
    finally:
        if fd >= 0:
            os.close(fd)
        if tmp_name:
            with contextlib.suppress(FileNotFoundError):
                Path(tmp_name).unlink()


def _usage() -> None:
    print(
        "usage: read-result-env.sh --input PATH [--fallback-input PATH] --allow KEY ... --output PATH",
        file=sys.stderr,
    )


def route_main(argv: Sequence[str]) -> int:
    return design_legacy.run_script("skills/design/scripts/design-route.sh", argv)


def init_runparams_main(argv: Sequence[str]) -> int:
    return design_legacy.run_script("skills/design/scripts/design-init-runparams.sh", argv)


def driver_main(argv: Sequence[str]) -> int:
    return design_legacy.run_script("skills/design/scripts/design-driver.sh", argv)
