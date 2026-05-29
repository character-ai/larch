### FINDING_7: [OUT_OF_SCOPE] `commit-log.txt` still includes larch-logs-only commits
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `gather-branch-context.sh` commit log still includes commits touching only `larch-logs` while `diff.txt` is trimmed; log-only consumers may see run-log noise.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Apply the same pathspec to log formatting if log-driven reviewers are added later


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_1: [OUT_OF_SCOPE] Scout acceptance lists Cursor tier; documentation-only mismatch
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Waterfall is Codex→Claude only while issue acceptance mentions Cursor; not a harness gap in changed files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Update acceptance or issue close note to match scout vs panel behavior.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_2: [OUT_OF_SCOPE] Harness missing waterfall cases (3) and (4)
- **Reviewer(s)**: dyn-waterfall-state-machine-output.txt
- **Severity**: nit
- **Concern**: No harness asserts Codex launch-fail + Claude probe-miss → `empty`, or both launch-fail → `claude-failed`; logic matches contract but coverage thinner than cases (1)–(2).
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_3: [OUT_OF_SCOPE] `last_scout_status` initialized to `claude-failed` before tiers (amplifies empty-raw gap)
- **Reviewer(s)**: dyn-waterfall-state-machine-output.txt
- **Severity**: nit
- **Concern**: Combined with exit-0 empty-raw handling (FINDING_9), all-empty multi-tier path can report `claude-failed` without any launcher failure.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_4: [OUT_OF_SCOPE] No harness for Codex + staged description ~128 KiB–1 MiB / E2BIG argv
- **Reviewer(s)**: dyn-argv-materialization-output.txt
- **Severity**: nit
- **Concern**: Test gap for `--codex-present true` with large staged description to catch `E2BIG` or assert argv omits bulk `--description-text`.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_5: [OUT_OF_SCOPE] Staged-context and launch-env artifact lifecycle (intentional retention)
- **Reviewer(s)**: dyn-temp-file-lifecycle-output.txt
- **Severity**: nit
- **Concern**: `STAGED_DIR` not removed per scout; launch env files truncated not deleted; `cleanup_temps` covers only fenced/validated temps—acceptable except fenced-probe leak (FINDING_17).
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### OOS_6: [OUT_OF_SCOPE] Plan allows panel PATH `codex` fallthrough vs fully stubbed launchers
- **Reviewer(s)**: dyn-harness-codex-stub-gap-output.txt
- **Severity**: nit
- **Concern**: Plan “ok-path” note documents tradeoff; conflicts with testing strategy calling for stubbed launchers—panel tests remain weak link (see FINDING_19).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-codex-stub-gap-output.txt: The implementation plan explicitly allows `dynamic4` / `dynamic8` / `dynamic-empty` to keep `--codex-available true` with PATH `codex` fallthrough (plan “ok-path” note). That documents the tradeoff but still conflicts with the same plan’s testing strategy calling for fully stubbed launchers and with FINDING_7’s split override variables; panel tests remain the weak link.

Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

