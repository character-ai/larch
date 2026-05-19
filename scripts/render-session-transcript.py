#!/usr/bin/env python3
"""render-session-transcript.py — render a Claude Code session JSONL as a chat-view markdown file.

Filter rules:
  - Drop records with isMeta=true (harness-injected slash-command/@file expansions).
  - Drop housekeeping record types: permission-mode, file-history-snapshot,
    attachment, last-prompt, queue-operation, system.
  - User records:
      * <command-message>/<command-name>/<command-args> blocks → '> /name args'.
      * plain text → '> text' (with <system-reminder> blocks stripped).
      * tool_result blocks → see tool_result rule below.
  - Assistant records:
      * text blocks rendered verbatim.
      * tool_use rendered as 'Tool name(compact-input)'.
      * thinking blocks kept only when at least one tool_use in the same
        assistant turn produced an errored tool_result.
  - tool_result kept in full when:
      (a) block has is_error=true, OR
      (b) tool is 'Bash' AND first 500 chars contain '^(Error:|Exit code [1-9])'
          OR a 'warning:' substring (case-insensitive).
    Otherwise replaced with '[Tool → N bytes elided]'.

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
BASH_FAIL_RE = re.compile(r"(?m)^(Error:|Exit code [1-9])")
WARN_RE = re.compile(r"warning:", re.I)


def is_error_result(blk: dict, tool_name: str) -> bool:
    """Return True when this tool_result should be kept in full."""
    if blk.get("is_error") is True:
        return True
    if tool_name != "Bash":
        return False
    c = blk.get("content")
    if isinstance(c, str):
        txt = c
    elif isinstance(c, list):
        txt = "".join(
            x.get("text", "") for x in c
            if isinstance(x, dict) and x.get("type") == "text"
        )
    else:
        return False
    head = txt[:500]
    return bool(BASH_FAIL_RE.search(head) or WARN_RE.search(head))


def extract_text_from_tool_result(blk: dict) -> str:
    c = blk.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return "".join(
            x.get("text", "") for x in c
            if isinstance(x, dict) and x.get("type") == "text"
        )
    return ""


def compact_input(inp: object, limit: int = 200) -> str:
    """Render a tool_use input dict as a compact one-liner, truncated."""
    if not isinstance(inp, (dict, list)):
        return str(inp)[:limit]
    s = json.dumps(inp, separators=(",", ":"), ensure_ascii=False)
    if len(s) <= limit:
        return s
    return s[:limit] + "…"


def parse_jsonl(path: Path):
    """Yield (line_number, record) for each parseable line."""
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for ln, line in enumerate(fh, 1):
            line = line.rstrip("\n")
            if not line:
                continue
            try:
                yield ln, json.loads(line)
            except json.JSONDecodeError:
                continue


def first_pass(records):
    """Build tool_use_id → name and tool_use_id → error_status maps."""
    id_to_name: dict[str, str] = {}
    id_to_err: dict[str, bool] = {}
    for _, rec in records:
        if rec.get("isMeta"):
            continue
        if rec.get("type") in HOUSEKEEPING_TYPES:
            continue
        msg = rec.get("message", {})
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        for blk in content:
            if not isinstance(blk, dict):
                continue
            t = blk.get("type")
            if t == "tool_use":
                bid = blk.get("id", "")
                if bid:
                    id_to_name[bid] = blk.get("name", "?")
            elif t == "tool_result":
                tid = blk.get("tool_use_id", "")
                if not tid:
                    continue
                # tool name comes from a prior assistant turn already scanned
                tname = id_to_name.get(tid, "?")
                id_to_err[tid] = is_error_result(blk, tname)
    return id_to_name, id_to_err


def render_user(rec, msg, id_to_name, id_to_err, out):
    content = msg.get("content")
    if isinstance(content, str):
        s = SYSREM_RE.sub("", content).strip()
        if "<command-name>" in s:
            m = CMD_NAME_RE.search(s)
            a = CMD_ARGS_RE.search(s)
            cmd = (m.group(1).strip() if m else "")
            args = (a.group(1).strip() if a else "")
            line = (cmd + (" " + args if args else "")).strip()
            if line:
                out.append(f"> {line}")
        elif s:
            for ln in s.splitlines():
                out.append(f"> {ln}")
        return

    if not isinstance(content, list):
        return
    for blk in content:
        if not isinstance(blk, dict):
            continue
        if blk.get("type") != "tool_result":
            continue
        tid = blk.get("tool_use_id", "")
        tname = id_to_name.get(tid, "?")
        txt = extract_text_from_tool_result(blk)
        if id_to_err.get(tid, False) or is_error_result(blk, tname):
            head = txt[:500]
            first_err = ""
            m = BASH_FAIL_RE.search(head)
            if m:
                first_err = head.split("\n", 1)[0][:160]
            label = f"[{tname} ERROR"
            if first_err:
                label += f" — {first_err}"
            label += "]"
            out.append(label)
            out.append("```")
            out.append(txt)
            out.append("```")
        else:
            n = len(txt)
            out.append(f"[{tname} → {n} bytes elided]")


def render_assistant(rec, msg, id_to_name, id_to_err, out):
    content = msg.get("content")
    if not isinstance(content, list):
        return
    # Determine whether any tool_use in this turn errored.
    turn_has_error = False
    for blk in content:
        if isinstance(blk, dict) and blk.get("type") == "tool_use":
            if id_to_err.get(blk.get("id", ""), False):
                turn_has_error = True
                break
    for blk in content:
        if not isinstance(blk, dict):
            continue
        t = blk.get("type")
        if t == "text":
            txt = SYSREM_RE.sub("", blk.get("text", "")).rstrip()
            if not txt or txt.startswith("Base directory for this skill"):
                continue
            out.append(txt)
        elif t == "thinking":
            if not turn_has_error:
                continue
            think = blk.get("thinking", "").strip()
            if not think:
                continue
            out.append("<thinking>")
            out.append(think)
            out.append("</thinking>")
        elif t == "tool_use":
            name = blk.get("name", "?")
            inp = compact_input(blk.get("input", {}))
            out.append(f"[{name}({inp})]")


def render(input_path: Path) -> str:
    if not input_path.is_file():
        raise FileNotFoundError(str(input_path))
    records = list(parse_jsonl(input_path))
    if not records:
        raise ValueError(f"no parseable records in {input_path}")
    id_to_name, id_to_err = first_pass(records)
    out: list[str] = []
    out.append(f"# Session transcript — chat view")
    out.append(f"")
    out.append(f"Source: `{input_path.name}` ({len(records)} records)")
    out.append(f"")
    turn = 0
    for _, rec in records:
        if rec.get("isMeta"):
            continue
        if rec.get("type") in HOUSEKEEPING_TYPES:
            continue
        msg = rec.get("message", {})
        role = msg.get("role")
        if role not in ("user", "assistant"):
            continue
        turn += 1
        out.append(f"## Turn {turn} — {role}")
        out.append("")
        before = len(out)
        if role == "user":
            render_user(rec, msg, id_to_name, id_to_err, out)
        else:
            render_assistant(rec, msg, id_to_name, id_to_err, out)
        if len(out) == before:
            # nothing rendered for this turn (e.g. only housekeeping content) — drop header
            out.pop()  # blank line
            out.pop()  # header
            turn -= 1
        else:
            out.append("")
    return "\n".join(out).rstrip() + "\n"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--input", required=True, help="Path to session-transcript.jsonl")
    p.add_argument("--output", help="Path to write rendered .md (default: stdout)")
    args = p.parse_args()
    inp = Path(args.input)
    try:
        md = render(inp)
    except FileNotFoundError as e:
        print(f"render-session-transcript: input missing: {e}", file=sys.stderr)
        return 2
    except ValueError as e:
        print(f"render-session-transcript: {e}", file=sys.stderr)
        return 3
    if args.output:
        Path(args.output).write_text(md, encoding="utf-8")
    else:
        sys.stdout.write(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
