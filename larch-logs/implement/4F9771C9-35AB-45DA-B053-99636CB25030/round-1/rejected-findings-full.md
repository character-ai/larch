### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: code-quality: skills/cleanup/scripts/cleanup.sh:36-44,81-86
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Duplicated age-delete while/rm/count loops in cache and /tmp passes A fix to deletion or counting logic updated in one loop but not the other leaves inconsistent cleanup behavior Extract a small shared prune helper or add an explicit comment that both loops must stay in sync
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: risk-integration: skills/cleanup/scripts/test-cleanup.sh:240-260
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] large-tmp-scales uses ~2000 entries and SECONDS<60 not acceptance sub-second/16k scale A future perf regression could pass CI in tens of seconds while /cleanup on a full host /tmp still hangs Increase fixture size toward incident scale and/or tighten timing bound (e.g. SECONDS -lt 5)
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: risk-integration: skills/cleanup/scripts/cleanup.sh:39-44
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Cache pass now deletes stale top-level files via ! -type l not only directories Untested loose file under sessions parent could be removed unexpectedly vs old behavior Add stale-cache-file-removed harness case or document intentional file deletion in cleanup.md
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: risk-integration: skills/cleanup/scripts/test-cleanup.sh:165-175
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] No /tmp symlink skip regression case /tmp pattern symlink could be rm -rf through in a broken find predicate rewrite Mirror symlinked-session-dir-skipped under LARCH_TEST_TMP_ROOT
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: risk-integration: skills/cleanup/scripts/test-cleanup.sh:254-256
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] large-tmp-scales only checks noise-0 survives Partial erroneous deletion of noise dirs might not fail Assert multiple noise-* paths or count entries after cleanup
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: security: skills/cleanup/scripts/cleanup.sh:39-44,81-86
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Age-pass find errors are swallowed and cleanup exits 0. Operator runs /cleanup after enumeration failure; secret-bearing session tmpdirs (CMD_JSON in .meta) remain on disk while stdout shows success and zero removal counts. Emit non-zero exit or a dedicated stderr warning when find fails; keep performance-friendly flat passes.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: security: skills/cleanup/scripts/cleanup.sh:39-44
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Cache pass now deletes stale top-level files as well as directories. Unexpected loose file at sessions/ root with old mtime is permanently removed without redaction. Confirm no such files in workflows or restrict cache find to -type d if parity with main is desired.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: risk-integration: skills/cleanup/scripts/cleanup.sh:39-44; SECURITY.md:234
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Top-level mtime can GC dirs with fresh deep-only activity after retention window. Long-paused or deep-only debug session older than retention at root mtime loses tmpdir while issue markers still imply continuity. Document in SKILL.md; acceptable if 7-day invariant holds.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: code-quality: skills/cleanup/scripts/cleanup.sh:36,92
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] CACHE_DIR and SESSIONS_PARENT duplicate the same path expression One constant renamed or repointed without the other breaks symlink reap vs cache cleanup Reuse CACHE_DIR (or one SESSIONS_ROOT) for pass 3
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: risk-integration: skills/cleanup/scripts/cleanup.sh:39-44,81-86
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Age-pass find enumeration errors are fully swallowed; cleanup exits 0 with zero counts and no stderr signal. Permission or I/O failure on cache or /tmp find makes /cleanup report success with CACHE_REMOVED=0 TMP_REMOVED=0 while stale larch dirs remain; SKILL Step 2 cannot distinguish failure from an empty result. Emit one larch_err warning or a fifth stdout status key when find exits non-zero on an age pass.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: correctness: skills/cleanup/scripts/cleanup.sh:39-44
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Deletion uses top-level mtime only; deep-only activity and old per-entry scan fail-closed semantics are gone. A >7-day run that only mutates existing nested files keeps a stale directory mtime and can be deleted mid-run; previously unreadable inner trees were kept with a warning. Accept under the 7-day assumption; add operator-facing note in SKILL.md that deep writes do not protect directories from age GC.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_22: architecture: skills/cleanup/scripts/test-cleanup.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] No harness covers documented fail-open behavior when age-pass find enumeration fails. find-failure-skips-deletion was dropped without replacement; a future regression to silent no-op would not be caught. Add a stubbed-find case asserting exit 0 zero counts and optional warning or status key.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_23: risk-integration: skills/cleanup/scripts/test-cleanup.sh:806-831
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] large-tmp-scales uses SECONDS -lt 60 as hang guard. Heavily loaded CI may exceed 60s despite correct algorithmic behavior causing flaky failures. Raise ceiling gate on CI or use a relative scaling check instead of absolute wall clock.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_24: correctness: skills/cleanup/scripts/cleanup.sh:81-86
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] /tmp symlinks matching TMP_PATTERNS are skipped by ! -type l. Stale symlink-to-file /tmp entries matching larch patterns are no longer removed; old code deleted them via the -f branch. Accept as symlink hardening or add a dedicated stale-symlink pass with -type l -mtime +N and rm -f.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: correctness: skills/cleanup/scripts/cleanup.sh:43
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Cache find uses ! -type l without -type d so stale top-level regular files are removed Old code only deleted directories; a rare top-level file under sessions/ would now be age-deleted Add -type d to cache find if dirs-only is intended; else document in cleanup.md
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: code-quality: skills/cleanup/scripts/test-cleanup.sh:243-262
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] large-tmp-scales only checks noise-0 survival Partial deletion of non-matching tmp entries might not fail the test Also assert noise-1999 exists or count remaining noise dirs
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: correctness: skills/cleanup/scripts/cleanup.sh:39-43
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Cache pass deletes stale top-level files; old code only deleted stale top-level directories A regular file directly under ~/.cache/larch/sessions/ with mtime past retention is removed; previously it would be kept even when stale Add -type d to the cache find only or document dirs-only convention at the sessions parent
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

