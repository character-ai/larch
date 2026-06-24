# pyright: reportUnusedCallResult=false
"""Issue-body wire helpers for plan blocks, named blocks, titles, and untrusted text."""

from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path
from collections.abc import Sequence
from dataclasses import dataclass

import gh
import logging_util
import proc
import redact
from errors import ShipError
from proc import Runner

_ALLOWED_MARKERS = {"plan", "design-pause"}
_MALFORMED_TOKENS = {
    "multiple-start",
    "multiple-end",
    "start-without-end",
    "end-without-start",
    "end-before-start",
}

# Byte-compatible with the legacy title-eligibility shell helper.
ARCHIVAL_JQ_FILTER = 'select((.title // "" | ascii_downcase | sub("^[[:space:]]+"; "")) as $t | (($t | startswith("research ")) or ($t | startswith("[research] ")) or ($t | startswith("investigate ")) or ($t | startswith("[investigate] ")) or ($t | test("^\\[.*report\\] "))) | not)'
ARCHIVAL_REPORT_RE = re.compile(r"^\[.*report\] ", re.IGNORECASE)
LIFECYCLE_REJECT_RE = re.compile(r"^\[(IMPLEMENTING|DONE|DESIGNING|DESIGNED)\]", re.IGNORECASE)
BRAINSTORM_RE = re.compile(r"^brainstorm([^A-Za-z]|$)", re.IGNORECASE)
_SCOPE_PATH_FALLBACK = ["skills/design/SKILL.md"]
_LIFECYCLE_INSERT_PREFIXES = (
    "DESIGNING",
    "DESIGNED",
    "IMPLEMENTING",
    "DONE",
    "STALLED",
    "IN PROGRESS",
    "PLANNED",
)


class _DiagnosticArgumentParser(argparse.ArgumentParser):
    def _print_message(self, message: str, file: object | None = None) -> None:
        _ = file
        if message:
            logging_util.diagnostic(message)


def _marker_re(*, marker: str, kind: str) -> re.Pattern[str]:
    return re.compile(rf"^\s*<!--\s+larch:{re.escape(marker)}:{kind}\s+-->\s*$")


def _line_is_marker(*, line: str, marker: str, kind: str) -> bool:
    return _marker_re(marker=marker, kind=kind).match(line.rstrip("\n")) is not None


@dataclass(frozen=True)
class _BlockSpan:
    start: int | None
    end: int | None
    malformed: str


def _classify_named_block_lines(*, lines: Sequence[str], marker: str) -> _BlockSpan:
    start_indexes: list[int] = [idx for idx, line in enumerate(lines) if _line_is_marker(line=line, marker=marker, kind="start")]
    end_indexes: list[int] = [idx for idx, line in enumerate(lines) if _line_is_marker(line=line, marker=marker, kind="end")]
    if not start_indexes and not end_indexes:
        return _BlockSpan(None, None, "")
    if len(start_indexes) > 1:
        return _BlockSpan(None, None, "multiple-start")
    if len(end_indexes) > 1:
        return _BlockSpan(None, None, "multiple-end")
    if start_indexes and not end_indexes:
        return _BlockSpan(None, None, "start-without-end")
    if end_indexes and not start_indexes:
        return _BlockSpan(None, None, "end-without-start")
    start = start_indexes[0]
    end = end_indexes[0]
    if end < start:
        return _BlockSpan(None, None, "end-before-start")
    return _BlockSpan(start, end, "")


def parse_named_block(*, body: str, marker: str) -> tuple[str | None, str]:
    """Return the requested larch named block inner text and malformed token."""
    lines = body.splitlines(keepends=True)
    span = _classify_named_block_lines(lines=lines, marker=marker)
    if span.malformed:
        return None, span.malformed
    if span.start is None or span.end is None:
        return None, ""
    return "".join(lines[span.start + 1 : span.end]), ""


def strip_named_block(*, body: str, marker: str) -> tuple[str, str]:
    """Remove only the requested named block, preserving unrelated larch blocks."""
    lines = body.splitlines(keepends=True)
    span = _classify_named_block_lines(lines=lines, marker=marker)
    if span.malformed:
        return "", span.malformed
    if span.start is None or span.end is None:
        return body, ""
    return "".join([*lines[: span.start], *lines[span.end + 1 :]]), ""


