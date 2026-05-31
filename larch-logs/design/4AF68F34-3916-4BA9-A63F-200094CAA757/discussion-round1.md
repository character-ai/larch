## Decision 1: Item 2.1 (#3260a) propagation scope
- **Question**: How far should the "warn on top-level enumeration `find` failure" fix propagate?
- **Resolution**: Full correct sync. Add `larch_err` warning to BOTH enumeration passes (cache + /tmp); update `cleanup.md` (fail-open invariant + edit-in-sync note); add a `test-cleanup.sh` assertion; update the `SECURITY.md` `/cleanup` retention note that documents the fail-open.
- **Source**: user

## Decision 2: Items 1 (#3255) and 2.2 (#3260b) treatment
- **Question**: Both appear already resolved in the current tree — touch them or skip?
- **Resolution**: Skip both; the plan records each as already-resolved with concrete evidence and makes NO edits. Item 1's `approval-gates.md:209` reference was removed by #3265; item 2.2's asymmetry is already documented at `cleanup.md` (cache no-pre-filter vs /tmp `-mtime +N`).
- **Source**: user

## Decision 3: Convergence-threshold forwarding mismatch (out of issue's stated scope)
- **Question**: A real Step 3 regression was found — `run-step3-review.sh` forwards `--convergence-threshold` to `plan-review-loop.sh`, which rejects unknown options (exit 2). Fold the fix into #3274?
- **Resolution**: Fold into this plan. Fix the forwarding mismatch AND add the missing integration-seam test that would have caught it.
- **Source**: user

## Decision 4: Correct shape of the convergence fix (in-scope file set)
- **Question**: Minimal forward-fix vs full dead-config removal?
- **Resolution**: Full end-to-end removal of the dead `LARCH_DESIGN_CONVERGENCE_THRESHOLD` / `--convergence-threshold` plumbing. #3265 replaced per-round convergence with a hardcoded single-round rule (`_round_qualifies_for_convergence`: ≤5 non-nit accepted, 0 important) and deliberately removed `--convergence-threshold` from `plan-review-loop.sh`. `run-step3-review.sh` uses `CONVERGENCE_THRESHOLD` ONLY to forward it (init/parse/required-check/forward — no other logic), so a partial fix would leave a required-but-ignored argv + stale docs. Removing it end-to-end fixes the mismatch and completes the half-done removal the #3255 author assumed was complete.
- **Source**: codebase (git history #3265/#3269; `run-step3-review.sh`, `plan-review-loop.sh`)

## Decision 5: Hard constraint — preserve normal cleanup behavior
- **Question**: What must not break in the cleanup.sh change?
- **Resolution**: Only the enumeration-FAILURE path gains a warning. Normal-path behavior (counts, NUL-safe iteration, never delete through a symlink, nested `maxdepth 5` confirm, `/tmp` `-mtime +N` pre-filter) must be byte-for-byte preserved. The fix must capture `find`'s real exit (process substitution hides it today) — e.g. redirect enumeration output to a temp file, branch on `find`'s exit, then read NUL-delimited from the temp file. Bash 3.2-compatible only.
- **Source**: codebase (`cleanup.sh`)

## Decision 6: Test harness — distinguishing enumeration failure from nested-scan failure
- **Question**: How to test a top-level enumeration `find` failure without also failing the nested scan?
- **Resolution**: The existing `write_stub_find_failure` fails only on the `-maxdepth 5` nested-scan pair. A new sibling stub must fail only when it sees `-mindepth 1` (used solely by the two enumeration passes; the nested scan uses `-maxdepth 5` and the symlink reaper uses `-maxdepth 1` with no `-mindepth`). Assert the new warning fires, exit stays 0, and counts stay 0.
- **Source**: codebase (`test-cleanup.sh`)
