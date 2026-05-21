```text
### FINDING_1: Misdocumented `emit_breadcrumb` / quiet routing in `apply-bump.md`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-retry-semantics-output.txt, dyn-test-stub-fidelity-output.txt, dyn-breadcrumb-routing-output.txt
- **Concern**: Contract text misstates how retry breadcrumbs route relative to `scripts/lib-quiet.md` / `emit_breadcrumb` (FD1 quiet log vs caller-visible `emit`/FD3 when `LARCH_QUIET_BREADCRUMBS=1`, and how `LARCH_QUIET_DISABLE=1` affects harness captures). Risks wrong operator expectations and wrong integration assumptions (e.g., `ship-pr` capture patterns, teeing only FD3).
- **Suggested revision**: Rewrite the invariant to match `scripts/lib-quiet.md` (and explicitly separate contract `emit`/`emit_kv` stream vs breadcrumb routing), including harness note for `LARCH_QUIET_DISABLE=1` if relevant.

### FINDING_2: [OUT_OF_SCOPE] Stale `apply-bump.sh` header “contract” vs retry-loop behavior
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-retry-semantics-output.txt, dyn-breadcrumb-routing-output.txt, cursor-specialist-security-output.txt
- **Concern**: Top-of-file comments still describe immediate fail-closed origin same-version/regression handling and related exit semantics, but implementation now retries until cap exhaustion with a different terminal `ERROR=` shape; misleads maintainers skimming headers.
- **Suggested revision**: Update header comments to match retry cap, which failures retry vs hard-abort, and final exhaustion error string/shape (coordinate with any “touch header on future edit” guidance if this stays deferred).

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

### FINDING_6: [OUT_OF_SCOPE] Bump-version SKILL + operator runbooks stale vs new apply-bump contract
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Concern**: `.claude/skills/bump-version/SKILL.md` “How it works” / ERROR strings / Step 8 routing still reflect older fail-fast semantics (no internal retry / older terminal errors), risking orchestration assumptions and operator confusion relative to `apply-bump.sh` behavior.
- **Suggested revision**: Refresh SKILL documentation for retry loop, new terminal errors, and when downstream sub-procedures still apply (likely follow-up PR).

### FINDING_7: [OUT_OF_SCOPE] `rebase-rebump-subprocedure.md` contract/examples stale post-retry loop
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Concern**: Subprocedure text still centers older same-version `ERROR` literals/trigger framing, misleading rare-path runbooks after in-script retries absorb most races.
- **Suggested revision**: Update triggers and literal `ERROR` examples to match the post-retry `apply-bump.sh` contract when editing that doc.

### FINDING_8: `scripts/ship-pr.sh` pattern match / stall routing may not fit new bump-race exhaustion
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: New cap-exhaustion `ERROR` may no longer align with existing exit-5 “same-version recovery” parsing assumptions; could route stalls differently than prior behavior unless patterns/docs/tests are updated consistently.
- **Suggested revision**: Extend/adjust case patterns and tests if exit-5 recovery remains desired; otherwise explicitly document the new stall routing and update matchers accordingly.

### FINDING_9: Missing strict semver validation for `ORIGINAL_CURRENT_VERSION` before retry inference
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: `ORIGINAL_CURRENT_VERSION` read via `jq` may be empty/invalid while JSON remains “valid enough,” causing `_infer_bump_type` / arithmetic paths to misbehave or become brittle under `set -e`.
- **Suggested revision**: Validate non-empty `^[0-9]+\\.[0-9]+\\.[0-9]+$` (or reuse classify output) before inferring bump type inside the retry loop.

### FINDING_10: Retry recompute assumes a single semver step from original→initial bump type
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Collision retries re-derive only MAJOR/MINOR/PATCH from the original→initial pair, not a full numeric delta; if classification ever implied multi-step jumps, retries could undershoot until many collisions/cap exhaustion.
- **Suggested revision**: Document the single-increment assumption explicitly, or re-invoke `classify-bump` after fetch instead of coarse type inference.

### FINDING_11: `assert_stdout_match_count` portability risk for expected count 0
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: `grep ... || echo 0` style counting can mishandle zero-match cases across grep implementations (double-print / wrong count).
- **Suggested revision**: Replace with a portable counting idiom safe for zero expected matches.

### FINDING_12: Harness stub JSON built via `printf` with raw sequence data
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Today trusted, but widened inputs could break JSON shape or confuse `jq` in tests.
- **Suggested revision**: Constrain fixtures to digit-only semver components or emit JSON via `jq --arg`.

### FINDING_13: Breadcrumb line format diverges from plan Sub-test O regex
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Implemented breadcrumb text does not match the plan’s exact format (automation/checklists keyed to plan strings may false-fail despite passing tests).
- **Suggested revision**: Align implementation to the plan’s format, or formally amend the plan and dependent requirements/checklists.

### FINDING_14: Extra human-oriented lines on FD1 during retries when quiet is disabled
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Legacy “parse full stdout” integrations may need to tolerate non-`emit_kv` lines mixed with contract output when quiet redirection is off.
- **Suggested revision**: Document that FD1 may include breadcrumb lines outside the strict contract stream in that mode.

### FINDING_15: [OUT_OF_SCOPE] `docs/linting.md` harness catalog understates `test-apply-bump` coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-retry-semantics-output.txt
- **Concern**: Linting inventory row still markets the harness as primarily same-version rollback-centric vs newer retry/cap/sequence coverage; stale relative to current harness scope.
- **Suggested revision**: Update the row when editing `docs/linting.md` for harness inventory.

### FINDING_16: [OUT_OF_SCOPE] Pre-existing `emit_breadcrumb` interaction in `lib-quiet.sh`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Potential routing nuance when `LARCH_QUIET_BREADCRUMBS` is set without `LARCH_QUIET_BREADCRUMB_FD` (global contract tightening likely separate scope).
- **Suggested revision**: No change required for this PR unless explicitly tightening global `emit_breadcrumb` semantics.

### FINDING_17: Sequence fixture advancement uses `|| true`, risking silent stub desync
- **Reviewer(s)**: dyn-test-stub-fidelity-output.txt
- **Concern**: `tail`/`mv` steps that advance the origin-version sequence file ignore failures; stub may consume a line while the sequence file does not advance, replaying versions and weakening K–O ordering guarantees (possible false pass / wrong counts).
- **Suggested revision**: Make sequence advancement fail-closed (drop `|| true`, check exits, exit stub with a clear error on desync).
```
