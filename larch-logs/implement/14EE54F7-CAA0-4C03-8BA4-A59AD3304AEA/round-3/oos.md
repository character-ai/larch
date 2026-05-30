### OOS_1: [OUT_OF_SCOPE] Uncommitted `_ci_fix_rebase_pending_set` calls without definition
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parser-quoting-output.txt, dyn-rebase-dirty-state-output.txt
- **Severity**: important
- **Concern**: Working-tree / uncommitted edits call `_ci_fix_rebase_pending_set` at `scripts/ship-pr.sh:1886,1956,1962` (or equivalent) but no such function exists in the repo; successful push paths would log “command not found” and may leave `CI_FIX_REBASE_PENDING` stuck true, skewing later push routing in the same process.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Define _ci_fix_rebase_pending_set (or use direct assignment) at all three call sites
  - From cursor-specialist-testing-output.txt: Define _ci_fix_rebase_pending_set or inline assignments; add a harness asserting the flag clears after successful force-push
  - From cursor-specialist-edge-cases-output.txt: Define the helper or assign CI_FIX_REBASE_PENDING directly; add regression coverage for clear-on-success
  - From cursor-specialist-plan-fidelity-output.txt: Define the helper or keep direct CI_FIX_REBASE_PENDING assignment
  - From dyn-bash-parser-quoting-output.txt: Uncommitted edits to `scripts/ship-pr.sh` (not in commit `1e8effa87`) call `_ci_fix_rebase_pending_set` at `scripts/ship-pr.sh:1886,1956,1962` but no such function is defined anywhere in the repo; those paths would fail at runtime until replaced with `CI_FIX_REBASE_PENDING=…` assignments or a real helper.
  - From dyn-rebase-dirty-state-output.txt: Either define `_ci_fix_rebase_pending_set` (if persistence was intended) or replace all three calls with direct `CI_FIX_REBASE_PENDING=true/false` assignments matching the diff’s original `CI_FIX_REBASE_PENDING=false` at push success.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_10: [OUT_OF_SCOPE] Stale `ship-pr.md` waterfall paragraph vs rotation invariant
- **Reviewer(s)**: dyn-waterfall-rotation-semantics-output.txt
- **Severity**: nit
- **Concern**: Recovery waterfall paragraph still describes first-fixer shortcut as “when the **first** tier (`cursor`) fails…”, conflicting with Invariants text for rotated first tier.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-waterfall-rotation-semantics-output.txt: **code-quality** `scripts/ship-pr.md:108` vs `scripts/ship-pr.md:140-142` — The Recovery waterfall paragraph still describes the shortcut as “when the **first** tier (`cursor`) fails…”, while the Invariants section documents rotation and “first tier of the rotated list”; the stale paragraph conflicts with the implementation intent and the newer invariant text.

---

**Merge notes (for voters, not part of machine output):**

