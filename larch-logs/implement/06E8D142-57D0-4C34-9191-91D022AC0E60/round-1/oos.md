### FINDING_1: [OUT_OF_SCOPE] residual TOCTOU windows around `chmod` and `mktemp`
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, dyn-dyn-hook-toctou
- **Severity**: major
- **Concern**: Validation still does not atomically bind `chmod` or `mktemp` to the vetted `state_dir`, so a same-UID swap after the checks can redirect side effects into attacker-controlled storage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Revalidate immediately before each mutating syscall, or use a verified directory fd if scope expands beyond this plan.
  - From codex-specialist-correctness: close it with a stable directory handle or another atomic primitive
  - From dyn-dyn-hook-toctou: Bind temp creation to a verified directory handle (open `O_DIRECTORY`, `mktemp` relative to that fd, or a trusted fixed root) so the target cannot change between validation and creation; keep fail-open exit 0 on validation failure.
  - From dyn-dyn-hook-toctou: Revalidate immediately before `chmod`, or `chmod` through a directory fd opened and vetted after `mkdir` (with `fchmod`/`fchmodat` where available), exiting 0 if revalidation fails.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=true

### FINDING_2: [OUT_OF_SCOPE] state-file read still races after the containment check
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-edge-cases
- **Severity**: minor
- **Concern**: A single containment check still leaves a gap before reopening the state file, so a same-UID swap can poison reminder counting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add the standalone state_dir guard immediately before the state-file read if that window must close.
  - From codex-specialist-edge-cases: Revalidate containment immediately before opening the existing state file, or bind the read to a verified directory handle


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_3: [OUT_OF_SCOPE] `deep_guardless` misses a redirect-mode assertion
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: The `deep_guardless` path never checks that redirect mode stays unchanged after the hook run, so a stripped variant could still chmod the redirect before the pre-`mktemp` guard without failing the harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Record dir_mode before/after on deep_redirect, matching swap_after_mkdir.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_4: post-`mkdir` test coverage does not prove the new guard is load-bearing
- **Reviewer(s)**: codex-specialist-correctness, dyn-dyn-hook-toctou
- **Severity**: major
- **Concern**: The current regression paths still leave the old post-`chmod` guard in place, so they do not isolate whether line 42 is independently preventing the new race window.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: move the injected swap to after the guard and before chmod, or add a second harness path that forces that exact window and asserts the redirect mode stays unchanged
  - From dyn-dyn-hook-toctou: Add a variant that removes line 44 (and optionally line 59) while keeping line 42, or assert a side effect that only line 42 prevents (for example, a cooperative swap strictly between lines 42–43 with post-chmod guards stripped).


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_5: [OUT_OF_SCOPE] ancestor `TMPDIR` symlinks remain unvalidated
- **Reviewer(s)**: dyn-dyn-hook-toctou
- **Severity**: minor
- **Concern**: A compromised `TMPDIR` can redirect `${TMPDIR}/larch-read-poll` before the leaf guards run because symlinked ancestors of `${TMPDIR:-/tmp}` are still unchecked.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-hook-toctou: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_6: [OUT_OF_SCOPE] state-file promotion still lacks a pre-`mv` revalidation
- **Reviewer(s)**: dyn-dyn-hook-toctou
- **Severity**: minor
- **Concern**: Promotion still lacks an immediate pre-`mv` containment check, so a later swap can redirect the move through a symlinked `$state_dir`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-hook-toctou: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_7: [OUT_OF_SCOPE] `SECURITY.md` overstates the TOCTOU mitigation
- **Reviewer(s)**: dyn-dyn-hook-toctou
- **Severity**: minor
- **Concern**: The doc still implies validation fully covers temp creation and promotion, but the mitigation is only point-in-time and races remain between checks and pathname-based syscalls.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-hook-toctou: Address the concern above.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

