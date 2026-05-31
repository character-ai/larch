### OOS_1: [OUT_OF_SCOPE] Fast poll exports in plan-review-loop test
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `skills/design/scripts/test-plan-review-loop.sh` fast poll interval exports are unrelated to Step 0b extraction; no breakage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Keep or split to separate PR for clarity.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_2: [OUT_OF_SCOPE] `larch-logs` markdown lint exclusion bundled in branch
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `scripts/lint-literal-counts.py` exclusion change is unrelated to Step 0b; no action required for this review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: No action required for Step 0b review.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_3: [OUT_OF_SCOPE] CI structure test pins hard-abort `rename-failed` in SKILL
- **Reviewer(s)**: dyn-rename-fail-behavior-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-design-structure.sh:871-872` pins the `rename-failed` abort branch in `SKILL.md`, so CI encodes hard-abort rather than #3245 warn-and-continue; fixing regression requires updating that grep as well as driver/orchestrator.
- **Suggested revisions (informational for voters; coder decides)**:
  - (no separate fix bullet beyond concern; reviewer tied fix to FINDING_1 cluster)


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_4: [OUT_OF_SCOPE] `_rename_seen` guard unlikely under current `tracking-issue-write.sh`
- **Reviewer(s)**: dyn-rename-fail-behavior-output.txt
- **Severity**: nit
- **Concern**: `scripts/tracking-issue-write.sh:490-508` always emits `RENAMED=true|false` on success, so the `_rename_seen` guard in `design-init-runparams.sh:196-203` is unlikely to fire in normal operation; spurious `rename-failed` would imply a broken quiet/capture contract, not missing helper KV.
- **Suggested revisions (informational for voters; coder decides)**:
  - (none)


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_5: [OUT_OF_SCOPE] Step 0b `printf -v` only in allowlisted `case` arms — no regression
- **Reviewer(s)**: dyn-kv-parse-safety-output.txt
- **Severity**: nit
- **Concern**: File-first and stdout-merge loops only call `printf -v` inside explicit `case` arms for routing keys; tampered lines like `PATH=evil` are ignored. Matches Step 3 handoff pattern; not worsened by this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - (none)


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_6: [OUT_OF_SCOPE] `phase_driver_write_result_env` lacks write-side allowlist/newline checks
- **Reviewer(s)**: dyn-kv-parse-safety-output.txt
- **Severity**: nit
- **Concern**: Only `phase_driver_read_result_env` filters; orchestrator does not call it on the Step 0b path. Safety relies on driver-known KVs and SKILL `case` at read time — same tradeoff as Step 3 (related to in-scope FINDING_7 for pause-load values).
- **Suggested revisions (informational for voters; coder decides)**:
  - (none)


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### OOS_7: [OUT_OF_SCOPE] Values containing `=` handled correctly
- **Reviewer(s)**: dyn-kv-parse-safety-output.txt
- **Severity**: nit
- **Concern**: `${_line#*=}` / `${_pline#*=}` preserve everything after the first `=`; no defect found.
- **Suggested revisions (informational for voters; coder decides)**:
  - (none)


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_8: [OUT_OF_SCOPE] `design-route.sh` pause-load parse uses fixed `case` on `_pkey`
- **Reviewer(s)**: dyn-kv-parse-safety-output.txt
- **Severity**: nit
- **Concern**: No dynamic `printf -v`; only allowlisted pause-load keys applied. Driver ERROR tokens are single-token today; SKILL dedup (FINDING_4) is the main correctness risk for surfaced breadcrumbs.
- **Suggested revisions (informational for voters; coder decides)**:
  - (none)


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_9: [OUT_OF_SCOPE] Init handoff prints WARN without dedup (duplicate lines possible)
- **Reviewer(s)**: dyn-kv-parse-safety-output.txt
- **Severity**: nit
- **Concern**: `skills/design/SKILL.md:385-399` may print duplicate file+stdout WARNs; inconsistent with route path but lower severity and outside scout dedup focus.
- **Suggested revisions (informational for voters; coder decides)**:
  - (none)

Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

