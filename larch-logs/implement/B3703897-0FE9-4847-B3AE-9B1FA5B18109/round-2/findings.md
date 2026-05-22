### FINDING_1: code-quality: scripts/design-log-publish.sh:71-77
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Run-id slug validation duplicates lib-larch-log.sh larch_log_validate_slug pattern Two copies can drift if slug rules ever change; plan asked for helper reuse Add a non-stdout-polluting slug validator in lib-larch-log.sh used by both paths
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: scripts/design-log-publish.sh:199-211
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] .result stripped for all *.json not only *-output*.json Non-tool JSON under the design tmpdir loses a legitimate top-level result object Narrow the filename pattern or document broaden intent in design-log-publish.md
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: skills/design/SKILL.md:179,815
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Wording print `printf ...` confuses literal print vs printf builtin Orchestrator may emit wrong user-visible text Rephrase as run printf or show a single shell snippet
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] code-quality: Makefile:26-27
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] PHONY list remains one huge line Pre-existing style None required
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] risk-integration: (review environment)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] merge-base..HEAD and cache diff empty when HEAD is main Local review needs origin/main...HEAD or a feature branch None required
- **Suggested revision**: Address the concern above.

### FINDING_6: correctness: scripts/design-log-publish.sh:206-211
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Strips top-level .result from every *.json via larch_redact_strip_json_result. A non-sidecar design artifact foo.json that intentionally stores domain data under .result loses that field in committed logs. Limit stripping to known tool-output patterns (e.g. *-output*.json) or an allowlist.
- **Suggested revision**: Address the concern above.

### FINDING_7: risk-integration: scripts/design-log-publish.sh:359-360
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] gh pr merge stderr is discarded. Merge fails (policy_denied, etc.); operator gets PUBLISH_OK=false without GitHub’s reason on stderr. Stop redirecting stderr for gh pr merge (or tee/larch_err last lines).
- **Suggested revision**: Address the concern above.

### FINDING_8: risk-integration: skills/design/SKILL.md:813-816,989-1001
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] append-tool-failure for PUBLISH_OK=false only when SESSION_ENV_PATH is set. Standalone /design publish failure is not written to execution-issues.md; only nested runs get durable Warnings. Append failures to DESIGN_TMPDIR-backed log when SESSION_ENV_PATH is empty.
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: scripts/design-log-publish.sh:88-96
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Duplicate run-id slug validation vs lib-larch-log.sh. Future drift between duplicated case and larch_log_validate_slug causes inconsistent acceptance of RUN_ID. Centralize validation in one function with PUBLISH_OK=false mapping.
- **Suggested revision**: Address the concern above.

### FINDING_10: code-quality: skills/design/SKILL.md:989-990
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Wording says print printf. Orchestrator might emit the word print literally. Rephrase as run printf ...
- **Suggested revision**: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] risk-integration: <OPERATOR_REPO_PATH>/larch/.../diff.txt
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Empty precomputed diff; used origin/main..HEAD instead. Reviewer could not use capped cache file as intended. Use populated sidecar or same diff source CI uses.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: scripts/test-design-log-publish.sh:664-822
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No harness for git push failure after local commit in design-log-publish.sh Push failure recovery (recovery ref + no gh PR) can regress without CI signal Add git stub path that fails push only; assert PUBLISH_OK=false and recovery ref exists; assert gh log lacks pr merge
- **Suggested revision**: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] risk-integration: <TMPDIR>/round-2/diff.txt:1
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Precomputed diff file empty; merge-base..HEAD empty on main Reviewer must use alternate git range to see changes Launcher should populate diff.txt or document fallback command
- **Suggested revision**: Address the concern above.

