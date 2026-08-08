"""Frozen Python behavior for the issue #8169 issue-creation cutover.

This reproduces the `issue create-one`, `issue write-sentinel`, and
`issue cleanup-failed` entrypoints in `python/larch/issue/issue_create.py` as
they behaved at cutover, restricted to the paths a hermetic sandbox can reach.

`write-sentinel` never touches GitHub, so its cases cover the whole command
including the published sentinel byte for byte. `create-one` and
`cleanup-failed` mutate GitHub, and the sandbox has no `gh`, no `git`, and no
network, so their cases cover the argument scanners, the offline dry-run path,
the fail-closed authorization gate, and the refusal each command reports when
no repository can be resolved.

Deliberate omissions, none of them part of a command contract:

* `logging_util.quiet_init` file routing. It duplicates stdout and stderr into a
  per-invocation `$TMPDIR/larch-quiet-*.log` while leaving the contract streams
  pointed at the original descriptors, so a caller sees identical bytes either
  way. The Rust owner writes the same bytes without the observability copy.
* PEM private-key block swallowing. `redact_secrets_outbound` removes a whole
  `-----BEGIN ... PRIVATE KEY-----` block; the family substitutions below stand
  in for that pass, and no case here carries a PEM block. Both owners share the
  behavior through their own redaction tests and `make test-redact`.
* Sentinel and temporary-file permissions. Python inherited `0600` from
  `NamedTemporaryFile` and Rust publishes at `0600` explicitly. The bytes are
  unchanged.

Five differences are intentional and documented in the pull request:

* Numeric validation. Python used `str.isdigit()` for the three sentinel
  counters and the cleanup issue number, which also accepted non-ASCII digits
  and values too large to count. Rust accepts only ASCII decimals that fit a
  64-bit unsigned integer and reports anything else through the same refusal.
* The created-issue resolution. Python parsed `gh issue create --json`, fell
  back to scraping a URL out of plain `gh` output for older `gh` builds, and
  then looked the node id up with a second `gh api` call. The Rust owner reads
  the typed create response, so the JSON-shape branches and the id lookup are
  gone; an echo without a number, node id, or URL is one `invalid-read-back`
  refusal, and the orphan rollback it triggers is unchanged.
* Label validation. Python probed each requested label with its own
  `gh label list --search`; Rust lists the repository's labels once and filters
  against that. Both drop an unknown label with the same warning and keep the
  create going.
* Sentinel and body-file confinement. Both owners refuse a relative `--path` and
  one containing `..`; Rust additionally refuses to publish through a symlinked
  parent directory, which no caller relies on.
* An unreadable body file. Python read the body as strict UTF-8 and raised an
  unhandled error on anything else; Rust reports it as the same exit-1 refusal
  the missing-file case already produced.

The `ISSUE` row of `cleanup-failed` is another small hardening: Python passed
the raw `--issue-number` token to `emit_kv`, which raised when the token
carried a newline. Rust collapses it the way every other diagnostic row is
collapsed. No case here reaches either shape.
"""
# ruff: noqa: PLR0911, PLR0912, PLR0915 - the frozen scanners return and branch exactly as they shipped.

from __future__ import annotations

import datetime as _dt
import os
import re
import sys
import tempfile
from pathlib import Path

REDACTED_TOKEN = "<REDACTED-TOKEN>"
EXIT_MUTATION_REFUSED = 5
LIVE_MUTATION_REFUSAL_STATUS = "mutation-refused"
LIVE_MUTATION_REFUSAL_REASON = "unauthorized-mutation"
LIVE_MUTATION_TEST_DENY_KEY = "LARCH_ISSUE_MUTATION_DENY"
OOS_HEADING = "## Out-of-Scope Observation"
ERROR_CHARS = 500

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

# The one refusal a sandbox can pin for either GitHub-backed verb: repository
# resolution needs `gh repo view` or a `git` remote, and neither exists here.
UNRESOLVABLE_REPO = "could not determine repo"


def warn(message: str) -> None:
    print(message, file=sys.stderr)


def emit_kv(key: str, value: object) -> None:
    print(f"{key}={value}")


def emit_kv_stderr(key: str, value: object) -> None:
    print(f"{key}={value}", file=sys.stderr)


def redact_secrets_outbound(text: str) -> str:
    """Secret families only; session and operator paths survive untouched."""
    if not text:
        return text
    out = text
    for pattern in SECRET_FAMILIES:
        out = pattern.sub(REDACTED_TOKEN, out)
    if text.endswith("\n"):
        return out
    return out.rstrip("\n")


