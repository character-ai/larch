### FINDING_1: finalize() drops quiet-mode contract KVs
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-artifact-contract-output.txt, dyn-tier4-state-machine-output.txt
- **Severity**: important
- **Concern**: `finalize()` emits revise contract KVs through stdout/`tee` instead of `emit_kv`, so quiet-mode FD 3 routing can be bypassed. `plan-review-loop.sh` may parse an empty revise output and report revision failure even after a successful apply or tier-4 fallback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-artifact-contract-output.txt, dyn-tier4-state-machine-output.txt: Address the concern above.


### FINDING_14: Artifact naming diverges from planned output reuse
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The branch adds `*-fallback-output.txt` artifacts and expands publish allowlists, while the plan required reusing `codex/cursor/claude-output.txt`; operators and docs following the plan will see different artifact paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_16: extract_patch failure can abort waterfall under set -e
- **Reviewer(s)**: dyn-patch-extraction-output.txt
- **Severity**: latent
- **Concern**: `extract_patch` runs under `set -euo pipefail` without guarding the Python exit code, so an unhandled Python failure can abort the full waterfall instead of being treated as an empty/no-patch tier.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-patch-extraction-output.txt: Address the concern above.


### FINDING_17: Timestamped unified-diff headers are missed
- **Reviewer(s)**: dyn-patch-extraction-output.txt
- **Severity**: latent
- **Concern**: `find_diff_start()` requires exact `--- a/plan.txt` / `+++ b/plan.txt` header equality, so tab- or timestamp-suffixed git headers can be missed even though later validation would accept them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-patch-extraction-output.txt: Address the concern above.


### FINDING_18: File-replacement trailer outside fence is dropped
- **Reviewer(s)**: dyn-patch-extraction-output.txt
- **Severity**: latent
- **Concern**: In file-replacement mode, a fenced `## Plan` block with `diff_lines:` immediately after the closing fence can be dropped, causing spurious `no-patch` or validation failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-patch-extraction-output.txt: Address the concern above.


### FINDING_2: Missing invalid-patch tiers 1-3 plus tier-4 success harness
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The harness does not cover corrupt or invalid unified-diff outputs from tiers 1-3 followed by a successful tier-4 file replacement, leaving the #3143/#3146 rescue path under-tested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_23: docs/run-logs.md omits new tier-4 fallback artifacts
- **Reviewer(s)**: dyn-artifact-contract-output.txt
- **Severity**: important
- **Concern**: The design run-log catalog still lists only the original revise artifacts, while publish/snapshot allowlists now include tier-4 fallback outputs and derived candidate patch names.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-contract-output.txt: Address the concern above.


### FINDING_4: Missing REVISE_TIER_4_STATUS assertions across harness cases
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Acceptance requires `REVISE_TIER_4_STATUS` in every harness case, but many early-win or failure cases do not assert it, so regressions could silently drop the key.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_5: Wrong-path diffs classify as no-patch instead of invalid-patch
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Unified diffs targeting the wrong path are now classified as `no-patch` / `failed-no-patch`, hiding validation failures and changing legacy failure semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_6: File-replacement extraction may choose first illustrative plan
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Tier-4 file-replacement extraction prefers the first fenced `## Plan` block, so multi-plan responses can apply an illustrative or example plan instead of the final intended plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_9: Unified-diff extraction selects first fenced patch over later valid patch
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Multi-patch LLM output can select the first fenced canonical diff even when a later patch is the valid intended one, causing failed revisions or attacker-chosen hunks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt: Address the concern above.


