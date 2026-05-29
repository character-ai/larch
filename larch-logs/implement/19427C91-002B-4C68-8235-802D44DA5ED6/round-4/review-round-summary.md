# Review Round 4

- Mode: `diff`
- 7 accepted, 8 rejected (6 exonerated)

## Accepted Findings

### FINDING_1: Keepalive guard blocks age-only session cleanup
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `should_remove_by_age` in `skills/cleanup/scripts/cleanup.sh` still returns early when `.larch-keepalive` exists (line 83), contradicting the plan’s age-only contract. Every `session-setup` writes that sentinel, so stale session trees past `LARCH_CLEANUP_RETENTION_DAYS` are never removed, `~/.cache/larch/sessions` keeps growing (original keepalive-skip / zombie-dir behavior), and acceptance that dirs are not skipped by sentinel alone is not met.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Remove the [ -f "$entry/.larch-keepalive" ] guard; rely on newest-activity mtime within maxdepth 5 only.


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


