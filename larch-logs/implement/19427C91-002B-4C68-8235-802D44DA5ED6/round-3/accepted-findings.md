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


### FINDING_17: Session cleanup rm -rf without symlink rejection
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Age-based cleanup uses `rm -rf` on session entries without rejecting symlinked top-level directories. A same-UID attacker or buggy tool creating `~<TMPDIR>` as a symlink to another tree can cause cleanup to delete the symlink target via `rm -rf`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_23: backfill_legacy_install_stamps plan, doc, and harness drift
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `backfill_legacy_install_stamps` was added but is not in the plan and contradicts stamp-presence-first migration semantics. Consumer docs (`installation-and-setup.md`, `SECURITY.md`) omit pre-prune backfill documented in `upgrade-larch.md`, breaking the edit-in-sync contract. Harness cases in `test-upgrade-larch-prune.sh` encode backfill behavior not listed in the plan testing strategy, allowing CI to pass while enforcing unapproved behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_3: test-resolve-implement-tmpdir harness discoverability gaps
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The new `test-resolve-implement-tmpdir` harness lacks a sibling `.md` contract, an `agent-lint.toml` Makefile-only entry (unlike `test-cleanup`), and a row in `docs/linting.md`— inconsistent with peer harness discoverability and documentation patterns.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_5: backfill_legacy_install_stamps runs every prune and freezes touch-inflated mtimes
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `backfill_legacy_install_stamps` runs on every prune pass, writing `.larch-installed-at` from directory mtime (including touch-inflated values) for unstamped legacy dirs before ranking. This cements zombie high-mtime cache dirs into the top-eight set, largely nullifies stamp-presence tier distinction after the first prune, and can evict real rollback targets until eight newer installs occur.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


