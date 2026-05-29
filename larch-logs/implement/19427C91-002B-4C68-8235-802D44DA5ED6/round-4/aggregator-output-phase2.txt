Reviewing a few source files only to confirm merge boundaries—not to change anything.
Normalized aggregator output from the supplied reviewer slots. Merges follow shared behavioral risk; distinct code paths or fixes stay separate.

### FINDING_1: Keepalive guard blocks age-only session cleanup
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `should_remove_by_age` in `skills/cleanup/scripts/cleanup.sh` still returns early when `.larch-keepalive` exists (line 83), contradicting the plan’s age-only contract. Every `session-setup` writes that sentinel, so stale session trees past `LARCH_CLEANUP_RETENTION_DAYS` are never removed, `~/.cache/larch/sessions` keeps growing (original keepalive-skip / zombie-dir behavior), and acceptance that dirs are not skipped by sentinel alone is not met.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Remove the [ -f "$entry/.larch-keepalive" ] guard; rely on newest-activity mtime within maxdepth 5 only.

### FINDING_2: Harness asserts keepalive prevents stale-dir removal
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `skills/cleanup/scripts/test-cleanup.sh` case `stale-dir-with-keepalive-kept` expects stale dirs with `.larch-keepalive` to be retained (`CACHE_REMOVED=0`), codifying the old sentinel skip so CI stays green if plan-required removal is never shipped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Replace with stale-dir-with-keepalive-removed expecting CACHE_REMOVED=1; update test-cleanup.md.

### FINDING_3: Operator docs conflict on keepalive vs age-only cleanup
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Published operator docs (README, `docs/skills.md`, `docs/workflow-lifecycle.md`) describe age-based reaping, while `skills/cleanup/SKILL.md`, `skills/cleanup/scripts/cleanup.md`, `docs/linting.md` (and partially `SECURITY.md`) still say or imply keepalive entries are never removed. Operators run `/cleanup` expecting a retention window while nearly all session dirs are skipped; regressions may be misread as fixed while zombie dirs remain.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Unify all docs to the chosen contract (plan: age-only, no sentinel skip)
  - From cursor-specialist-testing-output.txt: Unify all cleanup docs and the linting harness row after removing the keepalive guard.
  - From cursor-specialist-security-output.txt: Document keepalive exemption in SECURITY.md or remove the skip for finished sessions.
  - From cursor-specialist-edge-cases-output.txt: Align docs with behavior or remove the keepalive skip so implementation matches the published contract.
  - From cursor-specialist-plan-fidelity-output.txt: Reword the test-cleanup row to describe depth-5 age-based pruning only.

### FINDING_4: Unconditional INSTALLED_VERSION seed in prune
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `prune_cached_versions` in `skills/upgrade-larch/scripts/upgrade-larch.sh` (lines 158–161) unconditionally seeds `INSTALLED_VERSION` (PLUGIN_ROOT basename) beyond the plan’s ACTUAL_VERSION-only seed. An upgrade run from an old plugin root can force-retain that version even when it is outside the newest-eight by install stamp, displacing a newer stamped install and reproducing unexpected version loss.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove INSTALLED_VERSION pre-seed unless explicitly product-required; align upgrade-larch.md
  - From cursor-specialist-plan-fidelity-output.txt: Seed only ACTUAL_VERSION then fill to eight by install stamp, or amend plan/acceptance if unconditional executing-root retention is intended.

### FINDING_5: Activity scan maxdepth 5 may miss deeper session state
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `newest_activity_mtime` uses `find … -maxdepth 5` (`cleanup.sh` line 40). Live state or design plan-review files at depth 6–7 would not refresh the activity clock; an active `/design` or `/implement` could look stale and be deleted if the keepalive skip is removed. Harness covers depth 5 but not beyond.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Longer maxdepth or document exclusion; add harness if depth is raised
  - From cursor-specialist-testing-output.txt: Document depth-5 limit or add depth-6 fixture test if deeper run-log paths are plausible.
  - From cursor-specialist-edge-cases-output.txt: Document the depth-5 contract; add harness cases when layouts change; raise maxdepth only after auditing session tree depth.

