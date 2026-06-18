"""Voting, tally, parse-rate, and scoreboard helpers for larch."""

from __future__ import annotations

# pyright: reportUnusedCallResult=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportArgumentType=false

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from collections.abc import Iterable
from contextlib import suppress
from pathlib import Path
from typing import NoReturn

import logging_util
import proc
import redact

LONG_EXTS = "cc|cfg|cjs|cpp|css|csv|cs|dart|gradle|groovy|go|html|htm|hpp|java|json|jsx|js|kt|lua|mjs|mk|mm|md|php|pl|proto|py|rb|rs|sass|scala|scss|sh|sql|swift|toml|tsx|tsv|ts|vue|xml|yaml|yml"
SHORT_EXTS = "lock|env|txt|c|h|m|r"
LONG_RE = rf"(^|[^A-Za-z0-9])\.?[A-Za-z_][A-Za-z0-9_./-]*\.({LONG_EXTS})(:[0-9]+(-[0-9]+)?)?($|[^A-Za-z0-9_:/-])"
SHORT_PATH_RE = rf"(^|[^A-Za-z0-9])\.?[A-Za-z_][A-Za-z0-9_./-]*[/_-][A-Za-z0-9_./-]*\.({SHORT_EXTS})(:[0-9]+(-[0-9]+)?)?($|[^A-Za-z0-9_:/-])"
SHORT_LINE_RE = rf"(^|[^A-Za-z0-9])\.?[A-Za-z_][A-Za-z0-9_./-]*\.({SHORT_EXTS}):[0-9]+(-[0-9]+)?($|[^A-Za-z0-9_:/-])"
EXTENSIONLESS_RE = r"(^|[^A-Za-z0-9_])(Makefile|Dockerfile|GNUmakefile)(:[0-9]+(-[0-9]+)?)?"
ANY_RE = f"{LONG_RE}|{SHORT_PATH_RE}|{SHORT_LINE_RE}"

FILE_LINE_REGEXES = {
    "long-re": LONG_RE,
    "short-path-re": SHORT_PATH_RE,
    "short-line-re": SHORT_LINE_RE,
    "extensionless-re": EXTENSIONLESS_RE,
    "any-re": ANY_RE,
    "long-exts": LONG_EXTS,
    "short-exts": SHORT_EXTS,
}

BACKTICKED_FOCUS_FILES = (
    "skills/shared/reviewer-templates.md",
    "agents/code-reviewer.md",
    "agents/reviewer-structure.md",
    "agents/reviewer-correctness.md",
    "agents/reviewer-testing.md",
    "agents/reviewer-security.md",
    "agents/reviewer-edge-cases.md",
    "agents/reviewer-plan-fidelity.md",
    "agents/reviewer-code-robustness.md",
    "skills/shared/focus-area-prompt.md",
    "docs/review-agents.md",
)
UNQUOTED_FOCUS_FILES = (
    "skills/review/SKILL.md",
    "python/rendering.py",
    "skills/design/SKILL.md",
)

_ALLOWED_CODE_REVIEW_HEADERS = {
    "# Rejected Findings",
    "## Accepted Findings",
    "## Rejected Code Review Findings",
    "## Voting Tally",
    "# Code Review Voting Tally",
    "## Per-finding vote breakdown",
    "## Reviewer Competition Scoreboard",
}

_CORRECTNESS_VALUES = {"true", "partially-true", "false-positive", "uncertain"}
_SEVERITY_VALUES = {"blocker", "major", "minor", "nit", "uncertain"}
_QUALITY_VALUES = {"excellent", "good", "adequate", "weak", "no-fix", "uncertain"}
_UNCERTAIN_VALUES = {"true", "false"}

FINDINGS_CLASSIFICATION_HEADER = (
    "finding_id\tfinding_reviewers\tvoting_result\tv1_vote\tv1_correctness\tv1_severity\tv1_quality\tv1_uncertain\tv1_tool\tv2_vote\tv2_correctness\tv2_severity\tv2_quality\tv2_uncertain\tv2_tool\tv3_vote\tv3_correctness\tv3_severity\tv3_quality\tv3_uncertain\tv3_tool\tbody_severity"
)

CODE_REVIEW_FINDINGS_CLASSIFICATION_HEADER = (
    "finding_id\treviewer_slots\tvoting_result\tv1_vote\tv1_correctness\tv1_severity\tv1_quality\tv1_uncertain\tv1_tool\tv2_vote\tv2_correctness\tv2_severity\tv2_quality\tv2_uncertain\tv2_tool\tv3_vote\tv3_correctness\tv3_severity\tv3_quality\tv3_uncertain\tv3_tool"
)


def findings_classification_header() -> str:
    return FINDINGS_CLASSIFICATION_HEADER


def code_review_classification_header() -> str:
    return CODE_REVIEW_FINDINGS_CLASSIFICATION_HEADER


def findings_classification_header_main(argv: list[str]) -> int:
    if argv:
        return _error("usage: findings-classification-header")
    print(findings_classification_header())
    return 0


