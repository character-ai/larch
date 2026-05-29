### FINDING_1: newest_activity_mtime buffers full find output
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `newest_activity_mtime` stores the full bounded `find` result before scanning, which can make `/cleanup` memory-heavy for active sessions with many artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: semver-unsafe version tiebreak for equal install stamps
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: When cached versions have equal install stamps, lexicographic sorting can rank versions incorrectly, such as `29.1.9` above `29.1.10`, causing the wrong rollback directory to be retained or pruned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_3: duplicated stat_mtime implementations can drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `upgrade-larch` and `cleanup` each define their own portable `stat_mtime`, so future platform fixes must be duplicated and may diverge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: legacy stamp backfill can preserve inflated mtimes
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `backfill_legacy_install_stamps` can turn touch-inflated mtimes into permanent install stamps on the first prune, causing legacy directories to outrank newer unstamped installs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: read_install_stamp is called twice per cached version
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `list_cached_versions_by_install_stamp` performs redundant stamp reads while building sort keys.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: retained-version tracking uses brittle space-separated strings
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Retained versions are tracked as a space-separated string with `wc -w` and membership checks, which is harder to extend safely than arrays.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: prune log wording understates max-8 policy
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The prune log says it is keeping “up to 8,” which may imply fewer directories can remain when the cache has at least eight candidates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] TMP_PATTERNS omits claude-design-* cleanup
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `/tmp` cleanup patterns do not include `claude-design-*`, so design sessions that fell back to `/tmp` are not matched.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] stable release resolution trusts API order
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `get_stable_releases` can choose the first stable tag returned by the GitHub API instead of the semver-latest stable tag if API ordering diverges.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_10: /tmp pattern cleanup skips files
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `/tmp` pattern cleanup only deletes directories, so stale loose files matching cleanup patterns can persist indefinitely.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_11: max-8 pruning can evict versions still in use
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The global max-8 install-stamp retention policy only seeds/protects the executing version and can prune an older cached version that another active worktree or parked session is still using.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_12: sessionstart-health comment alignment missing or disputed
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Reviewers disagree on whether `scripts/sessionstart-health.sh` still needs comment-only keepalive alignment: one reports planned comment drift, while another says the script has no relevant keepalive prose and the advisory update was satisfied elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_13: missing concurrent-worktree hook-routing harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No offline test proves hook tmpdir resolution chooses the session matching the current worktree when multiple implement session roots with different `CLONE_PATH` values exist.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_14: missing negative test for depth-6 activity
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Cleanup tests do not cover fresh activity only below the `maxdepth 5` scan boundary, so regressions around activity depth could delete or retain sessions unexpectedly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_15: missing legacy multi-field keepalive parser test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: No test fixture verifies that legacy `.larch-keepalive` files with PID/PPID/NOTE fields still route hooks correctly during rolling upgrades.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_16: unused STAT_FAIL_VERSION prune harness stub
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `STAT_FAIL_VERSION` exists in the prune harness but is not exercised, leaving stat/backfill failure handling without coverage or creating dead test code.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_17: missing exactly-eight prune test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The prune harness does not explicitly assert that exactly eight cached directories are all retained.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_18: install stamp writes can follow symlinked cache entries
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `write_install_stamp` and `backfill_legacy_install_stamps` can operate on symlinked version-shaped entries under the cache parent without canonical containment checks, allowing stamp writes outside the cache tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_19: activity scan follows symlinks
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `newest_activity_mtime` stats `find` results in a way that can follow symlinks, so external file mtimes can prevent age-based cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] keepalive identity parsing lacks ownership verification
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Keepalive identity parsing does not verify file ownership before trusting session-root metadata.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_21: backfill_legacy_install_stamps extends the plan
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `backfill_legacy_install_stamps` is an implementation extension beyond the plan’s numbered prune steps, though the reviewer notes it is documented and covered by a migration test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_22: make lint acceptance was not verified
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The acceptance criterion that `make lint` is green was not executed in the read-only review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
