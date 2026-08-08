"""Frozen Python behavior for the issue #8170 issue-graph cutover.

This reproduces `issue add-blocked-by` and `issue add-sub-issue` from
`python/larch/issue/issue_create.py` and the two `/block-issue` dependency
mutations from `python/larch/issue/issue_block.py` as they behaved at cutover,
restricted to the paths a hermetic sandbox can reach.

All four verbs mutate GitHub, and the sandbox has no `gh`, no `git`, and no
network, so the cases cover each argument scanner, the numeric validation in
front of it, the fail-closed live-mutation gate, and the refusal each command
reports when no repository can be resolved. The retry contract, the idempotent
pre-read, and the exact read-back sit behind the first network request, so they
are proven by the unit tests in
`crates/larch-cli/src/issue_dependency_commands.rs` and the adapter tests in
`crates/larch-adapters/src/github/operations.rs` instead.

Deliberate omissions, none of them part of a command contract:

* `logging_util.quiet_init` file routing. It duplicates stdout and stderr into
  a per-invocation `$TMPDIR/larch-quiet-*.log` while leaving the contract
  streams pointed at the original descriptors, so a caller sees identical bytes
  either way.
* PEM private-key block swallowing. `redact_secrets_outbound` removes a whole
  `-----BEGIN ... PRIVATE KEY-----` block; the family substitutions below stand
  in for that pass, and no case here carries a PEM block.

Six differences are intentional and documented in the pull request:

* Numeric validation. Python used `str.isdigit()`, which also accepted
  non-ASCII digits and magnitudes no issue number can reach. Rust accepts only
  ASCII decimals that fit a 64-bit unsigned integer and reports anything else
  through the same refusal.
* The transport. Python's `/block-issue` resolved two GraphQL node ids and
  called the `addBlockedBy`/`removeBlockedBy` GraphQL mutations; Rust resolves
  the blocker's numeric database id and drives the same edge over the typed
  REST dependency adapter. The refusal classes and their exit codes are
  unchanged; the lookup diagnostic names the blocker rather than the GraphQL
  document, and a deterministic rejection — a self-dependency, an unknown
  target, a pull-request target — carries the adapter's typed read-back contract
  message where Python echoed GitHub's own prose. Both owners refuse such an
  edge, with the same exit code, and neither retries it.
* Idempotency. Python's `issue add-blocked-by` only treated a `422` as success
  after a read-back, and Python's `/block-issue` pre-read the edge set only in
  triage-controlled mode. The adapter pre-reads in every mode, so a repeated
  add or remove converges on the same edge set and reports success in both.
* Retries. Python retried every non-`404`, non-`422` failure, including an
  authorization refusal. Rust retries only the transport class the documented
  contract names, so a deterministic refusal reports immediately instead of
  spending two sleeps to reach the same answer.
* The repository slug. Python matched `--repo` against a character-class regular
  expression; Rust parses it into the typed repository reference every GitHub
  call already takes, which additionally refuses a bare `.` or `..` component
  and a component past 100 characters. No caller names such a repository.
* The `/block-issue` timestamp. Python matched `--expected-updated-at` against a
  shape-only regular expression, so an impossible instant such as
  `2026-13-45T99:99:99Z` passed the command line and failed later against the
  live snapshot. Rust parses it, so an impossible instant is the same exit-2
  refusal the malformed spelling already produced.

The `CLIENT`, `BLOCKER`, `PARENT`, and `CHILD` rows are one small hardening:
Python passed the raw token to `emit_kv`, which raised when the token carried a
newline. Rust collapses it the way every other contract row is collapsed. No
case here reaches that shape.
"""
# ruff: noqa: PLR0911, PLR0912 - the frozen scanners return and branch exactly as they shipped.

from __future__ import annotations

import os
import re
import sys

