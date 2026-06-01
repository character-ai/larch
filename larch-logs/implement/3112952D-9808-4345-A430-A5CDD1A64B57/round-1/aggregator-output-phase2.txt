Normalized aggregator output from the supplied reviewer slots (plain text; no empty-merge attestation).

### FINDING_1: Step 0 prose still describes session-env.sh for CLAUDE_PLUGIN_ROOT
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Step 0 narrative still says rehydrate `CLAUDE_PLUGIN_ROOT` from `session-env.sh`, while executable blocks use `plugin-root.env` plus `read-session-env-key.sh` for other keys. Orchestrators may follow stale prose and reintroduce awk-at-post-Step-0.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
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

### FINDING_6: Duplicated CLAUDE_PLUGIN_ROOT validation in write-session-env.sh
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `emit_plugin_root_env` and the argv0 path duplicate `CLAUDE_PLUGIN_ROOT` validation in `scripts/write-session-env.sh:39-60`, risking future drift if only one path is updated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: Preflight indented bash fences use CLAUDE_PLUGIN_ROOT without plugin-root rehydration
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Preflight indented bash fences at `skills/implement/SKILL.md:205-210,797-798` use `CLAUDE_PLUGIN_ROOT` without the post-Step-0 `plugin-root.env` pattern; Invariant C skips indented fences. If inherited env were missing before Step 0, plan-block-read / larch-log fences could mis-resolve (pre-existing, not widened by this PR).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_8: SECURITY.md still describes awk-only plugin-root recovery
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `SECURITY.md` still documents awk-only parsing and forbids sourcing for plugin-root rehydration, while `/implement` now sources `plugin-root.env` at scale. Security reviewers may underestimate tmpdir `source` execution and the trust model relative to non-sourceable `session-env.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_9: plugin-root.env sourced with -f only, no symlink hardening
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Post-Step-0 rehydration sources `plugin-root.env` with `-f` only, without regular non-symlink checks used elsewhere for sensitive tmpdir reads. Same-UID tmpdir tampering or TOCTOU could turn rehydration into arbitrary shell execution, worse than prior awk-only extraction from `session-env.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_10: Pre-bootstrap export CLAUDE_PLUGIN_ROOT cardinality no longer checked
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-implement-timing-rehydration.sh` removed export-count parity; a pre-bootstrap fence could drop `export CLAUDE_PLUGIN_ROOT` while keeping source+awk lines, breaking same-fence `${CLAUDE_PLUGIN_ROOT}/` calls until a later block exports.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: Sourcing write-session-env.sh on resume-tail lacks errexit/argv0 guards in tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: No assertion that sourcing `write-session-env.sh` during resume-tail avoids errexit leak or accidental argv0 execution. A top-level `set -e` or guard regression could abort `implement-bootstrap` on benign helper failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: Corrupt plugin-root.env can fail source without fallback
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Truncated or tampered `plugin-root.env` can make the source line fail; unlike legacy awk there is no `|| true` on the canonical path. A bad sibling may abort the fence or leave `CLAUDE_PLUGIN_ROOT` unset while later lines still call `${CLAUDE_PLUGIN_ROOT}/scripts/...`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_13: implement-bootstrap.md omits resume-tail plugin-root sync from idempotency section
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `plugin-root.env` resume sync is documented in the behavior-mapping table but not under `## Resume-tail idempotency`, so auditors of resume idempotency may miss the legacy-tmpdir sibling emit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] Pre-Step-0 SKILL prose uses CLAUDE_PLUGIN_ROOT without fence rehydration
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Pre-Step-0 prose at `skills/implement/SKILL.md:12,91` uses `CLAUDE_PLUGIN_ROOT` without fence rehydration; pre-existing, relies on plugin env at session start. No change required for this PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] Invariant C fence matcher lacks whitespace tolerance for indented bash
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Invariant C in `scripts/test-implement-timing-rehydration.sh` only matches `^```bash$` openers, not indented fence markers. Indented Preflight/helper snippets using `CLAUDE_PLUGIN_ROOT` are not checked for rehydration adjacency (pre-existing).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] Resume-tail never refreshes stale plugin-root.env when session-env changes
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Resume sync is create-if-missing only; it does not re-emit when `session-env.sh` `LARCH_CLAUDE_PLUGIN_ROOT` diverges from an existing `plugin-root.env`. Hand-edited or inconsistent pairs could leave post-Step-0 blocks on a cached sibling while other keys are read fresh from `session-env.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

**Merge notes (for voters, not part of machine output):** Input items 28 (`[OUT_OF_SCOPE]` G.4 isolation) were subsumed into FINDING_5 as the same testing gap with optional framing; no separate block. Eight distinct in-scope themes plus three `[OUT_OF_SCOPE]` blocks; 28 raw inputs → 16 aggregated blocks.