def compose_named_block(*, marker: str, inner: str) -> str:
    stripped = inner.rstrip("\n")
    block = f"<!-- larch:{marker}:start -->\n"
    if stripped:
        block += stripped + "\n"
    return block + f"<!-- larch:{marker}:end -->\n"


def _single_line_redacted(text: str) -> str:
    if not text:
        return ""
    redacted = redact.redact_secrets_only(text)
    if "[content truncated" in redacted:
        return "gh stderr redaction unavailable"
    return redacted.replace("\n", " ")[:500]


def _emit_failed(error: str) -> None:
    logging_util.emit_kv("FAILED", "true")
    logging_util.emit_kv("ERROR", error)


def _resolve_issue_wire_repo(*, runner: Runner, explicit: str | None) -> tuple[str | None, str]:
    if explicit:
        return explicit, ""
    try:
        repo = gh.resolve_repo_gh_only(runner)
    except ShipError:
        return None, "could not determine repo"
    if not repo:
        return None, "could not determine repo"
    return repo, ""


def _validate_positive_issue(*, prog: str, issue: str) -> bool:
    if not issue.isdecimal() or issue == "0":
        logging_util.diagnostic(f"{prog}: --issue must be a positive integer")
        return False
    return True


def _bool_str(value: object) -> str:
    return "true" if value else "false"


def named_block_write(
    *, runner: Runner,
    marker: str,
    issue: str,
    repo: str,
    content: str | None,
    delete: bool,
) -> dict[str, object]:
    if marker not in _ALLOWED_MARKERS:
        msg = f"unsupported marker: {marker}"
        raise ValueError(msg)
    current_body = gh.issue_view_body(runner, issue, repo=repo).rstrip("\n")
    _, malformed = parse_named_block(body=current_body, marker=marker)
    if malformed:
        return {"malformed": malformed}

    markers_present = parse_named_block(body=current_body, marker=marker)[0] is not None
    if delete:
        if markers_present:
            composed, strip_malformed = strip_named_block(body=current_body, marker=marker)
            if strip_malformed:
                return {"malformed": strip_malformed}
            mode = "removed"
        else:
            composed = current_body
            mode = "absent-noop"
    else:
        if content is None:
            msg = "content is required unless delete is true"
            raise ValueError(msg)
        block = compose_named_block(marker=marker, inner=content)
        if markers_present:
            _stripped, strip_malformed = strip_named_block(body=current_body, marker=marker)
            if strip_malformed:
                return {"malformed": strip_malformed}
            lines = current_body.splitlines(keepends=True)
            span = _classify_named_block_lines(lines=lines, marker=marker)
            assert span.start is not None
            assert span.end is not None
            composed = "".join([*lines[: span.start], block, *lines[span.end + 1 :]])
            mode = "replaced"
        else:
            composed = block if not current_body else current_body + "\n\n" + block
            mode = "appended"

    try:
        redacted_body = redact.redact_secrets_only(composed)
    except Exception as exc:  # pragma: no cover - defensive seam for monkeypatch tests
        msg = f"redaction:{exc}"
        raise ShipError(msg) from exc
    result = gh.issue_edit_body_with_retry(runner, issue, redacted_body, repo=repo)
    if result.returncode != 0:
        raise ShipError(_single_line_redacted(result.stdout + result.stderr))
    return {
        "written": True,
        "mode": mode,
        "markers_present": markers_present,
        "body_bytes": len(redacted_body.encode("utf-8")),
    }


def _content_file_text(path: str) -> tuple[str | None, str]:
    p = Path(path)
    if not p.is_file():
        return None, f"content file not found: {path}"
    return p.read_text(encoding="utf-8", errors="replace"), ""


def _named_block_arg_parser(*, prog: str, include_marker: bool) -> argparse.ArgumentParser:
    parser = _DiagnosticArgumentParser(prog=prog, add_help=True)
    if include_marker:
        parser.add_argument("--marker", required=True)
    parser.add_argument("--issue", required=True)
    parser.add_argument("--content-file")
    parser.add_argument("--delete", action="store_true")
    parser.add_argument("--repo")
    return parser


