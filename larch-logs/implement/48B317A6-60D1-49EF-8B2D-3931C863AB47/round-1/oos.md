### FINDING_1: [OUT_OF_SCOPE] State-path helper misses the discriminator key shape
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: `state_path_for` derives the state file path differently from the hook, so discriminator-only cases can point at the wrong state path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Mirror the hook's full session-key chain in the helper.
  - From cursor-specialist-edge-cases: Mirror the hook session_key logic in state_path_for and add a symlink case for that key


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_2: [OUT_OF_SCOPE] Temp-dir validation is still too late before chmod/mktemp
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-testing, dyn-dyn-hook-state
- **Severity**: major
- **Concern**: The hook still only revalidates `state_dir` before `chmod`/`mktemp`, so a same-UID swap can redirect temp creation into attacker-controlled storage before cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Re-validate `[ -d "$state_dir" ] && [ ! -L "$state_dir" ]` immediately before the mktemp call if you want to narrow the window further.
  - From cursor-specialist-edge-cases: Re-validate [ -d "$state_dir" ] && [ ! -L "$state_dir" ] immediately before the mktemp call at line 70
  - From codex-specialist-testing: The tempfile is created under $state_dir before the final containment check. A same-user symlink or rename swap between the guard and mktemp can still place the temp file in an attacker-controlled directory before the hook bails out. Move the last directory validation to immediately before mktemp, or create the tempfile under a trusted root and only mv after a fresh containment check; add a race-focused regression if the harness can model the swap.
  - From dyn-dyn-hook-state: Re-validate $state_dir immediately after mkdir -p and before chmod (exit 0 if missing, not a directory, or -L). Optionally repeat the check after chmod. Prefer chmod -h only when the path is confirmed not to be a symlink, or skip chmod entirely when validation fails.
  - From dyn-dyn-hook-state: Add the same `[ -d "$state_dir" ] && [ ! -L "$state_dir" ]` guard immediately before `mktemp`, mirroring the checks at lines 71, 80, and 87. Consider using `mktemp -t` with a validated directory or opening a dir fd and using `mktemp` relative to that fd if you need stronger TOCTOU resistance on shared `/tmp`.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=true

### FINDING_3: [OUT_OF_SCOPE] Hard-linked poison state files can still seed reminders
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Hard links at the predictable state path can still seed `prev_count` and trigger a false third-read reminder.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Optionally treat unexpected hardlink state (for example `stat` link count > 1) like non-regular entries if you want parity with symlink defenses.
  - From cursor-specialist-edge-cases: Reject reads unless the file is a regular file owned by the expected path and optionally verify inode/path with O_NOFOLLOW-style open semantics or post-read inode check


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_4: [OUT_OF_SCOPE] Promotion still uses mutable pathname after validation
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: The hook still uses the validated pathname through promotion, so a swap after validation or a symlinked ancestor can redirect the final write.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Resolve or reject the full temp-root path before any mutation, and revalidate immediately before mktemp and mv, failing closed if any path component is a symlink.
  - From codex-specialist-edge-cases: Keep the verified directory stable for the whole write, for example cd into it and rename by basename, or use a directory-handle based helper; if the directory cannot be held stable, delete the temp file and exit 0.
  - From codex-specialist-edge-cases: Canonicalize and validate every ancestor before use, or bind the work to a verified directory root before creating temp state.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=true

### FINDING_5: [OUT_OF_SCOPE] Parent-directory regression lacks a real-path happy-path assertion
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases, dyn-dyn-hook-state
- **Severity**: minor
- **Concern**: The parent-directory regression never proves the real-path happy path, so a bug that always exits before promotion could still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Add the real-path existence and row-match assertions for the non-blocked branch, and keep the redirected-tree-empty assertion for the blocked branch.
  - From codex-specialist-edge-cases: Add the missing success assertion on the real $TMPDIR/larch-read-poll/read-…state path and require a regular file with the expected fresh row.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_7: [OUT_OF_SCOPE] Non-directory state_dir pre-mutation guard is untested
- **Reviewer(s)**: cursor-specialist-testing, dyn-dyn-hook-state
- **Severity**: minor
- **Concern**: There is no regression for a non-directory `state_dir`, so the pre-mutation fail-open path is not proven.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add a test that creates a non-directory at state_dir and asserts silent fail-open behavior with no writes.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

