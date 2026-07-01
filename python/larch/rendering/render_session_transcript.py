# ruff: noqa: TC006,FURB167,PLW2901,PERF401
"""render-session-transcript.py — render a Claude Code session JSONL as a filtered chat-view JSONL.

Output schema (v3, policy: prose-errors-and-reference-reads):

  Line 1 is a header record:
      {"v": 3, "source_basename": "<input-basename>", "turns": N, "policy": "prose-errors-and-reference-reads"}

  Subsequent lines are per-turn records (one JSON object per line):
      {"turn": <int>, "role": "user" | "assistant", "blocks": [<block>...]}

  Block types kept:
      {"type": "command", "name": "/cmd", "args": "..."}     # slash command typed by user
      {"type": "text", "value": "..."}                       # plain user / assistant text
      {"type": "thinking", "value": "..."}                   # assistant thinking (kept only when adjacent to error)
      {"type": "tool_result", "tool_use_id": "toolu_...", "name": "Bash",
       "text": "...", "error": true, "exit_code": N}         # errored result (full body)
      {"type": "tool_result", "tool_use_id": "toolu_...", "name": "Bash",
       "text": "...", "warning": true}                       # warning result (full body)

  Tool-call policy (v3):
      Only Read invocations for runtime reference Markdown are kept, sanitized to
      type/name/input.file_path. All other tool invocations are omitted.
      non-error/non-warning tool_result blocks — routine results are omitted entirely.

  Accepted capability loss: general tool-sequence reconstruction for clean runs is no
  longer possible from the committed transcript. Incident forensics of that shape
  must use live-session artifacts instead.

Filter rules:
  - Drop records with isMeta=true (harness-injected slash-command/@file expansions).
  - Drop housekeeping record types: permission-mode, file-history-snapshot,
    attachment, last-prompt, queue-operation, system.
  - User <command-message>/<command-name>/<command-args> collapse to a `command` block.
  - User plain text strips <system-reminder> blocks.
  - tool_result body kept in full when:
      (a) is_error=true, OR
      (b) tool is 'Bash' AND first 500 chars contain '^(Error:|Exit code [1-9])'
          OR a 'warning:' substring (case-insensitive).
    Otherwise dropped entirely (v3; was elided_bytes in v2).
  - thinking blocks kept only when at least one tool_use in the same
    assistant turn produced an errored tool_result.
  - Read tool_use blocks for skills/**/references/*.md and skills/shared/*.md are kept with only normalized file_path; all other tool calls are dropped (v3).

Exit codes:
  0 success; output written.
  2 input file missing or unreadable.
  3 input parsed but produced zero records (suspect format).
  Any other non-zero on unexpected exceptions.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from collections.abc import Iterator
from typing import cast

from larch.core import config

SCHEMA_VERSION = 3
_SHARED_REFERENCE_PARTS = 3
SKILL_REFERENCE_PARTS = 4

HOUSEKEEPING_TYPES = {
    "permission-mode",
    "file-history-snapshot",
    "attachment",
    "last-prompt",
    "queue-operation",
    "system",
}

SYSREM_RE = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)
CMD_NAME_RE = re.compile(r"<command-name>(.*?)</command-name>", re.S)
CMD_ARGS_RE = re.compile(r"<command-args>(.*?)</command-args>", re.S)
EXIT_CODE_RE = re.compile(r"(?m)^Exit code ([1-9][0-9]*)")
ERROR_PREFIX_RE = re.compile(r"(?m)^Error:")
WARN_RE = re.compile(r"warning:", re.I)


Record = dict[str, object]
Block = dict[str, object]



def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _in_scope_reference(rel: str) -> bool:
    path = Path(rel)
    parts = path.parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        return False
    if path.suffix != ".md":
        return False
    if len(parts) == _SHARED_REFERENCE_PARTS and parts[0] == "skills" and parts[1] == "shared":
        return True
    return len(parts) == SKILL_REFERENCE_PARTS and parts[0] == "skills" and parts[2] == "references"


def strip_plugin_cache_read_suffix(path: str) -> str | None:
    """Return the repo-relative suffix after a known Claude plugin-cache root."""
    parts = path.split("/")
    for index, part in enumerate(parts):
        if (
            part == "plugins"
            and index + 4 < len(parts)
            and parts[index + 1] == "cache"
            and parts[index + 2] == "larch-local"
            and parts[index + 3] == "larch"
            and parts[index + 4]
        ):
            if index == 0 or parts[index - 1] == ".claude":
                suffix_parts = parts[index + 5 :]
                if suffix_parts:
                    return "/".join(suffix_parts)
            return None
    return None


def normalize_reference_read_path(raw: object, *, repo: Path | None = None) -> str | None:
    if not isinstance(raw, str) or not raw.endswith(".md"):
        return None
    path = raw
    redacted_prefix = f"{config.REDACTED_OPERATOR_REPO}/"
    if path.startswith(redacted_prefix):
        path = path[len(redacted_prefix) :]
    elif path == config.REDACTED_OPERATOR_REPO:
        return None
    if path.startswith("<"):
        return None
    root = repo or _repo_root()
    repo_prefix = f"{root}/"
    if path.startswith(repo_prefix):
        path = path[len(repo_prefix) :]
    else:
        stripped = strip_plugin_cache_read_suffix(path)
        if stripped is not None:
            path = stripped
        elif path.startswith("/"):
            return None
    if path.startswith(("/", "../")) or "/../" in path or path == "..":
        return None
    return path if _in_scope_reference(path) else None


def render_reference_read_tool_use(block: Block) -> Block | None:
    if block.get("type") != "tool_use" or block.get("name") != "Read":
        return None
    tool_input = block.get("input")
    if not isinstance(tool_input, dict):
        return None
    rel = normalize_reference_read_path(cast(Block, tool_input).get("file_path"))
    if rel is None:
        return None
    return {"type": "tool_use", "name": "Read", "input": {"file_path": rel}}


def _render_assistant_text_block(block: Block) -> Block | None:
    text = block.get("text", "")
    txt = SYSREM_RE.sub("", text if isinstance(text, str) else "").rstrip()
    if not txt or txt.startswith("Base directory for this skill"):
        return None
    return {"type": "text", "value": txt}


def _render_assistant_thinking_block(block: Block, *, turn_has_kept: bool) -> Block | None:
    if not turn_has_kept:
        return None
    thinking = block.get("thinking", "")
    think = (thinking if isinstance(thinking, str) else "").strip()
    return {"type": "thinking", "value": think} if think else None


def _render_assistant_block(block: Block, *, turn_has_kept: bool) -> Block | None:
    bt = block.get("type")
    if bt == "text":
        return _render_assistant_text_block(block)
    if bt == "thinking":
        return _render_assistant_thinking_block(block, turn_has_kept=turn_has_kept)
    if bt == "tool_use":
        return render_reference_read_tool_use(block)
    return None


def tool_result_text(blk: Block) -> str:
    c = blk.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        parts: list[str] = []
        content_items = cast(list[object], c)
        for item in content_items:
            if not isinstance(item, dict):
                continue
            block = cast(Block, item)
            if block.get("type") == "text":
                text = block.get("text", "")
                parts.append(text if isinstance(text, str) else "")
        return "".join(parts)
    return ""


def classify_tool_result(*, blk: Block, tool_name: str) -> tuple[bool, bool, int | None]:
    """Returns (kept_error, kept_warning, exit_code_or_None).

    kept_error is True when the harness flagged is_error OR the Bash output
    indicates a non-zero exit / Error prefix. kept_warning is True when the
    Bash output contains a 'warning:' substring and the result wasn't already
    classified as an error. exit_code is parsed from 'Exit code N' when present.
    """
    is_err_flag = blk.get("is_error") is True
    if tool_name != "Bash":
        return (is_err_flag, False, None)
    txt = tool_result_text(blk)
    head = txt[:500]
    exit_match = EXIT_CODE_RE.search(head)
    exit_code: int | None = int(exit_match.group(1)) if exit_match else None
    has_err_prefix = bool(ERROR_PREFIX_RE.search(head))
    has_warn = bool(WARN_RE.search(head))
    error = is_err_flag or exit_code is not None or has_err_prefix
    warning = (not error) and has_warn
    return (error, warning, exit_code)


def parse_jsonl(path: Path) -> Iterator[Record]:
    """Yield record dicts from a JSONL file, skipping unparseable lines."""
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line:
                continue
            try:
                parsed: object = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                yield cast(Record, parsed)


def _message_content(rec: Record) -> object:
    message = rec.get("message")
    if not isinstance(message, dict):
        return None
    message_record = cast(Record, message)
    return message_record.get("content")


def first_pass(records: list[Record]) -> tuple[dict[str, str], dict[str, bool]]:
    """Build tool_use_id → name and tool_use_id → error_or_warning status maps."""
    id_to_name: dict[str, str] = {}
    id_to_kept: dict[str, bool] = {}
    for rec in records:
        if rec.get("isMeta"):
            continue
        if rec.get("type") in HOUSEKEEPING_TYPES:
            continue
        content = _message_content(rec)
        if not isinstance(content, list):
            continue
        content_blocks = cast(list[object], content)
        for blk in content_blocks:
            if not isinstance(blk, dict):
                continue
            block = cast(Block, blk)
            bt = block.get("type")
            if bt == "tool_use":
                bid = block.get("id")
                if isinstance(bid, str) and bid:
                    name = block.get("name")
                    id_to_name[bid] = name if isinstance(name, str) else "?"
            elif bt == "tool_result":
                tid = block.get("tool_use_id")
                if not isinstance(tid, str) or not tid:
                    continue
                tname = id_to_name.get(tid, "?")
                error, warning, _ = classify_tool_result(blk=block, tool_name=tname)
                id_to_kept[tid] = (error or warning)
    return id_to_name, id_to_kept


def render_user_blocks(*, content: object, id_to_name: dict[str, str]) -> list[Block]:
    blocks: list[Block] = []
    if isinstance(content, str):
        s = SYSREM_RE.sub("", content).strip()
        if "<command-name>" in s:
            m = CMD_NAME_RE.search(s)
            a = CMD_ARGS_RE.search(s)
            name = (m.group(1).strip() if m else "")
            args = (a.group(1).strip() if a else "")
            if name:
                command_block: Block = {"type": "command", "name": name}
                if args:
                    command_block["args"] = args
                blocks.append(command_block)
        elif s:
            blocks.append({"type": "text", "value": s})
        return blocks
    if not isinstance(content, list):
        return blocks
    content_blocks = cast(list[object], content)
    for blk in content_blocks:
        if not isinstance(blk, dict):
            continue
        block = cast(Block, blk)
        if block.get("type") != "tool_result":
            continue
        tid_obj = block.get("tool_use_id", "")
        tid = tid_obj if isinstance(tid_obj, str) else ""
        tname = id_to_name.get(tid, "?")
        txt = tool_result_text(block)
        error, warning, exit_code = classify_tool_result(blk=block, tool_name=tname)
        out: Block = {"type": "tool_result", "tool_use_id": tid, "name": tname}
        if error or warning:
            out["text"] = txt
            if error:
                out["error"] = True
            if warning:
                out["warning"] = True
            if exit_code is not None:
                out["exit_code"] = exit_code
            blocks.append(out)
        # v3 policy: non-error/non-warning tool_results are dropped entirely
    return blocks


def render_assistant_blocks(*, content: object, id_to_kept: dict[str, bool]) -> list[Block]:
    blocks: list[Block] = []
    if not isinstance(content, list):
        return blocks
    # Does any tool_use in this assistant turn map to a kept (errored or warned) tool_result?
    turn_has_kept = False
    content_blocks = cast(list[object], content)
    for blk in content_blocks:
        if not isinstance(blk, dict):
            continue
        block = cast(Block, blk)
        if block.get("type") == "tool_use":
            bid = block.get("id")
            if isinstance(bid, str) and id_to_kept.get(bid, False):
                turn_has_kept = True
                break
    for blk in content_blocks:
        if not isinstance(blk, dict):
            continue
        block = cast(Block, blk)
        rendered = _render_assistant_block(block, turn_has_kept=turn_has_kept)
        if rendered is not None:
            blocks.append(rendered)
        # v3 policy: non-reference tool_use (tool_call) blocks are dropped entirely
    return blocks


def render(input_path: Path) -> str:
    if not input_path.is_file():
        raise FileNotFoundError(str(input_path))
    records: list[Record] = list(parse_jsonl(input_path))
    if not records:
        raise ValueError(f"no parseable records in {input_path}")
    id_to_name, id_to_kept = first_pass(records)
    turns: list[Block] = []
    turn_no = 0
    for rec in records:
        if rec.get("isMeta"):
            continue
        if rec.get("type") in HOUSEKEEPING_TYPES:
            continue
        msg_obj = rec.get("message")
        if not isinstance(msg_obj, dict):
            continue
        msg = cast(Record, msg_obj)
        role = msg.get("role")
        if role not in ("user", "assistant"):
            continue
        if role == "user":
            blocks = render_user_blocks(content=msg.get("content"), id_to_name=id_to_name)
        else:
            blocks = render_assistant_blocks(content=msg.get("content"), id_to_kept=id_to_kept)
        if not blocks:
            continue
        turn_no += 1
        turns.append({"turn": turn_no, "role": role, "blocks": blocks})

    header = {
        "v": SCHEMA_VERSION,
        "source_basename": input_path.name,
        "turns": len(turns),
        "policy": "prose-errors-and-reference-reads",
    }
    out_lines = [json.dumps(header, ensure_ascii=False, separators=(",", ":"))]
    for t in turns:
        out_lines.append(json.dumps(t, ensure_ascii=False, separators=(",", ":")))
    return "\n".join(out_lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    _ = p.add_argument("--input", required=True, help="Path to raw Claude Code session JSONL")
    _ = p.add_argument("--output", help="Path to write filtered JSONL (default: stdout)")
    args = p.parse_args(argv if argv is not None else sys.argv[1:])
    inp = Path(args.input)
    try:
        out = render(inp)
    except FileNotFoundError as e:
        print(f"render-session-transcript: input missing: {e}", file=sys.stderr)
        return 2
    except ValueError as e:
        print(f"render-session-transcript: {e}", file=sys.stderr)
        return 3
    if args.output:
        _ = Path(args.output).write_text(out, encoding="utf-8")
    else:
        _ = sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
