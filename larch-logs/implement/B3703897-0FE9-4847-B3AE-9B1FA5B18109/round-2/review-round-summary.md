# Review Round 2

- Mode: `diff`
- Accepted findings: 12
- Rejected findings: 0
- Exonerated findings: 15
- Neutral findings: 0

## Accepted Findings

### FINDING_1: code-quality: scripts/design-log-publish.sh:71-77
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Run-id slug validation duplicates lib-larch-log.sh larch_log_validate_slug pattern Two copies can drift if slug rules ever change; plan asked for helper reuse Add a non-stdout-polluting slug validator in lib-larch-log.sh used by both paths
- **Suggested revision**: Address the concern above.


### FINDING_12: risk-integration: scripts/test-design-log-publish.sh:664-822
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No harness for git push failure after local commit in design-log-publish.sh Push failure recovery (recovery ref + no gh PR) can regress without CI signal Add git stub path that fails push only; assert PUBLISH_OK=false and recovery ref exists; assert gh log lacks pr merge
- **Suggested revision**: Address the concern above.


### FINDING_14: security: scripts/design-log-publish.sh:258-276
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Symlinked or resolved-away render-cache root lets find emit paths outside DESIGN_TMPDIR; prefix strip fails and unintended files can still be staged under larch-logs/design/<RUN_ID>/render-cache and published. A hostile or mistaken render-cache symlink points find at a sensitive host directory; those files are ingested into the log commit/PR pipeline with only redactor-family protection. Reject symlink render-cache (or canonicalize roots) and refuse any enumerated path not strictly under the resolved render-cache directory.
- **Suggested revision**: Address the concern above.


### FINDING_17: architecture: skills/design/SKILL.md:819-828
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Step 5c deletes DESIGN_TMPDIR whenever PLAN_WRITE_OK=true, ignoring design-log publish outcome. Publish fails after successful plan-block-write; local design artifacts are removed so operators cannot retry publish or inspect the exact bytes that failed redaction/trim/gh without re-running the whole design. Gate cleanup on PUBLISH_OK (or a dedicated flag) when SESSION_ID was non-empty and publish was attempted; document recovery when tmpdir must be preserved.
- **Suggested revision**: Address the concern above.


### FINDING_19: risk-integration: skills/design/SKILL.md:814-715
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Issue title renamed to [PLANNED] before log publish completes. Publish or merge failure leaves GitHub title implying planned/logs flushed while default branch lacks larch-logs/design/<RUN_ID>. Reorder operations or document and enforce recovery semantics; avoid implying log merge from title alone.
- **Suggested revision**: Address the concern above.


### FINDING_2: code-quality: scripts/design-log-publish.sh:199-211
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] .result stripped for all *.json not only *-output*.json Non-tool JSON under the design tmpdir loses a legitimate top-level result object Narrow the filename pattern or document broaden intent in design-log-publish.md
- **Suggested revision**: Address the concern above.


### FINDING_28: **correctness** `scripts/design-log-publish.sh:297-301` — The “no tracked changes under `larch-logs/design/$RUN_ID`” fast path is implemented as `if ! git -C "$WT_DIR" status --porcelain -- "$rel" | grep -q .; then … PUBLISH_OK=true …`. With `set -o pipefail`, any **non-zero** pipeline status—including a **failed** `git status` (disk/repo error, broken worktree, etc.)—is treated the same as “grep found no lines”, because both yield a failing pipeline and `!` flips that into a successful `if` condition. That can emit `PUBLISH_OK=true` with empty `PR_NUMBER`/`PR_URL` even though nothing was verified as clean or published. **Suggested fix:** avoid coupling failure to emptiness; e.g. run `git status` to a temp file or variable with an explicit `git … status` success check first, then separately test `-s`/non-empty output, or use a two-step `if git …; then …; else … fi` pattern so only true “empty porcelain for `$rel`” hits the no-op success path.
- **Reviewer**: dyn-shell-robustness-output.txt
- **Concern**: - **correctness** `scripts/design-log-publish.sh:297-301` — The “no tracked changes under `larch-logs/design/$RUN_ID`” fast path is implemented as `if ! git -C "$WT_DIR" status --porcelain -- "$rel" | grep -q .; then … PUBLISH_OK=true …`. With `set -o pipefail`, any **non-zero** pipeline status—including a **failed** `git status` (disk/repo error, broken worktree, etc.)—is treated the same as “grep found no lines”, because both yield a failing pipeline and `!` flips that into a successful `if` condition. That can emit `PUBLISH_OK=true` with empty `PR_NUMBER`/`PR_URL` even though nothing was verified as clean or published. **Suggested fix:** avoid coupling failure to emptiness; e.g. run `git status` to a temp file or variable with an explicit `git … status` success check first, then separately test `-s`/non-empty output, or use a two-step `if git …; then …; else … fi` pattern so only true “empty porcelain for `$rel`” hits the no-op success path.
- **Suggested revision**: Address the concern above.


