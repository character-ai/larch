# design-step3b-tail.sh

## Purpose

Bgjob launcher for `/design` Step 4 rejected-findings output and Gate C preview setup.

## Primary callers

- `skills/design/SKILL.md`

## Invariants

- Accepts launcher-owned `--session-env-path` and `--claude-pid`; never derives the root Claude PID from `$PPID`.
- Fresh launcher stdout is exactly `BGJOB_STATUS=STARTED STEP=design-step4-tail PGID=<n>`.
- Before fresh `bgjob start`, reuses a live identity-valid `design-step4-tail` registry row or regular `$DESIGN_TMPDIR/bgjob/design-step4-tail.result.env`; stale or dead rows are cleared.
- Recreates `$DESIGN_TMPDIR/.design-step4-tail-result.env`, removes stale `$DESIGN_TMPDIR/bgjob/design-step4-tail.result.env`, then passes that merge env plus sentinel `$DESIGN_TMPDIR/.completed/step-4` to `bgjob start`.
- `$DESIGN_TMPDIR/bgjob/design-step4-tail.result.env` is completion truth for `SKIP_APPROVE_REQUESTED_GATEC`, rejected-findings marker KVs, `REJECTED_FINDINGS_BODY_PATH`, `GATEC_PREVIEW_PATH`, and optional `DIALECTIC_GATEC_DIGEST_PATH`.
- Thin launcher stdout is not a data source for `SKIP_APPROVE_REQUESTED_GATEC` or rejected findings.
- Filters rejected findings through `plan-review emit-rejected --report-framing`, with the legacy considered-not-adopted fallback on failure; leaves `rejected-findings.md` unchanged.
- Owns the Step 4 compatibility FINALIZE guard, `skip_approve_requested` read, foreground `design dialectic-gatec`, `.completed/dialectic-gatec-terminal`, and Gate C preview file.
- Exits early after preview when `.pause-save-complete` exists.
- Does not depend on architecture diagram artifacts and must not mutate repository files.

## Harness

Covered by `scripts/test-design-structure.sh`.
