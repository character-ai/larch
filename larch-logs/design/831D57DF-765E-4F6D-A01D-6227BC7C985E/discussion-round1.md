## Decision 1: Retry-loop refactor shape
- **Question**: Inline retry in initial check only, or extract a shared helper called from both the initial and post-force-push paths?
- **Resolution**: Extract a shared helper. Initial check passes 4 retries; post-force-push call site continues to pass 3 retries (issue body did not request changing the existing post-force-push retry count).
- **Source**: user (Step 1c clarifying question Q1)

## Decision 2: Sub-test G coverage shape
- **Question**: After the fix, should sub-test G also cover the success-after-retry path (parallel to existing Q "UNKNOWN resolves on retry → admin_merged"), or only update G1/G2 to assert the new 5-call retry count?
- **Resolution**: Add a success-after-retry case (e.g. G3) alongside the persistent-UNKNOWN/empty failure cases, mirroring the Q/R symmetry that already exists for the post-force-push retry.
- **Source**: user (Step 1c clarifying question Q2)

## Decision 3: Post-force-push retry behavior (hard constraint)
- **Question**: Does the shared helper refactor change the existing post-force-push retry count (currently 3 retries) or the existing error message ("mergeStateStatus still UNKNOWN after 3 retries post-force-push")?
- **Resolution**: NO. The post-force-push call site continues to request 3 retries via the helper. The existing R2 assertion `^ERROR=mergeStateStatus still UNKNOWN after 3 retries post-force-push` must continue to match — sub-test R is the prose-format parser for that path and acts as the regression gate.
- **Source**: codebase (scripts/test-merge-pr.sh:619 R2 assertion; CHANGELOG.md entry pinning the original empty/UNKNOWN treatment)

## Decision 4: Treatment of empty `MERGE_STATE`
- **Question**: Should the new retry loop trigger on empty `MERGE_STATE` (jq parse failure / `gh` non-zero exit) as well as on the `UNKNOWN` enum value?
- **Resolution**: YES. The issue body's pseudocode groups them together (`[[ -z "$MERGE_STATE" ]] || [[ "$MERGE_STATE" == "UNKNOWN" ]]`) and the existing post-force-push retry uses the same combined condition. Empty can also be transient (network blip, gh rate-limit retry-after).
- **Source**: codebase (scripts/merge-pr.sh:218 existing condition) + issue body pseudocode

## Decision 5: Affected files
- **Question**: Which files are in-scope vs out-of-scope for this fix?
- **Resolution**: In-scope — `scripts/merge-pr.sh` (helper + both call sites), `scripts/test-merge-pr.sh` (sub-test G expansion), `scripts/test-merge-pr.md` (sub-test G description). Sub-tests Q/R fixtures and assertions are NOT modified (post-force-push retry count unchanged). `scripts/merge-pr.md` MERGE_RESULT enum table not modified (enum unchanged — `error` row already documents empty/UNKNOWN coverage).
- **Source**: codebase + issue body
