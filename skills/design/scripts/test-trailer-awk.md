# test-trailer-awk.sh

Offline unit harness for `lib-plan-optional-trailers.awk` (issue #3204). Exercises all four awk modes (`keys`, `values`, `parse`, `has_key`) and edge cases that thin wrapper adapters do not cover: last-match-wins on duplicate strict trailers, `block_len` vs present-key count, `0[89]` octal rejection, `mechanical_churn` true/false, `diff_deleted`, block-boundary scans, and no-trailer plans.

## Invocation

`bash skills/design/scripts/test-trailer-awk.sh`

## Wiring

Invoked by `test-trailer-helpers.sh` before its final PASS line. No standalone Makefile target — `make test-trailer-helpers` and shard `test-harnesses-12` pick it up through the combined harness.

## Expected-failure probes

`has_key` exits **1** when a key is absent, octal-rejected, or above a block boundary. Under `set -euo pipefail`, never invoke those probes bare: wrap each in `set +e`, capture `$?`, assert the exit code, then `set -e` (same pattern as `test-trailer-helpers.sh` and `test-gate-b-dedup-plan.sh`).

**Two-fixture split for block boundaries:** `block-boundary` asserts `has_key diff_added` **rc=0** (trailer in the final contiguous metadata block). `boundary-orphan-only` and `blank-before-diff-lines` assert **rc=1** (trailer separated from `diff_lines:` by a non-trailer line or blank line). Do not expect exit 1 from `block-boundary` alone.

## `parse` line 1 (`block_len`)

Line 1 of `parse` output is the physical metadata-block line count from the upward scan (`metadata_trailer_lines = block_len` in `check-plan-size.sh`), **not** the count of distinct present keys. Duplicate strict-trailer lines (e.g. two `diff_added:` before `diff_lines:`) inflate `block_len` independently of last-match-wins on lines 2–4.

Normative awk contract: [`lib-plan-optional-trailers.md`](lib-plan-optional-trailers.md). Keep harness fixtures in sync when that contract changes.