def code_review_classification_header_main(argv: list[str]) -> int:
    if argv:
        return _error("usage: code-review-classification-header")
    print(code_review_classification_header())
    return 0


def _python_cli(plugin_root: str = "") -> Path:
    root = Path(plugin_root) if plugin_root else _plugin_root()
    return root / "python" / "cli.py"


def _run_log_cli_argv(*subcommand: str, plugin_root: str = "") -> list[str]:
    return ["python3", str(_python_cli(plugin_root)), "run-log", *subcommand]


def _plugin_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _truthy(name: str) -> bool:
    return os.environ.get(name, "").lower() in {"1", "true", "yes", "on"}


def _plain_diagnostic(message: str) -> None:
    line = redact.redact_outbound(logging_util.sanitize_diagnostic_line(message)).rstrip("\n") + "\n"
    if (
        _truthy("LARCH_QUIET_ACTIVE")
        and os.environ.get("LARCH_QUIET_PID")
        and not _truthy("LARCH_QUIET_DISABLE")
    ):
        try:
            os.write(4, line.encode("utf-8"))
            return
        except OSError:
            pass
    _ = sys.stderr.write(line)
    sys.stderr.flush()


def _error(message: str) -> int:
    print(message, file=sys.stderr)
    return 2


def _die(message: str) -> NoReturn:
    print(f"ERROR={message}", file=sys.stderr)
    raise SystemExit(2)


def _require_non_negative(name: str, value: str) -> int:
    if not value.isdigit():
        _die(f"{name} must be a non-negative integer: {value}")
    return int(value)


def _parse_kv(output: str, key: str) -> str:
    prefix = f"{key}="
    for line in output.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :]
    return ""


def vote_for_id(ballot_id: str, voter_file: str | Path) -> str:
    result = "JUDGE_ERROR"
    try:
        lines = Path(voter_file).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return result
    pattern = re.compile(rf"^{re.escape(ballot_id)}:\s*(YES|NO|EXONERATE)(?:[\s-]|$)", re.IGNORECASE)
    for line in lines:
        match = pattern.search(line)
        if match:
            token = match.group(1).upper()
            result = "NO" if token == "EXONERATE" else token
    return result


def vote_for_id_main(argv: list[str]) -> int:
    if len(argv) != 2:  # noqa: PLR2004
        return _error("usage: vote-for-id <id> <voter-file>")
    print(vote_for_id(argv[0], argv[1]))
    return 0


def reviewer_for_block(block_file: str | Path) -> str:
    label_re = re.compile(
        r"^[\s-]*(?:\*\*Reviewer\(s\)\*\*|\*\*Reviewers?\*\*|Reviewer\(s\)|Reviewers?)\s*:"
    )
    try:
        lines = Path(block_file).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return "unknown"
    for line in lines:
        if label_re.search(line):
            value = re.sub(r"^[\s-]*", "", line)
            value = re.sub(r"^[^:]*:\s*", "", value)
            value = value.replace("*", "").strip()
            return value or "unknown"
    return "unknown"


def reviewer_for_block_main(argv: list[str]) -> int:
    if len(argv) != 1:
        return _error("usage: reviewer-for-block <block-file>")
    sys.stdout.write(reviewer_for_block(argv[0]))
    return 0


def is_security_block(block_file: str | Path) -> bool:
    try:
        text = Path(block_file).read_text(encoding="utf-8")
    except OSError as exc:
        print(f"is_security_block: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    text_no_fence = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text_no_backtick = re.sub(r"`[^`\n]*`", "", text_no_fence)
    canonical_token = re.compile(r"focus-area\s*=\s*security", re.IGNORECASE)
    explicit_header = re.compile(
        r"^###\s+(?:OOS_\d+:|FINDING_\d+:)\s*(?:\[(?:OUT_OF_SCOPE|OOS)\]\s*)?"
        r"`?(?:\[security\]|<security>)`?(?:\s|$|[:-])",
        re.IGNORECASE,
    )
    field_value = re.compile(
        r"^[ \t-]*focus-area[ \t]*[:=][ \t]*security(?:[-a-z0-9 _]*)(?:[ \t]|$|\(|#|\.|,)",
        re.IGNORECASE,
    )
    lines = text_no_fence.splitlines()
    if canonical_token.search(text_no_backtick):
        return True
    if lines and explicit_header.search(lines[0]):
        return True
    for line in lines:
        normalized = line.replace("`", "").replace("*", "").strip()
        if field_value.search(normalized):
            return True
    return False


def is_security_block_main(argv: list[str]) -> int:
    if len(argv) != 1:
        return _error("usage: is-security-block <block-file>")
    return 0 if is_security_block(argv[0]) else 1


def accept_finding(yes: int, no: int, exonerate: int, eligible: int) -> bool:
    _ = no, exonerate
    if eligible <= 0:
        return False
    if eligible == 1:
        return yes == 1
    if eligible == 2:  # noqa: PLR2004
        return yes == 2  # noqa: PLR2004
    return yes >= 2  # noqa: PLR2004