REDACTED_TOKEN = "<REDACTED-TOKEN>"
EXIT_MUTATION_REFUSED = 5
LIVE_MUTATION_REFUSAL_STATUS = "mutation-refused"
LIVE_MUTATION_REFUSAL_REASON = "unauthorized-mutation"
LIVE_MUTATION_TEST_DENY_KEY = "LARCH_ISSUE_MUTATION_DENY"
ERROR_CHARS = 500
BLOCK_ISSUE_ERROR_CHARS = 1000

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

UPDATED_AT_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z")
REPO_RE = re.compile(r"[A-Za-z0-9._-]+/[A-Za-z0-9._-]+")

# The one refusal a sandbox can pin for any of the four verbs: repository
# resolution needs `gh repo view` or a `git` remote, and neither exists here.
UNRESOLVABLE_REPO = "could not determine repo"
BLOCK_ISSUE_UNRESOLVABLE_REPO = (
    "Could not determine repository: pass --repo owner/name"
)

BLOCKED_BY_USAGE = (
    "Usage: add-blocked-by --client-issue N --blocker-issue M [--blocker-id ID] "
    "[--repo OWNER/REPO] [--operator-invoked | --context-file PATH --run-id ID "
    "--trusted-root PATH]"
)
SUB_ISSUE_USAGE = (
    "Usage: add-sub-issue --parent-issue N --child-issue M [--child-id ID] "
    "[--repo OWNER/REPO]"
)


def warn(message: str) -> None:
    print(message, file=sys.stderr)


def emit_kv(key: str, value: object) -> None:
    print(f"{key}={value}")


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


def flat_error(text: str, limit: int = ERROR_CHARS) -> str:
    return sanitize_diagnostic_line(" ".join(redact_secrets_outbound(text).split())[:limit])


def check_live_mutation_auth(*, operator_mode: bool) -> tuple[bool, str]:
    """The sandbox reachable subset of the session-backed authorization gate.

    Operator mode authorizes, a test denial refuses next, and every other call
    refuses: a session-backed context file must sit directly under a canonical
    larch session root, and the sandbox has none.
    """
    if operator_mode:
        return True, "operator"
    if os.environ.get(LIVE_MUTATION_TEST_DENY_KEY) == "true":
        return False, "test-denied"
    return False, LIVE_MUTATION_REFUSAL_REASON


# -------------------------------------------------- issue add-blocked-by / add-sub-issue


def scan_edge_args(argv: list[str], options: dict[str, str]) -> tuple[dict[str, str], bool, str | None]:
    values: dict[str, str] = {}
    operator_invoked = False
    names = {
        options["subject"],
        options["object"],
        options["object_id"],
        "--repo",
        "--context-file",
        "--run-id",
        "--trusted-root",
    }
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg in names and index + 1 < len(argv):
            values[arg] = argv[index + 1]
            index += 2
        elif arg == "--operator-invoked":
            operator_invoked = True
            index += 1
        else:
            return values, operator_invoked, f"Unknown option: {arg}"
    return values, operator_invoked, None


def edge_failed(rows: dict[str, str], message: str, code: int = 2) -> int:
    if code == EXIT_MUTATION_REFUSED:
        emit_kv(LIVE_MUTATION_REFUSAL_STATUS, "true")
    emit_kv(rows["failed"], "true")
    emit_kv(rows["subject"], rows["subject_value"])
    emit_kv(rows["object"], rows["object_value"])
    emit_kv("ERROR", flat_error(message))
    return code


def run_edge(argv: list[str], options: dict[str, str], rows: dict[str, str]) -> int:
    values, operator_invoked, error = scan_edge_args(argv, options)
    if error:
        warn(error)
        return 1
    subject = values.get(options["subject"], "")
    obj = values.get(options["object"], "")
    if not subject or not obj:
        warn(options["usage"])
        return 1
    rows = dict(rows, subject_value=subject, object_value=obj)
    positive = lambda value: value.isdigit() and int(value) > 0  # noqa: E731
    if not positive(subject) or not positive(obj):
        return edge_failed(
            rows,
            f"{options['subject'][2:]} and {options['object'][2:]} must be positive integers",
            1,
        )
    object_id = values.get(options["object_id"], "")
    if object_id and not positive(object_id):
        return edge_failed(
            rows, f"{options['object_id'][2:]} must be a positive integer when provided", 1
        )
    authorized, reason = check_live_mutation_auth(operator_mode=operator_invoked)
    if not authorized:
        return edge_failed(
            rows, f"{LIVE_MUTATION_REFUSAL_REASON}:{reason}", EXIT_MUTATION_REFUSED
        )
    # Repository resolution is where every remaining sandbox path stops.
    return edge_failed(rows, UNRESOLVABLE_REPO)


