## Goal
Implement issue #6023: [IMPLEMENTING] [BUG] #5971 residual: claude-ci retry gaps for sentinel and permanent empty output.

## Implementation Plan
## Summary

#5971 / PR #5998 added the claude-ci lint-fix retry for exit-124 and missing/empty output, closing the filed failure mode. Two adjacent shapes remain: sentinel non-empty outputs (`CLAUDE_CI_EMPTY_RESULT`) never retry because the predicate is size-based, and permanent failures that produce empty output (binary missing, auth/quota with empty stdout) burn exactly one futile retry mislabeled as "subprocess transient".

## Original report

From the 2026-07-02 post-merge audit of #5971 / PR #5998 at 63ed17f18. Both shapes were surfaced in that run as OOS_3 and OOS_4 and dropped per the vetted plan's scope; 0 OOS filed. Both are live at HEAD. Terminal outcomes are unchanged in both cases; this is a cost/latency and log-accuracy defect, not a correctness break.

## Reproduction scenario

Shape (a), sentinel: claude exits 0 with a valid JSON envelope and empty `.result`; the launcher writes the 23-byte sentinel `CLAUDE_CI_EMPTY_RESULT` plus newline and forces exit 1 (python/larch/agents/_ci_launcher.py:884-887). The retry predicate sees a non-empty output file and returns None; no retry.

Shape (b), permanent: the claude binary is missing; preflight writes a zero-byte output file and `.done` rc 127 (python/larch/agents/_run_external.py:918-933); the predicate returns "empty-output"; one relaunch that cannot succeed runs anyway, logged with the transient-retry warning.

## Expected behavior

- (a) The empty-result sentinel is the same no-output failure expressed through a different envelope; it should be retry-eligible, or the non-retry choice should be documented at the predicate.
- (b) Known-permanent exits (127 binary-missing and similar) skip the retry and go straight to classify/health, and the warning label does not claim a transient cause.

## Observed behavior

`_ci_fix_retry_reason` (python/larch/implement/ci_agentic_fix.py:325-335) classifies solely by exit 124 or output-file absence/size. Sentinel writes are non-empty, so shape (a) is invisible; permanent failures are size-indistinguishable from transients, so shape (b) retries once.

## Root cause analysis

The #5971 vetted plan intentionally scoped the predicate to exit-124 plus missing/empty output with no health-rc carve-out, and the sentinel sub-mode was triaged as latent OOS. Both gaps are conscious descopes now lacking any tracking issue.

## Evidence

- ci_agentic_fix.py:325-335 (predicate) and :543-569 (single bounded retry site), verified at 63ed17f18.
- _ci_launcher.py:884-891 (sentinel write and forced exit; zero-byte write for empty stdout).
- _run_external.py:918-933 (binary-missing preflight).
- Run log larch-logs/implement/9DABFAEB-4BE3-4847-B85B-9FB630E959C4: OOS_3 and OOS_4 records; run-statistics.md "OOS filed: 0".

## Affected files

- python/larch/implement/ci_agentic_fix.py: `_ci_fix_retry_reason`, `_emit_ci_retry_warning`.
- python/larch/agents/_ci_launcher.py: sentinel contract (read-side awareness only).
- python/tests/implement/test_ci_agentic_fix.py: new cases.

## Suggested fix(es)

Extend `_ci_fix_retry_reason` to (a) recognize the exact sentinel content as an "empty-result" retry reason and (b) consult the `.done` rc for a small known-permanent set (127 at minimum) to suppress the retry and emit an accurate warning label. Add tests for both shapes.

## Open questions

- Is one futile retry for permanent failures acceptable by design given its near-zero cost when the binary is missing (claude never runs), or does the auth/quota variant (one full extra invocation) justify the rc carve-out?

## Test plan
(no test plan section in plan-file)