def accept_finding_main(argv: list[str]) -> int:
    if len(argv) != 4:  # noqa: PLR2004
        return _error("usage: accept-finding <yes> <no> <exonerate> <eligible>")
    yes, no, exonerate, eligible = (int(v) for v in argv)
    return 0 if accept_finding(yes, no, exonerate, eligible) else 1


def classify_result(yes: int, no: int, exonerate: int, eligible: int) -> str:
    if eligible <= 0:
        return "rejected"
    if accept_finding(yes, no, exonerate, eligible):
        return "accepted"
    if yes > 0:
        return "neutral"
    return "rejected"


def classify_result_main(argv: list[str]) -> int:
    if len(argv) != 4:  # noqa: PLR2004
        return _error("usage: classify-result <yes> <no> <exonerate> <eligible>")
    sys.stdout.write(classify_result(*(int(v) for v in argv)))
    return 0


def panel_tier(eligible: int) -> str:
    if eligible >= 3:  # noqa: PLR2004
        return "full-3"
    if eligible == 2:  # noqa: PLR2004
        return "unanimous-2"
    if eligible == 1:
        return "single-judge"
    return "main-agent-required"


def panel_tier_main(argv: list[str]) -> int:
    if len(argv) != 1:
        return _error("usage: panel-tier <eligible>")
    sys.stdout.write(panel_tier(int(argv[0])))
    return 0


