## Goal
Implement issue #3493: [IMPLEMENTING] Step 3 preview sentinel does not invalidate on plan.txt repair\n\n## Out-of-Scope Observation.

## Implementation Plan
## Plan

### Summary

Fix `skills/design/scripts/run-step3-review.sh --preview-only` so the `.step3-entry-plan-printed` sentinel is created **only** when a real `## Plan Candidate for Review` header renders — never on the missing-plan warning path. Today the touch condition matches the header **and** the exact missing-plan warning `**⚠ 3: plan.txt missing or empty; cannot present plan candidate for review**`. When `plan.txt` is missing/empty on the first Step 3 entry, the warning sets the sentinel; after the operator repairs `plan.txt` and triggers a Gate C re-run, the sentinel-exists early-exit (`exit 0`) suppresses the genuine first-time plan preview, and the missing-plan warning never repeats either.

Minimal presence-based fix (the approach selected at design time): drop the missing-plan-warning branch from the `_has_header` touch condition. A missing/empty `plan.txt` then re-warns on every re-entry and never sets the sentinel, so the first entry where `plan.txt` is actually present renders the full plan candidate and sets the sentinel exactly as designed. The common case (`plan.txt` present on first entry) is unchanged.

SIMPLE-tier change: one `case` branch removed plus its adjacent comment, one regression-test inversion plus a missing→repair scenario test, and the script's sibling contract doc. No SKILL.md, Makefile, or structure-test changes; no new flags, modes, or result-env keys. Not a submodule.

### Files to modify

**`skills/design/scripts/run-step3-review.sh`** (core)
- In the `--preview-only` touch block guarded by `if [[ "$_sentinel_ok" == true ]]; then`, remove the `case` branch `*'**⚠ 3: plan.txt missing or empty; cannot present plan candidate for review**'*) _has_header=true ;;`. Keep only `*'## Plan Candidate for Review'*) _has_header=true ;;` so the sentinel is touched solely after a real plan candidate renders.
- Update the adjacent comment ("Touch sentinel only when tmpdir validates AND renderer output contains the expected header **or the exact missing-plan warning**...") to drop the "or the exact missing-plan warning" clause and state that a missing/empty `plan.txt` re-warns until repaired, so the first real plan render owns the sentinel.
- Leave everything else byte-for-byte: the sentinel-exists early-exit (`exit 0` at the read site), the `_sentinel_ok` / `_canonical_tmpdir` allowlist validation, the raw-path renderer invocation, and the entire `--no-preview` path.

**`skills/design/scripts/test-run-step3-review.sh`** (harness — same-PR coverage)
- Invert the existing `=== --preview-only exact missing-plan warning creates sentinel on allowlisted tmpdir ===` case: rename it and flip the assertion to require that `.step3-entry-plan-printed` is **NOT** created when the renderer emits only the exact missing-plan warning.
- Add a regression case reproducing issue #3493: (1) first `--preview-only` call with `plan.txt` removed and a stub renderer emitting the exact missing-plan warning → assert no sentinel; (2) restore a non-empty `plan.txt` and swap to a header-emitting stub → second call renders `## Plan Candidate for Review` and now creates the sentinel. Locks the missing→repair→preview-re-renders path.
- Leave the other preview/sentinel cases unchanged: header creates sentinel; second-call suppression; non-header no-sentinel; exit-1 non-header no-sentinel; stale-sentinel-on-disallowed-tmpdir still warns; two-call non-header-then-header.

**`skills/design/scripts/run-step3-review.md`** (sibling contract — edit in sync)
- Refine Responsibility 0's "output-string ... touch rules" wording: the sentinel is touched only when the rendered output contains the `## Plan Candidate for Review` header; the missing-plan warning never touches it, so a later `plan.txt` repair re-renders the preview on the next Step 3 entry.

### Edge cases

- `plan.txt` present on first entry (normal path): header renders, sentinel set, re-entries suppressed — unchanged.
- `plan.txt` missing/empty across several re-entries: the warning re-prints each entry (operator stays informed) and no sentinel is set until a real plan renders. Intended per the issue.
- Invalid / non-allowlisted tmpdir: `_sentinel_ok=false`, so neither the early-exit nor the touch fires and warnings still print live — unchanged.
- Renderer emits a different (non-exact) warning: already never set the sentinel; still does not.

### Failure modes

1. The inverted harness assertion silently passes against the unfixed code — avoided because the old code DOES create the sentinel for the exact warning, so the flipped assertion fails loudly until the branch is removed.
2. A hidden consumer relies on the warning-path sentinel touch — none exists: the exact warning string lives only in `emit-design-plan-preview.sh` (emitter), `run-step3-review.sh` (this branch), and the test harness; no other caller keys off it.
3. Doc drift — `run-step3-review.md` is updated in the same change; SKILL.md (Pre-voting plan re-print prose) already describes "allowlist-gated touch rules" generically and stays accurate, so it is intentionally left untouched.

## Acceptance

- `run-step3-review.sh --preview-only` does NOT create `.step3-entry-plan-printed` when the renderer emits only the exact missing-plan warning, and still creates it when the `## Plan Candidate for Review` header renders.
- After a missing-plan first entry (warning printed, no sentinel) followed by a `plan.txt` repair, a subsequent `--preview-only` call re-renders the plan candidate and only then creates the sentinel.
- `bash skills/design/scripts/test-run-step3-review.sh` passes: the missing-plan-warning case asserts no sentinel, and a new missing→repair case asserts the preview re-renders after repair.
- No new flags, modes, or result-env keys; the `--no-preview` review path and the sentinel-exists early-exit are unchanged.
- `bash scripts/relevant-checks.sh` (or `make lint`) passes for the touched `.sh` / `.md` surfaces.

diff_lines: 45

## Test plan
(no test plan section in plan-file)
