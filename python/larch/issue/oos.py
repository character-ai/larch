"""OOS wire-format helpers for review findings."""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Callable
from pathlib import Path


_HEADER_TOKEN_RE = re.compile(r"^###[ \t]+[A-Za-z]+_[0-9]+:")
_CANONICAL_SECURITY_TOKEN_RE = re.compile(r"focus-area\s*=\s*security", re.IGNORECASE)
_EXPLICIT_SECURITY_HEADER_RE = re.compile(
    r"^###\s+(?:OOS_\d+:|FINDING_\d+:)\s*(?:\[(?:OUT_OF_SCOPE|OOS)\]\s*)?"
    r"`?(?:\[security\]|<security>)`?(?:\s|$|[:-])",
    re.IGNORECASE,
)
_FOCUS_AREA_FIELD_RE = re.compile(
    r"^[ \t-]*focus[- ]area[ \t]*[:=][ \t]*security(?:[-a-z0-9 _]*)(?:[ \t]|$|\(|#|\.|,)",
    re.IGNORECASE,
)
_FINDING_HEADER_RE = re.compile(r"^###\s+FINDING_\d+:")
_PRESENT_RESULT_RE = re.compile(r"(^|[ \t])Result=")
_ACCEPTED_RESULT_RE = re.compile(r"(^|[ \t])Result=accepted([ \t]|$)")


class OosClassificationError(RuntimeError):
    """Raised when OOS security classification cannot be trusted."""


def _security_classifier() -> Callable[[str], object]:
    return is_security_tagged


def normalize_oos_block_header(*, seq: int, block_text: str) -> str:
    """Rewrite only line 1 to use the canonical ``### OOS_<seq>:`` id."""
    if seq < 0:
        raise ValueError("seq must be a non-negative integer")
    lines = block_text.splitlines(keepends=True)
    if not lines:
        return block_text
    lines[0] = _HEADER_TOKEN_RE.sub(f"### OOS_{seq}:", lines[0], count=1)
    return "".join(lines)


def is_security_tagged(block_text: str) -> bool:
    """Return True when an OOS block carries a security tag."""
    text_no_fence = re.sub(r"```.*?```", "", block_text, flags=re.DOTALL)
    text_no_backtick = re.sub(r"`[^`\n]*`", "", text_no_fence)
    found = bool(_CANONICAL_SECURITY_TOKEN_RE.search(text_no_backtick))
    lines = text_no_fence.splitlines()
    if not found and lines and _EXPLICIT_SECURITY_HEADER_RE.search(lines[0]):
        found = True
    if not found:
        for line in lines:
            normalized = line.replace("`", "").replace("*", "").strip()
            if _FOCUS_AREA_FIELD_RE.search(normalized):
                found = True
                break
    return found


def _iter_finding_blocks(text: str) -> list[str]:
    blocks: list[str] = []
    in_block = False
    current: list[str] = []
    for line in text.splitlines():
        if _FINDING_HEADER_RE.search(line):
            if in_block:
                blocks.append("".join(current))
            in_block = True
            current = [f"{line}\n"]
            continue
        if in_block:
            current.append(f"{line}\n")
    if in_block:
        blocks.append("".join(current))
    return blocks


def _is_oos_block(block: str) -> bool:
    return "[OUT_OF_SCOPE]" in block or "[OOS]" in block


def _is_vote_tally_eligible(block: str) -> bool:
    found_result = False
    found_accepted = False
    for line in block.splitlines():
        if not line.startswith("Vote tally: "):
            continue
        if _PRESENT_RESULT_RE.search(line):
            found_result = True
            if _ACCEPTED_RESULT_RE.search(line):
                found_accepted = True
    return not found_result or found_accepted


def _classify_security(block: str) -> bool:
    try:
        classifier = _security_classifier()
        result = classifier(block)
    except Exception as exc:
        raise OosClassificationError("OOS security classifier failed") from exc
    if not isinstance(result, bool):
        raise OosClassificationError("OOS security classifier returned non-boolean result")
    return result


def oos_serialize(
    *,
    findings_file: Path,
    output_file: Path,
    session_env_path: Path | None = None,
) -> tuple[int, int]:
    """Serialize accepted non-security OOS findings and return count totals."""
    _ = session_env_path
    output_file.parent.mkdir(parents=True, exist_ok=True)
    _ = output_file.write_text("", encoding="utf-8")

    accepted = 0
    held_security = 0
    output_blocks: list[str] = []
    seq = 0
    text = findings_file.read_text(encoding="utf-8")

    for block in _iter_finding_blocks(text):
        if not _is_oos_block(block):
            continue
        if _classify_security(block):
            held_security += 1
            continue
        if not _is_vote_tally_eligible(block):
            continue
        seq += 1
        accepted += 1
        output_blocks.append(f"{normalize_oos_block_header(seq=seq, block_text=block)}\n")

    _ = output_file.write_text("".join(output_blocks), encoding="utf-8")
    return accepted, held_security


def _parser_error_code(exc: SystemExit) -> int:
    return exc.code if isinstance(exc.code, int) else 2


def oos_serialize_main(argv: list[str] | None = None) -> int:
    """CLI entry point for ``cli.py oos serialize``."""
    parser = argparse.ArgumentParser(prog="cli.py oos serialize")
    _ = parser.add_argument("--findings-file", required=True)
    _ = parser.add_argument("--output-file", required=True)
    _ = parser.add_argument("--session-env-path")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return _parser_error_code(exc)

    findings_file = Path(args.findings_file)
    output_file = Path(args.output_file)
    session_env_path = Path(args.session_env_path) if args.session_env_path else None
    if not findings_file.is_file():
        print("oos serialize: --findings-file must name a file", file=sys.stderr)
        return 2

    try:
        accepted, held_security = oos_serialize(
            findings_file=findings_file,
            output_file=output_file,
            session_env_path=session_env_path,
        )
    except OosClassificationError as exc:
        print(f"oos serialize: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"oos serialize: {exc}", file=sys.stderr)
        return 2

    print(f"OOS_ACCEPTED={accepted}")
    print(f"OOS_HELD_SECURITY={held_security}")
    return 0


def _parse_non_negative_seq(raw: str) -> int:
    if not raw.isdigit():
        raise ValueError
    return int(raw)


def oos_normalize_header_main(argv: list[str] | None = None) -> int:
    """CLI entry point for ``cli.py oos normalize-header``."""
    parser = argparse.ArgumentParser(prog="cli.py oos normalize-header")
    _ = parser.add_argument("--seq", required=True)
    _ = parser.add_argument("--block-file")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return _parser_error_code(exc)

    try:
        seq = _parse_non_negative_seq(args.seq)
    except ValueError:
        print("oos normalize-header: --seq must be a non-negative integer", file=sys.stderr)
        return 2

    block_file = Path(args.block_file) if args.block_file else None
    if block_file is not None:
        if not block_file.is_file():
            print("oos normalize-header: --block-file must name a file", file=sys.stderr)
            return 2
        try:
            block_text = block_file.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"oos normalize-header: {exc}", file=sys.stderr)
            return 2
    else:
        block_text = sys.stdin.read()

    _ = sys.stdout.write(normalize_oos_block_header(seq=seq, block_text=block_text))
    return 0
