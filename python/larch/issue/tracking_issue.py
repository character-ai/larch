"""Pure tracking-issue pull-request footer helpers.

GitHub reads, writes, lifecycle transitions, and marker comment behavior belong
to the Rust ``tracking-issue`` commands. Python workflows reach those commands
through :mod:`larch.core.rust_runtime` and ``scripts/larch.sh``.
"""

from __future__ import annotations


def _drop_issue_footer(*, body: str, issue_number: int) -> str:
    needles = {f"Closes #{issue_number}", f"Part of #{issue_number}"}
    lines = body.rstrip().splitlines()
    while lines and not lines[-1].strip():
        _ = lines.pop()
    if lines and lines[-1].strip() in needles:
        _ = lines.pop()
    return "\n".join(lines).rstrip()


def link_pr_closes(*, body: str, issue_number: int) -> str:
    """Ensure the PR body has a footer-style ``Closes #N`` line."""
    needle = f"Closes #{issue_number}"
    nonblank_lines = [line.strip() for line in body.splitlines() if line.strip()]
    if nonblank_lines and nonblank_lines[-1] == needle:
        return body
    stripped = _drop_issue_footer(body=body, issue_number=issue_number)
    return stripped.rstrip() + f"\n\n{needle}\n"


def link_pr_part_of(*, body: str, issue_number: int) -> str:
    """Ensure the PR body has a footer-style ``Part of #N`` line."""
    needle = f"Part of #{issue_number}"
    nonblank_lines = [line.strip() for line in body.splitlines() if line.strip()]
    if nonblank_lines and nonblank_lines[-1] == needle:
        return body
    stripped = _drop_issue_footer(body=body, issue_number=issue_number)
    return stripped.rstrip() + f"\n\n{needle}\n"


def link_pr_for_disposition(*, body: str, issue_number: int, partial: bool = False) -> str:
    """Link a full result as closing and a partial result as non-closing."""
    if partial:
        return link_pr_part_of(body=body, issue_number=issue_number)
    return link_pr_closes(body=body, issue_number=issue_number)
