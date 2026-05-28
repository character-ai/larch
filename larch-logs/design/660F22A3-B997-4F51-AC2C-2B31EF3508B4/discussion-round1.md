## Decision 1: Scope — all three hardening items in one design
- **Question**: Should all 3 OOS items (lib-voter-coverage plan-coupling, --design-tmpdir validation, emit_kv newline safety) be addressed together, or scoped down?
- **Resolution**: All 3 items in scope for this single SIMPLE-tier design (matches issue body framing).
- **Source**: user

## Decision 2: Item 1 — rename functions/file with plan_ scope marker
- **Question**: How to address `voter_coverage_emit_status_block` plan-review-specific KV ordering coupling?
- **Resolution**: Rename `voter_coverage_*` functions and the file to `voter_coverage_plan_*` (or equivalent plan-prefixed names) and update the sibling `.md` doc. A future code-review caller hits a missing-function/file error instead of silent KV breakage.
- **Source**: user

## Decision 3: Item 1 — call-site update scope (single sourcer)
- **Question**: How many call-sites must update for the rename?
- **Resolution**: Exactly one production sourcer (`scripts/dispatch-plan-voters.sh:14-15`). One regression harness (`scripts/test-dispatch-plan-voters.sh`) exercises behavior through the dispatcher stdout contract, not direct sourcing. Doc siblings `lib-voter-coverage.md` and `dispatch-plan-voters.md` updated in the same PR per `.claude/rules/script-md-siblings.md`.
- **Source**: codebase

## Decision 4: Item 2 — shared helper + apply to ALL --design-tmpdir consumers
- **Question**: Apply path validation to just the 2 named scripts, all ~22 --design-tmpdir consumers, or a shared helper?
- **Resolution**: Extract a shared validator helper (`larch_design_tmpdir_validate` or similar) and apply it via a one-line guard at every --design-tmpdir consumer. User explicitly chose broadest hardening despite SIMPLE-tier minimum-change bias.
- **Source**: user

## Decision 5: Item 2 — validation strategy: realpath + prefix
- **Question**: realpath canonicalization, prefix validation, or both?
- **Resolution**: Both — canonicalize via realpath (resolve symlinks/.. segments) and check the resolved path begins with one of the documented session-tmpdir prefixes (`$HOME/.cache/larch/sessions/`, `$TMPDIR`, `/tmp`). Fail with a clear error on mismatch.
- **Source**: user

## Decision 6: Item 3 — reject embedded newlines in emit_kv
- **Question**: emit_kv newline safety strategy: reject, escape, or both?
- **Resolution**: Reject with `larch_err` + non-zero return. Forces callers to sanitize; preserves the single-line FD-3 contract.
- **Source**: user

## Decision 7: Item 3 — reject applies to all keys and values
- **Question**: Should the newline reject apply to all emit_kv calls, or only path-like keys?
- **Resolution**: All keys and values. Uniform one-line-per-key FD-3 invariant; matches the existing implicit contract that consumers parse with `while IFS= read -r`.
- **Source**: user

## Decision 8: Hard constraint — no behavioral regression for existing well-behaved callers
- **Question**: Must the emit_kv reject not break existing call-sites that pass clean values?
- **Resolution**: Yes. All existing call-sites (grep audit during implementation) currently pass clean single-line values. The reject changes behavior ONLY when a caller passes a multi-line value, which is already a latent bug.
- **Source**: codebase

## Decision 9: Hard constraint — script-md-siblings rule
- **Question**: Must all touched `.sh` scripts also update their `.md` siblings in the same PR?
- **Resolution**: Yes. Per `.claude/rules/script-md-siblings.md`, every behavior-change PR touching a `.sh` must update the sibling `.md`. Scope: `lib-voter-coverage.md`, `dispatch-plan-voters.md`, `tally-plan-review.md`, `lib-quiet.md`, plus the new shared-helper sibling `.md` (and any other --design-tmpdir consumer .md siblings touched).
- **Source**: codebase

## Decision 10: Non-goal — do NOT add backward-compat shim for the renamed function
- **Question**: Should the rename keep a deprecated stub for old callers?
- **Resolution**: No. Per `AGENTS.md` "Avoid backwards-compatibility hacks", and given there is exactly one production sourcer, a clean rename is the right call.
- **Source**: codebase
