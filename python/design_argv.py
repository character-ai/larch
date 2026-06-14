"""Python CLI entrypoint for /design argv parsing."""

from __future__ import annotations

from pathlib import Path
from collections.abc import Sequence


def _quote_single(value: str) -> str:
    parts = value.split("'")
    return "'" + "'\"'\"'".join(parts) + "'"


def _write_output(
    output_path: str,
    fields: dict[str, str],
) -> bool:
    p = Path(output_path)
    parent = p.parent
    if not parent.is_dir():
        return False
    tmp = parent / f".{p.name}.tmp"
    try:
        with tmp.open("w", encoding="utf-8") as fh:
            for key, val in fields.items():
                fh.write(f"{key}={_quote_single(val)}\n")  # pyright: ignore[reportUnusedCallResult]
        tmp.replace(p)  # pyright: ignore[reportUnusedCallResult]
        return True
    except OSError:
        tmp.unlink(missing_ok=True)
        return False


def _emit_validation_error(token: str, output_path: str) -> int:
    if "\n" in token or "\r" in token:
        token = "newline-in-value"
    fields = {"VALIDATION_ERROR": token}
    if output_path:
        _write_output(output_path, fields)  # pyright: ignore[reportUnusedCallResult]
    print(f"VALIDATION_ERROR={token}")
    return 3


def parse_argv_main(argv: Sequence[str]) -> int:
    argv = list(argv)
    output_path = ""

    # Leading --output is internal-only
    _MIN_ARGS_OUTPUT = 2
    if len(argv) >= _MIN_ARGS_OUTPUT and argv[0] == "--output":
        output_path = argv[1]
        argv = argv[2:]

    # Check for leading --output as public flag (reject)
    for a in argv:
        if a == "--output":
            return _emit_validation_error("--output", output_path)
        break

    partition_requested = False
    brainstorm_requested = False
    approve_requested = False
    skip_approve_requested = False
    no_dedup_requested = False
    run_id = ""
    after_terminator = False
    positional_args: list[str] = []

    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--":
            after_terminator = True
            i += 1
            positional_args = argv[i:]
            break
        if a in ("-p", "--partition"):
            partition_requested = True
            i += 1
        elif a == "--brainstorm":
            brainstorm_requested = True
            i += 1
        elif a == "--per-round-approval":
            if approve_requested:
                return _emit_validation_error("--per-round-approval", output_path)
            approve_requested = True
            i += 1
        elif a in ("--skip-approve", "-s"):
            if skip_approve_requested:
                return _emit_validation_error("--skip-approve", output_path)
            skip_approve_requested = True
            i += 1
        elif a == "--no-dedup":
            no_dedup_requested = True
            i += 1
        elif a == "--run-id":
            if i + 1 >= len(argv):
                return _emit_validation_error("--run-id", output_path)
            run_id = argv[i + 1]
            i += 2
        elif a == "--hard":
            return _emit_validation_error("--hard", output_path)
        elif a.startswith("-"):
            return _emit_validation_error(a, output_path)
        else:
            positional_args = argv[i:]
            break
        continue

    first_positional = positional_args[0] if positional_args else ""

    # Validate run_id for newlines
    if "\n" in run_id or "\r" in run_id:
        return _emit_validation_error("newline-in-value", output_path)

    # Determine positional kind and value
    positional_kind = "none"
    positional_value = ""
    if first_positional:
        if first_positional.isdigit():
            positional_kind = "issue"
            positional_value = first_positional
            # After numeric positional, only --hard is forbidden (skip other args)
            if not after_terminator:
                for extra in positional_args[1:]:
                    if extra == "--hard":
                        return _emit_validation_error("--hard", output_path)
        else:
            positional_kind = "verbal"
            positional_value = " ".join(positional_args)

    fields = {
        "partition_requested": str(partition_requested).lower(),
        "brainstorm_requested": str(brainstorm_requested).lower(),
        "approve_requested": str(approve_requested).lower(),
        "skip_approve_requested": str(skip_approve_requested).lower(),
        "no_dedup_requested": str(no_dedup_requested).lower(),
        "run_id": run_id,
        "POSITIONAL_KIND": positional_kind,
        "POSITIONAL_VALUE": positional_value,
    }

    if output_path:
        if not _write_output(output_path, fields):
            return 1
    else:
        for key, val in fields.items():
            print(f"{key}={_quote_single(val)}")

    return 0
