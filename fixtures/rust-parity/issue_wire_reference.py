"""Frozen Python behavior for the issue #8171 issue-body wire cutover.

This reproduces `plan-block read`, `plan-block write`, `plan-block strip-body`,
`named-block write`, `plan scope-paths`, `issue title-eligibility`,
`issue title-archival-jq`, `issue insert-signal-marker`, `untrusted file-block`,
`untrusted content-block`, `untrusted redact-stream`, and
`untrusted xml-escape-attr` from `python/larch/issue/issue_wire.py` as they
behaved at cutover, restricted to the paths a hermetic sandbox can reach.

The eight offline verbs are covered end to end: their scanners, their exact
stdout bytes, and the `## Files to modify/create` scope grammar. The three
GitHub-backed verbs — `plan-block read`, `plan-block write`, and `named-block
write` — reach the network for everything past their scanners, and the sandbox
has no `gh`, no `git`, and no network, so their cases cover the argument
scanner, the marker and issue validation in front of it, the content-file read,
and the refusal each reports when no repository can be resolved. The
compare-and-swap, the outbound redaction, and the post-write proof sit behind
the first request and are covered by the unit tests in
`crates/larch-cli/src/issue_wire_commands.rs` and the mutation-owner tests in
`crates/larch-core/src/issue_mutation.rs` instead.

Deliberate omissions, none of them part of a command contract:

* `logging_util.quiet_init` file routing. It duplicates stdout and stderr into a
  per-invocation `$TMPDIR/larch-quiet-*.log` while leaving the contract streams
  pointed at the original descriptors, so a caller sees identical bytes either
  way.
* PEM private-key block swallowing. The secret-family substitutions below stand
  in for that pass, and no case here carries a PEM block.
* Session-tmpdir path redaction beyond the one recognized shape the cases use.

Nine differences are intentional and documented in the pull request:

* Numeric validation. Python used `str.isdecimal()` for `--issue`, which also
  accepted non-ASCII digits and magnitudes no issue number can reach. Rust
  accepts only ASCII decimals that fit a 64-bit unsigned integer and reports
  anything else through the same refusal.
* Filesystem error text. Python echoed the `OSError` repr for an unreadable
  `--file`, and let an unreadable `untrusted file-block` path escape as a
  traceback. Rust names the same failure in one line with the platform's own
  message, and exits `1` on both paths exactly as Python did.
* The named-block body redaction. Python scrubbed secret families only; the
  Rust mutation owner scrubs session and operator paths as well, which is
  strictly more redaction on a surface that is published to GitHub. It also
  changes `BODY_BYTES` when a body carries such a path.
* The post-write proof. Python re-read the issue after the write; Rust proves
  the block from the mutation owner's own read-back, which is the same bytes
  one request earlier.
* The compare-and-swap snapshot. Python read the body, then read a second
  snapshot for the swap; Rust composes and swaps against one snapshot, so a
  concurrent edit between the two reads is refused rather than overwritten.
* The `redaction:`-prefixed exit `3`. It could only fire when the redactor
  itself raised, which the Rust redactor cannot do; a failed redaction is the
  mutation owner's `redaction-failed` refusal and exits `2` in both owners.
* `OUTPUT=` and `ERROR=` row hardening. Python passed the raw value to
  `emit_kv`, which raised when it carried a newline; Rust strips the control
  bytes so the row can never forge a second contract line.
* The repository slug. Python matched `--repo` against a character-class regular
  expression; Rust parses it into the typed repository reference every GitHub
  call already takes, which additionally refuses a bare `.` or `..` component
  and a component past 100 characters. No caller names such a repository. On the
  same path, an ambient repository too malformed to parse reports `could not
  determine repo` and exit `2` where Python reported `invalid-repo` and exit
  `1`; only `gh` and `git` produce that value, and neither produces one.
* Artifact write failures. Python let a failed `--output` write escape as a
  traceback; Rust reports the same exit `1` through the `FAILED=true` / `ERROR=`
  envelope the verb already publishes for every other refusal.
"""
# ruff: noqa: FBT001, FBT003, PLR0911, PLR2004 - the frozen scanners return, branch, and take the marker
# switch exactly as they shipped.

