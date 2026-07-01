## Goal
Implement issue #5942: [IMPLEMENTING] [BUG] audit-runs 256-char title test hits wrong branch; stale 'pre-bump flush' in docs.

## Implementation Plan
## Summary

Two low-severity residual gaps left by recently merged fixes. (1) #5792's regression test for the 256-char audit-runs title cap exercises the wrong (contiguous) branch, so it does not actually guard the non-contiguous path that overflowed 256 chars — it passes even on the pre-fix code. (2) #5842's "pre-bump flush" → "pre-ship log flush" terminology rename left the old misnomer in `docs/run-logs.md` (3 spots), even though #5842 explicitly scoped "remaining docs."

## Original report

Audit of #5792 and #5842 found a misconstructed regression test and a stale-terminology miss.

## Reproduction scenario

**Defect 1:** Read `python/tests/issue/test_audit_runs.py:36-37`. `test_title_noncontiguous_stays_under_256_chars` builds `",".join(str(n) for n in range(5000, 5000 + 1138))` — a **contiguous** sequence. The title builder compacts contiguous ranges to `#first-#last (N total)`, so this input hits the contiguous branch, never the enumerated non-contiguous branch that produced the >256-char title. The test passes on the pre-#5792 code, so it does not pin the boundary its name claims.

**Defect 2:** `git grep -n "pre-bump flush" docs/run-logs.md` → lines 309, 325, 446. These describe the Step 7a flush that #5842 renamed to "pre-ship log flush" everywhere else.

## Expected behavior

- A regression test that constructs a genuinely non-contiguous PR list (the shape that triggered the >256-char overflow) and asserts the resulting title stays under 256 chars — so it would fail on the pre-fix code.
- `docs/run-logs.md` uses the renamed "pre-ship log flush" terminology consistently.

## Observed behavior

- The "noncontiguous" test is contiguous and does not exercise the fixed branch.
- Three stale "pre-bump flush" mentions remain in `docs/run-logs.md`.

## Root cause analysis

- **Defect 1:** the test author used a contiguous `range()` for a test named "noncontiguous"; because the builder collapses contiguous ranges, the 8.5k-char enumerated path that #5792 fixed is never reached. Verified by direct read.
- **Defect 2:** #5842 chose the lighter-touch prose rewrite (documented decision) and rewrote three prose sites plus code-symbol clarifiers, but missed `docs/run-logs.md`. Verified by direct read. (This is the same "patched siblings, left one" class the drift-prone-prose rule warns about.)

## Evidence

- `python/tests/issue/test_audit_runs.py:36-37` — contiguous `range(5000, 5000 + 1138)` in the "noncontiguous" test. A sibling `test_title_noncontiguous_compact` uses a 4-element list that does not stress length.
- `docs/run-logs.md:309, 325, 446` — literal "pre-bump flush".

## Affected files

- `python/tests/issue/test_audit_runs.py` — the misconstructed boundary test.
- `docs/run-logs.md` — three stale "pre-bump flush" mentions.

## Suggested fix(es)

- Rebuild `test_title_noncontiguous_stays_under_256_chars` with a genuinely non-contiguous list (e.g. every-other PR number, or the exact large non-contiguous shape that overflowed) and assert the title length is < 256 — confirm it fails against the pre-#5792 builder.
- Replace "pre-bump flush" with "pre-ship log flush" at `docs/run-logs.md:309, 325, 446` to match the rename applied elsewhere.

## Open questions

None identified.

## Test plan
(no test plan section in plan-file)