def add_blocked_by(argv: list[str]) -> int:
    return run_edge(
        argv,
        {
            "subject": "--client-issue",
            "object": "--blocker-issue",
            "object_id": "--blocker-id",
            "usage": BLOCKED_BY_USAGE,
        },
        {
            "failed": "BLOCKED_BY_FAILED",
            "subject": "CLIENT",
            "object": "BLOCKER",
        },
    )


def add_sub_issue(argv: list[str]) -> int:
    return run_edge(
        argv,
        {
            "subject": "--parent-issue",
            "object": "--child-issue",
            "object_id": "--child-id",
            "usage": SUB_ISSUE_USAGE,
        },
        {
            "failed": "SUB_ISSUE_FAILED",
            "subject": "PARENT",
            "object": "CHILD",
        },
    )


# ------------------------------------------ block-issue add/remove-blocked-by


def block_issue_error(message: str, code: int) -> int:
    print(f"ERROR={flat_error(message, BLOCK_ISSUE_ERROR_CHARS)}", file=sys.stderr)
    return code


def run_block_issue(argv: list[str], verb: str) -> int:
    positional: list[str] = []
    repo = ""
    expected = ""
    operator_invoked = False
    triage_controlled = False
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg in {"--repo", "--expected-updated-at"}:
            if index + 1 >= len(argv) or not argv[index + 1]:
                return block_issue_error(f"{arg} requires a value", 2)
            if arg == "--repo":
                repo = argv[index + 1]
            else:
                expected = argv[index + 1]
            index += 2
        elif arg == "--operator-invoked":
            operator_invoked = True
            index += 1
        elif arg == "--triage-controlled":
            triage_controlled = True
            index += 1
        elif arg.startswith("-"):
            return block_issue_error(f"Unknown flag: {arg}", 2)
        else:
            positional.append(arg)
            index += 1
    if len(positional) != 2:
        return block_issue_error(
            f"Usage: {verb} <ISSUE_A> <ISSUE_B> [--repo owner/name] "
            "--operator-invoked [--triage-controlled --expected-updated-at TIMESTAMP]",
            2,
        )
    if any(not item.isdigit() or int(item) < 1 for item in positional):
        return block_issue_error("Issue numbers must be positive integers (>=1)", 2)
    if not operator_invoked:
        return block_issue_error(
            "live mutation authorization refused: --operator-invoked is required", 2
        )
    if triage_controlled and UPDATED_AT_RE.fullmatch(expected) is None:
        return block_issue_error(
            "triage-controlled mutation requires a valid --expected-updated-at", 2
        )
    if expected and not triage_controlled:
        return block_issue_error("--expected-updated-at requires --triage-controlled", 2)
    if repo and REPO_RE.fullmatch(repo) is None:
        return block_issue_error("--repo must be exactly owner/name", 2)
    if not repo:
        # Repository resolution is where every remaining sandbox path stops.
        return block_issue_error(BLOCK_ISSUE_UNRESOLVABLE_REPO, 2)
    raise SystemExit("the sandbox cannot reach a live dependency mutation")


VERBS = {
    "issue-add-blocked-by": add_blocked_by,
    "issue-add-sub-issue": add_sub_issue,
    "block-issue-add-blocked-by": lambda argv: run_block_issue(argv, "add-blocked-by"),
    "block-issue-remove-blocked-by": lambda argv: run_block_issue(argv, "remove-blocked-by"),
}


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in VERBS:
        raise SystemExit(f"unknown reference verb: {argv[:1]}")
    return VERBS[argv[0]](argv[1:])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
