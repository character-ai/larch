### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: Tier success conflation: `LAUNCHER_EXIT` vs process exit / discarded launcher stdout
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt
- **Concern**: `launch-claude-ci.sh` exits 0 even when `LAUNCHER_EXIT` is non-zero; ship-pr recovery waterfall uses shell exit for `tier_rc`, so Claude timeout/failure can yield rc 0 and tier looks launched OK until verify; with `>/dev/null` on launcher output, failed vendor runs can still look like successful tiers and skip immediate post-launcher rollback, behavior depending on verifier gaps.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Propagate LAUNCHER_EXIT (exit non-zero on failure) to match other CI launchers
  - From cursor-specialist-security-output.txt: Omit >/dev/null and parse LAUNCHER_EXIT or exit non-zero from launcher when LAUNCHER_EXIT!=0


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: Brittle negative grep in `test-launch-claude-ci.sh`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Negative grep for subprocess marker couples test to unrelated text drift (false pass/fail).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Use a stable positive writer-preamble sentinel assertion


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: Makefile `test-harnesses-2` shard timing risk
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Second launcher harness added to shard 2 without shown timing rebalance; possible CI shard wall-time regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Rebalance harness shards if CI shows shard 2 slowdown


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: Symlinked `--failure-log` may bypass tmp containment intent
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Symlinked `--failure-log` could steer `head -c` reads while passing prefix checks; same-user tmp races could read sensitive paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Validate no symlink / copy to mktemp before read


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: `merge-pr` transient predicate scans only first `MERGE_RESULT`/`ERROR` pair
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Stale first lines could misclassify envelopes and change retry vs stall.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Parse last matching envelope or tighten log shape contract


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: Recovery commit + failed verify leaves HEAD off baseline; later tiers skipped
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: If a recovery tier creates a commit and verification fails, HEAD no longer matches baseline; remaining waterfall tiers are skipped and run aborts as total failure though other tiers were never tried.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Reset HEAD to baseline after failed verify or adjust baseline policy document harness-only env


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Divergent bump vs non-bump classification
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Parallel logic between `ship_pr_vendor_conflict_csv_is_non_bump_only`, the deterministic rebase loop CSV gate, and the waterfall can disagree after partial edits, so the waterfall may run on paths the loop classifies differently (bump-only vs non-bump) or vice versa.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Share one classification helper or document a single source of truth with cross-callsite tests


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_22: `ship-pr.md` lacks explicit `RESUME_PHASE` / `CALLER_KIND` mapping example
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Acceptance #4 explicit `RESUME_PHASE=bump` + `CALLER_KIND=step8_apply_bump_same_version` vs wrong `RESUME_PHASE` token not spelled in `ship-pr.md`; orchestrator-facing doc may mislead.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add a one-line explicit mapping example to ship-pr.md (and keep docs/linting.md aligned).


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: Awk KV extract for `BAIL_REASON` / `ERROR` is first-line only
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Multi-line or wrapped envelope values can miss transient tokens; `with_transient_retry` may return 0 then bail path `exit_transient_net` fires without intended retries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Match kv_value semantics or forbid multiline KV in helpers; add harness for multiline envelope


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0