### FINDING_14: security: scripts/design-log-publish.sh:258-276
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Symlinked or resolved-away render-cache root lets find emit paths outside DESIGN_TMPDIR; prefix strip fails and unintended files can still be staged under larch-logs/design/<RUN_ID>/render-cache and published. A hostile or mistaken render-cache symlink points find at a sensitive host directory; those files are ingested into the log commit/PR pipeline with only redactor-family protection. Reject symlink render-cache (or canonicalize roots) and refuse any enumerated path not strictly under the resolved render-cache directory.
- **Suggested revision**: Address the concern above.

### FINDING_15: code-quality: scripts/design-log-publish.sh:199-217
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Broad *.json .result stripping may exceed the intended sidecar-only contract from the written plan and differs from the narrower write-round wording in docs/run-logs.md. Non-sidecar JSON that legitimately uses a top-level .result field loses data in published design logs. Narrow the filename case to sidecar globs or update docs/plan text to match the broader behavior explicitly.
- **Suggested revision**: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] risk-integration: .gitleaks.toml / SECURITY.md (pre-existing)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] New design logs under larch-logs/ inherit the existing gitleaks allowlist gap for that subtree. Secrets pasted into design logs are less likely to be caught by regex scanners that skip larch-logs/. Policy is pre-existing; rely on redaction discipline and SECURITY.md guidance rather than treating this diff as introducing the gap.
- **Suggested revision**: Address the concern above.

### FINDING_17: architecture: skills/design/SKILL.md:819-828
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Step 5c deletes DESIGN_TMPDIR whenever PLAN_WRITE_OK=true, ignoring design-log publish outcome. Publish fails after successful plan-block-write; local design artifacts are removed so operators cannot retry publish or inspect the exact bytes that failed redaction/trim/gh without re-running the whole design. Gate cleanup on PUBLISH_OK (or a dedicated flag) when SESSION_ID was non-empty and publish was attempted; document recovery when tmpdir must be preserved.
- **Suggested revision**: Address the concern above.

### FINDING_18: correctness: scripts/design-log-publish.sh:297-300
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] No git changes under the log path yields PUBLISH_OK=true with empty PR fields. Re-run or identical tree makes the script report success without opening/merging a PR; consumers assume logs reached main. Emit an explicit skipped/unchanged outcome or treat no-commit as non-success for callers that require a merge.
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: skills/design/SKILL.md:814-715
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Issue title renamed to [PLANNED] before log publish completes. Publish or merge failure leaves GitHub title implying planned/logs flushed while default branch lacks larch-logs/design/<RUN_ID>. Reorder operations or document and enforce recovery semantics; avoid implying log merge from title alone.
- **Suggested revision**: Address the concern above.

### FINDING_20: correctness: scripts/design-log-publish.sh:198-217
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] All *.json files strip top-level .result, not only sidecar outputs. A non-output JSON artifact that must retain .result for diagnosis is silently truncated. Restrict trimming to known output filenames or document and test the broader policy.
- **Suggested revision**: Address the concern above.

### FINDING_21: architecture: skills/design/SKILL.md:179
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Clarify-loop exit references undefined Step 5 hygiene vs full cleanup. Publish failure on clarify path may or may not preserve tmpdir relative to the main Step 5c path, confusing operators. Spell out whether 5c runs on clarify-only exit and align with main path.
- **Suggested revision**: Address the concern above.

### FINDING_22: risk-integration: scripts/design-log-publish.sh:71-77
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Run-id slug rules are duplicated instead of using larch_log_validate_slug. Future slug tightening in lib-larch-log could leave design-log-publish accepting IDs larch-log init rejects or vice versa. Delegate validation to larch_log_validate_slug or a shared helper.
- **Suggested revision**: Address the concern above.

### FINDING_23: correctness: scripts/design-log-publish.sh:206-211
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Pasted plan Step 6 described stripping top-level .result only for *-output*.json; implementation strips for every *.json (tests assert plain.json). Operators relying on the narrower written rule might be surprised if a non-output JSON needed a top-level .result preserved in published logs. Narrow the case pattern to the planned output-json glob or update the canonical plan to the broader all-JSON rule.
- **Suggested revision**: Address the concern above.