from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

REDACTED_TOKEN = "<REDACTED-TOKEN>"
SCOPE_PATH_FALLBACK = ["skills/design/SKILL.md"]
ALLOWED_MARKERS = {"plan", "design-pause"}

SECRET_FAMILIES = (
    re.compile(r"sk-(ant-)?[A-Za-z0-9_-]{20,}"),
    re.compile(r"(ghp|gho|ghu|ghs|ghr|github_pat)_[A-Za-z0-9_]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    re.compile(r"crsr_[A-Za-z0-9_-]{20,}|key_[A-Za-z0-9]{32,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"AIza[0-9A-Za-z_-]{35}"),
    re.compile(r"(?:sk|rk)_live_[0-9A-Za-z]{16,}"),
    re.compile(r"glpat-[0-9A-Za-z_-]{20,}"),
)

ARCHIVAL_JQ_FILTER = 'select((.title // "" | ascii_downcase | sub("^[[:space:]]+"; "")) as $t | (($t | startswith("research ")) or ($t | startswith("[research] ")) or ($t | startswith("investigate ")) or ($t | startswith("[investigate] ")) or ($t | test("^\\[.*report\\] "))) | not)'
ARCHIVAL_REPORT_RE = re.compile(r"^\[.*report\] ", re.IGNORECASE)
LIFECYCLE_REJECT_RE = re.compile(
    r"^\[(IMPLEMENTING|DONE|DESIGNING|DESIGNED|DEBATING|DEBATED)\]", re.IGNORECASE
)
BRAINSTORM_RE = re.compile(r"^brainstorm([^A-Za-z]|$)", re.IGNORECASE)
LIFECYCLE_INSERT_PREFIXES = (
    "DEBATING",
    "DEBATED",
    "DESIGNING",
    "DESIGNED",
    "IMPLEMENTING",
    "DONE",
    "STALLED",
    "IN PROGRESS",
    "PLANNED",
)

HEADING_RE = re.compile(
    r"^(?P<level>##|###)[ \t]+(?P<kind>NEW|UPDATED|REWRITTEN|MAY_UPDATE)"
    r"(?:[ \t]*:[ \t]*(?P<colon>.+?)|[ \t]+\[(?P<bracket>[^]\r\n]+)\][ \t]*:?)[ \t]*$"
)
GENERIC_LEVEL_TWO_RE = re.compile(r"^##(?:[ \t]+|$)(?!#)")
FENCE_MARKER_RE = re.compile(r"^(`{3,}|~{3,})(.*)$")
SCOPE_SECTION_RE = re.compile(r"^##\s+Files to modify(?:/create)?\s*$")

# The one refusal a sandbox can pin for the three GitHub-backed verbs:
# repository resolution needs `gh repo view` or a `git` remote, and the sandbox
# has neither.
UNRESOLVABLE_REPO = "could not determine repo"


def redact_secrets(text: str) -> str:
    for family in SECRET_FAMILIES:
        text = family.sub(REDACTED_TOKEN, text)
    return text


def redact(text: str) -> str:
    scrubbed = redact_secrets(text)
    if scrubbed and not scrubbed.endswith("\n"):
        scrubbed += "\n"
    return scrubbed


def diagnostic(message: str) -> None:
    sanitized = "".join(ch for ch in message if ch >= " " and ch != "\x7f")
    print(redact_secrets(sanitized), file=sys.stderr)


def emit_kv(key: str, value: object) -> None:
    print(f"{key}={value}")


def emit_failed(error: str) -> None:
    emit_kv("FAILED", "true")
    emit_kv("ERROR", error)


def bool_str(value: object) -> str:
    return "true" if value else "false"


class DiagnosticArgumentParser(argparse.ArgumentParser):
    def _print_message(self, message: str, file: object | None = None) -> None:
        _ = file
        if message:
            diagnostic(message)


# ---------------------------------------------------------------- named blocks


def marker_line(line: str, marker: str, kind: str) -> bool:
    pattern = re.compile(rf"^[ \t]*<!--[ \t]+larch:{re.escape(marker)}:{kind}[ \t]+-->[ \t]*\r?$")
    return pattern.fullmatch(line.rstrip("\n")) is not None


def balanced_fence_line_indices(lines: list[str]) -> set[int]:
    fenced: set[int] = set()
    stack: list[tuple[int, str, int]] = []
    for index, line in enumerate(lines):
        match = FENCE_MARKER_RE.match(line.strip())
        if match is None:
            continue
        marker = match.group(1)
        if not stack:
            stack.append((index, marker[0], len(marker)))
            continue
        top_index, top_char, top_len = stack[-1]
        if marker[0] == top_char and len(marker) >= top_len and match.group(2).strip() == "":
            stack.pop()
            fenced.update(range(top_index + 1, index))
    return fenced


def classify_named_block(lines: list[str], marker: str) -> tuple[int | None, int | None, str]:
    fenced = balanced_fence_line_indices([line.rstrip("\r\n") for line in lines])
    starts = [i for i, line in enumerate(lines) if i not in fenced and marker_line(line, marker, "start")]
    ends = [i for i, line in enumerate(lines) if i not in fenced and marker_line(line, marker, "end")]
    if not starts and not ends:
        return None, None, ""
    if len(starts) > 1:
        return None, None, "multiple-start"
    if len(ends) > 1:
        return None, None, "multiple-end"
    if not ends:
        return None, None, "start-without-end"
    if not starts:
        return None, None, "end-without-start"
    if ends[0] < starts[0]:
        return None, None, "end-before-start"
    return starts[0], ends[0], ""


def strip_named_block(body: str, marker: str) -> tuple[str, str]:
    lines = body.splitlines(keepends=True)
    start, end, malformed = classify_named_block(lines, marker)
    if malformed:
        return "", malformed
    if start is None or end is None:
        return body, ""
    return "".join(lines[:start] + lines[end + 1 :]), ""


# ------------------------------------------------------------------- untrusted


def redact_untrusted_stream(text: str) -> str:
    return html.escape(redact(text), quote=False)


def untrusted_xml_escape_attr(argv: list[str]) -> int:
    if argv:
        print(f"untrusted xml-escape-attr: unknown option: {argv[0]}", file=sys.stderr)
        return 2
    text = sys.stdin.read()
    sys.stdout.write(
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )
    return 0


def untrusted_redact_stream(argv: list[str]) -> int:
    if argv:
        print(f"untrusted redact-stream: unknown option: {argv[0]}", file=sys.stderr)
        return 2
    sys.stdout.write(redact_untrusted_stream(sys.stdin.read()))
    return 0


def untrusted_file_block(argv: list[str]) -> int:
    if len(argv) != 2:
        print("untrusted file-block: usage: untrusted file-block TAG PATH", file=sys.stderr)
        return 2
    tag, path = argv
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    sys.stdout.write(f'<{tag} encoding="literal-redacted">\n{redact_untrusted_stream(text)}\n</{tag}>\n\n')
    return 0


def untrusted_content_block(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="untrusted content-block", add_help=True)
    parser.add_argument("tag")
    parser.add_argument("--text")
    args = parser.parse_args(argv)
    text = args.text if args.text is not None else sys.stdin.read()
    sys.stdout.write(
        f'<{args.tag} encoding="literal-redacted">\n{redact_untrusted_stream(text)}\n</{args.tag}>\n\n'
    )
    return 0


# ----------------------------------------------------------------- issue title


def parse_title_marker_args(argv: list[str], want_marker: bool) -> tuple[str | None, str | None, int]:
    title: str | None = None
    marker: str | None = None
    idx = 0
    while idx < len(argv):
        arg = argv[idx]
        if arg == "--title":
            if idx + 1 >= len(argv):
                print("issue title: --title requires a value", file=sys.stderr)
                return None, None, 2
            title = argv[idx + 1]
            idx += 2
        elif arg.startswith("--title="):
            title = arg.split("=", 1)[1]
            idx += 1
        elif want_marker and arg == "--marker":
            if idx + 1 >= len(argv):
                print("issue title: --marker requires a value", file=sys.stderr)
                return None, None, 2
            marker = argv[idx + 1]
            idx += 2
        elif want_marker and arg.startswith("--marker="):
            marker = arg.split("=", 1)[1]
            idx += 1
        else:
            print(f"issue title: unknown option: {arg}", file=sys.stderr)
            return None, None, 2
    if title is None:
        print("issue title: --title is required", file=sys.stderr)
        return None, None, 2
    if want_marker and marker is None:
        print("issue title: --marker is required", file=sys.stderr)
        return None, None, 2
    return title, marker, 0


def issue_title_eligibility(argv: list[str]) -> int:
    title, _marker, rc = parse_title_marker_args(argv, False)
    if rc:
        return rc
    assert title is not None
    trimmed = title.lstrip()
    match = LIFECYCLE_REJECT_RE.match(trimmed)
    print(f"LIFECYCLE_REJECT={bool_str(match is not None)}")
    if match is not None:
        print(f"LIFECYCLE_MARKER=[{match.group(1).upper()}]")
    print(f"ARCHIVAL_REPORT={bool_str(ARCHIVAL_REPORT_RE.match(trimmed) is not None)}")
    print(f"BRAINSTORM={bool_str(BRAINSTORM_RE.match(trimmed) is not None)}")
    return 0


def issue_title_archival_jq(argv: list[str]) -> int:
    if argv:
        print(f"issue title-archival-jq: unknown option: {argv[0]}", file=sys.stderr)
        return 2
    print(ARCHIVAL_JQ_FILTER)
    return 0


def issue_insert_signal_marker(argv: list[str]) -> int:
    title, marker, rc = parse_title_marker_args(argv, True)
    if rc:
        return rc
    assert title is not None
    assert marker is not None
    marker_block = f"[{marker}]"
    if not title:
        sys.stdout.write(marker_block)
        return 0
    rest = title
    while rest.startswith("["):
        close_space = rest.find("] ")
        if close_space < 0:
            break
        if rest[: close_space + 1] == marker_block:
            sys.stdout.write(title)
            return 0
        rest = rest[close_space + 2 :]
    for prefix in LIFECYCLE_INSERT_PREFIXES:
        block = f"[{prefix}] "
        if title[: len(block)].casefold() == block.casefold():
            sys.stdout.write(f"{title[: len(block) - 1]} [{marker}] {title[len(block) :]}")
            return 0
    sys.stdout.write(f"[{marker}] {title}")
    return 0


# ------------------------------------------------------------ plan scope-paths


def extract_scope_paths(plan_text: str) -> list[str]:
    lines = plan_text.splitlines()
    fenced = balanced_fence_line_indices(lines)
    has_scope_section = any(
        index not in fenced
        and FENCE_MARKER_RE.match(line.strip()) is None
        and HEADING_RE.fullmatch(line.rstrip("\r\n")) is None
        and GENERIC_LEVEL_TWO_RE.match(line) is not None
        and SCOPE_SECTION_RE.match(line)
        for index, line in enumerate(lines)
    )
    in_section = not has_scope_section
    seen: list[str] = []
    for index, line in enumerate(lines):
        if index in fenced or FENCE_MARKER_RE.match(line.strip()) is not None:
            continue
        heading = HEADING_RE.fullmatch(line.rstrip("\r\n"))
        if SCOPE_SECTION_RE.match(line):
            in_section = True
            continue
        if in_section and heading is not None:
            tail = (heading.group("colon") or heading.group("bracket") or "").strip()
            if not tail:
                continue
            candidates = [match.group(1).strip() for match in re.finditer(r"`([^`]+)`", tail)]
            if not candidates:
                parts = tail.split()
                candidates = [re.sub(r"\(.*$", "", parts[0]).strip()] if parts else []
            for path in candidates:
                if path and not path.startswith("+") and path not in seen:
                    seen.append(path)
            continue
        if has_scope_section and in_section and heading is None and GENERIC_LEVEL_TWO_RE.match(line):
            break
    return seen or list(SCOPE_PATH_FALLBACK)


def plan_scope_paths(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="extract-plan-scope-paths.sh", add_help=True)
    parser.add_argument("--plan-file", required=True)
    parser.add_argument("-z", "--null", action="store_true")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 2 if int(exc.code or 0) != 0 else 0
    path = Path(args.plan_file)
    if not path.is_file():
        print(f"extract-plan-scope-paths.sh: plan file not found: {args.plan_file}", file=sys.stderr)
        return 2
    paths = extract_scope_paths(path.read_text(encoding="utf-8", errors="replace"))
    sep = "\0" if args.null else "\n"
    sys.stdout.write(sep.join(paths))
    if paths:
        sys.stdout.write(sep)
    return 0


# ------------------------------------------------------------------ plan-block


def plan_block_strip_body(argv: list[str]) -> int:
    parser = DiagnosticArgumentParser(prog="plan-block-strip-body.sh", add_help=True)
    parser.add_argument("--file")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        body = (
            Path(args.file).read_text(encoding="utf-8", errors="replace")
            if args.file
            else sys.stdin.read()
        )
    except OSError as exc:
        diagnostic(f"plan-block-strip-body.sh: {exc}")
        return 1
    stripped, malformed = strip_named_block(body, "plan")
    if malformed:
        if args.output:
            Path(args.output).write_text("", encoding="utf-8")
        emit_kv("MALFORMED", malformed)
        return 1
    if args.output:
        Path(args.output).write_text(stripped, encoding="utf-8")
    else:
        sys.stdout.write(stripped)
    return 0


def validate_positive_issue(prog: str, issue: str) -> bool:
    if not issue.isdecimal() or issue == "0":
        diagnostic(f"{prog}: --issue must be a positive integer")
        return False
    return True


def plan_block_read(argv: list[str]) -> int:
    parser = DiagnosticArgumentParser(prog="plan-block-read.sh", add_help=True)
    parser.add_argument("--issue", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--repo")
    args = parser.parse_args(argv)
    if not validate_positive_issue("plan-block-read.sh", args.issue):
        return 1
    Path(args.output).write_text("", encoding="utf-8")
    emit_failed(UNRESOLVABLE_REPO)
    return 2


def named_block_write(argv: list[str], marker_default: str | None) -> int:
    prog = "plan-block-write.sh" if marker_default else "named-block-write.sh"
    parser = DiagnosticArgumentParser(prog=prog, add_help=True)
    if marker_default is None:
        parser.add_argument("--marker", required=True)
    parser.add_argument("--issue", required=True)
    parser.add_argument("--content-file")
    parser.add_argument("--delete", action="store_true")
    parser.add_argument("--repo")
    args = parser.parse_args(argv)
    marker = marker_default or args.marker
    if marker not in ALLOWED_MARKERS:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", marker or ""):
            diagnostic(f"{prog}: --marker must match ^[a-z0-9][a-z0-9-]*$")
            return 1
        diagnostic(f"{prog}: unsupported marker: {marker}")
        return 1
    if not validate_positive_issue(prog, args.issue):
        return 1
    if args.delete and args.content_file:
        diagnostic(f"{prog}: --delete and --content-file are mutually exclusive")
        return 1
    if not args.delete and not args.content_file:
        parser.print_usage()
        return 1
    if args.content_file and not Path(args.content_file).is_file():
        emit_failed(f"content file not found: {args.content_file}")
        return 1
    emit_failed(UNRESOLVABLE_REPO)
    return 2


COMMANDS = {
    "untrusted-xml-escape-attr": untrusted_xml_escape_attr,
    "untrusted-redact-stream": untrusted_redact_stream,
    "untrusted-file-block": untrusted_file_block,
    "untrusted-content-block": untrusted_content_block,
    "issue-title-eligibility": issue_title_eligibility,
    "issue-title-archival-jq": issue_title_archival_jq,
    "issue-insert-signal-marker": issue_insert_signal_marker,
    "plan-scope-paths": plan_scope_paths,
    "plan-block-strip-body": plan_block_strip_body,
    "plan-block-read": plan_block_read,
    "plan-block-write": lambda argv: named_block_write(argv, "plan"),
    "named-block-write": lambda argv: named_block_write(argv, None),
}


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print("usage: issue_wire_reference.py COMMAND [args...]", file=sys.stderr)
        return 2
    return COMMANDS[sys.argv[1]](sys.argv[2:])


if __name__ == "__main__":
    raise SystemExit(main())
