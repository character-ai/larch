### FINDING_1: Dirty-tree resume-tail recovery fence missing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Dirty-tree recovery in `skills/implement/SKILL.md` no longer provides an executable fenced bootstrap recipe for `implement-bootstrap.sh --up-to-phase coder --resume-plan-tail`, leaving `IMPLEMENT_BAIL_REASON=dirty-tree` recovery under-specified and unpinned by structure tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: SECURITY.md omits narrow Cursor-first scope and Codex-first fixer adjacency
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `SECURITY.md` does not clearly document that the Cursor-first reversal applies only to `/implement` Step 0 omitted-coder routing, while fixer paths remain Codex-first and operators can pin Codex with `--coder=codex`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_3: Bootstrap harness lacks planned coder-skip and B4/B5 guard coverage
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `skills/implement/scripts/test-implement-bootstrap.sh` does not cover plan-required coder-skip cases for repo unavailable or missing plan, and B4/B5 all-phase cases do not assert coder KV and breadcrumb behavior across deferred and stall paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_4: Explicit-coder availability branch coverage is incomplete
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Explicit coder availability tests cover only part of the tri-state surface; undeterminable binary state, runtime-probe-failed, explicit Codex unavailable, and explicit Codex/Claude happy paths can regress silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_5: Implicit Claude fallback harness lacks warning and manifest assertions
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `B5-coder-implicit-claude` does not assert stderr, execution-issues, or `coder_fallback` manifest invoke behavior, so warning/report regressions can pass while KV output still succeeds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_6: Step 2.4 warning logic still uses stale explicit/fallback semantics
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `skills/implement/SKILL.md` Step 2.4 warning text still depends on stale or undefined explicit-coder semantics instead of the planned `coder_fallback` KV plus argv-level explicit coder signal, which can mislead operators for explicit `--coder=claude` and fallback cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_7: Structure harness lacks planned Session Setup and resume-tail pins
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `scripts/test-implement-structure.sh` does not include the planned narrowed Session Setup structural pins, foreground banner/coder fallback checks, or exact single `--up-to-phase coder --resume-plan-tail` assertion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_8: Step 2 routing documentation pins are incomplete
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-implement-step2-routing.sh` pins routing order only in `SKILL.md` and does not guard `scripts/implement-bootstrap.md` or stale Step 2.4 explicit-coder wording from reappearing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] Unrelated write-final-report changes are included
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `skills/implement/scripts/write-final-report.sh` changes appear unrelated to Phase 4 and increase the PR’s lint/CI blast radius.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: Step 2 cursor-present mismatch silently falls back to Claude
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `skills/implement/scripts/step2-implement.sh` still falls back from cursor to Claude when `--cursor-present=false`, bypassing Step 0 `coder_fallback` semantics and warnings if session env degrades after bootstrap selected cursor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_11: phase_coder_select has unused presence reads that can drift from routing state
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `scripts/implement-bootstrap.sh` reads `CODEX_PRESENT` and `CURSOR_PRESENT` but routes using separate availability variables, creating a future drift risk between tri-state warnings and actual coder selection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] CHANGELOG.md still describes Codex-first default
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `CHANGELOG.md` Unreleased text conflicts with SECURITY/bootstrap Cursor-first omitted-coder behavior, creating inconsistent operator guidance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] Cross-Skill Presence Propagation subsection removed
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The planned Cross-Skill Presence Propagation contract was removed from `skills/implement/SKILL.md` without an equivalent pinned relocation, weakening documentation of first-boundary env propagation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] Design workflow changes are outside Phase 4
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `skills/design/SKILL.md` includes Gate A/C full-plan changes outside the Phase 4 plan and should be tracked separately from #2738 acceptance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