def _run_named_block_cli(*, argv: list[str], prog: str, marker_default: str | None) -> int:
    logging_util.quiet_init(argv0=prog)
    parser = _named_block_arg_parser(prog=prog, include_marker=marker_default is None)
    args = parser.parse_args(argv)
    marker = marker_default or args.marker
    if marker not in _ALLOWED_MARKERS:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", marker or ""):
            logging_util.diagnostic(f"{prog}: --marker must match ^[a-z0-9][a-z0-9-]*$")
            return 1
        logging_util.diagnostic(f"{prog}: unsupported marker: {marker}")
        return 1
    if not _validate_positive_issue(prog=prog, issue=args.issue):
        return 1
    if args.delete and args.content_file:
        logging_util.diagnostic(f"{prog}: --delete and --content-file are mutually exclusive")
        return 1
    if not args.delete and not args.content_file:
        parser.print_usage()
        return 1
    content = None
    if args.content_file:
        content, content_error = _content_file_text(args.content_file)
        if content_error:
            _emit_failed(content_error)
            return 1
    if args.repo and not gh.validate_repo_slug(args.repo):
        _emit_failed("invalid-repo")
        return 1
    runner: Runner = proc
    repo, repo_error = _resolve_issue_wire_repo(runner=runner, explicit=args.repo)
    if repo_error or repo is None:
        _emit_failed(repo_error or "could not determine repo")
        return 2
    if not gh.validate_repo_slug(repo):
        _emit_failed("invalid-repo")
        return 1
    try:
        result = named_block_write(runner=runner, marker=marker, issue=args.issue, repo=repo, content=content, delete=args.delete)
    except ShipError as exc:
        message = str(exc)
        if message.startswith("redaction:"):
            _emit_failed(message)
            return 3
        _emit_failed(_single_line_redacted(message))
        return 2
    malformed = result.get("malformed")
    if isinstance(malformed, str) and malformed:
        logging_util.emit_kv("MALFORMED", malformed)
        return 1
    logging_util.emit_kv("WRITTEN", "true")
    logging_util.emit_kv("MODE", str(result["mode"]))
    logging_util.emit_kv("MARKERS_PRESENT", _bool_str(bool(result["markers_present"])))
    logging_util.emit_kv("BODY_BYTES", str(result["body_bytes"]))
    return 0


def named_block_write_main(argv: list[str]) -> int:
    return _run_named_block_cli(argv=argv, prog="named-block-write.sh", marker_default=None)


def plan_block_write_main(argv: list[str]) -> int:
    return _run_named_block_cli(argv=argv, prog="plan-block-write.sh", marker_default="plan")


