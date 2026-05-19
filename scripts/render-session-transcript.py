#!/usr/bin/env python3
"""render-session-transcript.py — render a Claude Code session JSONL as a filtered chat-view JSONL.

Output schema (v1):

  Line 1 is a header record:
      {"v": 1, "source_basename": "<input-basename>", "turns": N}

  Subsequent lines are per-turn records (one JSON object per line):
      {"turn": <int>, "role": "user" | "assistant", "blocks": [<block>...]}

  Block types:
      {"type": "command", "name": "/cmd", "args": "..."}     # slash command typed by user
      {"type": "text", "value": "..."}                       # plain user / assistant text
      {"type": "thinking", "value": "..."}                   # assistant thinking (kept only when adjacent to error)
      {"type": "tool_call", "id": "toolu_...", "name": "Bash", "input": {...}}
      {"type": "tool_result", "tool_use_id": "toolu_...", "name": "Bash",
       "elided_bytes": N}                                    # routine result, body elided
      {"type": "tool_result", "tool_use_id": "toolu_...", "name": "Bash",
       "text": "...", "error": true, "exit_code": N}         # errored result (full body)
      {"type": "tool_result", "tool_use_id": "toolu_...", "name": "Bash",
       "text": "...", "warning": true}                       # warning result (full body)

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
    Otherwise replaced with `elided_bytes`.
  - thinking blocks kept only when at least one tool_use in the same
    assistant turn produced an errored tool_result.

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

SCHEMA_VERSION = 1

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


def tool_result_text(blk: dict) -> str:
    c = blk.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return "".join(
            x.get("text", "") for x in c
            if isinstance(x, dict) and x.get("type") == "text"
        )
    return ""


def classify_tool_result(blk: dict, tool_name: str) -> tuple[bool, bool, int | None]:
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
    exit_code = int(exit_match.group(1)) if exit_match else None
    has_err_prefix = bool(ERROR_PREFIX_RE.search(head))
    has_warn = bool(WARN_RE.search(head))
    error = is_err_flag or exit_code is not None or has_err_prefix
    warning = (not error) and has_warn
    return (error, warning, exit_code)


def parse_jsonl(path: Path):
    """Yield record dicts from a JSONL file, skipping unparseable lines."""
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def first_pass(records):
    """Build tool_use_id → name and tool_use_id → error_or_warning status maps."""
    id_to_name: dict[str, str] = {}
    id_to_kept: dict[str, bool] = {}
    for rec in records:
        if rec.get("isMeta"):
            continue
        if rec.get("type") in HOUSEKEEPING_TYPES:
            continue
        content = rec.get("message", {}).get("content")
        if not isinstance(content, list):
            continue
        for blk in content:
            if not isinstance(blk, dict):
                continue
            bt = blk.get("type")
            if bt == "tool_use":
                bid = blk.get("id", "")
                if bid:
                    id_to_name[bid] = blk.get("name", "?")
            elif bt == "tool_result":
                tid = blk.get("tool_use_id", "")
                if not tid:
                    continue
                tname = id_to_name.get(tid, "?")
                error, warning, _ = classify_tool_result(blk, tname)
                id_to_kept[tid] = (error or warning)
    return id_to_name, id_to_kept


def render_user_blocks(content, id_to_name) -> list[dict]:
    blocks: list[dict] = []
    if isinstance(content, str):
        s = SYSREM_RE.sub("", content).strip()
        if "<command-name>" in s:
            m = CMD_NAME_RE.search(s)
            a = CMD_ARGS_RE.search(s)
            name = (m.group(1).strip() if m else "")
            args = (a.group(1).strip() if a else "")
            if name:
                blk: dict = {"type": "command", "name": name}
                if args:
                    blk["args"] = args
                blocks.append(blk)
        elif s:
            blocks.append({"type": "text", "value": s})
        return blocks
    if not isinstance(content, list):
        return blocks
    for blk in content:
        if not isinstance(blk, dict):
            continue
        if blk.get("type") != "tool_result":
            continue
        tid = blk.get("tool_use_id", "")
        tname = id_to_name.get(tid, "?")
        txt = tool_result_text(blk)
        error, warning, exit_code = classify_tool_result(blk, tname)
        out: dict = {"type": "tool_result", "tool_use_id": tid, "name": tname}
        if error or warning:
            out["text"] = txt
            if error:
                out["error"] = True
            if warning:
                out["warning"] = True
            if exit_code is not None:
                out["exit_code"] = exit_code
        else:
            out["elided_bytes"] = len(txt)
        blocks.append(out)
    return blocks


def render_assistant_blocks(content, id_to_kept) -> list[dict]:
    blocks: list[dict] = []
    if not isinstance(content, list):
        return blocks
    # Does any tool_use in this assistant turn map to a kept (errored or warned) tool_result?
    turn_has_kept = False
    for blk in content:
        if isinstance(blk, dict) and blk.get("type") == "tool_use":
            if id_to_kept.get(blk.get("id", ""), False):
                turn_has_kept = True
                break
    for blk in content:
        if not isinstance(blk, dict):
            continue
        bt = blk.get("type")
        if bt == "text":
            txt = SYSREM_RE.sub("", blk.get("text", "")).rstrip()
            if not txt or txt.startswith("Base directory for this skill"):
                continue
            blocks.append({"type": "text", "value": txt})
        elif bt == "thinking":
            if not turn_has_kept:
                continue
            think = blk.get("thinking", "").strip()
            if think:
                blocks.append({"type": "thinking", "value": think})
        elif bt == "tool_use":
            out: dict = {"type": "tool_call"}
            tid = blk.get("id", "")
            if tid:
                out["id"] = tid
            out["name"] = blk.get("name", "?")
            inp = blk.get("input", {})
            if inp:
                out["input"] = inp
            blocks.append(out)
    return blocks


def render(input_path: Path) -> str:
    if not input_path.is_file():
        raise FileNotFoundError(str(input_path))
    records = list(parse_jsonl(input_path))
    if not records:
        raise ValueError(f"no parseable records in {input_path}")
    id_to_name, id_to_kept = first_pass(records)
    turns: list[dict] = []
    turn_no = 0
    for rec in records:
        if rec.get("isMeta"):
            continue
        if rec.get("type") in HOUSEKEEPING_TYPES:
            continue
        msg = rec.get("message", {})
        role = msg.get("role")
        if role not in ("user", "assistant"):
            continue
        if role == "user":
            blocks = render_user_blocks(msg.get("content"), id_to_name)
        else:
            blocks = render_assistant_blocks(msg.get("content"), id_to_kept)
        if not blocks:
            continue
        turn_no += 1
        turns.append({"turn": turn_no, "role": role, "blocks": blocks})

    header = {
        "v": SCHEMA_VERSION,
        "source_basename": input_path.name,
        "turns": len(turns),
    }
    out_lines = [json.dumps(header, ensure_ascii=False, separators=(",", ":"))]
    for t in turns:
        out_lines.append(json.dumps(t, ensure_ascii=False, separators=(",", ":")))
    return "\n".join(out_lines) + "\n"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--input", required=True, help="Path to raw Claude Code session JSONL")
    p.add_argument("--output", help="Path to write filtered JSONL (default: stdout)")
    args = p.parse_args()
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
        Path(args.output).write_text(out, encoding="utf-8")
    else:
        sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
