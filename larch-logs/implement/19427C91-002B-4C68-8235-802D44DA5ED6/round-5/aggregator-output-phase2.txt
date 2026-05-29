### FINDING_1: Duplicate `stat_mtime` helpers across production scripts
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `stat_mtime` (or equivalent) is duplicated in `skills/upgrade-larch/scripts/upgrade-larch.sh` (lines 69–83) and `skills/cleanup/scripts/cleanup.sh` (lines 18–32). Portability or bugfix changes to mtime reading must be applied twice or the copies drift. Extract a shared helper (e.g. `scripts/lib-stat-mtime.sh`) or source one canonical copy from the other.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: Install stamp read twice per cached version during listing
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `list_cached_versions_by_install_stamp` reads each install stamp twice per version (lines 126–128 in `upgrade-larch.sh`), adding unnecessary I/O on every prune and a theoretical mismatch if the stamp disappears between reads. Read the stamp once after a single successful `read_install_stamp`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Brittle space-delimited retained-version membership
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Retained-set membership and cap checks use a space-delimited string plus `wc -w` (e.g. `upgrade-larch.sh` lines 137–146, 165). Safe for numeric dotted versions today but brittle if retention logic grows or version tokens are non-word characters; unquoted word-splitting could break membership or counting. Prefer an integer `retained_count`, newline-delimited membership, marker-file set, or `read` loops.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_4: Lexicographic version tie-break can mis-rank equal-second installs
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Install-stamp tie-break uses lexicographic version sort (line 134 in `upgrade-larch.sh`). Equal-second installs could rank 9.x above 10.x and prune the wrong directory. Use numeric padded sort for tie-break or document the lexicographic tie-break explicitly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: `newest_activity_mtime` buffers entire `find` output in memory
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `newest_activity_mtime` in `cleanup.sh` (lines 39–51) buffers all `find` output before scanning (`paths=$(find ...)` and `<<< "$paths"`). Very large session trees at depth 5 can consume large memory or stress shell limits. Stream `find` output instead of materializing all paths first.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: Harness `write_install_stamp` name collides with production helper
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The harness helper `write_install_stamp` in `test-upgrade-larch-prune.sh` (lines 55–58) shares a name with the production helper. Readers may assume harness and production share semantics. Rename the harness helper (e.g. `seed_install_stamp`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] Plan-expected `sessionstart-health.sh` keepalive comment not present
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The plan listed a comment-only update describing `.larch-keepalive` as a slim session-identity record in `scripts/sessionstart-health.sh`, but that file has no keepalive-related diff on this branch (only `SECURITY.md` and test fixtures were updated elsewhere). Maintainers reading the plan file list may expect in-script commentary that was never added. No functional gap, but plan fidelity is incomplete—add a short comment near the `lib-resolve-implement-tmpdir` invocation or amend the plan to name `SECURITY.md` as the sole canonical description.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] `get_stable_releases` picks first stable tag, not semver max
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `get_stable_releases` in `upgrade-larch.sh` (lines 49–66) picks the first API stable tag without semver max selection. Pre-existing and unrelated to #3174 retention redesign; future issue if tag ordering is not newest-first.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_9: Prune retains metadata version but may delete executing plugin root
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: After round 4 removed `INSTALLED_VERSION` seeding, prune seeds only metadata `ACTUAL_VERSION`, not `basename(CLAUDE_PLUGIN_ROOT)` / executing cache dir (`upgrade-larch.sh` lines 148–195, 244–247). Example: nine cached versions, metadata 31.0.0, session still running from 30.9.0—already-latest upgrade prunes 30.9.0 underfoot. Retain `INSTALLED_VERSION` when its cache dir exists, seed executing `PLUGIN_ROOT` version, or defer prune until restart; document dual retention of registered vs executing roots.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_10: Docs claim no restart on already-latest conflicts with prune deleting active root
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `docs/installation-and-setup.md` (lines 36–40) says no restart when already on latest, but prune may delete the unstamped executing plugin root. An operator skips restart, reruns upgrade-larch, cache is full, and the active `PLUGIN_ROOT` is deleted. Align docs with prune behavior or restore executing-root retention.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_11: Depth-5 activity scan misses deeper writes; active sessions misclassified stale
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `newest_activity_mtime` uses `find -maxdepth 5` (`cleanup.sh` lines 40–51). Activity solely below depth 6 leaves a stale `newest_activity`; long-parked `/implement` or `/design` sessions with writes only at depth 6+ (or copied design publish trees) can be misclassified stale and deleted while Claude still runs. Concurrent `/cleanup` is no longer blocked by singleton/keepalive for this path. Document depth-5 as an implement-only boundary and the `/cleanup` trust model in `SECURITY.md`; raise `maxdepth` with tests, add targeted glob scans for known deep artifacts, or add depth-6 stale-root/fresh-leaf negative harness coverage when scan depth changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_12: Max-8 stamp cap lacks in-use / cross-clone protection for older versions
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Max-8 install-stamp retention has no in-use age window or session pins (accepted per plan). A job on an older stamped version (e.g. ninth concurrent worktree design, or work on 42.4.0 across eight releases) loses its version dir on the next install from another clone. Document the tradeoff; consider always seeding executing `PLUGIN_ROOT` version; revisit only if cross-clone protection remains a goal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_13: `LARCH_CLEANUP_RETENTION_DAYS=0` invalid; cannot disable reaping
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `parse_retention_days` treats `0` as invalid and falls back to 7 (`cleanup.sh` lines 55–63), so `LARCH_CLEANUP_RETENTION_DAYS=0` cannot disable age-based reaping. Tests exercise `abc` invalid input but not the `0`-day case, allowing silent doc/validation drift. Document positive-only semantics, add an explicit disable value, or add a harness case expecting warn-and-fallback-to-7 for `0`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_14: No harness for corrupt/non-numeric `.larch-installed-at` under cap pressure
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: No test covers corrupt/non-numeric `.larch-installed-at`; `read_install_stamp` rejects and the dir falls back to mtime tier. Under cap pressure, a legacy dir with touch-bumped mtime and a garbage stamp file may outrank real stamped installs and survive eviction incorrectly. Add a prune case with invalid stamp contents and controlled mtimes asserting mtime-tier ordering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_15: Accepted max-8 cap tradeoff not encoded in tests or contract docs
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Operator-accepted max-8 cap tradeoff (job across 9+ releases loses version dir) is documented in plan but not encoded in `test-upgrade-larch-prune.sh` / `test-upgrade-larch-prune.md`. Future refactors could reintroduce pin/age-window logic without a failing test that encodes the accepted regression. Add a scenario test or explicit contract note tying harness cases to the 8-release survival model.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_16: Unvalidated `LARCH_TEST_TMP_ROOT` redirects destructive cleanup scans
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Production `cleanup.sh` (line 104) honors unvalidated `LARCH_TEST_TMP_ROOT`, redirecting destructive pattern scans away from `/tmp`. A stale test env export or poisoned shell profile setting `LARCH_TEST_TMP_ROOT` to `$HOME` or a repo tree could cause `/cleanup` to delete age-qualified `claude-implement-*` / `larch-*` matches outside `/tmp`. Require explicit opt-in before honoring the override or keep the seam test-only; document in `SECURITY.md` and configuration docs if retained.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_17: Install stamps are same-UID writable and fully trusted for retention ranking
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Install stamps are same-UID writable and fully trusted for retention ranking (`upgrade-larch.sh` lines 85–134). A local process can write inflated `.larch-installed-at` values to keep junk version dirs in the top-8 retained set or skew eviction. Document stamps as same-UID recency signals in `SECURITY.md`; optional future hardening: ignore non-owned stamp files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_18: `SECURITY.md` lacks `/cleanup` trust-boundary documentation after retention redesign
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `SECURITY.md` (around line 239) lacks a `/cleanup` trust-boundary paragraph after the retention redesign. Auditors may assume old singleton/keepalive protections still apply to session tmpdir deletion. Add a concise `/cleanup` section covering concurrent runs, retention days, depth-5 scan, and session-tmpdir sensitivity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] Prune `rm -rf` does not reject symlinked cache entries
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Prune `rm -rf` in `upgrade-larch.sh` (lines 176–184) does not reject symlinked version cache entries. A same-UID symlink under cache could redirect deletion outside the cache tree. Pre-existing; add `-L` checks or canonicalize before `rm` in a follow-up.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] Implement tmpdir resolver scans `/tmp` without ownership checks
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `lib-resolve-implement-tmpdir.sh` (lines 29–54) scans `/tmp` `claude-implement-*` without ownership checks. A same-host attacker with writable `/tmp` could plant matching identity records (mitigated by cwd/session binding). Pre-existing; unchanged by this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_21: Legacy unstamped dirs rank by touch-inflated mtime on first post-change prune
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Legacy unstamped dirs rank by touch-inflated mtime after touch-helper removal (`upgrade-larch.sh` lines 112–135, 289–292). First post-change prune can evict an in-use unstamped version while keeping touch-fresh idle dirs. Best-effort stamp all cached version dirs missing `.larch-installed-at` before ranking, or run a one-time migration touch/stamp.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_22: Age-only cleanup deletes sessions despite keepalive or open Claude UI
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Age-only cleanup in `cleanup.sh` (lines 65–71, 78–85) deletes sessions with no recent file activity regardless of keepalive or open Claude. A `/design` paused more than seven days with no tmpdir writes loses the session dir while the UI is still open. Count identity-file mtime as activity, detect live sessions, or document mandatory refresh; add harness for stale tree plus keepalive.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
