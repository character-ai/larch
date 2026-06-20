# Review Round 1

- Mode: `diff`
- 7 accepted, 6 rejected (4 neutral)

## Accepted Findings

### FINDING_1: Apply-time cycle check uses incomplete dependency graph
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-deps-edge-rules-output.txt, dyn-deps-cli-tests-output.txt
- **Severity**: important
- **Concern**: Apply-time cycle revalidation reads dependency edges only for edge endpoints plus rewrite/close targets, not the full open-issue graph that fetch/plan use. Transitive cycles through intermediate issues can be missed (for example existing chains like 1←2←3←4 with a planned 4→1 or 6→2), so apply can write edges that plan would have rejected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Re-fetch all open issues and current dependency edges before each edge write, or recursively expand the reachable dependency graph.
  - From cursor-specialist-edge-cases-output.txt: Re-fetch full dependency graph or expand the issue set before each _revalidate_edge_before_write call and merge edges written earlier in the batch.
  - From codex-specialist-edge-cases-output.txt: Re-fetch the full current open-issue dependency graph before each edge write or traverse dependencies from the client until the blocker is found or exhausted.
  - From codex-specialist-testing-output.txt: Re-fetch the full open dependency graph or traverse dependencies transitively before each edge write
  - From dyn-deps-edge-rules-output.txt: Rebuild the full edge set at apply time the same way `fetch` does (all open issues, or at minimum a transitive closure over blockers/dependents for each edge), or persist `existing_edges` from plan and merge with a fresh full re-fetch before each `_revalidate_edge_before_write` call.
  - From dyn-deps-cli-tests-output.txt: Before the edge loop, re-fetch dependency edges for all open issues (or reuse a fresh `deps fetch` snapshot) and run `_revalidate_edge_before_write` against that complete edge set.


### FINDING_2: Python does not enforce --pair-cap / skipped_latent_pairs for audit completion
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-deps-cli-tests-output.txt
- **Severity**: important
- **Concern**: Partial-audit completion depends on prompt-supplied `skipped_latent_pairs`; Python does not verify that latent pairing was actually capped under `--pair-cap`. If the orchestrator omits or under-reports `skipped_latent_pairs`, `audit_complete` can stay true and dependency writes proceed on an incomplete latent audit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-deps-cli-tests-output.txt: Have `deps plan` compute or cross-check latent skip metadata (for example require `pair_cap` and `skipped_latent_pairs` together, or reject `--pair-cap` unless proposals carry a matching `pair_cap_applied` field), and add a test for the `partial_audit_approved=true` approval path.


### FINDING_3: Partial-audit approval parsing is fail-open on loose types
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Partial-audit gating uses truthiness and loose count parsing instead of fail-closed schema validation. With `--pair-cap` set, `partial_audit_approved` as the string `"false"` or `skipped_latent_pairs` as a non-integer string can unlock `dependency_writes_allowed` and allow dependency writes without explicit partial approval.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Require partial_audit_approved is True exactly and validate skipped_latent_pairs as a non-negative integer.
  - From codex-specialist-testing-output.txt: Require strict JSON types and treat only boolean true as approval; fail closed on malformed partial-audit fields


### FINDING_4: apply_main ignores plan dependency_writes_allowed
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-deps-safety-output.txt, dyn-deps-edge-rules-output.txt, dyn-deps-cli-tests-output.txt
- **Severity**: important
- **Concern**: `apply_main` writes all `edges_to_write` without checking `plan["dependency_writes_allowed"]`. A stale or hand-edited `plan.json` can reintroduce edges while `dependency_writes_allowed=false`, bypassing the partial-audit gate and the `--pair-cap` contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-deps-safety-output.txt: In `apply_main`, refuse edge writes when `plan.get("dependency_writes_allowed")` is false unless an explicit partial-audit approval sentinel is supplied; treat any mismatch between that flag and non-empty `edges_to_write` as fail-closed.
  - From dyn-deps-edge-rules-output.txt: Fail closed at the start of the edge-apply loop: if `plan.get("dependency_writes_allowed") is False`, skip every edge with reason `partial-audit block` (and do not call `block-issue`), matching `plan_main` behavior.
  - From dyn-deps-cli-tests-output.txt: In `apply_main`, refuse edge writes unless `plan.get("dependency_writes_allowed") is True`; return a structured skip/error when `edges_to_write` is non-empty but the flag is false.


### FINDING_5: fetch.json and issue-bodies bypass untrusted delimiter boundary
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, dyn-deps-safety-output.txt
- **Severity**: blocking
- **Concern**: `deps fetch` persists full raw issue bodies and comments in `fetch.json` and plaintext `issue-bodies/issue-*.md`, while `skills/deps/SKILL.md` tells the prompt to read `fetch.json`. A malicious issue body can reach in-model reasoning outside `<deps_issue_N>` delimiter blocks, bypassing the intended untrusted corpus boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-deps-safety-output.txt: Keep machine-only body storage for `explicit-refs` (or read from wrapped corpus internally), omit or HTML-escape body fields in operator-facing `fetch.json`, delete or chmod-restrict plaintext `issue-bodies/` after corpus build, and tighten the skill to reason only from `untrusted_corpus_file`.


### FINDING_6: apply cannot validate mutation targets against fetch snapshot
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `deps apply` cannot validate mutation targets against the fetch snapshot because the plan lacks snapshot membership and apply has no fetch-file input. A status-ok plan for open mutable issue #123 can edit #123 even if #123 was not in the original fetch snapshot.
- **Suggested revisions (informational for voters; coder decides)**:


### FINDING_7: REGULAR rewrite/close eligibility not mechanically enforced in plan/apply
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Rewrite and close planning does not mechanically enforce origin/repo alignment and origin/main refresh eligibility. On repo mismatch or failed main refresh, prompt-side instructions say to skip rewrites, but deps plan still accepts them and deps apply can mutate the wrong repository's issues.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Carry regular_refresh_allowed into the plan contract and reject rewrites/closes unless alignment and main refresh succeeded


