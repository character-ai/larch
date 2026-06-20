# Review Round 2

- Mode: `diff`
- 10 accepted, 3 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Apply-time dependency revalidation fail-open on graph refresh failure
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-generic-output.txt, dyn-deps-cli-tests-output.txt
- **Severity**: important
- **Concern**: When apply-time live dependency graph refresh fails or is incomplete (open-issue fetch failure, dropped per-issue dependency-read warnings), `live_edges` can be empty or partial. Duplicate and cycle checks then run against a weakened graph and `apply_main` may still call `/block-issue`, allowing bad edge writes (including cycles) on transient GitHub API errors.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Skip edge writes when open-issue or dependency refresh fails; do not proceed with empty live_edges
  - From cursor-specialist-edge-cases-output.txt: Propagate dependency-read warnings; skip or fail all edge writes when graph refresh is incomplete. Cache one successful graph snapshot per apply run.
  - From codex-generic-output.txt: Return graph completeness with the edge set. If any live dependency read or open-issue fetch fails, skip or fail the affected edge write before calling `/block-issue`, and surface the warning.
  - From dyn-deps-cli-tests-output.txt: Fail closed for edge writes when the live graph fetch fails or dependency reads are incomplete; skip all edge writes with a explicit reason, or retry with backoff before any mutation.


### FINDING_2: pair-cap partial audit trusts prompt-reported skipped_latent_pairs
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: With `--pair-cap` set, orchestrator can report `skipped_latent_pairs=0` while emitting many latent edges. Plan may mark `audit_complete=true` and allow dependency writes without mechanical verification of pair-cap metadata.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Count latent edges in plan or require Python-side pairing; fail closed on inconsistent pair-cap metadata


### FINDING_4: write-proposals skips snapshot validation when --fetch-file is omitted
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-deps-safety-output.txt, dyn-deps-cli-tests-output.txt
- **Severity**: important
- **Concern**: `deps write-proposals` treats `--fetch-file` as optional, so proposals can be persisted without snapshot membership validation when the flag is omitted. Out-of-snapshot issue numbers may enter the pipeline until a later `plan` failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Require --fetch-file or fail closed when validation cannot run
  - From dyn-deps-safety-output.txt: make `--fetch-file` required in `write_proposals_main`, matching `plan` and `explicit-refs`.
  - From dyn-deps-cli-tests-output.txt: Make `--fetch-file` required on `write-proposals`, or default to rejecting writes when snapshot validation cannot run; add a test covering rejection of out-of-snapshot proposals at write time.


### FINDING_9: plan/apply trust prompt-supplied regular_refresh_allowed without origin re-check
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: After `ORIGIN_MATCHES=false`, a mistaken `proposals.json` with `regular_refresh_allowed:true` can pass plan and apply, persisting body rewrites/closes based on issue text compared against the wrong repo checkout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Re-run _origin_slug_matches in plan (and apply) and reject rewrite/close mutations when origin does not match --repo.


### FINDING_11: machine_fetch_file path and presence not constrained fail-closed
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-deps-safety-output.txt
- **Severity**: important
- **Concern**: `explicit-refs` and `plan` load `machine_fetch_file` from a path stored in `fetch.json` without requiring it or constraining it to the fetch output directory. Missing, stale, or tampered machine-fetch data can yield `status: ok` with zero or widened explicit edges, hiding prose dependencies or accepting endpoints outside the operator-reviewed snapshot.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Require machine_fetch_file; fail closed if missing or unreadable.
  - From dyn-deps-safety-output.txt: resolve `machine_fetch_file` only as a sibling under the fetch output directory (or verify a hash of the machine file at fetch time) and fail closed on mismatch.


### FINDING_12: Missing unit tests for apply --rewrites-only and --edges-only modes
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Operator may choose "Apply rewrites and closes only" at Step 5, but a regression in `apply_main` could still invoke block-issue and write dependency edges without test coverage for approval-mode flags.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add apply tests that assert --rewrites-only applies rewrites/closes without block-issue calls and --edges-only skips rewrite/close mutations; include mutual-exclusion coverage for both flags set.


### FINDING_13: Apply-time title/in-flight revalidation for non-mutable clients is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-deps-cli-tests-output.txt
- **Severity**: important
- **Concern**: No apply-time test covers client issues retitled to non-mutable REGULAR or in-flight prefixes (`[IMPLEMENTING]`, `[DESIGNED]`, busy prefix) between plan and apply. A regression in `_live_issue_meta` + `_is_mutable_regular` / `_revalidate_edge_before_write` could still write blocked-by edges.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add an apply test stubbing live metadata with a non-mutable client title and assert skip reason client is no longer mutable REGULAR with no block-issue invocation.
  - From dyn-deps-cli-tests-output.txt: Add an apply test where `_live_issue_meta` returns an in-flight title for the client and assert the edge is skipped with reason `client is no longer mutable REGULAR` and no `block-issue` call is made.


### FINDING_14: Apply treats missing or empty snapshot_issue_numbers as no snapshot restriction
- **Reviewer(s)**: codex-generic-output.txt, dyn-deps-safety-output.txt, dyn-deps-cli-tests-output.txt
- **Severity**: important
- **Concern**: If `plan.json` lacks a non-empty `snapshot_issue_numbers`, `_issue_not_in_snapshot` never blocks rewrites, closes, or edges. A malformed or hand-edited plan can mutate issues outside the original fetch snapshot, bypassing the fetch-snapshot validation boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Require `snapshot_issue_numbers` to be present and non-empty for any plan containing rewrites, closes, or edges. Fail closed when it is missing, malformed, or does not contain every mutation endpoint.
  - From dyn-deps-safety-output.txt: require a non-empty `snapshot_issue_numbers` in `apply` and reject plans without it.
  - From dyn-deps-cli-tests-output.txt: Require a non-empty `snapshot_issue_numbers` in `apply_main` and return a non-zero exit when it is missing or malformed; add a test that apply rejects mutations when the field is absent.


### FINDING_15: plan never records audited repository; apply mutates whatever --repo names
- **Reviewer(s)**: dyn-deps-safety-output.txt
- **Severity**: important
- **Concern**: `deps plan` never records the audited repository, and `deps apply` mutates whatever repo `--repo` names without comparing it to the fetch snapshot. A mistyped Step 6 invocation or swapped `plan.json` can rewrite, close, or block issues in the wrong repository when issue numbers collide.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-deps-safety-output.txt: persist `repo` from fetch in plan JSON and fail closed in `apply` when `--repo` does not match exactly.


### FINDING_16: apply trusts dependency_writes_allowed without re-deriving partial-audit policy
- **Reviewer(s)**: dyn-deps-safety-output.txt
- **Severity**: important
- **Concern**: `deps apply` trusts `dependency_writes_allowed` from the plan file and does not re-derive partial-audit policy from `audit_complete`, `--pair-cap`, or `skipped_latent_pairs`. A tampered plan can set `dependency_writes_allowed: true` while `audit_complete: false`, bypassing Step 5 partial-audit gates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-deps-safety-output.txt: recompute dependency-write eligibility in `apply` from stored audit metadata (or require an operator-attested approval token written only after Step 5) and reject plans where flags disagree fail-closed.