### FINDING_24: architecture: scripts/design-log-publish.sh:71-77
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Plan text said validate via larch_log_validate_slug; code duplicates the case pattern instead of calling the helper. Future edits to slug rules in lib-larch-log.sh could drift unless both sites are updated, or someone might try to call larch_log_validate_slug and break the PUBLISH_OK exit-0 contract. Document the intentional duplication or add a non-exiting shared validator used by both paths.
- **Suggested revision**: Address the concern above.

### FINDING_25: risk-integration: scripts/design-log-publish.sh:297-301
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Clean git tree under larch-logs/design/$RUN_ID yields PUBLISH_OK=true with empty PR fields and no PR merge. Downstream automation interpreting PUBLISH_OK=true as always meaning a merged PR could take the wrong branch on a no-op publish. Document the no-op path or add an explicit machine-readable marker for skipped PR.
- **Suggested revision**: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] correctness: (review environment)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Precomputed diff cache empty; local main equaled HEAD so merge-base log was empty. Reviewer could conclude there was no change without fetching diff against origin/main. Have the launcher emit a non-empty diff against the integration base.
- **Suggested revision**: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] architecture: (acceptance anchor)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Acceptance claims all 12 review findings addressed without listing them in context. Cannot verify closure of each finding from supplied materials alone. Attach the finding enumeration to the review packet.
- **Suggested revision**: Address the concern above.

### FINDING_28: **correctness** `scripts/design-log-publish.sh:297-301` — The “no tracked changes under `larch-logs/design/$RUN_ID`” fast path is implemented as `if ! git -C "$WT_DIR" status --porcelain -- "$rel" | grep -q .; then … PUBLISH_OK=true …`. With `set -o pipefail`, any **non-zero** pipeline status—including a **failed** `git status` (disk/repo error, broken worktree, etc.)—is treated the same as “grep found no lines”, because both yield a failing pipeline and `!` flips that into a successful `if` condition. That can emit `PUBLISH_OK=true` with empty `PR_NUMBER`/`PR_URL` even though nothing was verified as clean or published. **Suggested fix:** avoid coupling failure to emptiness; e.g. run `git status` to a temp file or variable with an explicit `git … status` success check first, then separately test `-s`/non-empty output, or use a two-step `if git …; then …; else … fi` pattern so only true “empty porcelain for `$rel`” hits the no-op success path.
- **Reviewer**: dyn-shell-robustness-output.txt
- **Concern**: - **correctness** `scripts/design-log-publish.sh:297-301` — The “no tracked changes under `larch-logs/design/$RUN_ID`” fast path is implemented as `if ! git -C "$WT_DIR" status --porcelain -- "$rel" | grep -q .; then … PUBLISH_OK=true …`. With `set -o pipefail`, any **non-zero** pipeline status—including a **failed** `git status` (disk/repo error, broken worktree, etc.)—is treated the same as “grep found no lines”, because both yield a failing pipeline and `!` flips that into a successful `if` condition. That can emit `PUBLISH_OK=true` with empty `PR_NUMBER`/`PR_URL` even though nothing was verified as clean or published. **Suggested fix:** avoid coupling failure to emptiness; e.g. run `git status` to a temp file or variable with an explicit `git … status` success check first, then separately test `-s`/non-empty output, or use a two-step `if git …; then …; else … fi` pattern so only true “empty porcelain for `$rel`” hits the no-op success path.
- **Suggested revision**: Address the concern above.

