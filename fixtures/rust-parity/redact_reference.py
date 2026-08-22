#!/usr/bin/env python3
"""Frozen Python command boundary for the Rust redaction parity suite."""

from __future__ import annotations

import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[2]
python_dir = repo_root / "python"
if str(python_dir) not in sys.path:
    sys.path.insert(0, str(python_dir))

from larch.core.redact import (  # noqa: E402
    _streaming_redact,
    redact_secrets_only,
    redact_tmpdir_paths,
    scrub_log_directory,
    scrub_submodule_paths,
)


def secrets(argv: list[str]) -> int:
    streaming = False
    state_file = ""
    index = 0
    while index < len(argv):
        argument = argv[index]
        if argument == "--streaming":
            streaming = True
            index += 1
        elif argument == "--state-file":
            if index + 1 >= len(argv):
                print("redact secrets: --state-file requires a value", file=sys.stderr)
                return 2
            state_file = argv[index + 1]
            index += 2
        elif argument.startswith("--state-file="):
            state_file = argument.split("=", 1)[1]
            index += 1
        else:
            print(f"redact secrets: unknown option: {argument}", file=sys.stderr)
            return 2
    text = sys.stdin.read()
    if streaming:
        if not state_file:
            print("redact secrets: --streaming requires --state-file", file=sys.stderr)
            return 2
        sys.stdout.write(_streaming_redact(stdin_text=text, state_file=Path(state_file)))
        return 0
    sys.stdout.write(redact_secrets_only(text))
    return 0


def tmpdir_paths(argv: list[str]) -> int:
    if argv:
        print(f"redact tmpdir-paths: unknown option: {argv[0]}", file=sys.stderr)
        return 2
    sys.stdout.write(redact_tmpdir_paths(sys.stdin.read()))
    return 0


def scrub_log_secrets(argv: list[str]) -> int:
    directory = ""
    index = 0
    while index < len(argv):
        argument = argv[index]
        if argument in {"--dir", "--log-root", "--path"}:
            if index + 1 >= len(argv):
                print(
                    f"python3 python/cli.py redact scrub-log-secrets: {argument} requires a value",
                    file=sys.stderr,
                )
                return 2
            directory = argv[index + 1]
            index += 2
        else:
            if directory:
                print(
                    f"python3 python/cli.py redact scrub-log-secrets: unknown option: {argument}",
                    file=sys.stderr,
                )
                return 2
            directory = argument
            index += 1
    if not directory:
        print(
            "python3 python/cli.py redact scrub-log-secrets: directory is required",
            file=sys.stderr,
        )
        return 2
    root = Path(directory)
    if not root.exists():
        print(
            f"python3 python/cli.py redact scrub-log-secrets: directory not found: {root}",
            file=sys.stderr,
        )
        return 2
    try:
        result = scrub_log_directory(root)
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 3
    print(f"LARCH_SECRET_SCRUB_VIOLATIONS={result.total}")
    print(f"LARCH_SECRET_SCRUB_FILES={result.files}")
    return 0


def scrub_submodules(argv: list[str]) -> int:
    input_path = ""
    output_path = ""
    log_path = ""
    index = 0
    while index < len(argv):
        argument = argv[index]
        if argument == "--input" and index + 1 < len(argv):
            input_path = argv[index + 1]
            index += 2
        elif argument == "--output" and index + 1 < len(argv):
            output_path = argv[index + 1]
            index += 2
        elif argument == "--log" and index + 1 < len(argv):
            log_path = argv[index + 1]
            index += 2
        else:
            print(
                f"scrub-submodule-paths.sh: unknown or incomplete option: {argument}",
                file=sys.stderr,
            )
            return 2
    if not input_path or not output_path or not log_path:
        print(
            "scrub-submodule-paths.sh: --input, --output, and --log are required",
            file=sys.stderr,
        )
        return 2
    try:
        result = scrub_submodule_paths(
            input_path=Path(input_path),
            output_path=Path(output_path),
            log_path=Path(log_path),
        )
    except OSError as error:
        print(f"scrub-submodule-paths.sh: {error}", file=sys.stderr)
        print("SCRUB_COUNT=0")
        print("SCRUB_OK=false")
        return 2
    print(f"SCRUB_COUNT={result.count}")
    print(f"SCRUB_OK={'true' if result.ok else 'false'}")
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        return 2
    verb = sys.argv[1]
    arguments = sys.argv[2:]
    if verb == "secrets":
        return secrets(arguments)
    if verb == "tmpdir-paths":
        return tmpdir_paths(arguments)
    if verb == "scrub-log-secrets":
        return scrub_log_secrets(arguments)
    if verb == "scrub-submodule-paths":
        return scrub_submodules(arguments)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
