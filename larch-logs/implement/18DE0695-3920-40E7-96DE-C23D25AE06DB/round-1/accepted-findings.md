### FINDING_1: Misdocumented `emit_breadcrumb` / quiet routing in `apply-bump.md`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-retry-semantics-output.txt, dyn-test-stub-fidelity-output.txt, dyn-breadcrumb-routing-output.txt
- **Concern**: Contract text misstates how retry breadcrumbs route relative to `scripts/lib-quiet.md` / `emit_breadcrumb` (FD1 quiet log vs caller-visible `emit`/FD3 when `LARCH_QUIET_BREADCRUMBS=1`, and how `LARCH_QUIET_DISABLE=1` affects harness captures). Risks wrong operator expectations and wrong integration assumptions (e.g., `ship-pr` capture patterns, teeing only FD3).
- **Suggested revision**: Rewrite the invariant to match `scripts/lib-quiet.md` (and explicitly separate contract `emit`/`emit_kv` stream vs breadcrumb routing), including harness note for `LARCH_QUIET_DISABLE=1` if relevant.


### FINDING_17: Sequence fixture advancement uses `|| true`, risking silent stub desync
- **Reviewer(s)**: dyn-test-stub-fidelity-output.txt
- **Concern**: `tail`/`mv` steps that advance the origin-version sequence file ignore failures; stub may consume a line while the sequence file does not advance, replaying versions and weakening K–O ordering guarantees (possible false pass / wrong counts).
- **Suggested revision**: Make sequence advancement fail-closed (drop `|| true`, check exits, exit stub with a clear error on desync).
```

### FINDING_3: `scripts/test-apply-bump.md` purpose line understates new harness scope
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Concern**: Opening “Purpose” still reads rollback/same-version-centric vs expanded collision-retry / sequence coverage (e.g., K–O) now present in the same doc.
- **Suggested revision**: Broaden the purpose sentence to include retries/cap exhaustion and sequence fixtures without overstating assertions not enforced.


### FINDING_4: `apply-bump.md` harness summary still reads rollback-only
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Concern**: Maintainer-facing harness paragraph/catalog implies rollback-only coverage for same-version/regression paths, diverging from actual `scripts/test-apply-bump.md` behavior and updated C/H semantics.
- **Suggested revision**: Rewrite harness summary to reflect retries, success paths, and K–O fixtures consistently with the test doc.


### FINDING_5: `scripts/test-apply-bump.md` claims vs missing breadcrumb assertions (C/H)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Coverage text implies breadcrumb-on-stdout assertions for cases including C/H, but those tests do not assert breadcrumbs—so doc overpromises and regressions could slip silently.
- **Suggested revision**: Either add breadcrumb assertions to C/H (if meaningful) or trim coverage claims to match what is actually asserted.


### FINDING_9: Missing strict semver validation for `ORIGINAL_CURRENT_VERSION` before retry inference
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: `ORIGINAL_CURRENT_VERSION` read via `jq` may be empty/invalid while JSON remains “valid enough,” causing `_infer_bump_type` / arithmetic paths to misbehave or become brittle under `set -e`.
- **Suggested revision**: Validate non-empty `^[0-9]+\\.[0-9]+\\.[0-9]+$` (or reuse classify output) before inferring bump type inside the retry loop.