### FINDING_29: **code-quality** `scripts/design-log-publish.sh:115-136` — Non-`--dry-run` mode requires `jq` up front but does not similarly preflight `gh` before allocating the disposable worktree, initializing logs, staging, trimming, and redacting. A missing/broken `gh` only surfaces at PR creation time, wasting work and making failures harder to reason about in automation. **Suggested fix:** after the `jq` check (and alongside `git rev-parse` / `ORIGIN_DEFAULT` resolution), add `command -v gh`/`gh auth status` (per repo policy) and fail fast with `PUBLISH_OK=false` before `worktree add`.
- **Reviewer**: dyn-shell-robustness-output.txt
- **Concern**: - **code-quality** `scripts/design-log-publish.sh:115-136` — Non-`--dry-run` mode requires `jq` up front but does not similarly preflight `gh` before allocating the disposable worktree, initializing logs, staging, trimming, and redacting. A missing/broken `gh` only surfaces at PR creation time, wasting work and making failures harder to reason about in automation. **Suggested fix:** after the `jq` check (and alongside `git rev-parse` / `ORIGIN_DEFAULT` resolution), add `command -v gh`/`gh auth status` (per repo policy) and fail fast with `PUBLISH_OK=false` before `worktree add`.
- **Suggested revision**: Address the concern above.

### FINDING_30: [OUT_OF_SCOPE] The path `<TMPDIR>/round-2/diff.txt` was empty, so review used the current tree and a focused `git diff origin/main..HEAD` for the listed shell files; the broader branch diff also contains large unrelated churn (for example under `larch-logs/` and `skills/review/scripts/`) that this shell-robustness pass did not treat as part of the scoped feature surface.
- **Reviewer**: dyn-shell-robustness-output.txt
- **Concern**: - The path `<TMPDIR>/round-2/diff.txt` was empty, so review used the current tree and a focused `git diff origin/main..HEAD` for the listed shell files; the broader branch diff also contains large unrelated churn (for example under `larch-logs/` and `skills/review/scripts/`) that this shell-robustness pass did not treat as part of the scoped feature surface.
- **Suggested revision**: Address the concern above.

### FINDING_31: [OUT_OF_SCOPE] `git log "$(git merge-base HEAD main)"..HEAD --oneline` was empty because local `HEAD` matches local `main`; commits on top of upstream `main` were `4173ce19` and `d8df7c0c` per `git log origin/main..HEAD --oneline`.
- **Reviewer**: dyn-shell-robustness-output.txt
- **Concern**: - `git log "$(git merge-base HEAD main)"..HEAD --oneline` was empty because local `HEAD` matches local `main`; commits on top of upstream `main` were `4173ce19` and `d8df7c0c` per `git log origin/main..HEAD --oneline`.
- **Suggested revision**: Address the concern above.

### FINDING_32: **security** `scripts/design-log-publish.sh:199-211` and `scripts/lib-redact.sh:12-18` — `design_publish_stage_file` runs `larch_redact_strip_json_result` on every basename matching `*.json`, but that helper only deletes a **top-level** `.result` when the document root is a JSON object (`jq 'if type == "object" then del(.result) else . end'` and the Python branch’s `isinstance(data, dict)` guard). Valid JSON whose root is an array, or objects that carry sensitive `.result` fields nested under other keys, pass through unchanged into the `redact-tmpdir-paths.sh` / `redact-secrets.sh` pipeline, so a public PR could still contain `.result` blobs if the design tmpdir ever includes such shapes. **Suggested fix:** Either narrow the `*.json` branch to the same basename patterns as `stage_round_artifact` in `scripts/larch-log.sh` (`*-output.txt.json` and `*-output-*.txt.json`, lines 113–114), where sidecars are known to be single objects, or harden `larch_redact_strip_json_result` to recurse (for example `walk(if type == "object" then del(.result) else . end)` with a matching Python traversal) so every `.result` key is removed before publish.
- **Reviewer**: dyn-redaction-completeness-output.txt
- **Concern**: - **security** `scripts/design-log-publish.sh:199-211` and `scripts/lib-redact.sh:12-18` — `design_publish_stage_file` runs `larch_redact_strip_json_result` on every basename matching `*.json`, but that helper only deletes a **top-level** `.result` when the document root is a JSON object (`jq 'if type == "object" then del(.result) else . end'` and the Python branch’s `isinstance(data, dict)` guard). Valid JSON whose root is an array, or objects that carry sensitive `.result` fields nested under other keys, pass through unchanged into the `redact-tmpdir-paths.sh` / `redact-secrets.sh` pipeline, so a public PR could still contain `.result` blobs if the design tmpdir ever includes such shapes. **Suggested fix:** Either narrow the `*.json` branch to the same basename patterns as `stage_round_artifact` in `scripts/larch-log.sh` (`*-output.txt.json` and `*-output-*.txt.json`, lines 113–114), where sidecars are known to be single objects, or harden `larch_redact_strip_json_result` to recurse (for example `walk(if type == "object" then del(.result) else . end)` with a matching Python traversal) so every `.result` key is removed before publish.
- **Suggested revision**: Address the concern above.

