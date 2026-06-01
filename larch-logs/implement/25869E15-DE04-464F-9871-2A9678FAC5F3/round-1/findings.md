### FINDING_1: code-quality: skills/upgrade-larch/scripts/upgrade-larch.sh:221-244
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] backfill_install_stamps duplicates stamp-file write logic from write_install_stamp instead of sharing one helper Future stamp-format or error-handling changes may be updated in one path and missed in the other Extend write_install_stamp with an optional stamp value and call it from backfill_install_stamps after mtime validation
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: skills/upgrade-larch/scripts/upgrade-larch.sh:185-297
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Third parallel [0-9]*/ cache directory walk added (backfill list delete) Higher maintenance burden and risk of inconsistent guards between three loops Defer unless refactoring; consider single enumerator on a later touch
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: skills/upgrade-larch/scripts/upgrade-larch.sh:246-308
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] prune_cached_versions relies on INSTALLED_VERSION global set only at lines 306-308 A future call inserted before line 308 would prune without protecting the running tree Pass installed version into prune_cached_versions or re-derive basename PLUGIN_ROOT inside the function
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] code-quality: skills/upgrade-larch/scripts/upgrade-larch.sh:199-201
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] list_cached_versions_by_install_stamp reads install stamp twice per stamped dir Slightly redundant I/O on large caches; not introduced by this branch Cache stamp in a local variable after first successful read
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] architecture: skills/upgrade-larch/scripts/upgrade-larch.sh:1-422
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Script not source-safe for offline prune tests Manual verification requires copying functions to a scratch script per plan No change in this PR per plan decision
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] code-quality: skills/upgrade-larch/scripts/upgrade-larch.sh:251
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Prune log says most-recently-installed but retention may keep running version outside top-8 by stamp Operators may misread prune output after explicit running-version protection Update log wording on a follow-up if desired
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 1. **correctness** `skills/upgrade-larch/scripts/upgrade-larch.sh:142-156` — `stat_mtime` returns `0` on failure; backfill correctly skips `mt=0`. Pre-existing helper; unchanged semantics.
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] architecture
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 2. **architecture** Original issue scoped Defect C backfill out; the plan expanded scope and the code implements backfill. This is a requirements/plan divergence, not a logic error — behavior matches the plan.
- **Suggested revision**: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 3. **risk-integration** No committed offline harness for retention (plan Decision 1). Acceptance depends on manual verification; not a code defect.
- **Suggested revision**: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] code-quality
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 4. **code-quality** `backfill_install_stamps` / `prune_cached_versions` toggle `nullglob` without save/restore. Pre-existing pattern in this file (`list_cached_versions_by_install_stamp`); not introduced by this diff. --- **Verdict:** Approve from a correctness lens. The three-layer fix (protect running dir, stamp all installs, backfill at prune) directly prevents the self-delete / redaction-unavailable failure mode and aligns with the plan.
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: skills/upgrade-larch/scripts/upgrade-larch.sh:219-303
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No automated test covers prune retention stamp or backfill semantics CI passes while a future edit re-breaks protected-version retention or re-deletes the running cache dir; same class as the 47.0.34 incident Add scripts/test-upgrade-larch-prune.sh (or equivalent) with a temp LARCH_CACHE_DIR fixture and Makefile target per plan manual check
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: (PR / plan verification)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Plan-required manual retention and stamp-on-unverified checks are not evidenced in the diff Merge without proof the incident scenario was simulated; regression could ship again Run plan scratch simulation and document in PR test plan or commit a harness
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: SECURITY.md:240
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] SECURITY says eight-cap ranked set plus target and running dirs implying up to ten dirs Auditors or future tests assume ten cached versions; cap regressions go unnoticed Reword to state protected dirs count toward the eight-directory cap
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: skills/upgrade-larch/scripts/upgrade-larch.sh:219-240
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] backfill_install_stamps has no test for success failure or read-only cache Read-only cache causes repeated warn_install_stamp_failure on every prune with no CI signal Add harness cases for backfill success skip and write failure
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: (branch)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Lint success is only implied by commit message not diff Undetected shellcheck or lint-bash32 failure could merge if CI was not run Confirm green make lint on PR CI
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: docs/skills.md:147-153
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] edit-in-sync lists docs/skills.md but catalog was not updated for new prune stamp contract Minor doc drift between catalog and installation/security docs Add one sentence on stamp and prune behavior or narrow edit-in-sync list
- **Suggested revision**: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] risk-integration: skills/upgrade-larch/scripts/upgrade-larch.sh:1-422
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Script is not source-safe for unit tests Pre-existing barrier to cheap CI coverage; not introduced by this diff Consider BASH_SOURCE guard as follow-up if harnesses return
- **Suggested revision**: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] risk-integration: (repo)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No CI workflow exercises upgrade-larch behavior Pre-existing lint-only safety net for the skill None required for this PR unless team wants E2E upgrade tests
- **Suggested revision**: Address the concern above.

