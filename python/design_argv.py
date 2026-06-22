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

    # Hidden --output is internal-only; reject any public appearance after stripping.
    if "--output" in argv:
        return _emit_validation_error("--output", output_path)

    partition_requested = False
    brainstorm_requested = False
    approve_requested = False
    skip_approve_requested = False
    no_dedup_requested = False
    run_id = ""
    positional_args: list[str] = []
    positional_kind = "none"
    positional_value = ""
    issue_captured = False

    # Flags may appear on either side of a numeric issue positional
    # (non-contiguous argv): after capturing the issue id the loop keeps
    # parsing, so trailing flags are honored and unknown trailing flags
    # still error, rather than being silently dropped. A non-digit first
    # positional starts verbal feature text: flag parsing stops and the
    # remainder is taken literally.
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--":
            i += 1
            rest = argv[i:]
            if not issue_captured:
                if rest and rest[0].isdigit():
                    positional_kind = "issue"
                    positional_value = rest[0]
                    issue_captured = True
                else:
                    positional_args = rest
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
        elif not issue_captured and a.isdigit():
            # First positional is a numeric issue id: capture it and keep
            # parsing so flags after it are honored, not dropped.
            positional_kind = "issue"
            positional_value = a
            issue_captured = True
            i += 1
        elif issue_captured:
            # Extra non-flag token after the issue id: ignored.
            i += 1
        else:
            # First positional is non-numeric: verbal feature text tail.
            positional_args = argv[i:]
            break
        continue

    # Validate run_id/positional values for newline-smuggling. The issue id
    # is all-digits (newline-free by construction); verbal tokens are checked
    # here before they are joined into POSITIONAL_VALUE.
    if "\n" in run_id or "\r" in run_id:
        return _emit_validation_error("newline-in-value", output_path)
    for token in positional_args:
        if "\n" in token or "\r" in token:
            return _emit_validation_error("newline-in-value", output_path)

    # A non-empty positional_args list is verbal feature text; the issue path
    # sets kind/value inline above and leaves positional_args empty.
    if not issue_captured and positional_args:
        positional_kind = "verbal"
        positional_value = " ".join(positional_args)

    output_fields = {
        "partition_requested": str(partition_requested).lower(),
        "brainstorm_requested": str(brainstorm_requested).lower(),
        "approve_requested": str(approve_requested).lower(),
        "skip_approve_requested": str(skip_approve_requested).lower(),
        "no_dedup_requested": str(no_dedup_requested).lower(),
        "run_id": run_id,
        "POSITIONAL_KIND": positional_kind,
        "POSITIONAL_VALUE": positional_value,
    }
    stdout_fields = {
        "PARTITION_REQUESTED": str(partition_requested).lower(),
        "BRAINSTORM_REQUESTED": str(brainstorm_requested).lower(),
        "APPROVE_REQUESTED": str(approve_requested).lower(),
        "SKIP_APPROVE_REQUESTED": str(skip_approve_requested).lower(),
        "NO_DEDUP_REQUESTED": str(no_dedup_requested).lower(),
        "RUN_ID": run_id,
        "POSITIONAL_KIND": positional_kind,
        "POSITIONAL_VALUE": positional_value,
    }

    if output_path and not _write_output(output_path, output_fields):
        return 1
    for key, val in stdout_fields.items():
        print(f"{key}={val}")

    return 0
