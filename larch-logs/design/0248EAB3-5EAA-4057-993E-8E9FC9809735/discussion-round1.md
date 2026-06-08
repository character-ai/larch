## Decision 1: Per-round plan-apply delegation
- **Question**: How should per-round plan revisions be applied inside the new script-internal Step 3 loop?
- **Resolution**: Wire `revise-plan-with-waterfall.sh` into the loop body. The common path applies accepted findings in-loop as a subprocess; the main agent re-enters only on waterfall exhaustion via a new `main-agent-apply-required` bail-out. (Rejected: main-agent apply every round — returns to the orchestrator on every continuing round, fails the goal.)
- **Source**: user

## Decision 2: Launcher shape
- **Question**: Extend `run-step3-review.sh` with `--mode loop`, or add a sibling `run-step3-review-loop.sh`?
- **Resolution**: Extend `run-step3-review.sh` with `--mode loop` (parity with `run-step5-review.sh`'s `--mode`). Per `.claude/rules/launcher-argv-test-coverage.md`, the argv change requires same-PR `test-run-step3-review.sh` updates.
- **Source**: user

## Decision 3: In-loop reviser patch format
- **Question**: Which patch format should `revise-plan-with-waterfall.sh` use when invoked in-loop?
- **Resolution**: Pass `--patch-format file-replacement` directly (not the unified-diff default), since plan rewrites are often large and whole-file replacement avoids diff-apply fragility.
- **Source**: user

## Decision 4: Per-round revert mechanism
- **Question**: Do we need git commits at the end of every round for revertability?
- **Resolution**: No git commits. The existing revert mechanism suffices: `revise-plan-with-waterfall.sh` snapshots `plan.txt` to `plan.txt.before-revise` before any tier and auto-reverts on any failed validation/apply/heading/emit; HARD runs additionally keep `plan-after-round-N.txt` and `plan.txt-original` write-once snapshots. `plan.txt` is not a git-tracked file (it lives in `$DESIGN_TMPDIR`), so no new git history is introduced.
- **Source**: user
