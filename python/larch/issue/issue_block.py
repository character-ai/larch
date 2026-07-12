# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false
"""Python entrypoints for /block-issue dependency mutations."""

from __future__ import annotations

import json
import re
import sys

from larch.core import proc

LOOKUP_QUERY = """query($owner: String!, $name: String!, $ia: Int!, $ib: Int!) {
  repository(owner: $owner, name: $name) {
    ia: issue(number: $ia) { id }
    ib: issue(number: $ib) { id }
  }
}"""
ADD_MUTATION = """mutation($issueId: ID!, $blockingId: ID!) {
  addBlockedBy(input: {issueId: $issueId, blockingIssueId: $blockingId}) {
    issue { blockedBy(first: 100) { nodes { number } } }
  }
}"""
REMOVE_MUTATION = """mutation($issueId: ID!, $blockingId: ID!) {
  removeBlockedBy(input: {issueId: $issueId, blockingIssueId: $blockingId}) {
    issue { blockedBy(first: 100) { nodes { number } } }
  }
}"""


def _err(message: str) -> None:
    print(f"ERROR={message}", file=sys.stderr)


def _repo() -> str:
    result = proc.run(["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"])
    return result.stdout.strip() if result.returncode == 0 else ""


def _has_errors(payload: object) -> bool:
    return isinstance(payload, dict) and bool(payload.get("errors"))


def _mutation_main(argv: list[str], *, remove: bool) -> int:
    verb = "remove-blocked-by" if remove else "add-blocked-by"
    graphql_field = "removeBlockedBy" if remove else "addBlockedBy"
    mutation_query = REMOVE_MUTATION if remove else ADD_MUTATION
    issue_a = ""
    issue_b = ""
    repo = ""
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == "--repo":
            if index + 1 >= len(argv) or not argv[index + 1]:
                _err("--repo requires a value (e.g. --repo owner/name)")
                return 1
            repo = argv[index + 1]
            index += 2
        elif arg.startswith("-"):
            _err(f"Unknown flag: {arg}")
            return 1
        elif not issue_a:
            issue_a = arg
            index += 1
        elif not issue_b:
            issue_b = arg
            index += 1
        else:
            _err(f"Unexpected argument: {arg}")
            return 1
    if not issue_a or not issue_b:
        _err(f"Usage: {verb} <ISSUE_A> <ISSUE_B> [--repo owner/name]")
        return 1
    if not issue_a.isdigit() or not issue_b.isdigit() or int(issue_a) < 1 or int(issue_b) < 1:
        _err(f"Issue numbers must be positive integers (≥1); got: ISSUE_A='{issue_a}' ISSUE_B='{issue_b}'")
        return 1
    if not repo:
        repo = _repo()
        if not repo:
            _err("Could not determine repository: pass --repo owner/name")
            return 1
    if re.fullmatch(r"[A-Za-z0-9._-]+/[A-Za-z0-9._-]+", repo) is None:
        _err(f"--repo must be exactly owner/name (got: '{repo}')")
        return 1
    owner, name = repo.split("/", 1)
    lookup = proc.run(
        ["gh", "api", "graphql", "-F", f"owner={owner}", "-F", f"name={name}", "-F", f"ia={issue_a}", "-F", f"ib={issue_b}", "-f", f"query={LOOKUP_QUERY}"],
    )
    if lookup.returncode != 0:
        _err(f"GraphQL node-ID lookup failed: {lookup.stdout}{lookup.stderr}")
        return 1
    try:
        lookup_data: object = json.loads(lookup.stdout)
    except json.JSONDecodeError:
        _err(f"GraphQL node-ID lookup failed: {lookup.stdout}{lookup.stderr}")
        return 1
    if _has_errors(lookup_data):
        _err(f"GraphQL node-ID lookup returned errors: {lookup.stdout}")
        return 1
    repo_data = lookup_data.get("data", {}).get("repository", {}) if isinstance(lookup_data, dict) else {}
    node_a = (repo_data.get("ia") or {}).get("id") if isinstance(repo_data, dict) else ""
    node_b = (repo_data.get("ib") or {}).get("id") if isinstance(repo_data, dict) else ""
    if not node_a:
        _err(f"Could not resolve node ID for issue #{issue_a} in {repo}")
        return 1
    if not node_b:
        _err(f"Could not resolve node ID for issue #{issue_b} in {repo}")
        return 1
    mutation = proc.run(["gh", "api", "graphql", "-F", f"issueId={node_a}", "-F", f"blockingId={node_b}", "-f", f"query={mutation_query}"])
    if mutation.returncode != 0:
        _err(f"{graphql_field} mutation failed: {mutation.stdout}{mutation.stderr}")
        return 1
    try:
        mutation_data: object = json.loads(mutation.stdout)
    except json.JSONDecodeError:
        _err(f"{graphql_field} mutation failed: {mutation.stdout}{mutation.stderr}")
        return 1
    if _has_errors(mutation_data):
        _err(f"{graphql_field} mutation returned errors: {mutation.stdout}")
        return 1
    try:
        data = mutation_data if isinstance(mutation_data, dict) else {}
        nodes = data["data"][graphql_field]["issue"]["blockedBy"]["nodes"]
        numbers = [int(node["number"]) for node in nodes]
    except (KeyError, TypeError, ValueError):
        numbers = []
    relation_present = int(issue_b) in numbers
    expected_present = not remove
    if relation_present != expected_present:
        expected = "absent" if remove else "present"
        print(f"WARNING={graphql_field} succeeded but #{issue_b} was not {expected} in the blockedBy payload: relationship status is uncertain", file=sys.stderr)
    print("SUCCESS=true")
    state = "is no longer blocked by" if remove else "is now blocked by"
    print(f"✓ #{issue_a} {state} #{issue_b}")
    return 0


def add_blocked_by_main(argv: list[str]) -> int:
    return _mutation_main(argv, remove=False)


def remove_blocked_by_main(argv: list[str]) -> int:
    return _mutation_main(argv, remove=True)
