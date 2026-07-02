## Goal
Implement issue #6019: [IMPLEMENTING] [BUG] #5982 residual: relevant-checks failure digest is contentless for marker-less failures.

## Implementation Plan
## Summary

The failure-triage digest introduced by #5982 / PR #6011 emits `check=unknown / failure_count=0 / first_location=unknown / first_error=unknown` for failing logs that contain no marker line. That includes the common direct `make py-lint` ruff failure shape, so the digest saves no tokens for exactly the repair-loop class the issue targeted. Nothing breaks functionally: the documented fallback to `REDACTED_LOG_FILE` remains intact, so cost degrades to pre-#5982 levels for this class.

## Original report

From the 2026-07-02 post-merge audit of #5982 / PR #6011 at 63ed17f18. The audit executed the scenario against the shipped code and observed the contentless digest. The run's accepted review finding FINDING_5 (voted 3-0) described this failure shape; the shipped fix (carrying `pending_location` forward) only helps when a marker line eventually appears, so the accepted finding was only partially fixed.

## Reproduction scenario

Run the digest builder over a redacted failure log of this shape (typical direct py-lint failure):

1. A banner line: `=== Running direct relevant make target(s): py-lint ===`
2. A ruff violation row: `python/larch/foo.py:10:5: F401 'os' imported but unused`
3. A GNU make tail: `make: *** [Makefile:42: py-lint] Error 1`

No line matches the marker regex, so no record is created and the digest is contentless.

## Expected behavior

The digest carries at least the failing file:line and the first error row for marker-less tool output (ruff/flake8-style `path:line:col: CODE message` rows, GNU make `Error N` tails), so the repair loop can consume the digest instead of the full redacted log.

## Observed behavior

`check=unknown`, `failure_count=0`, `first_location=unknown`, `first_error=unknown`. The location captured into `pending_location` from the ruff row is silently discarded when the log ends without any marker line.

## Root cause analysis

`_CHECKS_FAILURE_DIGEST_MARKER_RE` (python/larch/implement/checks_run_relevant.py:32-34) matches only `ERROR:|Error:|FAILED|Failed|Traceback|AssertionError|DEFECT:`. Ruff rows contain no marker token, and `Error 1` in the make tail has no colon. In `_parse_checks_failure_records` (checks_run_relevant.py:856-880), records are created only on a marker match; the final no-records fallback (lines 877-880) cannot even use the failing line because `fallback_line` is set only inside the marker branch. Secondary, suspected (minor): the `elif records:` branch (line 870) appends context to a record minted by an earlier section, so a marker word leaked from a passing phase could mint a `failure_count=0` record for a passing check; noise only, contained by the byte cap and fallback.

## Evidence

- checks_run_relevant.py:32-39: marker, location, pre-commit, and direct-target regexes (verified by direct read at 63ed17f18).
- checks_run_relevant.py:856-880: marker-gated record creation and unknown fallback (verified by direct read).
- Run log larch-logs/implement/454633C3-5D3B-4678-818F-56D3A3C26D6D: FINDING_5 accepted 3-0; committed review summary shows the pending_location fix as the applied remedy.
- Audit execution of the reproduction shape produced the contentless digest.

## Affected files

- python/larch/implement/checks_run_relevant.py: marker regex, `_parse_checks_failure_records`, `_build_checks_failure_digest`.
- The #5982 test file for the digest (python/tests/implement/, digest tests): add marker-less fixtures.

## Suggested fix(es)

- When a section (or the log) ends with a `pending_location` and no record, mint a record using the current section's check name (the direct-target banner already names the target) with that line as `first_error`.
- Extend the marker set with make-tail and lint-row shapes, for example a `make: \*\*\*` prefix rule and a `^[^:]+:\d+(:\d+)?: [A-Z]+\d+` lint-code rule, or a small per-tool marker table.
- Add unit tests for the direct py-lint failure shape and assert the digest is non-contentless.

## Open questions

- Should `check=unknown` rows exist at all when the direct-target banner names the target?

## Test plan
(no test plan section in plan-file)
