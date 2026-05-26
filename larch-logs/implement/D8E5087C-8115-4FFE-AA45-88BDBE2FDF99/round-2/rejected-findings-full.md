### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: code-quality: scripts/test-design-log-publish.sh:678-757
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Five render-cache symlink tests duplicate the plan-review harness structure (~80 LOC). A future guard change updated only in the plan-review block could leave render-cache cases passing while production behavior diverges. Extract a parameterized harness helper for symlink-rejection cases; keep only case-specific setup in each block.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_10: **Regular file at `render-cache` path (round-1 test):** `-e` true, `-L` false, `! -d` → `PUBLISH_OK=false`. Correct.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - **Regular file at `render-cache` path (round-1 test):** `-e` true, `-L` false, `! -d` → `PUBLISH_OK=false`. Correct. Logic ordering matches plan-review and does not introduce new control-flow bugs. ### Out-of-scope branch content `0a9c32ea` (`launch-claude-review.sh` `--context-files`) and `592ca7a4` (larch-logs) are outside the OOS/plan surface; no blocking correctness defects identified in a secondary pass of the launcher refactor (canonical-path dedup is an improvement over delimiter-string `seen_allow_roots`).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: risk-integration: scripts/test-design-log-publish.sh:678-757
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Symlink tests only grep PUBLISH_OK=false and discard stderr; they do not assert that render-cache destinations were not created under larch-logs/design/<RUN_ID>/. A publish path that emitted PUBLISH_OK=false after partially staging a symlink target would pass the harness while leaving attacker-controlled content in the disposable worktree log tree. Add post-publish negative filesystem checks for at least the leaf-symlink and race cases (mirror happy-path staging assertions at lines 256-257).
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_15: risk-integration: (branch)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Branch bundles render-cache hardening with #2945 launch-claude-review context-files and validate-plan-commands harness changes. CI shard failure does not identify which harness regressed without re-running individual make targets. Triage with make test-design-log-publish and make test-launch-claude-review separately.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_5: **Dangling root symlink (Case B):** `-e` is false on a broken symlink, but `|| -L` enters the block; the existing `[[ -L "$DESIGN_TMPDIR/render-cache" ]]` guard fires before `cd`/`pwd -P`. Correct.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - **Dangling root symlink (Case B):** `-e` is false on a broken symlink, but `|| -L` enters the block; the existing `[[ -L "$DESIGN_TMPDIR/render-cache" ]]` guard fires before `cd`/`pwd -P`. Correct.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_6: **Root symlink to real tree (Case A):** Caught by root `-L` before canonicalization. Correct.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - **Root symlink to real tree (Case A):** Caught by root `-L` before canonicalization. Correct.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_7: **Leaf / intermediate symlinks (Cases C/D):** Caught by tree-wide `find -type l` before file enumeration. Correct.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - **Leaf / intermediate symlinks (Cases C/D):** Caught by tree-wide `find -type l` before file enumeration. Correct.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_8: **Find→stage race (Case E):** Stub swaps a listed path to a symlink between enumeration and staging; per-file `[[ -L "$f" ]]` fails closed. Correct.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - **Find→stage race (Case E):** Stub swaps a listed path to a symlink between enumeration and staging; per-file `[[ -L "$f" ]]` fails closed. Correct.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_9: **Missing `render-cache`:** Outer guard false; block skipped (success, no files). Correct.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - **Missing `render-cache`:** Outer guard false; block skipped (success, no files). Correct.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