def split_ballot(ballot_file: str | Path, out_dir: str | Path) -> None:
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    current: Path | None = None
    heading_re = re.compile(r"^### (FINDING_[0-9]+|OOS_[0-9]+):")
    with Path(ballot_file).open(encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            line = raw.rstrip("\n")
            match = heading_re.match(line)
            if match:
                item_id = match.group(1)
                if item_id in seen:
                    print(f"duplicate ballot heading {item_id}", file=sys.stderr)
                    raise SystemExit(1)
                seen.add(item_id)
                current = out_path / f"{item_id}.md"
                current.write_text(raw, encoding="utf-8")
            elif current is not None:
                with current.open("a", encoding="utf-8") as output:
                    output.write(raw)


def split_ballot_main(argv: list[str]) -> int:
    if len(argv) != 2:  # noqa: PLR2004
        return _error("usage: split-ballot <ballot-file> <out-dir>")
    split_ballot(argv[0], argv[1])
    return 0


def parse_judge_vote(voter_file: str | Path, ballot_id: str) -> tuple[str, str, str, str, str]:
    vote = correctness = severity = quality = uncertain_token = ""
    pattern = re.compile(rf"^{re.escape(ballot_id)}:\s*", re.IGNORECASE)
    try:
        lines = Path(voter_file).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        raise FileNotFoundError(str(exc)) from exc
    for raw in lines:
        if not pattern.search(raw):
            continue
        vote = correctness = severity = quality = uncertain_token = ""
        scoped = pattern.sub("", raw, count=1)
        scoped = scoped.split(" -- ", 1)[0]
        match = re.match(r"^(YES|NO|EXONERATE)(?:[\s-]|$)", scoped, flags=re.IGNORECASE)
        if match:
            token = match.group(1).upper()
            vote = "NO" if token == "EXONERATE" else token
        for part in re.split(r"[\s]+", scoped.strip()):
            if part.startswith("CORRECTNESS="):
                value = part.removeprefix("CORRECTNESS=")
                correctness = value if value in _CORRECTNESS_VALUES else ""
            elif part.startswith("SEVERITY="):
                value = part.removeprefix("SEVERITY=")
                severity = value if value in _SEVERITY_VALUES else ""
            elif part.startswith("QUALITY="):
                value = part.removeprefix("QUALITY=")
                quality = value if value in _QUALITY_VALUES else ""
            elif part.startswith("UNCERTAIN="):
                value = part.removeprefix("UNCERTAIN=")
                uncertain_token = value if value in _UNCERTAIN_VALUES else ""
    uncertain = "true"
    if correctness and severity and quality and uncertain_token:
        uncertain = uncertain_token
    return vote, correctness, severity, quality, uncertain


def parse_judge_vote_main(argv: list[str]) -> int:
    logging_util.quiet_init(argv0="cli.py")
    if len(argv) != 2:  # noqa: PLR2004
        logging_util.BreadcrumbWriter().emit("usage: parse-judge-vote <voter_file> <ballot_id>")
        return 2
    voter_file, ballot_id = argv
    if not os.access(voter_file, os.R_OK) or not Path(voter_file).is_file():
        logging_util.BreadcrumbWriter().emit(
            f"parse-judge-vote: voter file is missing or unreadable: {voter_file}"
        )
        return 2
    vote, correctness, severity, quality, uncertain = parse_judge_vote(voter_file, ballot_id)
    logging_util.emit_kv("PARSED_VOTE", vote)
    logging_util.emit_kv("PARSED_CORRECTNESS", correctness)
    logging_util.emit_kv("PARSED_SEVERITY", severity)
    logging_util.emit_kv("PARSED_QUALITY", quality)
    logging_util.emit_kv("PARSED_UNCERTAIN", uncertain)
    return 0


def voter_parse_rate_diag_path(voter_path: str | Path) -> Path:
    path = Path(voter_path)
    text = str(path)
    if text.endswith(".txt"):
        return Path(text[:-4] + "-parse-rate-diag.txt")
    return Path(text + "-parse-rate-diag.txt")


def voter_output_sha256(voter_path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(voter_path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _darwin_path_aliases(path: str | Path) -> set[str]:
    text = str(path)
    aliases = {text, str(Path(text))}
    for candidate in tuple(aliases):
        if candidate.startswith("/private/var/"):
            aliases.add(candidate.removeprefix("/private"))
        elif candidate.startswith("/var/"):
            aliases.add("/private" + candidate)
    return aliases


def voter_parse_rate_diag_matches_output(voter_path: str | Path) -> bool:
    # tally-code-votes.sh no longer reads this sidecar; it calls parse-rate-check directly.
    path = Path(voter_path)
    diag_file = voter_parse_rate_diag_path(path)
    if not diag_file.is_file() or not path.is_file():
        return False
    recorded_path = recorded_sha = ""
    for line in diag_file.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("voter_file=") and not recorded_path:
            recorded_path = line[len("voter_file=") :]
        elif line.startswith("voter_sha256=") and not recorded_sha:
            recorded_sha = line[len("voter_sha256=") :]
    path_matches = bool(_darwin_path_aliases(recorded_path) & _darwin_path_aliases(path))
    return bool(recorded_path and recorded_sha) and path_matches and recorded_sha == voter_output_sha256(path)


def parse_rate_diag_matches_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="parse-rate-diag-matches")
    parser.add_argument("--voter-file", required=True)
    args = parser.parse_args(argv)
    return 0 if voter_parse_rate_diag_matches_output(args.voter_file) else 1


def _ballot_ids(ballot_file: str | Path, grammar: str) -> list[str]:
    ids: list[str] = []
    seen: set[str] = set()
    if grammar == "finding-oos":
        pattern = re.compile(r"^(?:###\s+)?((?:FINDING|OOS)_[0-9]+):")
    else:
        pattern = re.compile(r"^(?:###\s+)?(FINDING_[0-9]+):")
    try:
        lines = Path(ballot_file).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    for line in lines:
        match = pattern.match(line)
        if match and match.group(1) not in seen:
            seen.add(match.group(1))
            ids.append(match.group(1))
    return ids


def voter_launcher_tool(voter_tool: str) -> str:
    if voter_tool.startswith("cursor-"):
        return "cursor"
    return voter_tool


def parse_rate_check_tool_label(voter_tool: str) -> str:
    launcher_tool = voter_launcher_tool(voter_tool)
    if launcher_tool == "claude":
        return "agent launch-claude-review (voter parse-rate check)"
    if launcher_tool in {"codex", "cursor"}:
        return f"agent launch-review --tool {launcher_tool} (voter parse-rate check; label {voter_tool})"
    return f"voter parse-rate check ({voter_tool})"


def is_harness_review_path(path: str | Path) -> bool:
    text = str(path)
    patterns = (
        "test-dispatch-code-voters.",
        "test_agent_voters.",
        "test-dispatch-plan-voters.",
        "test-plan-review-loop.",
        "test-collect-",
        "test-check-",
        "test-tally-",
    )
    return any(token in text for token in patterns)


def should_suppress_parse_rate_issue_append(voter_path: str | Path, base_tmp: str | Path) -> bool:
    # Normalize via Path to collapse repeated slashes (e.g. $TMPDIR ending in /)
    voter = str(Path(voter_path))
    base = str(Path(base_tmp))
    return voter.startswith(base + "/") and (is_harness_review_path(base) or is_harness_review_path(voter))


def _issues_log(base_tmp: str) -> str:
    if os.environ.get("LARCH_EXECUTION_ISSUES_LOG"):
        return os.environ["LARCH_EXECUTION_ISSUES_LOG"]
    if os.environ.get("SESSION_ENV_PATH"):
        return str(Path(os.environ["SESSION_ENV_PATH"]).parent / "execution-issues.md")
    if os.environ.get("IMPLEMENT_TMPDIR"):
        return str(Path(os.environ["IMPLEMENT_TMPDIR"]) / "execution-issues.md")
    return str(Path(base_tmp) / "execution-issues.md")


def check_voter_parse_rate(
    *,
    voter_file: str,
    voter_tool: str,
    ballot_file: str,
    id_grammar: str,
    review_tmpdir: str,
    slot: str = "",
    log_mode: str = "log",
    plugin_root: str = "",
    dispatch_label: str = "agent dispatch-voters",
) -> str:
    voter_path = Path(voter_file)
    diag_file = voter_parse_rate_diag_path(voter_path)
    if not voter_path.is_file() or voter_path.stat().st_size == 0:
        return "OK"
    ids = _ballot_ids(ballot_file, id_grammar)
    if not ids:
        return "OK"
    judge_error_count = 0
    for item_id in ids:
        try:
            parsed_vote = parse_judge_vote(voter_path, item_id)[0]
        except FileNotFoundError:
            parsed_vote = ""
        one = parsed_vote or "JUDGE_ERROR"
        if one == "JUDGE_ERROR":
            judge_error_count += 1
    if judge_error_count / len(ids) >= 0.8:  # noqa: PLR2004
        first_bytes = voter_path.read_bytes()[:200].decode("utf-8", errors="replace")
        voter_file_aliases = sorted(_darwin_path_aliases(voter_file), key=lambda alias: (alias.startswith("/private/var/"), alias))
        lines: list[str] = []
        if slot:
            lines.append(f"slot={slot}")
        lines.extend(
            [
                f"voter_tool={voter_tool}",
                f"judge_error_count={judge_error_count}",
                f"total_findings={len(ids)}",
                f"total_ballot_items={len(ids)}",
            ]
        )
        lines.extend(f"voter_file={alias}" for alias in voter_file_aliases)
        lines.extend(
            [
                f"voter_sha256={voter_output_sha256(voter_path)}",
                "--- first 200 bytes of voter output ---",
                first_bytes,
            ]
        )
        with suppress(OSError):
            diag_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        if log_mode == "log":
            _plain_diagnostic(
                f"**⚠ Voter {voter_tool}: {judge_error_count}/{len(ids)} ballot items returned JUDGE_ERROR — voter likely produced prose without FINDING_N:/OOS_N: VOTE lines. Check voter output at {voter_path}.**"
            )
            if not should_suppress_parse_rate_issue_append(voter_path, review_tmpdir):
                proc.run(
                    [
                        *_run_log_cli_argv("append-failure", plugin_root=plugin_root),
                        "--log",
                        _issues_log(review_tmpdir),
                        "--site",
                        f"{dispatch_label} {voter_tool}",
                        "--tool",
                        parse_rate_check_tool_label(voter_tool),
                        "--exit-code",
                        "0",
                        "--status-label",
                        "warning",
                        "--category",
                        "Warnings",
                        "--output-file",
                        str(diag_file),
                        "--redact",
                    ]
                )
        return "NOT_SUBSTANTIVE"
    with suppress(FileNotFoundError):
        diag_file.unlink()
    return "OK"


def _parse_rate_common_parser(prog: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=prog)
    parser.add_argument("--voter-file", required=True)
    parser.add_argument("--voter-tool", required=True)
    parser.add_argument("--ballot-file", required=True)
    parser.add_argument("--id-grammar", choices=("finding-only", "finding-oos"), required=True)
    parser.add_argument("--review-tmpdir", required=True)
    parser.add_argument("--slot", default="")
    parser.add_argument("--log-mode", default="log")
    parser.add_argument("--plugin-root", default="")
    parser.add_argument("--dispatch-label", default="agent dispatch-voters")
    return parser


def parse_rate_check_main(argv: list[str]) -> int:
    parser = _parse_rate_common_parser("parse-rate-check")
    args = parser.parse_args(argv)
    status = check_voter_parse_rate(
        voter_file=args.voter_file,
        voter_tool=args.voter_tool,
        ballot_file=args.ballot_file,
        id_grammar=args.id_grammar,
        review_tmpdir=args.review_tmpdir,
        slot=args.slot,
        log_mode=args.log_mode,
        plugin_root=args.plugin_root,
        dispatch_label=args.dispatch_label,
    )
    print(f"PARSE_RATE_STATUS={status}")
    return 0


def _extract_ctx(argv: list[str]) -> tuple[list[str], list[str]]:
    rest: list[str] = []
    ctx: list[str] = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--ctx":
            if i + 1 >= len(argv):
                raise SystemExit(_error("parse-rate-retry: --ctx requires a value"))
            ctx.append(argv[i + 1])
            i += 2
        elif arg.startswith("--ctx="):
            ctx.append(arg[len("--ctx=") :])
            i += 1
        else:
            rest.append(arg)
            i += 1
    return rest, ctx


def parse_rate_retry_main(argv: list[str]) -> int:
    rest, _ctx = _extract_ctx(argv)
    parser = _parse_rate_common_parser("parse-rate-retry")
    parser.add_argument("--prompt-file", default="")
    parser.add_argument("--retry-prefix-kind", choices=("code", "plan"), default="code")
    parser.add_argument("--launch-mode", default="")
    args = parser.parse_args(rest)
    status = check_voter_parse_rate(
        voter_file=args.voter_file,
        voter_tool=args.voter_tool,
        ballot_file=args.ballot_file,
        id_grammar=args.id_grammar,
        review_tmpdir=args.review_tmpdir,
        slot=args.slot,
        log_mode="log",
        plugin_root=args.plugin_root,
        dispatch_label=args.dispatch_label,
    )
    print(status)
    return 0


def effective_judges(records: Iterable[str]) -> int:
    count = 0
    for record in records:
        if not record:
            continue
        parts = record.split("\t")
        status = parts[0] if len(parts) > 0 else ""
        path = parts[1] if len(parts) > 1 else ""
        parse_rate_status = parts[2] if len(parts) > 2 else ""  # noqa: PLR2004
        if status != "failed" and parse_rate_status != "NOT_SUBSTANTIVE" and path and Path(path).is_file() and Path(path).stat().st_size > 0:
            count += 1
    return count


def effective_judges_main(argv: list[str]) -> int:
    records = argv or sys.stdin.read().splitlines()
    print(effective_judges(records))
    return 0


def degraded_warning_main(argv: list[str]) -> int:
    if len(argv) not in {2, 3}:
        return _error("usage: degraded-warning <effective> <expected> [reason]")
    effective = int(argv[0])
    expected = int(argv[1])
    reason = argv[2] if len(argv) == 3 else ""  # noqa: PLR2004
    if effective < expected:
        warn_msg = f"**⚠ Degraded plan-review panel: {effective}/{expected} effective judges produced substantive vote output.**"
        if reason:
            warn_msg += f" {reason}"
        _plain_diagnostic(warn_msg)
        print(f"DEGRADED_PANEL_WARNING={warn_msg}")
    return 0


def voter_status_block_main(argv: list[str]) -> int:
    if len(argv) != 13:  # noqa: PLR2004
        return _error("usage: voter-status-block <13 positional args>")
    (
        voter_1_path,
        voter_1_tool,
        voter_1_status,
        voter_1_parse_rate_status,
        voter_2_path,
        voter_2_tool,
        voter_2_status,
        voter_2_parse_rate_status,
        voter_3_path,
        voter_3_tool,
        voter_3_status,
        voter_3_parse_rate_status,
        plan_voter_paths_file,
    ) = argv
    rows = [
        ("VOTER_1_PATH", voter_1_path),
        ("VOTER_1_TOOL", voter_1_tool),
        ("VOTER_1_STATUS", voter_1_status),
        ("VOTER_1_PARSE_RATE_STATUS", voter_1_parse_rate_status),
        ("VOTER_2_PATH", voter_2_path),
        ("VOTER_3_PATH", voter_3_path),
    ]
    if Path(plan_voter_paths_file).is_file() and Path(plan_voter_paths_file).stat().st_size > 0:
        rows.append(("VOTER_PATHS_FILE", plan_voter_paths_file))
    rows.extend(
        [
            ("VOTER_2_TOOL", voter_2_tool),
            ("VOTER_3_TOOL", voter_3_tool),
            ("VOTER_2_STATUS", voter_2_status),
            ("VOTER_3_STATUS", voter_3_status),
            ("VOTER_2_PARSE_RATE_STATUS", voter_2_parse_rate_status),
            ("VOTER_3_PARSE_RATE_STATUS", voter_3_parse_rate_status),
        ]
    )
    for key, value in rows:
        print(f"{key}={value}")
    return 0


def _compose_args(argv: list[str], *, require_log: bool = False) -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    if require_log:
        parser.add_argument("--log-root", required=True)
        parser.add_argument("--skill", required=True)
        parser.add_argument("--run-id", required=True)
    parser.add_argument("--phase", required=True)
    parser.add_argument("--mode", required=True)
    parser.add_argument("--rounds", default="0")
    parser.add_argument("--accepted", default="0")
    parser.add_argument("--rejected", default="0")
    parser.add_argument("--exonerated", default="0")
    parser.add_argument("--neutral", default="0")
    parser.add_argument("--body-file", default="")
    return parser.parse_args(argv)


def _validate_tally_args(args: argparse.Namespace) -> tuple[str, int, int, int, int]:
    if args.phase == "plan-review":
        batch = "plan-review-tally"
        allowed_modes = {"simple", "hard"}
        if not args.body_file:
            _die("--body-file is required for --phase plan-review")
    elif args.phase == "code-review":
        batch = "code-review-tally"
        allowed_modes = {"simple", "hard", "self-review"}
    else:
        _die(f"--phase must be plan-review or code-review: {args.phase}")
    if args.mode not in allowed_modes:
        _die(f"--mode must be one of {', '.join(sorted(allowed_modes))} for --phase {args.phase}: {args.mode}")
    rounds = _require_non_negative("--rounds", args.rounds)
    accepted = _require_non_negative("--accepted", args.accepted)
    rejected = _require_non_negative("--rejected", args.rejected)
    exonerated = _require_non_negative("--exonerated", args.exonerated)
    _require_non_negative("--neutral", args.neutral)
    if args.body_file:
        body_path = Path(args.body_file)
        if not body_path.is_file():
            _die(f"body file not found: {args.body_file}")
        if body_path.is_symlink():
            _die(f"body file must not be a symlink: {args.body_file}")
    return batch, rounds, accepted, rejected, exonerated


def compose_tally_record(args: argparse.Namespace) -> str:
    batch, rounds, accepted, rejected, exonerated = _validate_tally_args(args)
    record: dict[str, object] = {
        "schema_version": 2,
        "phase": args.phase,
        "batch": batch,
        "mode": args.mode,
        "rounds": rounds,
        "accepted_count": accepted,
        "rejected_count": rejected,
        "exonerated_count": exonerated,
    }
    # code-review body files are validation input only; their prose is intentionally
    # excluded from code-review-tally records.
    if args.body_file and args.phase != "code-review":
        record["body"] = Path(args.body_file).read_text(encoding="utf-8")
    return json.dumps(record, separators=(",", ":"))


def compose_tally_record_main(argv: list[str]) -> int:
    logging_util.quiet_init(argv0="cli.py")
    try:
        args = _compose_args(argv)
        logging_util.emit(compose_tally_record(args))
        return 0
    except SystemExit as exc:
        return int(exc.code)


def _validate_code_review_headers(body_file: str) -> tuple[int, str]:
    in_fence = False
    try:
        lines = Path(body_file).read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return 3, str(exc)
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if re.match(r"^# Review Round [0-9]+$", line):
            continue
        if line.startswith("### [Code Review] "):
            continue
        if re.match(r"^### \[rejected\] FINDING_[0-9]+$", line):
            continue
        if re.match(r"^### FINDING_[0-9]+: ", line):
            continue
        if re.match(r"^#{1,6}\s", line) and line in _ALLOWED_CODE_REVIEW_HEADERS:
            continue
        if re.match(r"^#{1,6}\s", line):
            return 4, line
    return 0, ""


def write_tally_main(argv: list[str]) -> int:
    logging_util.quiet_init(argv0="cli.py")
    try:
        args = _compose_args(argv, require_log=True)
        batch, *_ = _validate_tally_args(args)
        if args.phase == "code-review" and args.body_file:
            rc, output = _validate_code_review_headers(args.body_file)
            if rc == 3:  # noqa: PLR2004
                _die(f"code-review body header validation failed: {output or 'python3 validation error'}")
            if rc == 4:  # noqa: PLR2004
                _plain_diagnostic(
                    "WARNING=code-review body header validation ignored: "
                    f"unrecognized section header: {output}"
                )
            if rc not in (0, 4):
                _die("code-review body header validation failed")
        record = compose_tally_record(args)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, prefix="write-tally-record.") as handle:
            handle.write(record + "\n")
            record_file = handle.name
        try:
            result = proc.run(
                [
                    *_run_log_cli_argv("write"),
                    "--log-root",
                    args.log_root,
                    "--skill",
                    args.skill,
                    "--run-id",
                    args.run_id,
                    "--batch",
                    batch,
                    "--input-file",
                    record_file,
                ]
            )
        finally:
            with suppress(FileNotFoundError):
                Path(record_file).unlink()
        for line in result.stdout.splitlines():
            if not line:
                continue
            if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", line):
                logging_util.emit_kv(line.split("=", 1)[0], line.split("=", 1)[1])
            else:
                logging_util.emit(line)
        return result.returncode
    except SystemExit as exc:
        return int(exc.code)


def false_positive_match(text: str) -> bool:
    negated = (
        r"(^|[^a-z])not\s+((a|an)\s+)?duplicate([^a-z]|$)",
        r"(^|[^a-z])not\s+((a|an)\s+)?false[- ]positive([^a-z]|$)",
    )
    positives = (
        r"(^|[^a-z])won[^\s]*t\s+fix([^a-z]|$)",
        r"(^|[^a-z])wontfix([^a-z]|$)",
        r"(^|[^a-z])superseded(\s+by\s+#[0-9]+)?([^a-z]|$)",
        r"(^|[^a-z])not\s+an\s+issue([^a-z]|$)",
        r"(^|[^a-z])not\s+a\s+bug([^a-z]|$)",
        r"(^|[^a-z])duplicate\s+of\s+#[0-9]+([^a-z]|$)",
        r"(^|[^a-z])false[- ]positive([^a-z]|$)",
    )
    if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in negated):
        return False
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in positives)


