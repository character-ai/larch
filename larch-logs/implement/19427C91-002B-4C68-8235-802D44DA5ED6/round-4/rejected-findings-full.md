### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: find in activity scan follows symlinks outside session tree
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `newest_activity_mtime` uses `find` without `-P`, so activity can be anchored outside the session directory via symlinks, keeping stale session dirs artificially young and leaving CMD_JSON-bearing `.meta` files under same-UID cache longer than intended.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Use find -P (or skip symlinks) so retention is confined to the session directory.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: session-setup keepalive writes unvalidated paths/ids
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `scripts/session-setup.sh` (248–254) writes `.larch-keepalive` from unvalidated `CLONE_PATH`/`SESSION_ID`; resolver uses line-oriented awk, so newlines in PWD or session id can break field parsing and mis-bind hooks to another session tmpdir.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Reject control characters/newlines before write, or parse with the same hardened rules as session-env.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_15: Legacy unstamped cache dirs lack mtime backfill on prune
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Unstamped legacy dirs under `~/.cache/larch` sort only by directory mtime after `backfill_legacy_install_stamps` was removed; first post-change prune on machines with touch-bumped unstamped dirs can evict the wrong rollback target before operators reinstall each version.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Restore one-time mtime-to-stamp backfill on prune or document a migration step to stamp legacy dirs.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Activity scan maxdepth 5 may miss deeper session state
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `newest_activity_mtime` uses `find … -maxdepth 5` (`cleanup.sh` line 40). Live state or design plan-review files at depth 6–7 would not refresh the activity clock; an active `/design` or `/implement` could look stale and be deleted if the keepalive skip is removed. Harness covers depth 5 but not beyond.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Longer maxdepth or document exclusion; add harness if depth is raised
  - From cursor-specialist-testing-output.txt: Document depth-5 limit or add depth-6 fixture test if deeper run-log paths are plausible.
  - From cursor-specialist-edge-cases-output.txt: Document the depth-5 contract; add harness cases when layouts change; raise maxdepth only after auditing session tree depth.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_6: Upgrade prune no longer protects long-running session plugin roots
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Prune logic (`upgrade-larch.sh` ~148–200) dropped session/fallback pin scanning; only install-stamp cap plus upgrade-runner `PLUGIN_ROOT` / `INSTALLED_VERSION` seeding remain. Eight newer releases while `/design` (or review/implement) stays on an older version can evict that version’s cache dir (`rm -rf`) even though the job still references it via design rehydration—version blown away without pin or touch mitigations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Reintroduce narrow ownership-checked version discovery for active design/review/implement sessions, or document that only the eight newest installs plus the upgrade runner root are protected.
  - From cursor-specialist-edge-cases-output.txt: Refresh install stamps from design/implement session writers or retain plugin roots referenced by design-env files; otherwise document that only the eight most recently installed cache dirs are safe for long-running design/review.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Redundant read_install_stamp per version directory
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `list_cached_versions_by_install_stamp` calls `read_install_stamp` twice per cached version (`upgrade-larch.sh` lines 126–128), causing redundant stat/read on prune with many version dirs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Read stamp once per iteration
  - From cursor-specialist-edge-cases-output.txt: Read the stamp once per iteration and reuse the value for has_stamp and ts.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: Duplicated stat_mtime helpers across cleanup and upgrade-larch
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `stat_mtime` / dual-stat portability helpers are duplicated in `skills/cleanup/scripts/cleanup.sh` (18–32) and `skills/upgrade-larch/scripts/upgrade-larch.sh` (69–83), increasing maintenance burden.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract shared lib or accept documented duplication


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: wc -w counts space-separated retained version string
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Retention cap uses `wc -w` on a space-separated `retained` string (`upgrade-larch.sh` line 170); a future format change could miscount the retained set.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Track integer count or use array length


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