def sanitize_diagnostic_line(text: str) -> str:
    return "".join(character for character in text if character >= " " and character != "\x7f")


def flat_error(text: str) -> str:
    return " ".join(redact_secrets_outbound(text).split())[:ERROR_CHARS]


def normalize_title_prefix(*, title: str, title_prefix: str) -> str:
    if not title_prefix:
        return title
    stripped = title
    if stripped.lower().startswith(title_prefix.lower()):
        stripped = stripped[len(title_prefix) :].lstrip()
    return f"{title_prefix} {stripped}"


def check_live_mutation_auth(*, operator_mode: bool, context_file: str) -> tuple[bool, str]:
    """The sandbox reachable subset of the session-backed authorization gate.

    Operator mode authorizes, a test denial refuses next, and every other
    call refuses: a session-backed context file must sit directly under a
    canonical larch session root, and the sandbox has none.
    """
    if operator_mode:
        return True, "operator"
    if os.environ.get(LIVE_MUTATION_TEST_DENY_KEY) == "true":
        return False, "test-denied"
    _ = context_file
    return False, LIVE_MUTATION_REFUSAL_REASON


# ---------------------------------------------------------- issue create-one


def parse_create_args(argv: list[str]) -> tuple[dict[str, object], str | None]:
    args: dict[str, object] = {"labels": []}
    index = 0
    while index < len(argv):
        arg = argv[index]
        needs_value = {"--title", "--title-prefix", "--label", "--body", "--body-file", "--repo", "--context-file", "--run-id", "--trusted-root"}
        if arg in needs_value:
            if index + 1 >= len(argv):
                return args, f"{arg} requires a value"
            value = argv[index + 1]
            if arg == "--title":
                args["title"] = value
            elif arg == "--title-prefix":
                args["title_prefix"] = value
            elif arg == "--label":
                labels = args["labels"]
                assert isinstance(labels, list)
                labels.append(value)  # pyright: ignore[reportUnknownMemberType]
            elif arg in {"--body", "--body-file"}:
                args["body_file"] = value
            elif arg == "--repo":
                args["repo"] = value
            elif arg == "--context-file":
                args["context_file"] = value
            elif arg == "--run-id":
                args["run_id"] = value
            elif arg == "--trusted-root":
                args["trusted_root"] = value
            index += 2
        elif arg == "--dry-run":
            args["dry_run"] = True
            index += 1
        elif arg == "--operator-invoked":
            args["operator_invoked"] = True
            index += 1
        else:
            return args, f"Unknown option: {arg}"
    return args, None


def issue_failed(message: str, code: int = 2) -> int:
    if code == EXIT_MUTATION_REFUSED:
        emit_kv(LIVE_MUTATION_REFUSAL_STATUS, "true")
    emit_kv("ISSUE_FAILED", "true")
    emit_kv("ISSUE_ERROR", sanitize_diagnostic_line(flat_error(message)))
    return code


def create_one(argv: list[str]) -> int:
    parsed, error = parse_create_args(argv)
    if error:
        warn(error)
        return 1
    title = str(parsed.get("title") or "")
    if not title:
        return issue_failed("--title is required", 1)
    title = redact_secrets_outbound(title)
    dry_run = bool(parsed.get("dry_run"))
    title_prefix = str(parsed.get("title_prefix") or "")
    final_title = normalize_title_prefix(title=title, title_prefix=title_prefix)
    labels_obj = parsed.get("labels")
    labels = tuple(str(label) for label in labels_obj) if isinstance(labels_obj, list) else ()
    if dry_run:
        emit_kv("DRY_RUN", "true")
        emit_kv("DRY_RUN_TITLE", final_title)
        emit_kv("ISSUE_TITLE", final_title)
        if labels:
            emit_kv("DRY_RUN_LABELS", ",".join(labels))
        return 0
    body_file = str(parsed.get("body_file") or "")
    body_content = ""
    if body_file:
        path = Path(body_file)
        if not path.is_file():
            return issue_failed(f"body file not found: {body_file}", 1)
        body_content = path.read_text(encoding="utf-8")
        if body_content:
            body_content = redact_secrets_outbound(body_content)
    if not title_prefix and (body_content == OOS_HEADING or body_content.startswith(f"{OOS_HEADING}\n")):
        final_title = normalize_title_prefix(title=title, title_prefix="[OOS]")
    authorized, reason = check_live_mutation_auth(
        operator_mode=bool(parsed.get("operator_invoked")),
        context_file=str(parsed.get("context_file") or ""),
    )
    if not authorized:
        return issue_failed(f"{LIVE_MUTATION_REFUSAL_REASON}:{reason}", EXIT_MUTATION_REFUSED)
    # Repository resolution is where every remaining sandbox path stops.
    return issue_failed(UNRESOLVABLE_REPO)


