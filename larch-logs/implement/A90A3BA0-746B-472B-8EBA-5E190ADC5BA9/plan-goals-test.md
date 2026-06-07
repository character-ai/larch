## Goal
Implement issue #3701: [IMPLEMENTING] [BUG] add-blocked-by.sh: false "may already exist" warning (stale summary read)\n\n## Context.

## Implementation Plan
## Context

Found 2026-06-07 while combining #3664 + #3665 → #3693 and carrying the blocker edge over with `/block-issue 3693 3662`. The helper printed:

```
WARNING=blocked_by count did not increase (before=0, after=0) — relationship may already exist
SUCCESS=true
✓ #3693 is now blocked by #3662
```

The warning was false on both counts: no relationship existed beforehand, and the mutation had succeeded — `gh api repos/{owner}/{repo}/issues/3693/dependencies/blocked_by` returned `[3662]` roughly 15 seconds later, and minutes later the issue's summary field read `{"blocked_by":1,"blocking":0,...}`.

## Root cause

`skills/block-issue/scripts/add-blocked-by.sh` writes and verifies on **two different data surfaces**:

1. **Write** (`skills/block-issue/scripts/add-blocked-by.sh:113-122`) — GraphQL `addBlockedBy` mutation. Commits the relationship edge synchronously; returned success with no errors.
2. **Verify** (`skills/block-issue/scripts/add-blocked-by.sh:109` and `:131`) — immediate REST re-read of the issue object, extracting `.issue_dependencies_summary.blocked_by // 0`. That field is a **denormalized rollup counter** that GitHub updates asynchronously relative to the relationship write.

Observed timeline (issue #3693):

| When | Surface | Result |
|------|---------|--------|
| T+0, pre-mutation (script `BEFORE`) | `issue_dependencies_summary.blocked_by` | `0` — genuinely correct (fresh issue) |
| T+0, post-mutation (script `AFTER`) | `issue_dependencies_summary.blocked_by` | `0` — **stale** |
| T+~15 s | `/issues/3693/dependencies/blocked_by` (relational endpoint) | `[3662]` — already consistent |
| T+minutes | `issue_dependencies_summary` | `{"blocked_by":1,...}` — rollup caught up |

The script raced GitHub's counter rollup: the relational data was consistent essentially immediately, but the aggregate it polls lagged past the script's immediate read. (That the lag is async-rollup/replica behavior inside GitHub is inference — internals aren't observable — but the surface-level reads above pin the race down.)

Two compounding design weaknesses in the check:

1. **Wrong postcondition.** The real postcondition is membership — `ISSUE_B ∈ blocked_by(ISSUE_A)` — directly readable from the relational endpoint or from the mutation payload itself. The script instead checks a *count delta* on an eventually-consistent aggregate, which cannot distinguish "already existed" from "stale read". The warning text (`relationship may already exist`) anticipates only the former, so the stale-read case is misreported.
2. **Fail-open `// 0`.** A renamed or absent field would also silently read as `0` and produce the identical signature. Not the cause here (the field exists and eventually reads `1`), but it fails in the same direction, masking real problems as the same benign-looking warning.

Scope notes (verified):

- The similarly-named `/issue`-skill helper `skills/issue/scripts/add-blocked-by.sh` does **not** share this pattern (REST POST with retry/idempotent-422 contract, no summary-counter verification) — not implicated.
- The sibling contract `skills/block-issue/scripts/add-blocked-by.md:30` documents the count-based verification ("Verifies by comparing `issue_dependencies_summary.blocked_by` on issue A before and after") and must be updated alongside the script.

## Fix

Verify read-your-own-write **inside the mutation response**. Schema introspection confirms `AddBlockedByPayload` exposes `issue` (and `blockingIssue`), so the mutation can return the blocked issue's `blockedBy` connection in the same response — transactionally consistent, zero extra round-trips:

```graphql
mutation($issueId: ID!, $blockingId: ID!) {
  addBlockedBy(input: {issueId: $issueId, blockingIssueId: $blockingId}) {
    issue { blockedBy(first: 100) { nodes { number } } }
  }
}
```

Then assert `ISSUE_B` is among the returned `nodes[].number`:

- present → verified success; print the confirmation, no warning;
- absent → real verification failure → warn (or hard-fail) with an accurate message.

Concretely in `skills/block-issue/scripts/add-blocked-by.sh`:

- Replace the mutation document (lines 113-122) with the payload above.
- Delete the `BEFORE`/`AFTER` summary-counter reads and the count comparison (lines 108-109, 130-135).
- Parse `data.addBlockedBy.issue.blockedBy.nodes[].number` from `MUTATION_OUT` (python3, same style as the existing node-ID parses) and check membership of `ISSUE_B`.
- Update `skills/block-issue/scripts/add-blocked-by.md:30` to describe membership verification via the mutation payload.

Edge note: `blockedBy(first: 100)` is GraphQL's max page size; an issue with >100 blockers could false-negative the membership check. Blocker lists are tiny in practice — if paranoia is warranted, fall back to the relational REST endpoint (`/issues/A/dependencies/blocked_by`, paginated) on a miss before warning.

Fallback alternative (if the payload read proves unreliable): verify membership via `gh api repos/$REPO/issues/$ISSUE_A/dependencies/blocked_by` — still strictly better than the count diff, because it tests the true postcondition on the relational surface, which was observed consistent within seconds of the mutation.

## Test plan
(no test plan section in plan-file)
