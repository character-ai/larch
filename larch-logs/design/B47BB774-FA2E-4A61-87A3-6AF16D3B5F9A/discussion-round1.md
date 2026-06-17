## Decision 1: Secondary gate location
- **Question**: Where should the `launched_success_count==0` secondary gate be patched?
- **Resolution**: In `python/legacy_review_shell/review-core.sh` at the existing secondary gate block (lines ~876–888). Bypass panel-failed when `launched_success_count == 0` but either `$REVIEW_TMPDIR/findings.md` or `$REVIEW_TMPDIR/oos.md` is non-empty (parseable output was produced). The code flow after bypass naturally hits `emit_zero_findings_branch` (clean review) or the aggregation/voting path.
- **Source**: codebase

## Decision 2: Run log observability
- **Question**: Which files to add to the run log for panel-failed diagnosis?
- **Resolution**: (a) Remove `collector-results.env` from `_ROUND_SIDECAR_FILES` and add to `_ROUND_ARTIFACT_ALLOW` in `python/run_logs.py`. (b) Add `review-core-threshold.env` to `_ROUND_ARTIFACT_ALLOW`. Both are in `$REVIEW_TMPDIR` and small (~50 lines).
- **Source**: codebase

## Decision 3: Loud --merge downgrade warning
- **Question**: Where to emit the warning when `--merge` is silently downgraded to `pr-created` after panel-failed stall recovery?
- **Resolution**: In `skills/implement/scripts/stall-recovery-report.sh`, after outcome determination, emit an explicit `⚠` warning when `outcome=pr-created` and the stall reason includes `panel-failed` and the original run had `MERGE=true`. Keep independent of Fix 2 (applies even if fix 2 doesn't land).
- **Source**: codebase
