# Review Round 1

- Mode: `diff`
- 5 accepted, 3 rejected (3 neutral)

## Accepted Findings

### FINDING_1: seed-initial-state accepts empty required identity fields
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-state-seeder-output.txt
- **Severity**: important
- **Concern**: `seed-initial-state` / `_write_initial_ship_state` treats empty strings as valid for `--branch`, `--issue`, `--repo`, and `--run-id`. When `bootstrap-routing.env` and/or `parent-issue.md` lack values (including `BRANCH_NAME`, which `read_sentinel_key` cannot recover via `tracking-issue read`), the shell wrapper assembles empty argv and Python writes a non-empty `ship-pr-state.sh` with blank identity anchors. `oos file` can succeed on that bad state; create-if-absent then blocks re-seed; retries loop on `require_value` failures or stall late (Step 5 path may never hit `step-8-ship.sh` hard checks). Regression from live-orchestrator Step 0 exports on the old path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Reject empty --branch --issue --repo --run-id in _write_initial_ship_state before atomic write; add test_ship coverage
  - From cursor-specialist-correctness-output.txt: Read parent-issue.md via read_kv_file per contract; validate non-empty BRANCH_NAME before invoking Python
  - From codex-specialist-correctness-output.txt: Validate non-empty branch, issue, repo, and run-id before writing state.
  - From cursor-specialist-edge-cases-output.txt: Validate non-empty branch (via _valid_branch_name), digit issue, repo slug, and run-id before atomic write; add negative tests
  - From codex-specialist-edge-cases-output.txt: Validate branch issue run id and repo before writing and add no-partial-state tests for empty anchors.
  - From codex-specialist-testing-output.txt: Validate branch, issue, repo, and run-id before writing, and test that empty required values fail without creating state.
  - From dyn-state-seeder-output.txt: After argv assembly, reject empty `BRANCH_NAME`, `ISSUE_NUMBER`, `RUN_ID`, or `REPO` in `_write_initial_ship_state` (or in `step-8-seed-initial.sh` before invoking Python) with a clear stderr error and non-zero exit; add a unit test that missing durable inputs produce no state file.


### FINDING_10: Missing test that _write_ship_state preserves NO_ADMIN_FALLBACK
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan edge case requires `NO_ADMIN_FALLBACK=true` survive driver `_write_ship_state` refreshes; only seeder output is tested today. A future `_write_ship_state` change could clobber seeded `NO_ADMIN_FALLBACK` when `ctx.no_admin_fallback` is true, breaking `--no-admin-fallback` merge behavior without a unit-test failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add test_ship_state_merge_preserves_no_admin_fallback: seed state with NO_ADMIN_FALLBACK=true, call _write_ship_state with ctx.no_admin_fallback=True, assert the key remains true.


### FINDING_4: ship-seed-input.env write failure is warning-only in bootstrap
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-step8-routing-output.txt
- **Severity**: important
- **Concern**: `_merge_write_ship_seed_input` failures in `bootstrap invoke` are logged to stderr but bootstrap still exits `0`. On `--merge` / `--draft` / `--no-admin-fallback` runs, Step 8 seeding then falls back to default `MERGE=false` / `DRAFT=false` / `NO_ADMIN_FALLBACK=false`, silently dropping operator flags and skipping the merge loop despite `--merge`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Fail bootstrap on ship-seed-input write failure or fail seeder when merge/draft flags missing from durable file
  - From cursor-specialist-edge-cases-output.txt: Fail bootstrap invoke on ship-seed-input write failure or fail seeder when durable flag inputs are missing after a logged write error
  - From dyn-step8-routing-output.txt: Fail bootstrap closed when `ship-seed-input.env` cannot be written on initial mode, or surface a routing KV the orchestrator must treat as a hard error before Step 8.


### FINDING_5: Bare OOS_N stable IDs collide across accepted source files
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_stable_identifier` returns bare `OOS_N` from headers. Two different accepted-OOS files both containing `OOS_1` can make persisted retry evidence for one block satisfy the other, silently skipping filing or losing a distinct OOS URL.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Make stable IDs source-qualified or hash-backed, or require title/body corroboration for bare OOS_N matches.
  - From codex-specialist-edge-cases-output.txt: Namespace stable IDs by source or use content-derived IDs, prevent URL reuse for colliding stable IDs, and add a multi-source duplicate-OOS_1 retry test.


### FINDING_6: SKILL.md recovery prose skips pre-driver guard/oos file chain
- **Reviewer(s)**: codex-specialist-correctness-output.txt, dyn-step8-routing-output.txt
- **Severity**: important
- **Concern**: Pre-driver contract (lines 748, 764) requires guard + `oos file` whenever state is seeded-but-no-PR (including after `oos file` failure). Line 776 tells the orchestrator that **every** Step 8+ recovery re-entry goes through `step-8-ship.sh` only. Following line 776 after an unexpected turn end can skip the pre-driver chain and ship without checkpoint-visible OOS evidence (e.g., seeded `PHASE=checks` with empty `PR_NUMBER` after `oos file` failed).
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Limit the sentence to post-driver re-entry and explicitly exempt pre-driver state.
  - From dyn-step8-routing-output.txt: Scope line 776 to post-driver continuations only, or add an explicit override: re-evaluate the pre-driver predicate first; when it matches, run guard → (seeder if absent/empty) → `oos file` before `step-8-ship.sh`.