def plan_block_read_main(argv: list[str]) -> int:
    logging_util.quiet_init(argv0="plan-block-read.sh")
    parser = _DiagnosticArgumentParser(prog="plan-block-read.sh", add_help=True)
    parser.add_argument("--issue", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--repo")
    args = parser.parse_args(argv)
    if not _validate_positive_issue(prog="plan-block-read.sh", issue=args.issue):
        return 1
    out_path = Path(args.output)
    runner: Runner = proc
    repo, repo_error = _resolve_issue_wire_repo(runner=runner, explicit=args.repo)
    if repo_error or repo is None:
        out_path.write_text("", encoding="utf-8")
        _emit_failed(repo_error or "could not determine repo")
        return 2
    try:
        body = gh.issue_view_body(runner, args.issue, repo=repo)
    except ShipError as exc:
        out_path.write_text("", encoding="utf-8")
        _emit_failed(_single_line_redacted(str(exc)))
        return 2
    inner, malformed = parse_named_block(body=body, marker="plan")
    if malformed:
        out_path.write_text("", encoding="utf-8")
        logging_util.emit_kv("MALFORMED", malformed)
        return 1
    if inner is None:
        out_path.write_text("", encoding="utf-8")
        logging_util.emit_kv("BLOCK_PRESENT", "false")
        return 0
    out_path.write_text(inner, encoding="utf-8")
    logging_util.emit_kv("BLOCK_PRESENT", "true")
    logging_util.emit_kv("OUTPUT", args.output)
    return 0


def plan_block_strip_body_main(argv: list[str]) -> int:
    parser = _DiagnosticArgumentParser(prog="plan-block-strip-body.sh", add_help=True)
    parser.add_argument("--file")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        body = Path(args.file).read_text(encoding="utf-8", errors="replace") if args.file else sys.stdin.read()
    except OSError as exc:
        logging_util.diagnostic(f"plan-block-strip-body.sh: {exc}")
        return 1
    stripped, malformed = strip_named_block(body=body, marker="plan")
    if malformed:
        if args.output:
            Path(args.output).write_text("", encoding="utf-8")
        logging_util.quiet_init(argv0="plan-block-strip-body.sh")
        logging_util.emit_kv("MALFORMED", malformed)
        return 1
    if args.output:
        Path(args.output).write_text(stripped, encoding="utf-8")
    else:
        sys.stdout.write(stripped)
    return 0


def extract_scope_paths(*, plan_text: str, use_fallback: bool = True, include_optional: bool = True) -> list[str]:
    lines = plan_text.splitlines()
    has_scope_section = any(re.match(r"^##\s+Files to modify(?:/create)?\s*$", line) for line in lines)
    if not use_fallback and not has_scope_section:
        return []
    in_section = not has_scope_section
    seen: list[str] = []
    for line in lines:
        if re.match(r"^##\s+Files to modify(?:/create)?\s*$", line):
            in_section = True
            continue
        if has_scope_section and in_section and re.match(r"^##\s+", line):
            break
        if not in_section:
            continue
        match = re.match(r"^###\s+(NEW|UPDATED|REWRITTEN|MAY_UPDATE)\s*:\s*(.+)$", line)
        if not match:
            continue
        if match.group(1) == "MAY_UPDATE" and not include_optional:
            continue
        tail = match.group(2)
        backtick_matches = list(re.finditer(r"`([^`]+)`", tail))
        if backtick_matches:
            for pm in backtick_matches:
                path = pm.group(1).strip()
                if path and path not in seen:
                    seen.append(path)
        else:
            parts = tail.split()
            if parts:
                token = re.sub(r"\(.*$", "", parts[0]).strip()
                if token and not token.startswith("+") and "/" in token and token not in seen:
                    seen.append(token)
    if seen:
        return seen
    if use_fallback:
        return list(_SCOPE_PATH_FALLBACK)
    return []


def plan_scope_paths_main(argv: list[str]) -> int:
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
    try:
        paths = extract_scope_paths(plan_text=path.read_text(encoding="utf-8", errors="replace"))
    except OSError as exc:
        print(f"extract-plan-scope-paths.sh: {exc}", file=sys.stderr)
        return 2
    sep = "\0" if args.null else "\n"
    sys.stdout.write(sep.join(paths))
    if paths:
        sys.stdout.write(sep)
    return 0


def _trim_leading_ws(title: str) -> str:
    return title.lstrip()


def title_lifecycle_reject_marker(title: str) -> str | None:
    match = LIFECYCLE_REJECT_RE.match(_trim_leading_ws(title))
    if match is None:
        return None
    return f"[{match.group(1).upper()}]"


def title_has_archival_report_prefix(title: str) -> bool:
    return ARCHIVAL_REPORT_RE.match(_trim_leading_ws(title)) is not None


def title_starts_with_brainstorm(title: str) -> bool:
    return BRAINSTORM_RE.match(_trim_leading_ws(title)) is not None


def insert_signal_marker(*, title: str, marker: str) -> str:
    marker_block = f"[{marker}]"
    if not title:
        return marker_block
    rest = title
    while rest.startswith("["):
        close_space = rest.find("] ")
        if close_space < 0:
            break
        block = rest[: close_space + 1]
        if block == marker_block:
            return title
        rest = rest[close_space + 2 :]
    for prefix in _LIFECYCLE_INSERT_PREFIXES:
        block = f"[{prefix}] "
        if title.startswith(block):
            return f"[{prefix}] [{marker}] {title[len(block):]}"
    return f"[{marker}] {title}"


def _parse_title_marker_args(*, argv: list[str], want_marker: bool = False) -> tuple[str | None, str | None, int]:
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


def issue_title_eligibility_main(argv: list[str]) -> int:
    title, _, rc = _parse_title_marker_args(argv=argv)
    if rc:
        return rc
    assert title is not None
    marker = title_lifecycle_reject_marker(title)
    print(f"LIFECYCLE_REJECT={_bool_str(marker is not None)}")
    if marker is not None:
        print(f"LIFECYCLE_MARKER={marker}")
    print(f"ARCHIVAL_REPORT={_bool_str(title_has_archival_report_prefix(title))}")
    print(f"BRAINSTORM={_bool_str(title_starts_with_brainstorm(title))}")
    return 0


def issue_title_archival_jq_main(argv: list[str]) -> int:
    if argv:
        print(f"issue title-archival-jq: unknown option: {argv[0]}", file=sys.stderr)
        return 2
    print(ARCHIVAL_JQ_FILTER)
    return 0


def issue_insert_signal_marker_main(argv: list[str]) -> int:
    title, marker, rc = _parse_title_marker_args(argv=argv, want_marker=True)
    if rc:
        return rc
    assert title is not None
    assert marker is not None
    print(insert_signal_marker(title=title, marker=marker), end="")
    return 0


def xml_escape_attr(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def redact_untrusted_stream(text: str) -> str:
    return html.escape(redact.redact(text), quote=False)


def emit_untrusted_file_block(*, tag: str, path: Path) -> str:
    return f'<{tag} encoding="literal-redacted">\n{redact_untrusted_stream(path.read_text(encoding="utf-8", errors="replace"))}\n</{tag}>\n\n'


def emit_untrusted_content_block(*, tag: str, text: str) -> str:
    return f'<{tag} encoding="literal-redacted">\n{redact_untrusted_stream(text)}\n</{tag}>\n\n'


def untrusted_xml_escape_attr_main(argv: list[str]) -> int:
    if argv:
        print(f"untrusted xml-escape-attr: unknown option: {argv[0]}", file=sys.stderr)
        return 2
    sys.stdout.write(xml_escape_attr(sys.stdin.read()))
    return 0


def untrusted_redact_stream_main(argv: list[str]) -> int:
    if argv:
        print(f"untrusted redact-stream: unknown option: {argv[0]}", file=sys.stderr)
        return 2
    sys.stdout.write(redact_untrusted_stream(sys.stdin.read()))
    return 0


def untrusted_file_block_main(argv: list[str]) -> int:
    expected_arg_count = 2
    if len(argv) != expected_arg_count:
        print("untrusted file-block: usage: untrusted file-block TAG PATH", file=sys.stderr)
        return 2
    sys.stdout.write(emit_untrusted_file_block(tag=argv[0], path=Path(argv[1])))
    return 0


def untrusted_content_block_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="untrusted content-block", add_help=True)
    parser.add_argument("tag")
    parser.add_argument("--text")
    args = parser.parse_args(argv)
    text = args.text if args.text is not None else sys.stdin.read()
    sys.stdout.write(emit_untrusted_content_block(tag=args.tag, text=text))
    return 0


def _join(*parts: str) -> str:
    return "".join(parts)


P3119_TOKENS: tuple[str, ...] = (
    _join("breadcrumb-", "monitor", ".sh"),
    _join("LARCH_", "DONE", "_SENTINEL"),
    _join("LARCH_", "STATUS", "_FILE"),
    _join("LARCH_", "PAIRED", "_PID", "_FILE"),
    _join("LARCH_", "BREADCRUMB", "_STREAM"),
    _join("LARCH_", "BREADCRUMB", "_MONITOR", "_SH"),
    _join("LARCH_", "BREADCRUMBS", "_SURFACED", "_FILE"),
    _join("monitor", "_rc"),
    _join("larch_quiet_append", "_done_trap"),
    _join("larch_quiet_write", "_paired_pid_file"),
    _join("Background pair", " required"),
    _join("BASH_AUTHORING", ".md §4"),
)


def lint_p3119_fence_absence(*, path: Path, label: str, ship_pr: bool = False) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    violations = [
        f"(3119) {label} still references removed Family-B token: {token}"
        for token in P3119_TOKENS
        if token in text
    ]
    ship_pr_token = _join("background", "+", "monitor invocation")
    if ship_pr and ship_pr_token in text:
        violations.append(f"(3119) {label} still mandates {ship_pr_token}")
    return violations


def lint_p3119_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="lint p3119-fence-absence", add_help=True)
    parser.add_argument("path")
    parser.add_argument("label")
    parser.add_argument("--ship-pr", action="store_true")
    args = parser.parse_args(argv)
    violations = lint_p3119_fence_absence(path=Path(args.path), label=args.label, ship_pr=args.ship_pr)
    for violation in violations:
        print(violation, file=sys.stderr)
    return 1 if violations else 0
