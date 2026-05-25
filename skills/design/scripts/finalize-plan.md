# finalize-plan.sh

## Purpose

`finalize-plan.sh` performs the final mechanical artifact check for `/design` after plan review has completed.

## Primary Callers

- `skills/design/scripts/design-driver.sh` for `ACTION=FINALIZE`
- `/design` Step 4

## Invariants

- `rejected-findings.md`, `accepted-plan-findings.md`, `oos.md`, and `voting-tally.md` are required manifest artifacts but may be empty. The script creates missing regular files for those names.
- `plan.txt` and `diff-lines.txt` must exist and be non-empty.
- May-be-empty artifact paths must be regular files, not symlinks or directories.

## Makefile Wiring

The regression harness is `make test-finalize-plan`, wired into `test-harnesses-1`.

## Harness

`test-finalize-plan.sh` covers all-present, missing may-be-empty files, missing required files, missing design tmpdir, idempotent re-runs, auto-created empty `voting-tally.md`, permissive empty `voting-tally.md`, and symlink `voting-tally.md` rejection.

## Edit In Sync

Update this contract, `test-finalize-plan.sh`, `skills/design/SKILL.md`, and `skills/design/scripts/design-driver.sh` together when design-local plan artifacts required at finalize time change.

On non-zero exit, `FAILURE_LOG=<path>` may appear on stdout.
