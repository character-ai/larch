# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false
"""Fail-closed Python entrypoints for /block-issue dependency mutations."""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from typing import Final, cast

from larch.core import proc, redact
from larch.git import gh
from larch.issue.triage import (
    TriageError,
    _comment_bodies,  # pyright: ignore[reportPrivateUsage]  # shared triage helper reads every comment before public mutation
    _contains_security_content,  # pyright: ignore[reportPrivateUsage]  # shared triage helper reused by /block-issue; no public alias exists
    _has_protected_state,  # pyright: ignore[reportPrivateUsage]  # shared triage helper reused by /block-issue; no public alias exists
    _issue_snapshot,  # pyright: ignore[reportPrivateUsage]  # shared triage helper reused by /block-issue; no public alias exists
)
from larch.state.session_env import check_live_mutation_auth

LOOKUP_QUERY: Final = """query($owner: String!, $name: String!, $ia: Int!, $ib: Int!) {
  repository(owner: $owner, name: $name) {
    ia: issue(number: $ia) { id }
    ib: issue(number: $ib) { id }
  }
}"""
ADD_MUTATION: Final = """mutation($issueId: ID!, $blockingId: ID!) {
  addBlockedBy(input: {issueId: $issueId, blockingIssueId: $blockingId}) {
    issue { id }
  }
}"""
REMOVE_MUTATION: Final = """mutation($issueId: ID!, $blockingId: ID!) {
  removeBlockedBy(input: {issueId: $issueId, blockingIssueId: $blockingId}) {
    issue { id }
  }
}"""

_REPO_RE: Final = re.compile(r"[A-Za-z0-9._-]+/[A-Za-z0-9._-]+")
_UPDATED_AT_RE: Final = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z")
_POSITIONAL_COUNT: Final = 2


@dataclass(frozen=True)
class MutationArgs:
    """Validated dependency mutation arguments."""

    issue: int
    blocker: int
    repo: str
    operator_invoked: bool
    triage_controlled: bool
    expected_updated_at: str


class BlockIssueError(Exception):
    """A safe dependency-mutation failure and its distinct process code."""

    def __init__(self, message: str, exit_code: int) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def _flat(text: str) -> str:
    redacted = redact.redact_outbound(text)
    return redacted.replace("\r", " ").replace("\n", " ").strip()[:1000]


