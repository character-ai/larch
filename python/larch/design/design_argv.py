"""Python CLI entrypoint for /design argv parsing."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from collections.abc import Sequence


def _quote_single(value: str) -> str:
    parts = value.split("'")
    return "'" + "'\"'\"'".join(parts) + "'"


def _write_output(
    *, output_path: str,
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


def _emit_validation_error(*, token: str, output_path: str) -> int:
    if "\n" in token or "\r" in token:
        token = "newline-in-value"
    fields = {"VALIDATION_ERROR": token}
    if output_path:
        _write_output(output_path=output_path, fields=fields)  # pyright: ignore[reportUnusedCallResult]
    print(f"VALIDATION_ERROR={token}")
    return 3


@dataclass
class _DesignArgvParsed:
    partition_requested: bool
    brainstorm_requested: bool
    approve_requested: bool
    skip_approve_requested: bool
    no_dedup_requested: bool
    run_id: str
    difficulty: str
    positional_kind: str
    positional_value: str


@dataclass
class _ArgvParseState:
    partition_requested: bool = False
    brainstorm_requested: bool = False
    approve_requested: bool = False
    skip_approve_requested: bool = False
    no_dedup_requested: bool = False
    run_id: str = ""
    difficulty: str = ""
    positional_args: list[str] = field(default_factory=list[str])
    positional_kind: str = "none"
    positional_value: str = ""
    issue_captured: bool = False


_SIMPLE_FLAG_ATTRS = {
    "-p": "partition_requested",
    "--partition": "partition_requested",
    "--brainstorm": "brainstorm_requested",
    "--no-dedup": "no_dedup_requested",
}

_ONCE_FLAG_TOKENS = {
    "--per-round-approval": ("approve_requested", "--per-round-approval"),
    "--skip-approve": ("skip_approve_requested", "--skip-approve"),
    "-s": ("skip_approve_requested", "--skip-approve"),
}

_KNOWN_PUBLIC_FLAG_TOKENS = frozenset(
    {
        *_SIMPLE_FLAG_ATTRS.keys(),
        *_ONCE_FLAG_TOKENS.keys(),
        "--run-id",
        "--difficulty",
        "--hard",
    }
)


def _strip_leading_output(argv: list[str]) -> tuple[str, list[str]]:
    output_path = ""
    if len(argv) >= 2 and argv[0] == "--output":  # noqa: PLR2004
        output_path = argv[1]
        argv = argv[2:]
    return output_path, argv


def _set_flag_once(
    *, state: _ArgvParseState,
    attr: str,
    token: str,
    output_path: str,
) -> int | None:
    if getattr(state, attr):
        return _emit_validation_error(token=token, output_path=output_path)
    setattr(state, attr, True)
    return None


def _parse_value_flag(
    *,
    argv: list[str],
    index: int,
    state: _ArgvParseState,
    output_path: str,
) -> tuple[int, int | None]:
    token = argv[index]
    if index + 1 >= len(argv):
        return index + 1, _emit_validation_error(token=token, output_path=output_path)
    value = argv[index + 1]
    if token == "--run-id":
        if value.startswith("-") or value in _KNOWN_PUBLIC_FLAG_TOKENS:
            return index + 1, _emit_validation_error(token=value, output_path=output_path)
        state.run_id = value
        return index + 2, None
    difficulty = value.upper()
    if difficulty not in {"TRIVIAL", "MODERATE", "HARD"}:
        return index + 1, _emit_validation_error(token=value, output_path=output_path)
    state.difficulty = difficulty
    return index + 2, None


def _apply_double_dash(*, state: _ArgvParseState, rest: list[str]) -> None:
    if state.issue_captured:
        return
    if rest and rest[0].isdigit():
        state.positional_kind = "issue"
        state.positional_value = rest[0]
        state.issue_captured = True
    else:
        state.positional_args = rest


def _parse_flag_token(
    *, argv: list[str],
    index: int,
    state: _ArgvParseState,
    output_path: str,
) -> tuple[str, int, int | None]:
    """Return (action, next_index, error_rc) for flag tokens.

    action is ``continue``, ``error``, or ``not_flag``.
    """
    token = argv[index]
    flag_attr: str | None = _SIMPLE_FLAG_ATTRS.get(token)
    if flag_attr is not None:
        setattr(state, flag_attr, True)
        return "continue", index + 1, None

    next_index = index + 1
    error_rc: int | None = None
    once: tuple[str, str] | None = _ONCE_FLAG_TOKENS.get(token)
    if once is not None:
        attr, err_token = once
        error_rc = _set_flag_once(state=state, attr=attr, token=err_token, output_path=output_path)
    elif token in {"--run-id", "--difficulty"}:
        next_index, error_rc = _parse_value_flag(argv=argv, index=index, state=state, output_path=output_path)
    elif token == "--hard":
        error_rc = _emit_validation_error(token="--hard", output_path=output_path)
    elif token.startswith("-"):
        error_rc = _emit_validation_error(token=token, output_path=output_path)
    else:
        return "not_flag", index, None

    if error_rc is not None:
        return "error", index, error_rc
    return "continue", next_index, None


def _parse_positional_token(
    *, argv: list[str],
    index: int,
    state: _ArgvParseState,
) -> tuple[str, int]:
    token = argv[index]
    if not state.issue_captured and token.isdigit():
        state.positional_kind = "issue"
        state.positional_value = token
        state.issue_captured = True
        return "continue", index + 1

    if state.issue_captured:
        return "continue", index + 1

    state.positional_args = argv[index:]
    return "break", index


def _dispatch_argv_token(
    *, argv: list[str],
    index: int,
    state: _ArgvParseState,
    output_path: str,
) -> tuple[str, int, int | None]:
    """Return (action, next_index, error_rc).

    action is one of ``continue``, ``break``, or ``error``.
    """
    token = argv[index]
    if token == "--":
        _apply_double_dash(state=state, rest=argv[index + 1 :])
        return "break", index + 1, None

    action, next_index, error_rc = _parse_flag_token(argv=argv, index=index, state=state, output_path=output_path)
    if action == "error":
        return "error", index, error_rc
    if action == "continue":
        return "continue", next_index, None

    action, next_index = _parse_positional_token(argv=argv, index=index, state=state)
    return action, next_index, None


def _validate_parsed_values(
    *, state: _ArgvParseState,
    output_path: str,
) -> int | None:
    if "\n" in state.run_id or "\r" in state.run_id:
        return _emit_validation_error(token="newline-in-value", output_path=output_path)
    for token in state.positional_args:
        if "\n" in token or "\r" in token:
            return _emit_validation_error(token="newline-in-value", output_path=output_path)
    return None


def _finalize_verbal_positional(state: _ArgvParseState) -> None:
    if not state.issue_captured and state.positional_args:
        state.positional_kind = "verbal"
        state.positional_value = " ".join(state.positional_args)


def _parse_design_flags(*, argv: list[str], output_path: str) -> tuple[_DesignArgvParsed | None, int]:
    state = _ArgvParseState()

    # Flags may appear on either side of a numeric issue positional
    # (non-contiguous argv): after capturing the issue id the loop keeps
    # parsing, so trailing flags are honored and unknown trailing flags
    # still error, rather than being silently dropped. A non-digit first
    # positional starts verbal feature text: flag parsing stops and the
    # remainder is taken literally.
    index = 0
    while index < len(argv):
        action, index, error_rc = _dispatch_argv_token(argv=argv, index=index, state=state, output_path=output_path)
        if action == "error":
            return None, error_rc if error_rc is not None else 3
        if action == "break":
            break

    error_rc = _validate_parsed_values(state=state, output_path=output_path)
    if error_rc is not None:
        return None, error_rc

    _finalize_verbal_positional(state)

    return (
        _DesignArgvParsed(
            partition_requested=state.partition_requested,
            brainstorm_requested=state.brainstorm_requested,
            approve_requested=state.approve_requested,
            skip_approve_requested=state.skip_approve_requested,
            no_dedup_requested=state.no_dedup_requested,
            run_id=state.run_id,
            difficulty=state.difficulty,
            positional_kind=state.positional_kind,
            positional_value=state.positional_value,
        ),
        0,
    )


def _emit_success(*, output_path: str, parsed: _DesignArgvParsed) -> int:
    output_fields: dict[str, str] = {
        "partition_requested": str(parsed.partition_requested).lower(),
        "brainstorm_requested": str(parsed.brainstorm_requested).lower(),
        "approve_requested": str(parsed.approve_requested).lower(),
        "skip_approve_requested": str(parsed.skip_approve_requested).lower(),
        "no_dedup_requested": str(parsed.no_dedup_requested).lower(),
        "run_id": parsed.run_id,
        "difficulty": parsed.difficulty,
        "POSITIONAL_KIND": parsed.positional_kind,
        "POSITIONAL_VALUE": parsed.positional_value,
    }
    stdout_fields: dict[str, str] = {
        "PARTITION_REQUESTED": str(parsed.partition_requested).lower(),
        "BRAINSTORM_REQUESTED": str(parsed.brainstorm_requested).lower(),
        "APPROVE_REQUESTED": str(parsed.approve_requested).lower(),
        "SKIP_APPROVE_REQUESTED": str(parsed.skip_approve_requested).lower(),
        "NO_DEDUP_REQUESTED": str(parsed.no_dedup_requested).lower(),
        "RUN_ID": parsed.run_id,
        "DIFFICULTY": parsed.difficulty,
        "POSITIONAL_KIND": parsed.positional_kind,
        "POSITIONAL_VALUE": parsed.positional_value,
    }

    if output_path and not _write_output(output_path=output_path, fields=output_fields):
        return 1
    for key, val in stdout_fields.items():
        print(f"{key}={val}")

    return 0


def parse_argv_main(argv: Sequence[str]) -> int:
    output_path, argv = _strip_leading_output(list(argv))

    # Hidden --output is internal-only; reject any public appearance after stripping.
    if "--output" in argv:
        return _emit_validation_error(token="--output", output_path=output_path)

    parsed, rc = _parse_design_flags(argv=argv, output_path=output_path)
    if parsed is None:
        return rc
    return _emit_success(output_path=output_path, parsed=parsed)