### FINDING_38: **correctness** `skills/fix-issue/scripts/umbrella-handler.sh:213-220` — `has_managed_prefix` here matches only `[IN PROGRESS] `, `[DONE] `, and `[STALLED] `, while `child_eligible` calls this helper to decide umbrella child dispatch; `find-lock-issue.sh`’s parallel helper includes `[PLANNED] `, so `pick-child` can return a child titled `[PLANNED] …` that the explicit non-umbrella path would reject, violating the intended “machine-managed lifecycle prefix” contract for `/fix-issue`. **Suggested fix:** Add the same `'[PLANNED] '*) return 0 ;;` branch (and trailing-space semantics) as in `skills/fix-issue/scripts/find-lock-issue.sh:146-151`, and update the nearby comments that still claim parity with `find-lock-issue.sh` or list only three prefixes (`skills/fix-issue/scripts/umbrella-handler.sh:47-51`, `skills/fix-issue/scripts/umbrella-handler.sh:210-212`) plus the matching prose in `skills/fix-issue/scripts/umbrella-handler.md` where pick-child eligibility is documented.
- **Reviewer**: dyn-prefix-state-machine-output.txt
- **Concern**: - **correctness** `skills/fix-issue/scripts/umbrella-handler.sh:213-220` — `has_managed_prefix` here matches only `[IN PROGRESS] `, `[DONE] `, and `[STALLED] `, while `child_eligible` calls this helper to decide umbrella child dispatch; `find-lock-issue.sh`’s parallel helper includes `[PLANNED] `, so `pick-child` can return a child titled `[PLANNED] …` that the explicit non-umbrella path would reject, violating the intended “machine-managed lifecycle prefix” contract for `/fix-issue`. **Suggested fix:** Add the same `'[PLANNED] '*) return 0 ;;` branch (and trailing-space semantics) as in `skills/fix-issue/scripts/find-lock-issue.sh:146-151`, and update the nearby comments that still claim parity with `find-lock-issue.sh` or list only three prefixes (`skills/fix-issue/scripts/umbrella-handler.sh:47-51`, `skills/fix-issue/scripts/umbrella-handler.sh:210-212`) plus the matching prose in `skills/fix-issue/scripts/umbrella-handler.md` where pick-child eligibility is documented.
- **Suggested revision**: Address the concern above.


### FINDING_39: **code-quality** `skills/fix-issue/scripts/find-lock-issue.sh:855-857` — The block comment immediately above the `has_managed_prefix` gate still says managed prefixes are only `[IN PROGRESS]` / `[DONE]` / `[STALLED]`, omitting `[PLANNED]` even though the runtime check and the `ERROR=` string at line 864 include it. **Suggested fix:** Extend that comment to list all four prefixes so it cannot contradict the implementation.
- **Reviewer**: dyn-prefix-state-machine-output.txt
- **Concern**: - **code-quality** `skills/fix-issue/scripts/find-lock-issue.sh:855-857` — The block comment immediately above the `has_managed_prefix` gate still says managed prefixes are only `[IN PROGRESS]` / `[DONE]` / `[STALLED]`, omitting `[PLANNED]` even though the runtime check and the `ERROR=` string at line 864 include it. **Suggested fix:** Extend that comment to list all four prefixes so it cannot contradict the implementation.
- **Suggested revision**: Address the concern above.


### FINDING_43: **risk-integration** `scripts/design-log-publish.sh:156-175` — The script unconditionally attempts `git branch -D "$WT_BRANCH"` when `refs/heads/$WT_BRANCH` exists, ignores delete failures (`|| true`), then runs `git worktree add -b "$WT_BRANCH"`. If another publisher (or a leftover worktree) still holds that branch name, `worktree add` can fail while the error is only surfaced as the generic `design-log-publish: git worktree add failed`, so collisions on the same `RUN_ID` slug are hard to diagnose and there is no upfront check that the branch/worktree slot is free. **Suggested fix:** Before mutating refs, inspect `git worktree list` (and/or `git show-ref`) and fail with an explicit “branch `larch-log-design-<RUN_ID>` already in use” message when the branch is checked out elsewhere; avoid masking `branch -D` failures when the branch is still in use, and document in `scripts/design-log-publish.md` that concurrent publishes must not share a `RUN_ID` (and that `/design` is not serialized like `/implement` / `/fix-issue`).
- **Reviewer**: dyn-concurrency-safety-output.txt
- **Concern**: - **risk-integration** `scripts/design-log-publish.sh:156-175` — The script unconditionally attempts `git branch -D "$WT_BRANCH"` when `refs/heads/$WT_BRANCH` exists, ignores delete failures (`|| true`), then runs `git worktree add -b "$WT_BRANCH"`. If another publisher (or a leftover worktree) still holds that branch name, `worktree add` can fail while the error is only surfaced as the generic `design-log-publish: git worktree add failed`, so collisions on the same `RUN_ID` slug are hard to diagnose and there is no upfront check that the branch/worktree slot is free. **Suggested fix:** Before mutating refs, inspect `git worktree list` (and/or `git show-ref`) and fail with an explicit “branch `larch-log-design-<RUN_ID>` already in use” message when the branch is checked out elsewhere; avoid masking `branch -D` failures when the branch is still in use, and document in `scripts/design-log-publish.md` that concurrent publishes must not share a `RUN_ID` (and that `/design` is not serialized like `/implement` / `/fix-issue`).
- **Suggested revision**: Address the concern above.


### FINDING_7: risk-integration: scripts/design-log-publish.sh:359-360
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] gh pr merge stderr is discarded. Merge fails (policy_denied, etc.); operator gets PUBLISH_OK=false without GitHub’s reason on stderr. Stop redirecting stderr for gh pr merge (or tee/larch_err last lines).
- **Suggested revision**: Address the concern above.


### FINDING_8: risk-integration: skills/design/SKILL.md:813-816,989-1001
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] append-tool-failure for PUBLISH_OK=false only when SESSION_ENV_PATH is set. Standalone /design publish failure is not written to execution-issues.md; only nested runs get durable Warnings. Append failures to DESIGN_TMPDIR-backed log when SESSION_ENV_PATH is empty.
- **Suggested revision**: Address the concern above.


