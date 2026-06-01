### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: code-quality: skills/upgrade-larch/scripts/upgrade-larch.sh:221-244
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] backfill_install_stamps duplicates stamp-file write logic from write_install_stamp instead of sharing one helper Future stamp-format or error-handling changes may be updated in one path and missed in the other Extend write_install_stamp with an optional stamp value and call it from backfill_install_stamps after mtime validation
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: risk-integration: skills/upgrade-larch/scripts/upgrade-larch.sh:219-303
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No automated test covers prune retention stamp or backfill semantics CI passes while a future edit re-breaks protected-version retention or re-deletes the running cache dir; same class as the 47.0.34 incident Add scripts/test-upgrade-larch-prune.sh (or equivalent) with a temp LARCH_CACHE_DIR fixture and Makefile target per plan manual check
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: risk-integration: (PR / plan verification)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Plan-required manual retention and stamp-on-unverified checks are not evidenced in the diff Merge without proof the incident scenario was simulated; regression could ship again Run plan scratch simulation and document in PR test plan or commit a harness
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: risk-integration: skills/upgrade-larch/scripts/upgrade-larch.sh:219-240
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] backfill_install_stamps has no test for success failure or read-only cache Read-only cache causes repeated warn_install_stamp_failure on every prune with no CI signal Add harness cases for backfill success skip and write failure
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: risk-integration: (branch)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Lint success is only implied by commit message not diff Undetected shellcheck or lint-bash32 failure could merge if CI was not run Confirm green make lint on PR CI
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: security: skills/upgrade-larch/scripts/upgrade-larch.sh:221-244
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] backfill_install_stamps writes .larch-installed-at via glob paths without rejecting symlinked version_dir entries A same-UID attacker who plants a numeric symlink under the plugin cache can cause prune-time stamp writes outside LARCH_CACHE_DIR when backfill runs Skip symlinks before write (e.g. [ -L "$version_dir" ] && continue) or enumerate with ! -type l like /cleanup; confirm resolved path stays under LARCH_CACHE_DIR
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: code-quality: skills/upgrade-larch/scripts/upgrade-larch.sh:185-297
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Third parallel [0-9]*/ cache directory walk added (backfill list delete) Higher maintenance burden and risk of inconsistent guards between three loops Defer unless refactoring; consider single enumerator on a later touch
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_23: risk-integration: skills/upgrade-larch/scripts/upgrade-larch.sh:383-418
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Unverified installs get a fresh date +%s stamp before exit 1 while prune is skipped. On ACTUAL_VERSION != LATEST_STABLE the cache dir is stamped with now; a later verified prune may keep that tree over older stamped rollbacks. Document the tradeoff or stamp unverified installs from mtime like backfill instead of date +%s.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_24: correctness: skills/upgrade-larch/scripts/upgrade-larch.sh:259-276
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Two protected seeds share the eight-word retention cap with ranked versions. With >8 cached versions and both protected outside the natural top eight, newer stamped rollbacks can be evicted while the running tree is kept. Accept as designed or emit a one-line log when retention is dominated by protected seeds.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_25

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_25: correctness: skills/upgrade-larch/scripts/upgrade-larch.sh:221-243
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Backfill persists mtime as install stamp. A copied or touched cache dir can get a wrong rank on prune; only re-downloadable dirs are affected. Keep plan-documented caveat; optional future sanity checks on mtime vs neighbors.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_26

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_26: architecture: skills/upgrade-larch/scripts/upgrade-larch.sh:221-243
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] backfill_install_stamps toggles nullglob without ERR trap restore. Rare set -e abort could leave nullglob enabled for the rest of the script. Add a short ERR trap to restore shopt like other helpers or avoid toggling in the function body.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: code-quality: skills/upgrade-larch/scripts/upgrade-larch.sh:246-308
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] prune_cached_versions relies on INSTALLED_VERSION global set only at lines 306-308 A future call inserted before line 308 would prune without protecting the running tree Pass installed version into prune_cached_versions or re-derive basename PLUGIN_ROOT inside the function
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