### FINDING_33: [OUT_OF_SCOPE] The precomputed diff at `<TMPDIR>/round-2/diff.txt` was empty and `git log "$(git merge-base HEAD main)"..HEAD --oneline` / `git diff "$(git merge-base HEAD main)"..HEAD` produced no output in this workspace, so the review relied on the current contents of the cited files rather than a branch-specific diff artifact.
- **Reviewer**: dyn-redaction-completeness-output.txt
- **Concern**: - The precomputed diff at `<TMPDIR>/round-2/diff.txt` was empty and `git log "$(git merge-base HEAD main)"..HEAD --oneline` / `git diff "$(git merge-base HEAD main)"..HEAD` produced no output in this workspace, so the review relied on the current contents of the cited files rather than a branch-specific diff artifact.
- **Suggested revision**: Address the concern above.

### FINDING_34: [OUT_OF_SCOPE] `larch_redact_strip_json_json` redirects `jq` stderr to `/dev/null` (`scripts/lib-redact.sh:16`), which obscures diagnostics; invalid JSON still yields a non-zero `jq` exit and triggers the Python fallback or failure, so this is pre-existing noise rather than a silent-parse success path.
- **Reviewer**: dyn-redaction-completeness-output.txt
- **Concern**: - `larch_redact_strip_json_json` redirects `jq` stderr to `/dev/null` (`scripts/lib-redact.sh:16`), which obscures diagnostics; invalid JSON still yields a non-zero `jq` exit and triggers the Python fallback or failure, so this is pre-existing noise rather than a silent-parse success path.
- **Suggested revision**: Address the concern above.

### FINDING_35: [OUT_OF_SCOPE] Enumeration uses `find … -type f` (`scripts/design-log-publish.sh:239-239` and `261-261`), so symbolic links are never passed to `design_publish_stage_file`; the later `[[ -L "$src" ]]` guard (`scripts/design-log-publish.sh:192-194`) is redundant but consistent with fail-safe skipping.
- **Reviewer**: dyn-redaction-completeness-output.txt
- **Concern**: - Enumeration uses `find … -type f` (`scripts/design-log-publish.sh:239-239` and `261-261`), so symbolic links are never passed to `design_publish_stage_file`; the later `[[ -L "$src" ]]` guard (`scripts/design-log-publish.sh:192-194`) is redundant but consistent with fail-safe skipping.
- **Suggested revision**: Address the concern above.

### FINDING_36: [OUT_OF_SCOPE] Redaction runs from a temp trim file into `$RUN_DEST/...` under the disposable worktree (`scripts/design-log-publish.sh:218-230`); sources under `DESIGN_TMPDIR` are only read or copied into `trim_tmp`, not rewritten in place by the redact scripts.
- **Reviewer**: dyn-redaction-completeness-output.txt
- **Concern**: - Redaction runs from a temp trim file into `$RUN_DEST/...` under the disposable worktree (`scripts/design-log-publish.sh:218-230`); sources under `DESIGN_TMPDIR` are only read or copied into `trim_tmp`, not rewritten in place by the redact scripts.
- **Suggested revision**: Address the concern above.

