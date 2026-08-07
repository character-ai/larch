"""Frozen Python behavior for the issue #8167 issue-query cutover.

This reproduces the `issue state`, `issue info`, and `issue context`
entrypoints in `python/larch/issue/issue_query.py` as they behaved at cutover,
restricted to the paths a hermetic sandbox can reach.

Deliberate omissions, none of them part of a command contract:

* `logging_util.quiet_init` file routing. It duplicates stdout and stderr into a
  per-invocation `$TMPDIR/larch-quiet-*.log` while leaving the contract streams
  pointed at the original descriptors, so a caller sees identical bytes either
  way. The Rust owner writes the same bytes without the observability copy.
* Every branch that needs a reachable GitHub API: the `issue state` and
  `issue context` reads and their file publication, and the `issue info` read.
  The sandbox has no `gh`, no `git`, and no network, so each command stops at
  the refusal this reference reproduces. `issue context` publication is covered
  by unit tests in `crates/larch-cli/src/issue_commands.rs`, which need no
  network.

A command line that names a repository reaches the GitHub client itself, whose
refusal text is not pinnable from a sandbox. Those lines are out of parity
scope here and raise rather than guess; the only read refusal this reference
reproduces is the one that stops before any client is built.

Two differences are intentional and documented in the pull request:

* The `ERROR` detail after a failed read. Python appended the failed `gh`
  invocation's flattened stdout and stderr. The Rust owner reports the typed
  adapter's redacted reason instead. The `FAILED=true` / `ERROR=` row shape,
  the row order, and the exit code are unchanged, and no consumer parses the
  detail.
* `--issue` numeric validation. Python used `str.isdigit()`, which accepts
  non-ASCII digits such as `٢` and then failed at the `gh` call with the
  read-failure envelope. Rust accepts only ASCII digits and reports
  `--issue must be numeric`. Both exit 1 with a `FAILED=true` row; only the
  `ERROR` detail differs, and no larch caller has ever supplied such a value.
"""
# ruff: noqa: PLR0911 - the frozen scanners return from every refusal branch, exactly as they shipped.

from __future__ import annotations

import re
import sys

CONTEXT_USAGE = "Usage: get-issue-context.sh --issue N --repo OWNER/REPO --tmpdir PATH"
CONTEXT_MISSING_VALUE_RC = 1
CONTEXT_USAGE_RC = 2
VALID_CONTEXT_REPO_RE = re.compile(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$")
# The one read refusal a sandbox can pin. Repository resolution needs
# `gh repo view` or a `git` remote, and neither exists here, so the command
# stops before it builds a GitHub client.
UNRESOLVABLE_REPO_ERROR = "gh issue view failed: could not resolve repo"
OUT_OF_SCOPE = "reaches the GitHub client and is out of parity scope"


def emit_kv(key: str, value: str) -> None:
    print(f"{key}={value}")


def emit_failed(message: str) -> None:
    emit_kv("FAILED", "true")
    emit_kv("ERROR", message)


# ------------------------------------------------------------------ issue state


def parse_state_args(argv: list[str]) -> tuple[str, str | None, str | None]:
    issue = ""
    repo: str | None = None
    idx = 0
    while idx < len(argv):
        token = argv[idx]
        if token == "--issue":
            if idx + 1 >= len(argv) or argv[idx + 1].startswith("--"):
                return issue, repo, "--issue requires a value"
            issue = argv[idx + 1]
            idx += 2
        elif token == "--repo":
            if idx + 1 >= len(argv) or argv[idx + 1].startswith("--"):
                return issue, repo, "--repo requires a value"
            repo = argv[idx + 1]
            idx += 2
        else:
            return issue, repo, f"unknown flag: {token}"
    if not issue:
        return issue, repo, "--issue is required"
    if not issue.isdigit():
        return issue, repo, "--issue must be numeric"
    return issue, repo, None


def issue_state_main(argv: list[str]) -> int:
    _, repo, error = parse_state_args(argv)
    if error:
        emit_failed(error)
        return 1
    if repo:
        raise AssertionError(f"issue state --repo {OUT_OF_SCOPE}")
    emit_failed(UNRESOLVABLE_REPO_ERROR)
    return 1


# ------------------------------------------------------------------- issue info


def parse_value_args(argv: list[str]) -> tuple[dict[str, str], bool, bool]:
    values = {"issue": "", "field": "", "repo": ""}
    idx = 0
    unknown = False
    while idx < len(argv):
        token = argv[idx]
        if token in {"--issue", "--field", "--repo"}:
            if idx + 1 >= len(argv):
                return values, True, unknown
            values[token.removeprefix("--")] = argv[idx + 1]
            idx += 2
        else:
            unknown = True
            idx += 1
    return values, False, unknown


def issue_info_main(argv: list[str]) -> int:
    values, missing_value, unknown = parse_value_args(argv)
    if missing_value:
        return 1
    # This verb has exactly one row and never fails: a refused line, an
    # unsupported field, an unresolvable repository, and a refused read all
    # report the same absent value, so every sandbox path converges here.
    del unknown, values
    emit_kv("VALUE", "")
    return 0


# ---------------------------------------------------------------- issue context


def parse_context_args(argv: list[str]) -> tuple[dict[str, str], int, bool]:
    values = {"issue": "", "repo": "", "tmpdir": ""}
    idx = 0
    while idx < len(argv):
        token = argv[idx]
        if token == "--help":
            return values, 0, True
        if token in {"--issue", "--repo", "--tmpdir"}:
            if idx + 1 >= len(argv):
                return values, CONTEXT_MISSING_VALUE_RC, False
            values[token.removeprefix("--")] = argv[idx + 1]
            idx += 2
        else:
            return values, CONTEXT_USAGE_RC, False
    if not values["issue"] or not values["repo"] or not values["tmpdir"]:
        return values, CONTEXT_USAGE_RC, False
    if not re.fullmatch(r"[1-9][0-9]*", values["issue"]):
        return values, CONTEXT_USAGE_RC, False
    if not VALID_CONTEXT_REPO_RE.fullmatch(values["repo"]):
        return values, CONTEXT_USAGE_RC, False
    return values, -1, False


def issue_context_main(argv: list[str]) -> int:
    _, status, help_requested = parse_context_args(argv)
    if help_requested:
        print(CONTEXT_USAGE)
        return 0
    if status == CONTEXT_MISSING_VALUE_RC:
        return CONTEXT_MISSING_VALUE_RC
    if status == CONTEXT_USAGE_RC:
        print(CONTEXT_USAGE, file=sys.stderr)
        return CONTEXT_USAGE_RC
    raise AssertionError(f"issue context publication {OUT_OF_SCOPE}")


COMMANDS = {
    "issue-state": issue_state_main,
    "issue-info": issue_info_main,
    "issue-context": issue_context_main,
}


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in COMMANDS:
        print(f"issue_query_reference: unknown command {argv[0] if argv else ''}", file=sys.stderr)
        return 64
    return COMMANDS[argv[0]](argv[1:])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