def false_positive_match_main(argv: list[str]) -> int:
    if len(argv) != 1:
        return _error("usage: false-positive-match <text>")
    return 0 if false_positive_match(argv[0]) else 1


def file_line_regex_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="file-line-regex")
    parser.add_argument("--name", required=True, choices=sorted(FILE_LINE_REGEXES))
    args = parser.parse_args(argv)
    print(FILE_LINE_REGEXES[args.name])
    return 0


def ballot_parse(ballot_file: str | Path) -> list[str]:
    lines = Path(ballot_file).read_text(encoding="utf-8", errors="replace").splitlines()
    output: list[str] = []
    idx = 0
    title = concern = ""
    oos = "false"

    def emit() -> None:
        if idx > 0:
            output.append(f"FINDING_{idx}_TITLE={title}")
            output.append(f"FINDING_{idx}_CONCERN={concern.strip()}")
            output.append(f"FINDING_{idx}_OOS={oos}")

    for line in lines:
        match = re.match(r"^### FINDING_[0-9]+:\s*(.*)", line)
        if match:
            emit()
            idx += 1
            title = match.group(1)
            concern = ""
            oos = "true" if re.match(r"^\[(OUT_OF_SCOPE|OOS)\]", title) else "false"
            continue
        if idx > 0:
            if line.startswith("- **Concern**:"):
                concern = re.sub(r"^- \*\*Concern\*\*:\s*", "", line)
            elif concern and not line.startswith("- **"):
                concern += " " + line
            if "[OUT_OF_SCOPE]" in line or "[OOS]" in line:
                oos = "true"
    emit()
    output.append(f"FINDING_COUNT={idx}")
    return output