### FINDING_37: [OUT_OF_SCOPE] `manifest.json` created in the worktree by `larch-log.sh init` uses placeholder `operator_cwd` / `operator_repo_root` values (`scripts/larch-log.sh:149-175`), and only `updated_at` is refreshed via `jq` (`scripts/design-log-publish.sh:281-295`), so that file does not bypass path redaction in a meaningful way compared to copied artifacts.
- **Reviewer**: dyn-redaction-completeness-output.txt
- **Concern**: - `manifest.json` created in the worktree by `larch-log.sh init` uses placeholder `operator_cwd` / `operator_repo_root` values (`scripts/larch-log.sh:149-175`), and only `updated_at` is refreshed via `jq` (`scripts/design-log-publish.sh:281-295`), so that file does not bypass path redaction in a meaningful way compared to copied artifacts.
- **Suggested revision**: Address the concern above.

### FINDING_38: **correctness** `skills/fix-issue/scripts/umbrella-handler.sh:213-220` — `has_managed_prefix` here matches only `[IN PROGRESS] `, `[DONE] `, and `[STALLED] `, while `child_eligible` calls this helper to decide umbrella child dispatch; `find-lock-issue.sh`’s parallel helper includes `[PLANNED] `, so `pick-child` can return a child titled `[PLANNED] …` that the explicit non-umbrella path would reject, violating the intended “machine-managed lifecycle prefix” contract for `/fix-issue`. **Suggested fix:** Add the same `'[PLANNED] '*) return 0 ;;` branch (and trailing-space semantics) as in `skills/fix-issue/scripts/find-lock-issue.sh:146-151`, and update the nearby comments that still claim parity with `find-lock-issue.sh` or list only three prefixes (`skills/fix-issue/scripts/umbrella-handler.sh:47-51`, `skills/fix-issue/scripts/umbrella-handler.sh:210-212`) plus the matching prose in `skills/fix-issue/scripts/umbrella-handler.md` where pick-child eligibility is documented.
- **Reviewer**: dyn-prefix-state-machine-output.txt
- **Concern**: - **correctness** `skills/fix-issue/scripts/umbrella-handler.sh:213-220` — `has_managed_prefix` here matches only `[IN PROGRESS] `, `[DONE] `, and `[STALLED] `, while `child_eligible` calls this helper to decide umbrella child dispatch; `find-lock-issue.sh`’s parallel helper includes `[PLANNED] `, so `pick-child` can return a child titled `[PLANNED] …` that the explicit non-umbrella path would reject, violating the intended “machine-managed lifecycle prefix” contract for `/fix-issue`. **Suggested fix:** Add the same `'[PLANNED] '*) return 0 ;;` branch (and trailing-space semantics) as in `skills/fix-issue/scripts/find-lock-issue.sh:146-151`, and update the nearby comments that still claim parity with `find-lock-issue.sh` or list only three prefixes (`skills/fix-issue/scripts/umbrella-handler.sh:47-51`, `skills/fix-issue/scripts/umbrella-handler.sh:210-212`) plus the matching prose in `skills/fix-issue/scripts/umbrella-handler.md` where pick-child eligibility is documented.
- **Suggested revision**: Address the concern above.

### FINDING_39: **code-quality** `skills/fix-issue/scripts/find-lock-issue.sh:855-857` — The block comment immediately above the `has_managed_prefix` gate still says managed prefixes are only `[IN PROGRESS]` / `[DONE]` / `[STALLED]`, omitting `[PLANNED]` even though the runtime check and the `ERROR=` string at line 864 include it. **Suggested fix:** Extend that comment to list all four prefixes so it cannot contradict the implementation.
- **Reviewer**: dyn-prefix-state-machine-output.txt
- **Concern**: - **code-quality** `skills/fix-issue/scripts/find-lock-issue.sh:855-857` — The block comment immediately above the `has_managed_prefix` gate still says managed prefixes are only `[IN PROGRESS]` / `[DONE]` / `[STALLED]`, omitting `[PLANNED]` even though the runtime check and the `ERROR=` string at line 864 include it. **Suggested fix:** Extend that comment to list all four prefixes so it cannot contradict the implementation.
- **Suggested revision**: Address the concern above.