### FINDING_6: Upgrade prune no longer protects long-running session plugin roots
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Prune logic (`upgrade-larch.sh` ~148–200) dropped session/fallback pin scanning; only install-stamp cap plus upgrade-runner `PLUGIN_ROOT` / `INSTALLED_VERSION` seeding remain. Eight newer releases while `/design` (or review/implement) stays on an older version can evict that version’s cache dir (`rm -rf`) even though the job still references it via design rehydration—version blown away without pin or touch mitigations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Reintroduce narrow ownership-checked version discovery for active design/review/implement sessions, or document that only the eight newest installs plus the upgrade runner root are protected.
  - From cursor-specialist-edge-cases-output.txt: Refresh install stamps from design/implement session writers or retain plugin roots referenced by design-env files; otherwise document that only the eight most recently installed cache dirs are safe for long-running design/review.

### FINDING_7: Redundant read_install_stamp per version directory
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `list_cached_versions_by_install_stamp` calls `read_install_stamp` twice per cached version (`upgrade-larch.sh` lines 126–128), causing redundant stat/read on prune with many version dirs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Read stamp once per iteration
  - From cursor-specialist-edge-cases-output.txt: Read the stamp once per iteration and reuse the value for has_stamp and ts.

### FINDING_8: Duplicated stat_mtime helpers across cleanup and upgrade-larch
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `stat_mtime` / dual-stat portability helpers are duplicated in `skills/cleanup/scripts/cleanup.sh` (18–32) and `skills/upgrade-larch/scripts/upgrade-larch.sh` (69–83), increasing maintenance burden.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract shared lib or accept documented duplication

### FINDING_9: wc -w counts space-separated retained version string
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Retention cap uses `wc -w` on a space-separated `retained` string (`upgrade-larch.sh` line 170); a future format change could miscount the retained set.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Track integer count or use array length

### FINDING_10: find in activity scan follows symlinks outside session tree
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `newest_activity_mtime` uses `find` without `-P`, so activity can be anchored outside the session directory via symlinks, keeping stale session dirs artificially young and leaving CMD_JSON-bearing `.meta` files under same-UID cache longer than intended.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Use find -P (or skip symlinks) so retention is confined to the session directory.

### FINDING_11: session-setup keepalive writes unvalidated paths/ids
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `scripts/session-setup.sh` (248–254) writes `.larch-keepalive` from unvalidated `CLONE_PATH`/`SESSION_ID`; resolver uses line-oriented awk, so newlines in PWD or session id can break field parsing and mis-bind hooks to another session tmpdir.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Reject control characters/newlines before write, or parse with the same hardened rules as session-env.

### FINDING_12: No harness asserts fresh install writes .larch-installed-at
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `test-upgrade-larch.sh` / `test-upgrade-larch-prune.sh` do not assert that a successful fresh install writes `.larch-installed-at` (only pre-seeded stamps); `write_install_stamp` could be dropped from the install path without CI signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Assert -f and numeric contents of .larch-installed-at on the installed version dir after install-then-prune-fills-eight.

### FINDING_13: No harness for valid non-default LARCH_CLEANUP_RETENTION_DAYS
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `test-cleanup.sh` only covers invalid `LARCH_CLEANUP_RETENTION_DAYS`; a regression in `parse_retention_days` for valid custom values would not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a case with e.g. LARCH_CLEANUP_RETENTION_DAYS=1 and mtimes straddling the cutoff.

### FINDING_14: STAT_FAIL_VERSION stub unused in prune harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `STAT_FAIL_VERSION` in `test-upgrade-larch-prune.sh` (150–168) is never used; `stat` / `read_install_stamp` failures during ordering are unguarded by CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add one prune case setting STAT_FAIL_VERSION on an unstamped dir and assert fallback retention behavior.

### FINDING_15: Legacy unstamped cache dirs lack mtime backfill on prune
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Unstamped legacy dirs under `~/.cache/larch` sort only by directory mtime after `backfill_legacy_install_stamps` was removed; first post-change prune on machines with touch-bumped unstamped dirs can evict the wrong rollback target before operators reinstall each version.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Restore one-time mtime-to-stamp backfill on prune or document a migration step to stamp legacy dirs.

### FINDING_16: [OUT_OF_SCOPE] Hook resolver trusts modifiable .larch-keepalive
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `skills/implement/scripts/lib-resolve-implement-tmpdir.sh` (47–65) trusts modifiable `.larch-keepalive` without integrity checks; same-UID tampering can redirect Stop/post-bump binding—pre-existing behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Harden with signed identity or canonical path checks (future work).

### FINDING_17: [OUT_OF_SCOPE] Same-UID can craft .larch-installed-at for sort rank
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Same-UID can craft `.larch-installed-at` to inflate install-stamp sort rank; local cap manipulation only, not cross-user.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Optional: reject non-single-line stamps or cap digit length.