def ballot_parse_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="ballot-parse")
    parser.add_argument("--ballot-file", required=True)
    args = parser.parse_args(argv)
    if not Path(args.ballot_file).is_file():
        return _error("ballot-parse: --ballot-file must name a file")
    print("\n".join(ballot_parse(args.ballot_file)))
    return 0


def tally_vote_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="tally-vote")
    parser.add_argument("--ballot-file", required=True)
    parser.add_argument("--voter-files", nargs="*", default=[])
    args = parser.parse_args(argv)
    if not Path(args.ballot_file).is_file():
        return _error("tally-vote: --ballot-file must name a file")
    count = int(_parse_kv("\n".join(ballot_parse(args.ballot_file)), "FINDING_COUNT") or "0")
    output: list[str] = []
    for idx in range(1, count + 1):
        yes = no = 0
        for voter_file in args.voter_files:
            path = Path(voter_file)
            if not path.is_file():
                continue
            vote = ""
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                if re.search(rf"^FINDING_{idx}([^0-9]|$)", line):
                    if "YES" in line:
                        vote = "YES"
                    elif "NO" in line or "EXONERATE" in line:
                        vote = "NO"
            if vote == "YES":
                yes += 1
            elif vote == "NO":
                no += 1
        accepted = "true" if len(args.voter_files) < 2 or yes >= 2 else "false"  # noqa: PLR2004
        output.extend(
            [
                f"FINDING_{idx}_ACCEPTED={accepted}",
                f"FINDING_{idx}_VOTES_YES={yes}",
                f"FINDING_{idx}_VOTES_NO={no}",
            ]
        )
    output.append(f"FINDING_COUNT={count}")
    print("\n".join(output))
    return 0


