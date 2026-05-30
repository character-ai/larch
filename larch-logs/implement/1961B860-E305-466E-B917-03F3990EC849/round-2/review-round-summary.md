# Review Round 2

- Mode: `diff`
- 11 accepted, 7 rejected (4 exonerated)

## Accepted Findings

### FINDING_1: ship-pr second fixup pass — decouple add from commit; hook re-dirty / single-pass gap
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-git-add-scope-output.txt
- **Severity**: important
- **Concern**: Pre-rebase Option A fixup can leave tracked porcelain dirty after a successful fixup commit when pre-commit hooks re-modify files (same class as Option B). The committed flow may use only one pass or a second pass that chains `git-commit.sh` on successful `git add -u` only (`elif`), while the first pass commits whenever the index is non-empty; if `git add -u` fails after hook re-dirty but staged tracked changes remain, no second fixup commit runs, `drop-bump-commit.sh` Guard 1 still yields `DROPPED=false`, and `ship-pr` stalls at step 10/12. Decouple add failure from commit (attempt commit when `git diff --cached` is non-empty, matching pass one / plan).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-git-add-scope-output.txt: Mirror the two-pass pattern already drafted in the working tree (`scripts/ship-pr.sh:2874-2890`): after a successful fixup commit, re-check tracked porcelain and attempt one more `git add -u` + fixup commit; bump `--max-depth` when a fixup commit was inserted so the bump walk still reaches the version commit.


### FINDING_15: ship-pr pre-rebase fixup lacks submodule scrub before commit
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Pre-rebase fixup has no submodule gitlink revert/scrub unlike review-and-fix; dirty submodule SHA can be committed via `git add -u` and pushed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_16: review-and-fix submodule handling order on follow-up path
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Follow-up may run `post_dispatch_submodule_revert` after the follow-up commit (or omit it), so submodule pointer dirt can enter history then be reverted in the working tree—bad object in history until manual repair; should match primary path ordering (checks/revert before follow-up `git-commit.sh`, re-run after successful follow-up where appropriate).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_17: Acceptance fixes exist only in working tree, not on branch tip
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Option A/B hardening and tests may exist only uncommitted; merge/CI reviews incomplete tip—stall fix and acceptance criteria not fully delivered until committed and pushed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_18: Option A fixup under errexit from larch_err bypasses record_failure fallthrough
- **Reviewer(s)**: dyn-set-e-safety-output.txt
- **Severity**: important
- **Concern**: ship-pr intends best-effort fixup fallthrough (`record_failure` then continue to drop-bump), but `larch_err` via `larch_quiet_redact_diagnostic_stream` enables `set -e`; after `run_rebase_rebump`’s `larch_err`, bare `git add -u` / `git-commit.sh` can abort the shell before `rc=$?` and `record_failure`, hard-aborting instead of Guard 1 stall or documented Warning path—opposite of “only improve, never regress” vs review-and-fix’s intentional `if`/`&&` under `set -e`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-set-e-safety-output.txt: Wrap the fixup git steps in an errexit-safe idiom: `set +e` … capture `rc` … `set +e` (or restore prior `-e` with the `had_errexit` pattern used in `run_lint_fix_loop_capture` at `scripts/ship-pr.sh:100-108`), or use `if ! git add -u …; then record_failure …; elif ! git diff --cached --quiet; then if ! git-commit.sh …; fi` so failures are evaluated inside `if`/`!` contexts where errexit does not trigger. Apply the same pattern to both passes in the block.


### FINDING_2: drop_max_depth must account for multiple fixup commits
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `drop_max_depth` increases by 1 for any fixup activity while up to two fixup commits may be created. With bump already deep (e.g. at `HEAD~19`) plus two fixup commits, bump sits at `HEAD~21` but max-depth 21 can miss it → `DROPPED=false`, no-op drop, stale bump, stall persists. Depth should reflect fixup commit count (e.g. 20 + count, capped), with harness covering deep bump + double fixup / hook re-dirty where noted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_4: Missing tests for hook re-dirty / max-depth on second fixup pass
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: No (or insufficient) harness drives pre-commit re-dirty through ship-pr’s second fixup pass and max-depth edge cases; regressions in second-pass control flow or depth-21 logic would not be caught by current fixtures (e.g. `rebump_dirty_tracked_fixup` alone).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_5: drop-changelog max-depth not aligned with fixup-deepened history
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Fixup commits deepen history but `drop-changelog` stays at max-depth 20; on deep branches an `Update CHANGELOG` commit beyond depth 20 after fixups can make changelog drop a no-op → stale changelog replay/conflict.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_6: review-and-fix must fail closed on persistent tracked residue after follow-up
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-git-add-scope-output.txt
- **Severity**: important
- **Concern**: After follow-up `git-commit.sh`, a non-idempotent hook can re-dirty tracked files; the script may only warn and still emit `CODER_STATUS=applied` / return 0, so Step 5 treats the round as applied while porcelain remains—recreating the upstream stall class at ship-pr time. Plan/docs may still describe warn-and-continue while code uses exit 2; behavior and acceptance must be reconciled (fail closed with `CODER_STATUS=failed` and return 2 when tracked porcelain remains after follow-up).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-git-add-scope-output.txt: On persistent tracked residue after follow-up, write `CODER_STATUS=failed` to `$result_file` and `return 2` (as in the uncommitted working-tree revision at `review-and-fix.sh:482-493`); optionally re-run `post_dispatch_submodule_revert` after a successful follow-up commit when using `git add -u`.


### FINDING_7: Follow-up staging `git add -A` vs tracked-only guard
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-git-add-scope-output.txt
- **Severity**: latent
- **Concern**: Follow-up path is gated on tracked-only porcelain but may stage with `git add -A`, sweeping untracked artifacts (e.g. hook-generated files) into the follow-up commit—contradicting tracked-only scope and Option A’s `git add -u` in ship-pr.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-git-add-scope-output.txt: Change the follow-up staging to `git add -u` (and update `skills/review-and-fix/scripts/review-and-fix.md:56` to match); keep `git add -A` only on the primary round commit at `review-and-fix.sh:438` where the orchestrator already owns full-tree staging.


### FINDING_8: review-and-fix.md out of sync with follow-up behavior
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Docs describe warn-and-continue / `git add -A` while shipped or staged code uses return 2 / `git add -u`, misleading operators and reviewers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


