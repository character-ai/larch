# Review Round 3

- Mode: `diff`
- 6 accepted, 3 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Partial-audit metadata bypass via tampered or incomplete plan.json
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-deps-safety-output.txt, dyn-deps-edge-rules-output.txt
- **Severity**: important
- **Concern**: `_dependency_writes_allowed_from_plan` and related partial-audit completion logic treat `audit_complete` as true when `pair_cap` is absent, defaulting missing `counts.skipped_latent_pairs` to 0. A partial-audit plan with latent pairs skipped can be tampered between `deps plan` and `deps apply` (for example by deleting `counts`, removing `pair_cap`, or setting `dependency_writes_allowed=true`) so `deps apply` writes dependency edges that the partial audit had blocked. `skipped_latent_pairs > 0` must remain authoritative partial-audit metadata even when `pair_cap` is missing; apply must fail closed on inconsistent or missing metadata.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-deps-safety-output.txt: Treat `skipped_latent_pairs > 0` as partial-audit metadata even when `pair_cap` is missing (for example require `pair_cap` whenever `skipped_latent_pairs > 0`, or derive `audit_complete` from `skipped_latent_pairs > 0` alone). Fail closed at apply when partial-audit metadata and `dependency_writes_allowed` disagree.
  - From dyn-deps-edge-rules-output.txt: Fail closed when `skipped_latent_pairs > 0` and `pair_cap` is missing; set `audit_complete = (skipped_latent_pairs == 0)` (and mirror that in apply revalidation) so partial-audit metadata cannot be bypassed by omitting `--pair-cap`.


### FINDING_2: apply_main exits 0 despite failed mutations
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `apply_main` always returns exit code 0 even when the `failed` list is non-empty (for example when all `gh issue edit` calls fail). Shell wrappers and orchestrators treat the run as successful instead of surfacing mutation failure.
- **Suggested revisions (informational for voters; coder decides)**:


### FINDING_4: Outbound rewrite sanitization weaker than issue_wire helpers
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-deps-safety-output.txt
- **Severity**: important
- **Concern**: `_sanitize_outbound_body()` uses a local regex (for example `<!--\s*larch:`) plus generic `redact.redact()` instead of the fuller `issue_wire` marker neutralization specified in the plan and `SECURITY.md`. Malformed or partial `larch:*` control markers may survive into posted issue bodies and confuse downstream `/design` or `/implement` parsers. There is no test asserting successful-write sanitization on bodies passed to `gh issue edit`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-deps-safety-output.txt: Route rewrite bodies through the same marker-stripping/neutralization helpers used by `issue_wire` plan writes before apply, strip entire `larch:*` blocks rather than prefix-substituting comment openers, and add apply tests that assert sanitized bodies passed to `gh issue edit`.


### FINDING_8: Stale live dependency graph reused across edges in one apply run
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: `deps apply` refreshes the live dependency graph only once, then reuses `live_edges_cached` for every later edge in the same apply run. If another dependency is added after the first planned edge is written but before the second is checked, the second edge is validated against stale graph data and can be written even though it is now a duplicate or creates a cycle.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Move `_full_open_dependency_edges(args.repo)` inside the per-edge loop immediately before `_revalidate_edge_before_write`, or refresh `live_edges_cached` before each edge write. Add a test where the second graph refresh contains a new cycle or duplicate.


### FINDING_9: partial_audit_approved is self-asserted JSON with no mechanical operator link
- **Reviewer(s)**: dyn-deps-safety-output.txt, dyn-deps-edge-rules-output.txt, dyn-deps-cli-tests-output.txt
- **Severity**: important
- **Concern**: `partial_audit_approved` is a self-asserted JSON boolean with no mechanical link to Step 5's second `AskUserQuestion`. It can be set to `true` in `proposals.json` or `plan.json` (including before operator confirmation) so `deps plan` / `deps apply` allow dependency writes during an incomplete latent audit without documented operator opt-in. The approval gate exists only in skill prompt text.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-deps-safety-output.txt: Persist an operator confirmation artifact under `$DEPS_TMPDIR` (timestamped sentinel or HMAC over plan hash + audit metadata) and require `deps apply` to read it when `skipped_latent_pairs > 0`, or reject `partial_audit_approved=true` unless recomputed from a signed/plan-bound confirmation step.
  - From dyn-deps-edge-rules-output.txt: Reject `partial_audit_approved: true` unless `audit_complete` is already true, or accept it only via a dedicated plan flag set after Step 5 confirmation (for example `--partial-audit-approved`), not from raw proposals JSON on the first plan pass.
  - From dyn-deps-cli-tests-output.txt: Require a separate apply-time flag (for example `--partial-audit-edges-confirmed`) that the skill sets only after the second confirmation, or reject `partial_audit_approved: true` unless a signed sentinel from the approval step is present; do not rely on prompt-side discipline alone.


### FINDING_12: SKILL.md Step 1 does not fail closed on fetch failure
- **Reviewer(s)**: dyn-deps-cli-tests-output.txt
- **Severity**: important
- **Concern**: Step 1 runs `deps fetch` in a separate Bash block with no `set -e` and no instruction to stop on non-zero exit. `fetch_main` still writes `fetch.json` with `"status": "failed"` and returns `1` on `gh` failure, so the orchestrator can continue with an empty or misleading snapshot instead of failing closed before later steps.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-deps-cli-tests-output.txt: Add `set -euo pipefail` to Step 1 (and Step 4), abort when the CLI exits non-zero, and require `"status": "ok"` in `fetch.json` before Steps 2–4.


