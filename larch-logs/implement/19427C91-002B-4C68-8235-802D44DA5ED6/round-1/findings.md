### FINDING_1: duplicated stat_mtime helper
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `stat_mtime()` is duplicated in cleanup and upgrade scripts, risking divergent portability or ordering fixes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: install-stamp listing reads stamps twice
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `list_cached_versions_by_install_stamp` reads each `.larch-installed-at` twice per directory, adding avoidable I/O during prune/list operations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: fragile retained-list counting
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `prune_cached_versions` uses `wc -w` over a space-separated retained list, which is fragile if retention bookkeeping changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: stamp-write failure with existing cache dir is untested
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The prune harness lacks coverage for failed `.larch-installed-at` writes when the target cache dir already exists, so regressions could prune the just-installed version despite warn-only stamp failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_5: cleanup may perform expensive per-session scans
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Cleanup now always runs a per-session `find -maxdepth 5` over cache entries, which can be slow on hosts with many session dirs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: cleanup skill dropped explicit NEVER guidance
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `skills/cleanup/SKILL.md` dropped the NEVER section instead of replacing the old singleton-abort rule with age-based guidance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] cleanup maxdepth can miss deeper activity
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `newest_activity_mtime` scans only to `-maxdepth 5`, so deeper active artifacts such as design plan-review files can be missed and stale-looking session dirs may be deleted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_8: stale upgrade-larch test comment
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: A test comment still references newer-than-stable pruning removed by the Stage A redesign, creating misleading maintenance context.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] latest stable tag selection may not pick max semver
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `LATEST_STABLE` selects the first paginated stable tag rather than the maximum semver, so release ordering changes could target an older stable version.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_10: missing absent-target cache-dir prune harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The `absent-target-fills-eight` case does not actually exercise a missing `ACTUAL_VERSION` cache dir at prune time, leaving regressions in absent-target retention/count behavior uncovered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_11: stale keepalive cleanup behavior is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: There is no test that stale session dirs containing `.larch-keepalive` are deleted, so a keepalive skip could return without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] concurrent-worktree resolver regression test missing
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The implement tmpdir resolver lacks a dedicated concurrent-worktree harness, so hooks could bind to the wrong tmpdir when multiple clones have active sessions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_13: TMP_REMOVED cleanup contract is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `/tmp` pattern scanning and `TMP_REMOVED=1` behavior are not covered by `make test-cleanup`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_14: cleanup test sed patch can drift from production
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The cleanup harness sed-patches the production `/tmp` loop, so production syntax could drift away from what CI actually exercises.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_15: misleading absent-target test name
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The case name `absent-target-fills-eight` implies absent-target behavior is covered even though the test creates the target cache dir.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] cleanup /tmp sweep lacks ownership check
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: The `/tmp` glob sweep does not check current-user ownership before `rm -rf`, which could matter on misconfigured shared `/tmp` systems.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] implement tmpdir routing trusts writable keepalive metadata
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Hook routing still trusts same-user-writable `.larch-keepalive` metadata under predictable tmp/cache paths, leaving a pre-existing spoofing surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] version cache prune can remove active plugin roots
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Install-stamp max-8 pruning does not track active design/review or other non-implement plugin roots, so long-running sessions on older versions can lose their plugin directory after newer installs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_19: cleanup silently disables deletion if date fails
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: If `date +%s` fails and `NOW=0`, cleanup can report success while silently disabling age-based deletions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_20: age-only cleanup can delete long-idle live sessions
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Cleanup can delete session dirs idle longer than retention even if Claude is still running, breaking long-paused design or idle implement sessions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_21: unstamped legacy cache dirs are evicted too aggressively
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Stamp-presence-first ordering can delete multiple still-in-use unstamped legacy cache versions during the first post-change prune.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_22: cleanup swallows find errors
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Suppressed `find` failures can under-read session activity, leaving stale parent mtimes and causing active sessions to be misclassified stale.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] claude-design tmp fallback is not reaped
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `claude-design-*` is absent from `TMP_PATTERNS`, so design `/tmp` fallback dirs are not age-reaped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] concurrent upgrade-larch lacks locking
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Concurrent `upgrade-larch` runs can interleave install and prune operations across worktrees.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
