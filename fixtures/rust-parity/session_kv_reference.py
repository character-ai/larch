"""Frozen Python behavior for the issue #8056 Rust command cutover."""
# ruff: noqa: C901, PLR0911

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def line_iter(text: str) -> list[str]:
    lines = text.split("\n")
    return [line.removesuffix("\r") if index < len(lines) - 1 else line for index, line in enumerate(lines)]


def strip_cr(value: str, mode: str) -> str:
    if mode == "suffix":
        return value.removesuffix("\r")
    if mode == "rstrip":
        return value.rstrip("\r")
    if mode == "strip":
        return value.strip("\r")
    return value


def kv_get(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py kv get", description="Extract one value from KEY=value input.")
    parser.add_argument("--key", required=True)
    parser.add_argument("--file", type=Path)
    parser.add_argument("--match", choices=("first", "last", "last-non-empty"), default="first")
    parser.add_argument("--default", default="")
    parser.add_argument("--cr-strip", choices=("none", "suffix", "rstrip", "strip"), default="none")
    args = parser.parse_args(argv)
    if args.file is None:
        text = sys.stdin.read()
    elif args.file.is_file():
        text = args.file.read_bytes().decode("utf-8", errors="replace")
    else:
        text = ""
    prefix = f"{args.key}="
    value = args.default
    for line in line_iter(text):
        if not line.startswith(prefix):
            continue
        candidate = strip_cr(line[len(prefix) :], args.cr_strip)
        if args.match == "first":
            value = candidate
            break
        if args.match == "last-non-empty" and not candidate:
            continue
        value = candidate
    print(value)
    return 0


def read_text(path: Path) -> str:
    text = path.read_bytes().decode("utf-8", errors="replace")
    if "\r" in text:
        raise ValueError(f"session env file contains carriage return: {path}")
    return text


def read_key(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="session read-key", add_help=False)
    parser.add_argument("--file", default=None)
    parser.add_argument("--key", default="")
    parser.add_argument("--default", default=None)
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 1
    if not args.key:
        print("read-session-env-key.sh: --key is required", file=sys.stderr)
        return 1
    if args.file is None or args.file == "":
        if "--file" in argv and args.default is not None:
            print(args.default)
            return 0
        print("read-session-env-key.sh: --file is required", file=sys.stderr)
        return 1
    path = Path(args.file)
    if not path.is_file():
        if args.default is not None:
            print(args.default)
            return 0
        print(f"read-session-env-key.sh: cannot read {args.file}", file=sys.stderr)
        return 1
    try:
        lines = read_text(path).splitlines()
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    value = ""
    found = False
    prefix = f"{args.key}="
    for line in lines:
        if line.startswith(prefix):
            value = line[len(prefix) :]
            found = True
            break
    if (not found or value == "") and args.default is not None:
        value = args.default
    print(value)
    return 0


def read_keys(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="session read-keys", add_help=False)
    parser.add_argument("--file", default=None)
    parser.add_argument("--key", action="append", default=[])
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 1
    if not args.key:
        print("read-session-env-keys.sh: at least one --key is required", file=sys.stderr)
        return 1
    if "--file" not in argv:
        print("read-session-env-keys.sh: --file is required", file=sys.stderr)
        return 1
    specs = [raw.split("=", 1) if "=" in raw else [raw, None] for raw in args.key]
    if any(not name for name, _default in specs):
        print("read-session-env-keys.sh: empty --key name", file=sys.stderr)
        return 1
    found: dict[str, str] = {}
    if args.file:
        path = Path(args.file)
        if path.is_file():
            try:
                for line in line_iter(read_text(path)):
                    if "=" not in line:
                        continue
                    name, value = line.split("=", 1)
                    if name and name not in found:
                        found[name] = value
            except ValueError as error:
                print(error, file=sys.stderr)
                return 1
    for name, default in specs:
        value = found.get(name, "")
        if (name not in found or value == "") and default is not None:
            value = default
        print(f"{name}={value}")
    return 0


def main() -> int:
    command, *arguments = sys.argv[1:]
    if command == "kv-get":
        return kv_get(arguments)
    if command == "read-key":
        return read_key(arguments)
    if command == "read-keys":
        return read_keys(arguments)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