### FINDING_19: security: skills/upgrade-larch/scripts/upgrade-larch.sh:221-244
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] backfill_install_stamps writes .larch-installed-at via glob paths without rejecting symlinked version_dir entries A same-UID attacker who plants a numeric symlink under the plugin cache can cause prune-time stamp writes outside LARCH_CACHE_DIR when backfill runs Skip symlinks before write (e.g. [ -L "$version_dir" ] && continue) or enumerate with ! -type l like /cleanup; confirm resolved path stays under LARCH_CACHE_DIR
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: SECURITY.md:240
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Prune-trust text says target and running version are retained in addition to the eight-cap ranked set Auditors may assume up to ten cached versions are kept; code still caps retained at eight total Reword to clarify both protected versions count inside the eight-slot cap
- **Suggested revision**: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] security: skills/upgrade-larch/scripts/upgrade-larch.sh:169-183
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] write_install_stamp uses LARCH_CACHE_DIR/$version without symlink guard Same symlink-follow write class as backfill; predates this branch Apply shared symlink-safe cache entry handling if hardening cache writes
- **Suggested revision**: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] security: skills/upgrade-larch/scripts/upgrade-larch.sh:284-297
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Prune deletion loop lacks /cleanup-style symlink skip on cache entries Pre-existing asymmetry with /cleanup trust model Consider ! -type l or -L skip on enumeration if cache symlink attacks are in threat model
- **Suggested revision**: Address the concern above.

### FINDING_23: risk-integration: skills/upgrade-larch/scripts/upgrade-larch.sh:383-418
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Unverified installs get a fresh date +%s stamp before exit 1 while prune is skipped. On ACTUAL_VERSION != LATEST_STABLE the cache dir is stamped with now; a later verified prune may keep that tree over older stamped rollbacks. Document the tradeoff or stamp unverified installs from mtime like backfill instead of date +%s.
- **Suggested revision**: Address the concern above.

### FINDING_24: correctness: skills/upgrade-larch/scripts/upgrade-larch.sh:259-276
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Two protected seeds share the eight-word retention cap with ranked versions. With >8 cached versions and both protected outside the natural top eight, newer stamped rollbacks can be evicted while the running tree is kept. Accept as designed or emit a one-line log when retention is dominated by protected seeds.
- **Suggested revision**: Address the concern above.

### FINDING_25: correctness: skills/upgrade-larch/scripts/upgrade-larch.sh:221-243
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Backfill persists mtime as install stamp. A copied or touched cache dir can get a wrong rank on prune; only re-downloadable dirs are affected. Keep plan-documented caveat; optional future sanity checks on mtime vs neighbors.
- **Suggested revision**: Address the concern above.

### FINDING_26: architecture: skills/upgrade-larch/scripts/upgrade-larch.sh:221-243
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] backfill_install_stamps toggles nullglob without ERR trap restore. Rare set -e abort could leave nullglob enabled for the rest of the script. Add a short ERR trap to restore shopt like other helpers or avoid toggling in the function body.
- **Suggested revision**: Address the concern above.