def bash_printf_q(value: str) -> str:
    """Return the common bash ``printf '%q'`` backslash form for scoreboard parity."""
    if value == "":
        return "''"
    safe = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_@%+=:,./-")
    return "".join(ch if ch in safe else "\\" + ch for ch in value)


def scoreboard_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="scoreboard")
    parser.add_argument("--tally-file", default="")
    parser.add_argument("--reviewer-labels", required=True)
    parser.add_argument("--output-file", required=True)
    args = parser.parse_args(argv)
    output_file = Path(args.output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    tally_text = Path(args.tally_file).read_text(encoding="utf-8", errors="replace") if args.tally_file and Path(args.tally_file).is_file() else ""
    rows = ["| Reviewer | Score |", "|---|---:|"]
    for raw_label in args.reviewer_labels.split(","):
        label = raw_label.strip()
        if not label:
            continue
        score = 0
        for line in tally_text.splitlines():
            if f"REVIEWER={label} " in line and "ACCEPTED=true" in line:
                score += 1
        rows.append(f"| {label} | {score} |")
    output_file.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"SCOREBOARD_FILE={bash_printf_q(str(output_file))}")
    return 0


def lint_focus_area_enum_main(argv: list[str]) -> int:
    if argv:
        return _error("usage: lint focus-area-enum")
    exit_code = 0
    root = _plugin_root()
    hits_re = re.compile(r"`code-quality`.*`risk-integration`.*`correctness`.*`architecture`")
    unquoted_re = re.compile(r"code-quality / risk-integration / correctness / architecture")
    for rel in BACKTICKED_FOCUS_FILES:
        path = root / rel
        if not path.is_file():
            print(f"::error file={rel}::expected file is missing")
            exit_code = 1
            continue
        hits = [(i, line) for i, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1) if hits_re.search(line)]
        if not hits:
            print(f"::error file={rel}::no backticked focus-area enumeration found")
            exit_code = 1
        for line_no, line_text in hits:
            if "security" not in line_text:
                print(f"::error file={rel},line={line_no}::backticked focus-area enumeration does not include 'security': {line_text}")
                exit_code = 1
    for rel in UNQUOTED_FOCUS_FILES:
        path = root / rel
        if not path.is_file():
            print(f"::error file={rel}::expected file is missing")
            exit_code = 1
            continue
        hits = [(i, line) for i, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1) if unquoted_re.search(line)]
        if not hits:
            print(f"::error file={rel}::no unquoted focus-area enumeration found")
            exit_code = 1
        for line_no, line_text in hits:
            if "security" not in line_text:
                print(f"::error file={rel},line={line_no}::unquoted focus-area enumeration does not include 'security': {line_text}")
                exit_code = 1
    return exit_code
