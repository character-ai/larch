## Plan

**Issue**: `/design` env-refresh drops `CODEX_PRESENT` / `CURSOR_PRESENT` / `CODEX_AVAILABLE` / `CURSOR_AVAILABLE`, breaking the Step 3 plan-review launch.

**Root cause**: `scripts/write-design-current-env.sh` rewrites `source-env.sh` from scratch and emits the four reviewer keys only when their shell var is non-empty. A no-flag refresh (Step 0b sub-step 6, Step 5.5-bis) omits the flags, so the keys are dropped; Step 3 then passes empty `--codex-present` / `--cursor-present` to `plan-review-loop.sh`, tripping its `${2:?}` argv guard.

**Fix (approach #1, issue's preferred)**: make the writer preserve/merge the four keys from the existing `--output` file when the matching flag is omitted, with alias-pair normalization for partial explicit overrides. No SKILL.md or consumer changes (Round 1 decisions).

### Files to modify

#### UPDATED: `scripts/write-design-current-env.sh`
- Track explicit-provided state per reviewer flag (`CODEX_PRESENT_SET`, `CURSOR_PRESENT_SET`, `CODEX_AVAILABLE_SET`, `CURSOR_AVAILABLE_SET` default `false`, flipped `true` in each argv-parse branch after `validate_bool`).
- Add a `recover_prior_env_value` helper that reads the `^export KEY=` line from the existing `--output` file (real `grep` inside the script; `|| true` guards the no-match exit under `pipefail`).
- Before the env-file build block: (1) alias-pair normalize — when exactly one side of a `*_PRESENT` / `*_AVAILABLE` pair is explicit, mirror it to the omitted peer; (2) recover only still-empty values from the prior file.
- The existing emit guards (`[[ -n "$KEY" ]] && build_export ...`) are unchanged. Do NOT touch the `MANUAL_REQUESTED` / `REPO` / `ISSUE_NUMBER` emit lines.

#### UPDATED: `scripts/write-design-current-env.md`
- Document refresh-preservation under "## Keys": the four keys are recovered when the flag is omitted; an explicit flag overrides; a partial alias override mirrors the explicit side to the omitted peer; `MANUAL_REQUESTED` / `REPO` / `ISSUE_NUMBER` keep clear-on-omit. Cross-reference issue #3181 and harness Case 12.

#### UPDATED: `skills/design/scripts/test-write-design-current-env.sh`
- Case 13 (preserve): seed all four keys + `--manual-requested true`, then a no-flag refresh to the same output; assert all four keys preserved AND `MANUAL_REQUESTED` cleared.
- Case 14 (partial override): seed all four (mixed values), then refresh with only `--codex-present false`; assert `CODEX_PRESENT=false` and mirrored `CODEX_AVAILABLE=false`, while `CURSOR_PRESENT` / `CURSOR_AVAILABLE` are preserved from the prior write.

### Constraints
- Scope the merge to exactly the four reviewer keys; `MANUAL_REQUESTED` clear-on-omit (test Case 12) must stay green.
- No Makefile change (the `test-write-design-current-env` target is already registered in `test-harnesses-6`).

## Acceptance

- A no-flag refresh of `write-design-current-env.sh` (the Step 0b / Step 5.5-bis shape) preserves `CODEX_PRESENT`, `CURSOR_PRESENT`, `CODEX_AVAILABLE`, `CURSOR_AVAILABLE` from the prior `source-env.sh`.
- An explicitly-passed flag still overrides the recovered value; a partial explicit override of one alias side mirrors to its omitted peer (no stale-peer mix).
- `MANUAL_REQUESTED` continues to clear on omit (existing test Case 12 passes).
- New Case 13 (preserve) and Case 14 (partial override) pass; existing Cases 1-12 still pass.
- `make test-write-design-current-env` passes; `bash scripts/relevant-checks.sh` passes over the touched files.
- No edits to `skills/design/SKILL.md` or the Step 3 / Step 3.6 consumer blocks.

diff_lines: 78