### FINDING_40: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: dyn-prefix-state-machine-output.txt
- **Concern**: - **risk-integration** `skills/fix-issue/scripts/find-lock-issue.md:7` — The “Verify” step still describes managed lifecycle title prefixes as only `[IN PROGRESS]` / `[DONE]` / `[STALLED]`, omitting `[PLANNED]`; align this contract doc with `find-lock-issue.sh` when convenient.
- **Suggested revision**: Address the concern above.

### FINDING_41: [OUT_OF_SCOPE] code-quality
- **Reviewer**: dyn-prefix-state-machine-output.txt
- **Concern**: - **code-quality** `scripts/lib-title-markers.md:1-4` — The stub points readers to `tracking-issue-write.md` but does not explicitly mention `[PLANNED]`; optional alignment for skimmers.
- **Suggested revision**: Address the concern above.

### FINDING_42: [OUT_OF_SCOPE] code-quality
- **Reviewer**: dyn-prefix-state-machine-output.txt
- **Concern**: - **code-quality** `skills/fix-issue/SKILL.md:415` — Known-limitations prose still lists three managed prefixes for explicit-target rejection; same optional doc alignment as above. **Note:** The precomputed diff at `<TMPDIR>/round-2/diff.txt` was empty in this environment, and `git log $(git merge-base HEAD main)..HEAD --oneline` produced no lines; the review above is from the current tree. The five coordinated sites in `scripts/tracking-issue-write.sh` (`state_to_prefix`, `strip_lifecycle_prefix`, invalid `--state` message, `usage`, `CUR_CANON_PREFIXES`), `scripts/lib-title-markers.sh:53-55` (`insert_signal_marker` stripping `${title#\[PLANNED\] }` before inserting the signal block), and `skills/fix-issue/scripts/find-lock-issue.sh:146-151` / `864` appear mutually consistent for the exact `[PLANNED] ` spelling and round-trip with `planned` → `[PLANNED] `.
- **Suggested revision**: Address the concern above.

### FINDING_43: **risk-integration** `scripts/design-log-publish.sh:156-175` — The script unconditionally attempts `git branch -D "$WT_BRANCH"` when `refs/heads/$WT_BRANCH` exists, ignores delete failures (`|| true`), then runs `git worktree add -b "$WT_BRANCH"`. If another publisher (or a leftover worktree) still holds that branch name, `worktree add` can fail while the error is only surfaced as the generic `design-log-publish: git worktree add failed`, so collisions on the same `RUN_ID` slug are hard to diagnose and there is no upfront check that the branch/worktree slot is free. **Suggested fix:** Before mutating refs, inspect `git worktree list` (and/or `git show-ref`) and fail with an explicit “branch `larch-log-design-<RUN_ID>` already in use” message when the branch is checked out elsewhere; avoid masking `branch -D` failures when the branch is still in use, and document in `scripts/design-log-publish.md` that concurrent publishes must not share a `RUN_ID` (and that `/design` is not serialized like `/implement` / `/fix-issue`).
- **Reviewer**: dyn-concurrency-safety-output.txt
- **Concern**: - **risk-integration** `scripts/design-log-publish.sh:156-175` — The script unconditionally attempts `git branch -D "$WT_BRANCH"` when `refs/heads/$WT_BRANCH` exists, ignores delete failures (`|| true`), then runs `git worktree add -b "$WT_BRANCH"`. If another publisher (or a leftover worktree) still holds that branch name, `worktree add` can fail while the error is only surfaced as the generic `design-log-publish: git worktree add failed`, so collisions on the same `RUN_ID` slug are hard to diagnose and there is no upfront check that the branch/worktree slot is free. **Suggested fix:** Before mutating refs, inspect `git worktree list` (and/or `git show-ref`) and fail with an explicit “branch `larch-log-design-<RUN_ID>` already in use” message when the branch is checked out elsewhere; avoid masking `branch -D` failures when the branch is still in use, and document in `scripts/design-log-publish.md` that concurrent publishes must not share a `RUN_ID` (and that `/design` is not serialized like `/implement` / `/fix-issue`).
- **Suggested revision**: Address the concern above.

