### FINDING_1: finalize() drops quiet-mode contract KVs
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-artifact-contract-output.txt, dyn-tier4-state-machine-output.txt
- **Severity**: important
- **Concern**: `finalize()` emits revise contract KVs through stdout/`tee` instead of `emit_kv`, so quiet-mode FD 3 routing can be bypassed. `plan-review-loop.sh` may parse an empty revise output and report revision failure even after a successful apply or tier-4 fallback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-artifact-contract-output.txt, dyn-tier4-state-machine-output.txt: Address the concern above.

### FINDING_2: Missing invalid-patch tiers 1-3 plus tier-4 success harness
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The harness does not cover corrupt or invalid unified-diff outputs from tiers 1-3 followed by a successful tier-4 file replacement, leaving the #3143/#3146 rescue path under-tested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_3: Python extraction policy diverges from planned awk strip
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `extract_patch` is implemented as a larger Python helper with selection behavior beyond the planned awk preamble strip, adding a dependency and creating plan-fidelity ambiguity around multi-patch outputs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

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

### FINDING_7: [OUT_OF_SCOPE] REVISE_WINNING_TIER missing from documented KV list
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `REVISE_WINNING_TIER` is emitted but not listed in the sibling documentation’s numbered KV contract, creating doc drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] Missing original unfenced preamble regression case
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: There is no harness case for an unfenced prose preamble before `--- a/plan.txt`, leaving the original Cursor-shaped bug scenario under-covered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_9: Unified-diff extraction selects first fenced patch over later valid patch
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Multi-patch LLM output can select the first fenced canonical diff even when a later patch is the valid intended one, causing failed revisions or attacker-chosen hunks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt: Address the concern above.

### FINDING_10: git apply --recount may loosen live apply semantics
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Using `git apply --recount` for live apply may accept corrupt hunks that strict apply would reject, unexpectedly mutating `plan.txt`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_11: Tier-4 fallback is not surfaced as degraded after earlier validation failures
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: After invalid-patch tiers, tier 4 can fully rewrite `plan.txt` and continue as `ok-fallback` without clearly surfacing degraded confidence in Gate B.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] LARCH_PLAN_REVIEW_REVISE_SH override can point at arbitrary code
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: The pre-existing `LARCH_PLAN_REVIEW_REVISE_SH` test hook can redirect the revise path to arbitrary code with tmpdir access if not documented or cleared in production paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] Gate B copy omits ok-fallback distinction
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Gate B operator-facing copy does not distinguish `ok-fallback`, so operators may not notice that tier 4 performed a full replacement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_14: Artifact naming diverges from planned output reuse
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The branch adds `*-fallback-output.txt` artifacts and expands publish allowlists, while the plan required reusing `codex/cursor/claude-output.txt`; operators and docs following the plan will see different artifact paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_15: merge_tier4_status lacks plan-precedence harness coverage
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-tier4-state-machine-output.txt
- **Severity**: latent
- **Concern**: `merge_tier4_status` uses numeric ranks rather than the documented case table. Reviewers disagree on whether behavior is currently correct, but both point to missing regression coverage for precedence invariants.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt, dyn-tier4-state-machine-output.txt: Address the concern above.

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

### FINDING_19: [OUT_OF_SCOPE] Unified-diff cases 14-16 match current implementation
- **Reviewer(s)**: dyn-patch-extraction-output.txt
- **Severity**: nit
- **Concern**: The reviewer notes that cases 14-16 align with the current first-fenced / last-unfenced extraction implementation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-patch-extraction-output.txt: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] Unfenced trailing narration becomes invalid-patch
- **Reviewer(s)**: dyn-patch-extraction-output.txt
- **Severity**: nit
- **Concern**: Unfenced unified-diff extraction keeps trailing lines until EOF, which can classify trailing narration as `invalid-patch` rather than silently misapplying.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-patch-extraction-output.txt: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] merge_tier4_status rank merge matches documented severity order
- **Reviewer(s)**: dyn-patch-extraction-output.txt
- **Severity**: nit
- **Concern**: The reviewer reports that the rank merge matches the documented severity order after the round-1 refactor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-patch-extraction-output.txt: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] Implement-run artifacts are unrelated noise
- **Reviewer(s)**: dyn-patch-extraction-output.txt, dyn-artifact-contract-output.txt
- **Severity**: nit
- **Concern**: Implement-run artifacts under `larch-logs/implement/3F2B5CF2-.../` are operational noise rather than part of the revise logic or #3146 fix surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-patch-extraction-output.txt, dyn-artifact-contract-output.txt: Address the concern above.

### FINDING_23: docs/run-logs.md omits new tier-4 fallback artifacts
- **Reviewer(s)**: dyn-artifact-contract-output.txt
- **Severity**: important
- **Concern**: The design run-log catalog still lists only the original revise artifacts, while publish/snapshot allowlists now include tier-4 fallback outputs and derived candidate patch names.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-contract-output.txt: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] Tier-4 artifact names are internally consistent
- **Reviewer(s)**: dyn-artifact-contract-output.txt
- **Severity**: nit
- **Concern**: Tier-4 fallback artifact names are internally consistent across implementation, allowlists, docs, and tests, though they deliberately diverge from the issue plan’s reuse strategy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-contract-output.txt: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] prompt.txt overwrite is documented
- **Reviewer(s)**: dyn-artifact-contract-output.txt
- **Severity**: nit
- **Concern**: Tier 4 overwrites published `prompt.txt` with the file-replacement prompt, and the reviewer reports this is documented and included in snapshot/publish by design.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-contract-output.txt: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] revise-plan doc uses generic candidate patch name
- **Reviewer(s)**: dyn-artifact-contract-output.txt
- **Severity**: nit
- **Concern**: `revise-plan-with-waterfall.md` lists `<tier>-candidate.patch`, while tier 4 writes names like `codex-fallback-output-candidate.patch` covered by `*-candidate.patch`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-contract-output.txt: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] Acceptance notes missing REVISE_TIER_4_STATUS test coverage
- **Reviewer(s)**: dyn-artifact-contract-output.txt, dyn-tier4-state-machine-output.txt
- **Severity**: nit
- **Concern**: Out-of-scope reviewers also noted acceptance required `REVISE_TIER_4_STATUS` assertions in all cases, while only a subset assert it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-contract-output.txt, dyn-tier4-state-machine-output.txt: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] Tier-4 absent-tools path lacks harness coverage
- **Reviewer(s)**: dyn-tier4-state-machine-output.txt
- **Severity**: nit
- **Concern**: When CodeX and Cursor are absent and Claude returns empty, tier 4 reports `no-patch` rather than `skipped-not-present`; this follows severity ordering but lacks a dedicated harness case.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-tier4-state-machine-output.txt: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] Regression provenance identified in branch commits
- **Reviewer(s)**: dyn-tier4-state-machine-output.txt
- **Severity**: nit
- **Concern**: The reviewer attributes the `printf|tee` finalize regression and separate fallback artifacts to commit `e9490962`, not the initial tier-4 design commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-tier4-state-machine-output.txt: Address the concern above.
