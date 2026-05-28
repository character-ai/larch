### FINDING_1: Dirty-tree resume recovery loses bootstrap argv and KV state
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Dirty-tree recovery in `skills/implement/SKILL.md` reuses state from the primary Step 0 Bash fence instead of rebuilding argv arrays, recovering `CLAUDE_PLUGIN_ROOT`, recapturing bootstrap output, and re-parsing KV. A separate recovery invocation can lose `--issue-number`, `--coder`, `--preflight-tmpdir`, or leave stale `IMPLEMENT_BAIL_REASON=dirty-tree`, causing resume failure or wrong Step 2/Step 18 routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_11: Dirty-tree resume tests stop before coder phase
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Dirty-tree resume harness coverage stops at `--up-to-phase plan`, so `--resume-plan-tail` regressions through `phase_coder_select` are not caught offline.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_15: B4-all lacks breadcrumb coverage for widened DEFERRED path
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `B4-all` does not assert the coder breadcrumb under `LARCH_QUIET_BREADCRUMBS=1`, leaving widened `DEFERRED` path breadcrumb behavior only partially covered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: Step 0 structural pins do not cover planned Session Setup invariants
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `scripts/test-implement-structure.sh` does not pin the full planned Step 0 structure: narrowed Session Setup anchors, session-local bootstrap fence count, `not-yet-implemented-phase-*` absence, bootstrap coder breadcrumb literal, standalone resume-tail count, and related documentation updates. Regressions could reintroduce prompt-side waterfall logic, phase stubs, extra bootstrap fences, or missing coder breadcrumbs without failing structure tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_3: Bootstrap harness lacks explicit Claude and missing-plan coder-skip cases
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `skills/implement/scripts/test-implement-bootstrap.sh` lacks planned cases for explicit `--coder=claude` with empty `coder_fallback` and non-`REPO_UNAVAILABLE` missing-plan coder skip. These gaps allow regressions where explicit Claude is treated as fallback, or Step 2 dispatch gets a coder without valid plan artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_5: phase_coder_select keeps unused presence-key reads
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `scripts/implement-bootstrap.sh` re-reads `CODEX_PRESENT` and `CURSOR_PRESENT` in `phase_coder_select` even though routing uses `codex_available` and `cursor_available`; only `*_BINARY_FOUND` reads are needed for explicit-coder tri-state warnings. The dead reads obscure the routing authority.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_6: Waterfall order pin targets the wrong authority
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `scripts/test-implement-step2-routing.sh` pins Cursor -> Codex -> Claude order against `SKILL.md`, while the canonical script contract lives in `scripts/implement-bootstrap.md` or `implement-bootstrap.sh`. The script-side routing contract could drift while lint still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_8: Missing runtime guard coverage for absent feature-description.txt
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The bootstrap harness does not test the `feature-description.txt` gate when `plan.txt` exists. Removing or breaking that runtime guard could still pass grep-only coverage while allowing Step 2 dispatch without a complete plan contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_9: Repo-unavailable coder skip lacks negative assertions
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `B5-coder-skip-repo-unavailable` does not assert absence of coder breadcrumbs or `coder-unavailable` bail state. Regressions in repo-unavailable skip behavior could go unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