def _repo() -> str:
    result = proc.run(
        ["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"]
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _parse_args(  # pylint: disable=too-many-branches  # each branch validates one CLI token class
    argv: list[str], *, verb: str
) -> MutationArgs:
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
                raise BlockIssueError(f"{arg} requires a value", 2)
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
            raise BlockIssueError(f"Unknown flag: {arg}", 2)
        else:
            positional.append(arg)
            index += 1
    if len(positional) != _POSITIONAL_COUNT:
        raise BlockIssueError(
            f"Usage: {verb} <ISSUE_A> <ISSUE_B> [--repo owner/name] "
            "--operator-invoked [--triage-controlled --expected-updated-at TIMESTAMP]",
            2,
        )
    if any(not item.isdigit() or int(item) < 1 for item in positional):
        raise BlockIssueError("Issue numbers must be positive integers (>=1)", 2)
    if not operator_invoked:
        raise BlockIssueError(
            "live mutation authorization refused: --operator-invoked is required", 2
        )
    if triage_controlled and _UPDATED_AT_RE.fullmatch(expected) is None:
        raise BlockIssueError(
            "triage-controlled mutation requires a valid --expected-updated-at", 2
        )
    if expected and not triage_controlled:
        raise BlockIssueError("--expected-updated-at requires --triage-controlled", 2)
    if repo and _REPO_RE.fullmatch(repo) is None:
        raise BlockIssueError("--repo must be exactly owner/name", 2)
    return MutationArgs(
        issue=int(positional[0]),
        blocker=int(positional[1]),
        repo=repo,
        operator_invoked=operator_invoked,
        triage_controlled=triage_controlled,
        expected_updated_at=expected,
    )


def _json_object(text: str, *, context: str, exit_code: int) -> dict[str, object]:
    try:
        value: object = json.loads(text)
    except json.JSONDecodeError as exc:
        raise BlockIssueError(f"{context} returned invalid JSON", exit_code) from exc
    if not isinstance(value, dict) or value.get("errors"):
        raise BlockIssueError(
            f"{context} returned errors or a malformed payload", exit_code
        )
    return cast("dict[str, object]", value)


def _lookup_nodes(args: MutationArgs) -> tuple[str, str]:
    owner, name = args.repo.split("/", 1)
    lookup = proc.run(
        [
            "gh",
            "api",
            "graphql",
            "-F",
            f"owner={owner}",
            "-F",
            f"name={name}",
            "-F",
            f"ia={args.issue}",
            "-F",
            f"ib={args.blocker}",
            "-f",
            f"query={LOOKUP_QUERY}",
        ],
    )
    if lookup.returncode != 0:
        raise BlockIssueError(
            f"GraphQL node-ID lookup failed: {lookup.stderr or lookup.stdout}", 7
        )
    payload = _json_object(lookup.stdout, context="GraphQL node-ID lookup", exit_code=7)
    try:
        repository = cast(
            "dict[str, object]",
            cast("dict[str, object]", payload["data"])["repository"],
        )
        node_a = str(cast("dict[str, object]", repository["ia"])["id"])
        node_b = str(cast("dict[str, object]", repository["ib"])["id"])
    except (KeyError, TypeError) as exc:
        raise BlockIssueError(
            "GraphQL node-ID lookup omitted an issue node", 7
        ) from exc
    return node_a, node_b


def _relation_present(*, repo: str, issue: int, blocker: int) -> bool:
    result = proc.run(
        [
            "gh",
            "api",
            f"repos/{repo}/issues/{issue}/dependencies/blocked_by",
            "--paginate",
        ],
    )
    if result.returncode != 0:
        raise BlockIssueError(
            f"blocked-by relation read-back failed: {result.stderr or result.stdout}",
            8,
        )
    try:
        rows = gh.loads_json_paginated_list(result.stdout)
        numbers = {
            int(row["number"])
            for row in rows
            if isinstance(row, dict) and isinstance(row.get("number"), int | str)
        }
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise BlockIssueError(
            "blocked-by relation read-back returned malformed JSON", 8
        ) from exc
    return blocker in numbers


def _triage_precondition(args: MutationArgs) -> None:
    if not args.triage_controlled:
        return
    try:
        target = _issue_snapshot(proc, issue=args.issue, repo=args.repo)
        comments = _comment_bodies(proc, issue=args.issue, repo=args.repo)
        protected = _has_protected_state(target, allow_stale_title=False)
    except TriageError as exc:
        raise BlockIssueError(f"target precondition read failed: {exc}", 4) from exc
    if target.updated_at != args.expected_updated_at:
        raise BlockIssueError(
            "target issue changed since the expected triage snapshot", 4
        )
    if _contains_security_content(target, comments=comments):
        raise BlockIssueError(
            "security-sensitive targets cannot receive public dependency mutations", 4
        )
    if protected:
        raise BlockIssueError("target has protected lifecycle state", 4)


def _resolve_repo(args: MutationArgs) -> MutationArgs:
    if args.repo:
        return args
    detected = _repo()
    if not detected or _REPO_RE.fullmatch(detected) is None:
        raise BlockIssueError(
            "Could not determine repository: pass --repo owner/name", 2
        )
    return MutationArgs(
        issue=args.issue,
        blocker=args.blocker,
        repo=detected,
        operator_invoked=args.operator_invoked,
        triage_controlled=args.triage_controlled,
        expected_updated_at=args.expected_updated_at,
    )


def _mutate_dependency(args: MutationArgs, *, remove: bool) -> str:
    graphql_field = "removeBlockedBy" if remove else "addBlockedBy"
    mutation_query = REMOVE_MUTATION if remove else ADD_MUTATION
    _triage_precondition(args)
    node_a, node_b = _lookup_nodes(args)
    _triage_precondition(args)
    mutation = proc.run(
        [
            "gh",
            "api",
            "graphql",
            "-F",
            f"issueId={node_a}",
            "-F",
            f"blockingId={node_b}",
            "-f",
            f"query={mutation_query}",
        ],
    )
    if mutation.returncode != 0:
        raise BlockIssueError(
            f"{graphql_field} mutation failed: {mutation.stderr or mutation.stdout}", 7
        )
    payload = _json_object(
        mutation.stdout, context=f"{graphql_field} mutation", exit_code=8
    )
    try:
        operation = cast(
            "dict[str, object]",
            cast("dict[str, object]", payload["data"])[graphql_field],
        )
        issue_node = cast("dict[str, object]", operation["issue"])
        if not issue_node.get("id"):
            raise KeyError("id")
    except (KeyError, TypeError) as exc:
        raise BlockIssueError(
            f"{graphql_field} mutation omitted its issue postcondition payload", 8
        ) from exc
    if (
        _relation_present(repo=args.repo, issue=args.issue, blocker=args.blocker)
        == remove
    ):
        raise BlockIssueError(f"{graphql_field} relation failed exact read-back", 8)
    if not args.triage_controlled:
        return ""
    try:
        target = _issue_snapshot(proc, issue=args.issue, repo=args.repo)
    except TriageError as exc:
        raise BlockIssueError(f"target postcondition read failed: {exc}", 8) from exc
    if target.updated_at == args.expected_updated_at:
        raise BlockIssueError(
            "dependency mutation did not advance the target snapshot", 8
        )
    return target.updated_at


def _mutation_main(argv: list[str], *, remove: bool) -> int:
    verb = "remove-blocked-by" if remove else "add-blocked-by"
    try:
        args = _resolve_repo(_parse_args(argv, verb=verb))
        auth_ok, auth_reason = check_live_mutation_auth(
            context_file=None, operator_mode=args.operator_invoked
        )
        if not auth_ok:
            raise BlockIssueError(
                f"live mutation authorization refused: {auth_reason}", 3
            )
        fresh_updated_at = _mutate_dependency(args, remove=remove)
    except BlockIssueError as exc:
        print(f"ERROR={_flat(str(exc))}", file=sys.stderr)
        return exc.exit_code
    print("SUCCESS=true")
    print("RELATION_VERIFIED=true")
    if fresh_updated_at:
        print(f"UPDATED_AT={fresh_updated_at}")
    state = "is no longer blocked by" if remove else "is now blocked by"
    print(f"✓ #{args.issue} {state} #{args.blocker}")
    return 0


def add_blocked_by_main(argv: list[str]) -> int:
    """Add and verify an ISSUE_A blocked-by ISSUE_B relationship."""
    return _mutation_main(argv, remove=False)


def remove_blocked_by_main(argv: list[str]) -> int:
    """Remove and verify an ISSUE_A blocked-by ISSUE_B relationship."""
    return _mutation_main(argv, remove=True)
