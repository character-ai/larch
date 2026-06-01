# Review Round 1

- Mode: `diff`
- 7 accepted, 6 rejected (6 exonerated)

## Accepted Findings

### FINDING_1: Step 0 prose still describes session-env.sh for CLAUDE_PLUGIN_ROOT
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Step 0 narrative still says rehydrate `CLAUDE_PLUGIN_ROOT` from `session-env.sh`, while executable blocks use `plugin-root.env` plus `read-session-env-key.sh` for other keys. Orchestrators may follow stale prose and reintroduce awk-at-post-Step-0.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_13: implement-bootstrap.md omits resume-tail plugin-root sync from idempotency section
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `plugin-root.env` resume sync is documented in the behavior-mapping table but not under `## Resume-tail idempotency`, so auditors of resume idempotency may miss the legacy-tmpdir sibling emit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_2: Dirty-tree routing table still references session-env-only rehydration
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The dirty-tree routing table at `skills/implement/SKILL.md:446` still tells operators to recover `CLAUDE_PLUGIN_ROOT` from `session-env.sh`, diverging from the source+awk / `plugin-root.env` pattern in adjacent Bash fences. Recovery guidance may omit the canonical sibling emit path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_3: write-session-env.md contradicts plugin-root.env consumer contract
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `scripts/write-session-env.md` still implies `/implement` recovers `CLAUDE_PLUGIN_ROOT` from `session-env.sh` for all blocks. Readers may miss the dual-output model: `LARCH_CLAUDE_PLUGIN_ROOT` in `session-env.sh` for resume/bootstrap, `plugin-root.env` sourcing post-Step-0 in the SKILL.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_4: Resume-tail may leave post-Step-0 without a verified plugin-root.env
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Under no-errexit bootstrap, `implement-bootstrap.sh` resume-tail calls `emit_plugin_root_env` but does not reliably ensure `plugin-root.env` exists when `LARCH_CLAUDE_PLUGIN_ROOT` is set. Emit/mktemp/mv failure or skip leaves no sibling while `session-env.sh` may still hold a valid key; ~37 post-Step-0 SKILL sites source-only with no awk fallback, so `CLAUDE_PLUGIN_ROOT` stays empty and `${CLAUDE_PLUGIN_ROOT}/...` helper paths break silently on legacy resume.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_5: Resume-tail plugin-root.env sync lacks integration test coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: New resume-tail `plugin-root.env` sync in `implement-bootstrap.sh` is not exercised end-to-end. `G.4` and related harnesses test `emit_plugin_root_env` in isolation; bootstrap-specific guard/sourcing/wiring regressions could pass CI while legacy session-env-only tmpdirs resume without a correct sibling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Add a resume-plan-tail harness case: session-env-only legacy tmpdir, assert plugin-root.env is created with correct value, sources cleanly, and is idempotent on repeat resume-tail.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_8: SECURITY.md still describes awk-only plugin-root recovery
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `SECURITY.md` still documents awk-only parsing and forbids sourcing for plugin-root rehydration, while `/implement` now sources `plugin-root.env` at scale. Security reviewers may underestimate tmpdir `source` execution and the trust model relative to non-sourceable `session-env.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


