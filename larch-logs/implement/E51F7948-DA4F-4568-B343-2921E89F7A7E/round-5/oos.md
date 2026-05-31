### FINDING_10: [OUT_OF_SCOPE] security — NDJSON manifest paths without JSON escaping
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `dispatch-plan-voters.sh` and `dispatch-plan-assessors.sh` still build manifest rows with `printf '{"slot":...,"prompt_file":"%s"}'` without escaping; paths with embedded `"` could corrupt NDJSON. Pre-existing; not introduced by availability gating.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_11: [OUT_OF_SCOPE] architecture — degraded-tools-gate env fallbacks
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `degraded-tools-gate.sh` env fallbacks plus stderr warnings when flags are omitted widen trust surface if callers rely on inherited env; mitigated by `norm_bool`/`norm_tristate`, warnings, and docs requiring explicit `--codex-*`/`--cursor-*` on skill paths. Residual risk is future mis-invocation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_12: [OUT_OF_SCOPE] security — dynamic slug filename constraints (no new issue)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Scout `_slug` values in `$DESIGN_TMPDIR` filenames are constrained by `scout-dynamic-archetypes.sh` (`^[a-z][a-z0-9-]{2,40}$`); branch improves safety by removing cross-slot copy and does not introduce new in-scope vulnerabilities under a security lens.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_16: [OUT_OF_SCOPE] architecture — #3243 bundled with #3266 on same branch
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `review-and-fix.sh` convergence changes bundled with panel availability work; PR reviewers should separate unrelated review-loop behavior or document dual scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Split commits/PRs or document dual scope in PR summary.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_17: [OUT_OF_SCOPE] dispatch-plan-voters.md documents legacy waterfall
- **Reviewer(s)**: dyn-voter-dispatch-data-flow-output.txt
- **Severity**: nit
- **Concern**: Docs still describe three-phase waterfall and reading `ALL_OUTPUT_FILES` for every slot; implementation uses `--no-fallback` and does not read those KVs; line 56 describes retry-path behavior the code does not implement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-voter-dispatch-data-flow-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_18: [OUT_OF_SCOPE] plan-review.md references obsolete ALL_OUTPUT_FILES binding
- **Reviewer(s)**: dyn-voter-dispatch-data-flow-output.txt
- **Severity**: nit
- **Concern**: Operator docs say `VOTER_2_PATH` / `VOTER_3_PATH` come from waterfall `ALL_OUTPUT_FILES`, which no longer matches `dispatch-plan-voters.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-voter-dispatch-data-flow-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_19: [OUT_OF_SCOPE] test-dispatch-plan-voters stub does not exercise -retry.txt path
- **Reviewer(s)**: dyn-voter-dispatch-data-flow-output.txt
- **Severity**: latent
- **Concern**: Stub waterfall writes success to manifest `output` only, not collector `-retry.txt` sidecar; FINDING_15-class regression would not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-voter-dispatch-data-flow-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_21: [OUT_OF_SCOPE] empty-manifest synthetic branch OK
- **Reviewer(s)**: dyn-voter-dispatch-data-flow-output.txt
- **Severity**: nit
- **Concern**: Synthetic `waterfall_output=$'DISPATCH_OK=true\n'` when manifest is empty parses cleanly; no inconsistency when Voter 1 succeeds.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_22: [OUT_OF_SCOPE] parse-rate retry mv mitigates static voter paths
- **Reviewer(s)**: dyn-voter-dispatch-data-flow-output.txt
- **Severity**: nit
- **Concern**: `check_and_retry_voter_parse_rate` moves successful `-parse-retry.txt` onto the canonical path before downstream use; parse-rate retries not affected by static-path change.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_23: [OUT_OF_SCOPE] production empty paths-file integration sound
- **Reviewer(s)**: dyn-no-fallback-sentinel-timing-output.txt
- **Severity**: nit
- **Concern**: `--no-fallback` omits dropped slots; `plan-review-loop.sh` skips collect when `PANEL_PATHS_FILE` empty; `collect-agent-results.sh` fail-closes on empty paths-file; `test-plan-review-loop.sh` covers empty-paths loop path.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_24: [OUT_OF_SCOPE] harness TMPROOT isolation limits stale .done cross-case
- **Reviewer(s)**: dyn-no-fallback-sentinel-timing-output.txt
- **Severity**: nit
- **Concern**: Per-run `mktemp` and distinct basenames make cross-case `.done` contamination unlikely; pre-existing sentinel semantics if `.done` pre-exists at listed path.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_25: [OUT_OF_SCOPE] no-fallback-absent subtest scope vs plan-review-loop skip
- **Reviewer(s)**: dyn-no-fallback-sentinel-timing-output.txt
- **Severity**: nit
- **Concern**: `no-fallback-absent` collect subtest validates direct `collect-agent-results.sh` on empty paths-file, not `plan-review-loop.sh` skip; loop coverage is in `test-plan-review-loop.sh`.
- **Suggested revisions (informational for voters; coder decides)**:

---

**Merge summary**: 31 raw inputs → **25** aggregated blocks. Major merges: both-absent `DISPATCH_OK`/TSV (4→1), decompose Opus flag (3→1), wall-clock timing tests (2→1). **In-scope actionable highlights**: FINDING_1, FINDING_5, FINDING_15, FINDING_20; voter retry-path regression (FINDING_15) is distinct from generic-floor issues (FINDING_1/14). OOS security items 9–12 and 16–19, 21–25 are informational for voters only.

Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_9: [OUT_OF_SCOPE] security — reuse_slot_result removal (positive)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Pre-change `reuse_slot_result` / `cp` impersonation caused missing `.done`, ~31-minute `SENTINEL_TIMEOUT`, and double-counting; this branch removes that path. Not introduced by this diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