### FINDING_44: **risk-integration** `scripts/design-log-publish.sh:319-326` — On `git push` failure the script runs `git -C "$REPO_ROOT" branch -f "larch-log-design-recovery-${RUN_ID}" "$commit_sha"`, so every recovery ref for a slug is a single fixed name; two overlapping invocations that both reach this path with the same `RUN_ID` (e.g. two manual retries in parallel) can race on that ref and the later `-f` can erase the earlier recovery pointer. **Suggested fix:** Make recovery refs unique per attempt (`$$`, short random suffix, or timestamp) and emit which ref was written, or use a file lock / flock around the whole publish for a given `(REPO_ROOT, RUN_ID)` if you need a stable recovery name.
- **Reviewer**: dyn-concurrency-safety-output.txt
- **Concern**: - **risk-integration** `scripts/design-log-publish.sh:319-326` — On `git push` failure the script runs `git -C "$REPO_ROOT" branch -f "larch-log-design-recovery-${RUN_ID}" "$commit_sha"`, so every recovery ref for a slug is a single fixed name; two overlapping invocations that both reach this path with the same `RUN_ID` (e.g. two manual retries in parallel) can race on that ref and the later `-f` can erase the earlier recovery pointer. **Suggested fix:** Make recovery refs unique per attempt (`$$`, short random suffix, or timestamp) and emit which ref was written, or use a file lock / flock around the whole publish for a given `(REPO_ROOT, RUN_ID)` if you need a stable recovery name.
- **Suggested revision**: Address the concern above.

### FINDING_45: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: dyn-concurrency-safety-output.txt
- **Concern**: - **risk-integration** (pre-existing / not amplified by this diff) — `AGENTS.md` still states a single-runner invariant only for `/implement` and `/fix-issue`; there is no matching serialization for `/design`, so GitHub-side races (two `/design` runs on the same issue) remain a process-level concern rather than something this script resolves.
- **Suggested revision**: Address the concern above.

### FINDING_46: [OUT_OF_SCOPE] risk-integration: scripts/session-setup.sh:238-245
- **Reviewer**: dyn-concurrency-safety-output.txt
- **Concern**: - **risk-integration** (mitigating, no issue) — Default `SESSION_ID` from `session-setup.sh` uses `uuidgen` when available ([`scripts/session-setup.sh:238-245`](<OPERATOR_REPO_PATH>/scripts/session-setup.sh)), so `larch-log-design-${RUN_ID}` branch names are practically unique across concurrent normal `/design` sessions; collision risk concentrates in reused or manually chosen identical `--run-id` values passed into `design-log-publish.sh`, not “same second” timestamps. **Note:** The precomputed diff at `<TMPDIR>/round-2/diff.txt` was empty; analysis used the current tree’s [`scripts/design-log-publish.sh`](<OPERATOR_REPO_PATH>/scripts/design-log-publish.sh) and related files. Read-only `git log $(git merge-base HEAD main)..HEAD` on this checkout was empty because `HEAD` is `main`; commits were inferred from `git diff origin/main..HEAD --stat` (local `main` ahead of `origin/main` by two commits).
- **Suggested revision**: Address the concern above.

