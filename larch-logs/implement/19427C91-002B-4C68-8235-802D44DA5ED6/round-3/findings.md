### FINDING_1: Duplicate stat_mtime helpers in upgrade-larch and cleanup
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Duplicate `stat_mtime` helpers exist in `upgrade-larch.sh` and `cleanup.sh`. A future portability fix applied in one script may not be carried to the other.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: Redundant read_install_stamp I/O in list_cached_versions_by_install_stamp
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `read_install_stamp` is called twice per version in `list_cached_versions_by_install_stamp`, causing unnecessary I/O on every prune listing pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: test-resolve-implement-tmpdir harness discoverability gaps
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The new `test-resolve-implement-tmpdir` harness lacks a sibling `.md` contract, an `agent-lint.toml` Makefile-only entry (unlike `test-cleanup`), and a row in `docs/linting.md`— inconsistent with peer harness discoverability and documentation patterns.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_4: Max-8 install-stamp cap lacks in-use, session, and age protection
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Prune retention is capped at eight newest install stamps with no version-dir age window, session pins, or in-use discovery. Long-running `/design` or `/review` jobs, parked sessions on older cached versions, or worktrees on versions outside the newest eight can lose their plugin directory after eight newer installs/releases; the blown-away symptom class persists globally across worktrees.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_5: backfill_legacy_install_stamps runs every prune and freezes touch-inflated mtimes
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `backfill_legacy_install_stamps` runs on every prune pass, writing `.larch-installed-at` from directory mtime (including touch-inflated values) for unstamped legacy dirs before ranking. This cements zombie high-mtime cache dirs into the top-eight set, largely nullifies stamp-presence tier distinction after the first prune, and can evict real rollback targets until eight newer installs occur.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_6: Lexicographic version tiebreak on equal install stamps
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: After equal install stamps, ranking uses lexicographic version comparison. Same-second installs can rank `29.1.9` above `29.1.10`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: Activity scan maxdepth-5 boundary may misclassify active sessions
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `newest_activity_mtime` uses `find -maxdepth 5`. Activity at depth 6+ (e.g. deep run-log layouts under `larch-logs/...`) does not refresh newest-activity classification; active sessions may be treated as stale and deleted. The boundary is tested at depth 5 but not depth 6.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] sessionstart-health.sh plan-listed comment refresh not applied
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Plan-listed comment refresh was not applied in `scripts/sessionstart-health.sh`. No functional regression; resolver comments live elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] cleanup TMP scan uses /tmp only, not /private/tmp
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Cleanup TMP scan uses `/tmp` only, not `/private/tmp`. Rare session roots only under `/private/tmp` may not be age-reaped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_10: Prune seeds only ACTUAL_VERSION, not basename(PLUGIN_ROOT)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: On already-latest runs, prune seeds only `ACTUAL_VERSION`, not `basename(PLUGIN_ROOT)`. When metadata reports `31.0.0` but Claude still executes from cached `30.9.0` outside the top-eight stamps, prune can `rm -rf` the live `30.9.0` directory under a running process.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_11: Age-based cleanup can delete active or long-paused session tmpdirs
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Removing keepalive skip and singleton abort lets `/cleanup` delete session tmpdirs during concurrent Claude use when shallow activity looks stale. Long-paused `/design` or `/implement` sessions with no writes within `find -maxdepth 5` for 7+ days lose their tmpdir while Claude still runs, destroying `session-env`, CMD_JSON-bearing meta, and hook tmpdir resolution.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_12: cap-trims test uses fresh mtime instead of stale executing-dir policy
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: The cap-trims test passes via a fresh mtime rather than production retention policy. A fresh `30.9.0` dir gets epoch backfill stamp and survives; a production old executing dir would be pruned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_13: Missing cap-pressure test for semver-newer-than-stable dirs in top eight
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No cap-pressure test asserts that semver-newer-than-stable cached dirs survive when in the newest-eight install-stamp set. Reintroducing Stage A delete-newer-than-stable would not fail CI; pre-release rollback dirs could be deleted again under cap pressure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_14: Missing SESSION_ID disambiguation test in test-resolve-implement-tmpdir
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The harness unsets `LARCH_TOKEN_SESSION_ID` and has no `SESSION_ID` disambiguation case. Slim keepalive or resolver regression on session-id binding would not fail CI despite production hooks setting `LARCH_TOKEN_SESSION_ID`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_15: Missing exactly-eight cached dirs zero-deletion test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Off-by-one prune when count equals eight could slip through. An exactly-eight stamped-dir fixture with no deletions and a "No old versions to prune" message is untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_16: Valid LARCH_CLEANUP_RETENTION_DAYS override not tested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Only invalid retention is tested; custom positive value parsing for `LARCH_CLEANUP_RETENTION_DAYS` could regress silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_17: Session cleanup rm -rf without symlink rejection
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Age-based cleanup uses `rm -rf` on session entries without rejecting symlinked top-level directories. A same-UID attacker or buggy tool creating `~<TMPDIR>` as a symlink to another tree can cause cleanup to delete the symlink target via `rm -rf`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_18: LARCH_TEST_TMP_ROOT redirects destructive globs without production opt-in gate
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `LARCH_TEST_TMP_ROOT` redirects destructive pattern globs without a production opt-in gate. Stale CI or shell exports pointing at a project directory could cause `/cleanup` `rm -rf` or `rm -f` to match `larch-*` and `claude-*` patterns outside `/tmp`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] Keepalive file remains same-UID tamperable hook-routing input
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: The keepalive file is still same-UID tamperable hook-routing input. A compromised same-UID process rewriting `CLONE_PATH` in `.larch-keepalive` could hijack Stop hook binding to another worktree session dir. Pre-existing; not introduced by this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_20: Activity scan buffers full find output in memory
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The activity scan buffers full `find` output in memory. Very large session trees can make `/cleanup` slow or memory-heavy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_21: Failed stable verification skips prune entirely
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Failed stable verification skips prune entirely. Repeated failed upgrades leave an unbounded version cache until a verified run succeeds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] TMP_PATTERNS lacks claude-design-* for /tmp fallback
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `TMP_PATTERNS` lacks `claude-design-*` for `/tmp` fallback. Design sessions in `/tmp` when cache is unwritable are not age-cleaned under `/tmp` patterns. Pre-existing gap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_23: backfill_legacy_install_stamps plan, doc, and harness drift
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `backfill_legacy_install_stamps` was added but is not in the plan and contradicts stamp-presence-first migration semantics. Consumer docs (`installation-and-setup.md`, `SECURITY.md`) omit pre-prune backfill documented in `upgrade-larch.md`, breaking the edit-in-sync contract. Harness cases in `test-upgrade-larch-prune.sh` encode backfill behavior not listed in the plan testing strategy, allowing CI to pass while enforcing unapproved behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