- Input items **8, 15, 29, 52** (undefined `_ci_fix_rebase_pending_set` on committed paths) were folded into **OOS_1** where reviewers tagged uncommitted/WIP state; the committed tree in this workspace uses direct `CI_FIX_REBASE_PENDING=` assignment and has no `_ci_fix_rebase_pending_set` symbol.
- **FINDING_4** (push failure pending) complements **FINDING_1** but stays separate because the fix differs (set flag on push failure vs re-run verify on retry).
- Reviewer-only “no bug” observations (**57**) are captured as **OOS_9** for traceability; voters may treat as informational.
- Slots that only said “Address the concern above” are omitted per aggregator rules; substantive fix text is taken from each reviewer’s concern or explicit suggested-fix paragraphs.

Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_2: [OUT_OF_SCOPE] Deliberate fail-open BEHIND_COUNT=0 (pre-existing / plan tradeoff)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-bash-parser-quoting-output.txt
- **Severity**: latent
- **Concern**: `ci-behind-count.sh` fail-open to `BEHIND_COUNT=0` on fetch/rev-list errors is an accepted design tradeoff; transient failures can skip needed rebase before push.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Pre-existing design tradeoff; monitor if needed
  - From cursor-specialist-testing-output.txt: Document operational risk; optional metric/alert on fail-open warnings
  - From dyn-bash-parser-quoting-output.txt: `scripts/ci-behind-count.sh` fail-open to `BEHIND_COUNT=0` on fetch/`rev-list` errors is deliberate; it can skip a needed rebase under transient git failures (accepted tradeoff per plan).


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_3: [OUT_OF_SCOPE] #3175 hook/doc work bundled with #3210
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parser-quoting-output.txt
- **Severity**: latent
- **Concern**: Anti-polling hook expansion (`hook-anti-read-poll.sh`, `AGENTS.md`, `orchestrator-never.md`, etc.) ships on the same branch as #3210 CI-fix work, increasing review/merge surface and conflicting with single-feature PR policy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Track as separate change or split PR if policy requires single-feature diffs
  - From cursor-specialist-plan-fidelity-output.txt: Track/review under its own issue
  - From dyn-bash-parser-quoting-output.txt: Branch also bundles unrelated `#3175` hook/doc work (`scripts/hook-anti-read-poll.sh`, `AGENTS.md`, `skills/shared/orchestrator-never.md`) via commit `2fc05d968`; the `#3210` core is commit `1e8effa87` (13 files).


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_4: [OUT_OF_SCOPE] `git-force-push.sh` hardcodes `origin`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Fork/upstream rebase may not align force-push remote with rebase base; pre-existing limitation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Pre-existing; thread base remote into git-force-push when fixing fork paths.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_5: [OUT_OF_SCOPE] nosession bucket shares poll counters across sessions
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Missing session metadata causes false shared reminders in `hook-anti-read-poll.md` nosession bucket.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Documented limitation; optional stricter session binding later.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_6: [OUT_OF_SCOPE] Pre-push vendor verify failure without CI_FIX_REBASE_PENDING
- **Reviewer(s)**: dyn-rebase-dirty-state-output.txt
- **Severity**: latent
- **Concern**: When `run_ci_fix_vendor` returns `4` from pre-push `_verify_failed_jobs_locally` (before `_stage_and_push_ci_fixes`), `CI_FIX_REBASE_PENDING` is not set; outer retries may re-dispatch with prior uncommitted verify deltas preserved by `_ci_fix_rollback`. Adjacent to scout scope, not introduced by deferred-rebase path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-rebase-dirty-state-output.txt: **risk-integration** `scripts/ship-pr.sh:2061-2066,2508-2511` — When `run_ci_fix_vendor` returns `4` from pre-push `_verify_failed_jobs_locally` (before `_stage_and_push_ci_fixes`), `CI_FIX_REBASE_PENDING` is not set; the next outer attempt can call `run_ci_fix_vendor` again with a new baseline that includes the prior attempt’s uncommitted verify deltas, and `_ci_fix_rollback` (1733–1777) will preserve those paths across tier failures. That is adjacent to the scout prompt but not introduced by the deferred-rebase path (which correctly avoids re-entering the vendor waterfall while pending).


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_7: [OUT_OF_SCOPE] Harness passes without asserting re-verify on pending retry
- **Reviewer(s)**: dyn-rebase-dirty-state-output.txt
- **Severity**: latent
- **Concern**: `ci_fix_no_double_rebase_pending_retry` asserts no second rebase when `BEHIND_COUNT=0` on retry but does not assert `_verify_failed_jobs_locally` runs on the pending retry, so the harness can pass while the production gap remains.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-rebase-dirty-state-output.txt: **architecture** `scripts/test-ship-pr.sh:5261-5367` — `ci_fix_no_double_rebase_pending_retry` asserts no second rebase when `BEHIND_COUNT=0` on retry, but does not assert that `_verify_failed_jobs_locally` runs on the pending retry; the harness can pass while the production gap above remains.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_8: [OUT_OF_SCOPE] Intentional conservative anti-poll warnings under short-circuit
- **Reviewer(s)**: dyn-bash-parser-quoting-output.txt
- **Severity**: nit
- **Concern**: Conservative Bash warnings (e.g. `test -f x || cat tasks/….output`) may fire even when short-circuiting would skip the read; matches warn-on-suspicious-syntax posture.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parser-quoting-output.txt: Intentional conservative Bash warnings (e.g. `test -f x || cat tasks/….output`, `echo 'waiting' || cat …` in `scripts/test-hook-anti-read-poll.sh`) may fire even when short-circuiting would skip the read; that matches a “warn on suspicious syntax” posture rather than exact shell semantics.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### OOS_9: [OUT_OF_SCOPE] `start_attempt` timing — no bug found
- **Reviewer(s)**: dyn-waterfall-rotation-semantics-output.txt
- **Severity**: nit
- **Concern**: Reviewer reports `start_attempt` passed as current `$_fix_attempt` before end-of-iteration increment matches intended rotation; no timing bug found.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-waterfall-rotation-semantics-output.txt: **correctness** `scripts/ship-pr.sh:2511,2532,2555` — `start_attempt` is passed as the current `$_fix_attempt` before the end-of-iteration increment at 2555, so the first outer retry uses `0` (cursor-first) and the second uses `1` (codex-first), matching `ci_fix_vendor_rotation_start_attempt`; no timing bug found there.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