# ------------------------------------------------------- issue write-sentinel


def write_sentinel(argv: list[str]) -> int:
    values: dict[str, str] = {}
    dry_run = False
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg in {"--path", "--issues-created", "--issues-deduplicated", "--issues-failed"}:
            if index + 1 >= len(argv) or not argv[index + 1]:
                emit_kv_stderr("ERROR", sanitize_diagnostic_line(f"Missing value for {arg}"))
                return 1
            values[arg] = argv[index + 1]
            index += 2
        elif arg == "--dry-run":
            dry_run = True
            index += 1
        else:
            emit_kv_stderr("ERROR", sanitize_diagnostic_line(f"Unknown argument: {arg}"))
            return 1
    path = values.get("--path", "")
    if not path:
        emit_kv_stderr("ERROR", "Missing required argument: --path")
        return 1
    counts = [values.get("--issues-created", ""), values.get("--issues-deduplicated", ""), values.get("--issues-failed", "")]
    if any(not value for value in counts):
        emit_kv_stderr("ERROR", "Missing required arguments: --issues-created, --issues-deduplicated, --issues-failed")
        return 1
    if not Path(path).is_absolute():
        emit_kv_stderr("ERROR", sanitize_diagnostic_line(f"--path must be absolute: {path}"))
        return 1
    if ".." in Path(path).parts:
        emit_kv_stderr("ERROR", sanitize_diagnostic_line(f"--path must not contain '..': {path}"))
        return 1
    if any(not value.isdigit() for value in counts):
        emit_kv_stderr("ERROR", "Counter values must be non-negative integers")
        return 1
    if dry_run:
        print("WROTE=false REASON=dry_run", file=sys.stderr)
        return 0
    if int(values["--issues-failed"]) > 0:
        print("WROTE=false REASON=failures", file=sys.stderr)
        return 0
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    timestamp = _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=str(target.parent), prefix=f"{target.name}.tmp.", delete=False) as tmp:
        _ = tmp.write("ISSUE_SENTINEL_VERSION=1\n")
        _ = tmp.write(f"ISSUES_CREATED={values['--issues-created']}\n")
        _ = tmp.write(f"ISSUES_DEDUPLICATED={values['--issues-deduplicated']}\n")
        _ = tmp.write(f"ISSUES_FAILED={values['--issues-failed']}\n")
        _ = tmp.write(f"TIMESTAMP={timestamp}\n")
        tmp_path = Path(tmp.name)
    tmp_path.replace(target)
    print("WROTE=true", file=sys.stderr)
    return 0


# ------------------------------------------------------- issue cleanup-failed


def emit_cleanup(issue: str, closed: bool, error: str) -> int:
    emit_kv("CLOSED", "true" if closed else "false")
    emit_kv("ISSUE", issue)
    if error:
        emit_kv("ERROR", sanitize_diagnostic_line(error))
    return 0


def cleanup_failed(argv: list[str]) -> int:
    issue = ""
    repo = ""
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == "--issue-number" and index + 1 < len(argv):
            issue = argv[index + 1]
            index += 2
        elif arg == "--repo" and index + 1 < len(argv):
            repo = argv[index + 1]
            index += 2
        else:
            warn(f"Unknown option: {arg}")
            return emit_cleanup(issue or "unknown", False, f"unknown option: {arg}")
    if not issue.isdigit():
        return emit_cleanup(issue, False, "invalid or missing --issue-number")
    _ = repo
    # Repository resolution is where every remaining sandbox path stops.
    return emit_cleanup(issue, False, UNRESOLVABLE_REPO)


VERBS = {
    "issue-create-one": create_one,
    "issue-write-sentinel": write_sentinel,
    "issue-cleanup-failed": cleanup_failed,
}


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in VERBS:
        raise SystemExit(f"unknown reference verb: {argv[:1]}")
    return VERBS[argv[0]](argv[1:])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
