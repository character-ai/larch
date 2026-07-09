# Review Round 2

- Mode: `diff`
- 4 accepted, 3 rejected (0 neutral)

## Accepted Findings

### FINDING_2: commit-route invalidation recomputes from a different manifest path
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-scope-gate
- **Severity**: major
- **Concern**: Coverage compute in commit-route resolves one manifest path, but stale-disposition invalidation passes a different hardcoded path. That can make `todos_left` and fingerprint recomputation disagree, so disposition requirements can be missed or become stale.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-scope-gate: "Pass the same resolved `manifest_path` variable into `invalidate_stale_disposition`."


### FINDING_3: raw todos_left entries should drive the disposition gate
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-plan-fidelity-auto, dyn-dyn-scope-gate
- **Severity**: major
- **Concern**: `disposition_required` is derived from the sanitized/truncated `todos_left` tuple, not the raw manifest list. Empty-string or whitespace-only entries can be filtered away, which lets a non-empty manifest `todos_left` list skip the disposition trigger.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: "Trigger disposition from raw manifest todos_left length before sanitization; keep sanitization for display/inventory output"
  - From cursor-specialist-plan-fidelity-auto: "Trigger disposition_required from raw list count; keep sanitization for display/fingerprint only."
  - From dyn-dyn-scope-gate: "Base `disposition_required` and fingerprint `todos_left` on a durable raw-entry count (with bounded text only for display), so any non-empty manifest `todos_left` keeps the gate live."


### FINDING_8: existing PR refresh can leave a stale closing footer
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: Existing PR refresh can preserve an old `Closes #N` footer because the remote body isn't compared against the final linked body or specifically refreshed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: "Compare remote_body to the final linked body or specifically refresh the issue footer and deferred-inventory section"


### FINDING_12: main-agent fallback returns before the required baseline is written
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: The main-agent fallback can return before writing the baseline required by the new scope-disposition compute fence, so the later pre-Step-3 compute command sees a missing baseline.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: "Write the baseline before early claude_fallback returns or use a Step 0 baseline for main-agent and recovery coverage."


