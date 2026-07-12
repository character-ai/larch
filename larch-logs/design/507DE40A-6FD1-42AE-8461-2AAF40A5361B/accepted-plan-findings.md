### FINDING_4: Wire triage into the anti-halt contract
- **Reviewer(s)**: Codex-Arch, Codex-Requirements
- **Severity**: major
- **Concern**: Triage can halt after child skills return, skipping dependency read-back, follow-up verification, cleanup, and terminal machine keys.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add the orchestrator banner and continuation reminders, and register `skills/triage/SKILL.md` in the shared scope list and harness 1. **[security] Dependency authorization is incomplete.** The plan authorizes `triage apply` and `/issue`, but `/block-issue` remains a separate mutation path without `--operator-invoked` enforcement. 2. **[architecture] Add the required anti-halt wiring.** `/triage` performs work after child skill calls, so it must follow the repository’s orchestrator banner, reminder, scope-list, and harness contracts.
  - From Codex-Requirements: Add canonical anti-halt reminders, verify `/issue` through counters and a sentinel, and register triage in `skills/shared/subskill-invocation.md` and `scripts/test-anti-halt-banners.sh`.


### FINDING_6: Inspect code from an immutable main snapshot
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: Investigation may inspect a feature branch or dirty worktree instead of main, producing false fixed or root-cause conclusions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Resolve and record a main commit before investigation, read cited files and symbols through that commit, and fail closed if the exact main ref cannot be verified


### FINDING_7: Provide a validated evidence-inspection CLI
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The required fetch-and-show workflow for unmerged branch evidence has no reachable, validated CLI surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add a triage inspect (or equivalent) entry point in triage.py, register it in cli.py, validate refs/paths and fixed-remote fetch/show there, record missing refs as evidence gaps, and pin the helper in skills/triage/SKILL.md and scripts/test-triage-structure.sh.
  - From Codex-Pragmatic: Add a triage evidence verb that validates refs and paths, uses the fixed remote with argument-vector execution, and has focused tests.
  - From Cursor-Requirements: Add a deterministic triage read-ref (or equivalent) verb in python/larch/issue/triage.py, register it in python/larch/cli.py, call it from skills/triage/SKILL.md for validated commit SHAs or refs/pull/N/head, and cover fetch-show success, rejection, and caps in python/tests/issue/test_triage.py and scripts/test-triage-structure.sh


### FINDING_8: Recheck freshness before dependency writes
- **Reviewer(s)**: Codex-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: Dependency application can use stale analysis after an intervening issue edit or lifecycle transition.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Pass the verified timestamp into a triage-controlled dependency mutation that rechecks freshness and protected state immediately before applying and reading back the edge.
  - From Codex-Requirements: Thread the latest verified `updatedAt` into dependency application and make `issue_block.py` compare it immediately before mutation. Test that mismatch prevents the GraphQL mutation.


### FINDING_9: Preserve title restoration on close verdicts
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Concern**: Rejecting lifecycle-prefixed titles before verdict routing makes required title restoration unreachable for already-fixed or duplicate issues.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Reject active lifecycle state, but allow close verdicts to restore a stale prefix when no protected block or label remains. Test both paths.


### FINDING_10: Permit narrowly scoped external-tool reproduction
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Concern**: A blanket ban on networked or authenticated probes prevents the specified safe external-tool reproduction path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Allow narrowly named, fixed-destination, read-only external probes through existing credential-safe launch paths. Keep arbitrary commands, arguments, and destinations forbidden.


