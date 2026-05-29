### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: Duplicate stat_mtime helpers in upgrade-larch and cleanup
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Duplicate `stat_mtime` helpers exist in `upgrade-larch.sh` and `cleanup.sh`. A future portability fix applied in one script may not be carried to the other.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: Valid LARCH_CLEANUP_RETENTION_DAYS override not tested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Only invalid retention is tested; custom positive value parsing for `LARCH_CLEANUP_RETENTION_DAYS` could regress silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: LARCH_TEST_TMP_ROOT redirects destructive globs without production opt-in gate
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `LARCH_TEST_TMP_ROOT` redirects destructive pattern globs without a production opt-in gate. Stale CI or shell exports pointing at a project directory could cause `/cleanup` `rm -rf` or `rm -f` to match `larch-*` and `claude-*` patterns outside `/tmp`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Redundant read_install_stamp I/O in list_cached_versions_by_install_stamp
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `read_install_stamp` is called twice per version in `list_cached_versions_by_install_stamp`, causing unnecessary I/O on every prune listing pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: Activity scan buffers full find output in memory
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The activity scan buffers full `find` output in memory. Very large session trees can make `/cleanup` slow or memory-heavy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: Failed stable verification skips prune entirely
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Failed stable verification skips prune entirely. Repeated failed upgrades leave an unbounded version cache until a verified run succeeds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Max-8 install-stamp cap lacks in-use, session, and age protection
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Prune retention is capped at eight newest install stamps with no version-dir age window, session pins, or in-use discovery. Long-running `/design` or `/review` jobs, parked sessions on older cached versions, or worktrees on versions outside the newest eight can lose their plugin directory after eight newer installs/releases; the blown-away symptom class persists globally across worktrees.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Lexicographic version tiebreak on equal install stamps
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: After equal install stamps, ranking uses lexicographic version comparison. Same-second installs can rank `29.1.9` above `29.1.10`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Activity scan maxdepth-5 boundary may misclassify active sessions
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `newest_activity_mtime` uses `find -maxdepth 5`. Activity at depth 6+ (e.g. deep run-log layouts under `larch-logs/...`) does not refresh newest-activity classification; active sessions may be treated as stale and deleted. The boundary is tested at depth 5 but not depth 6.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

