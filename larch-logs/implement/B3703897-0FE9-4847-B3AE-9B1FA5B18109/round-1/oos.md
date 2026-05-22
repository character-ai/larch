### FINDING_11: [OUT_OF_SCOPE] correctness: scripts/test-design-log-publish.sh:519-523
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Gh stub for pr list is not flag-aware like real gh. Harness could miss regressions in gh flag handling only if production changes. Optionally tighten stub when touching tests.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_16: [OUT_OF_SCOPE] risk-integration: <TMPDIR>/round-1/diff.txt
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Precomputed diff file was empty Reviewer could not use launcher-provplied diff without git fallback Fix session export of diff.txt for future reviews
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_26: [OUT_OF_SCOPE] code-quality: (session launcher)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Empty precomputed diff file for stated session path Reviewer had to use git diff vs origin/main Launcher should materialize diff or pass correct path
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_30: [OUT_OF_SCOPE] risk-integration: <TMPDIR>/round-1/diff.txt
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Precomputed diff path was empty; merge-base log vs local main was empty because HEAD is main. Reviewer had to substitute origin/main for the patch; launcher hygiene only. Regenerate or populate the sidecar diff for future reviews.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_31: [OUT_OF_SCOPE] architecture: feature_description (supplied)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Feature description mentions creating a branch when /design starts; twelve-item implementation plan omits that scope. No contradiction with the written implementation plan, but product intent may be incomplete versus the narrative. If branch-at-start is required, add it as an explicit plan item and implement separately.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_37: [OUT_OF_SCOPE] security
- **Reviewer**: dyn-redaction-completeness-output.txt
- **Concern**: - **security** `SECURITY.md:115-116` (durable run-store bullet) — States that schema v2 `manifest.json` records `operator_cwd` / `operator_repo_root` as local absolute paths, which conflicts with the `write_manifest_file` placeholder behavior described earlier in the same file (`"<OPERATOR_CWD>"` / `"<REPO_ROOT>"`); this documentation tension around committed manifests is not specific to `design-log-publish.sh`’s staging loop and appears broader than the new publish path alone.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_38: [OUT_OF_SCOPE] security
- **Reviewer**: dyn-redaction-completeness-output.txt
- **Concern**: - **security** `.gitleaks.toml` / `SECURITY.md:98` — The `larch-logs/` gitleaks path allowlist means merged design logs are not regex-scanned at commit/PR time the way most tree paths are; reliance on the redaction pipeline was already the stated posture for that subtree, but it amplifies any trimming-pattern gaps above.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_41: [OUT_OF_SCOPE] code-quality
- **Reviewer**: dyn-prefix-lifecycle-output.txt
- **Concern**: - **code-quality** `CHANGELOG.md` — Release/history prose for the tracking-issue rename subcommand still describes only `in-progress|done|stalled` in places; this branch does not touch `CHANGELOG.md`, so the drift is pre-existing relative to this diff, but operators relying on the changelog alone may still miss the new `planned` state until a future doc pass.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_45: [OUT_OF_SCOPE] **`scripts/test-tracking-issue-write.sh:11` and `97-146`** — The harness still fails fast if `tracking-issue-write.sh` is missing/non‑executable, and the new `planned` rename plus idempotent cases tie failures to concrete title/`RENAMED=`/`TITLE_CAPTURE` expectations (wrong prefix logic or an erroneous `gh issue edit` would trip the assertions or nonzero exit from the stub).
- **Reviewer**: dyn-harness-coverage-output.txt
- **Concern**: - **`scripts/test-tracking-issue-write.sh:11` and `97-146`** — The harness still fails fast if `tracking-issue-write.sh` is missing/non‑executable, and the new `planned` rename plus idempotent cases tie failures to concrete title/`RENAMED=`/`TITLE_CAPTURE` expectations (wrong prefix logic or an erroneous `gh issue edit` would trip the assertions or nonzero exit from the stub).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_46: [OUT_OF_SCOPE] **`scripts/test-design-log-publish.sh:92-96` and `134-146`** — Invalid `--run-id` and invalid `*-output*.json` sidecars are covered with injected bad inputs and `PUBLISH_OK=false` expectations, which does exercise distinct failure paths from the happy path.
- **Reviewer**: dyn-harness-coverage-output.txt
- **Concern**: - **`scripts/test-design-log-publish.sh:92-96` and `134-146`** — Invalid `--run-id` and invalid `*-output*.json` sidecars are covered with injected bad inputs and `PUBLISH_OK=false` expectations, which does exercise distinct failure paths from the happy path.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_47: [OUT_OF_SCOPE] **`skills/fix-issue/scripts/test-find-lock-issue.sh:676-701`** — Fixture `5b` adds integration coverage that `[PLANNED]` titles are treated as machine‑managed for lock eligibility, consistent with the prefix change in `find-lock-issue.sh`.
- **Reviewer**: dyn-harness-coverage-output.txt
- **Concern**: - **`skills/fix-issue/scripts/test-find-lock-issue.sh:676-701`** — Fixture `5b` adds integration coverage that `[PLANNED]` titles are treated as machine‑managed for lock eligibility, consistent with the prefix change in `find-lock-issue.sh`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_6: [OUT_OF_SCOPE] code-quality: Makefile:9-10
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Whole .PHONY declaration rewritten for one new target name. Blame noise and harder review of unrelated Makefile history. Minimal .PHONY edit or line splitting in a separate cleanup change.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

