### FINDING_1: correctness: scripts/design-log-publish.sh:128-130
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] git worktree add is unchecked while set -e is enabled; failure exits non-zero before emit_publish_result. Network or ref errors when adding the disposable worktree cause abrupt shell exit without PUBLISH_OK=false, breaking the documented stdout contract for callers parsing KEY=value lines. Wrap worktree add like other mutating steps: on failure larch_err, emit_publish_result false, exit 0, let EXIT trap clean up.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: scripts/design-log-publish.sh:219-223
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Early exit returns PUBLISH_OK=true with empty PR fields when git reports no changes under rel. If status/porcelain ever shows a false negative, SKILL treats publish as success while no PR merged and default branch may lack logs. Use a distinct skip flag or treat as non-success with explicit reason; add a guard assertion that this path is only for true no-op.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/design-log-publish.sh:217-223 vs scripts/lib-larch-log.sh:29-34
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Plan asked for larch_log_validate_slug; implementation duplicates slug case logic instead of shared helper. Future slug rule changes may update only one site, causing inconsistent validation between larch-log and design publish. Introduce non-exiting slug validator shared with larch_log_validate_slug or document intentional duplication in design-log-publish.md.
- **Suggested revision**: Address the concern above.

### FINDING_4: risk-integration: scripts/design-log-publish.sh:186-205
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] find pipelines append || true masking find failures. Permission or IO errors enumerating DESIGN_TMPDIR can drop all files silently and still complete merge with partial artifacts. Remove unconditional || true for find or check exit status and fail publish when enumeration fails.
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: scripts/design-log-publish.sh:253-257
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] PR URL/number parsed from free-text gh output via grep. gh output format changes could leave PR_NUM empty until fallback; primary path brittle. Prefer structured gh --json output for pr create when supported.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] code-quality: Makefile:9-10
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Whole .PHONY declaration rewritten for one new target name. Blame noise and harder review of unrelated Makefile history. Minimal .PHONY edit or line splitting in a separate cleanup change.
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: scripts/design-log-publish.sh:16-17,130
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Unguarded git worktree add under set -e breaks the PUBLISH_OK stdout contract on expected git failures. Example: origin ref missing or worktree add fails; script exits non-zero with no PUBLISH_OK= line so Step 5b cannot parse a controlled failure. Wrap worktree add in explicit if ! …; then emit_publish_result false; exit 0; fi (and keep cleanup in trap).
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: skills/design/SKILL.md:809-815
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Wrong reconciliation text when plan-block-write fails: warns steps 4–6 may have mutated GitHub though they are sequenced after step 3. Operator follows Step 5b after plan-block-write failure and believes rename/log publish already ran, causing incorrect manual cleanup. Reword failure guidance to match real ordering or explicitly skip steps 4–6 on step-3 failure.
- **Suggested revision**: Address the concern above.

### FINDING_9: risk-integration: skills/design/SKILL.md (Step 0 vs feature_description)
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Feature text still demands automatic branch creation at /design start; diff implements title + log publish only. Stakeholders expect a new design branch each run but behavior is unchanged from pre-commit baseline for branch creation. Align public requirements with shipped scope or implement branch creation in SKILL + scripts.
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: scripts/design-log-publish.sh:64-70
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Issue validation allows 0 while messages call it a positive integer. Call with --issue 0 passes validation though GitHub has no issue 0. Reject 0 or adjust documented wording to match validation.
- **Suggested revision**: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] correctness: scripts/test-design-log-publish.sh:519-523
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Gh stub for pr list is not flag-aware like real gh. Harness could miss regressions in gh flag handling only if production changes. Optionally tighten stub when touching tests.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: scripts/design-log-publish.sh:86-88;scripts/design-log-publish.md:40-42;scripts/test-design-log-publish.sh:82-90
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] dry-run emits PUBLISH_OK=true without git or tool checks; doc claims tool validation; harness runs dry-run outside a repo Operator or CI believes publish prerequisites are satisfied; real run fails immediately at git rev-parse or later; false confidence from contract and test Align behavior: run read-only prerequisite checks before dry-run success, or narrow contract and fix harness so dry-run does not pass outside a git worktree
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: scripts/design-log-publish.sh:64-70
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] --issue accepts 0 while messaging says positive integer Buggy caller passes issue 0; later gh or larch-log init errors or confusing semantics Reject 0 explicitly with a numeric-positive regex or dedicated case branch
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: scripts/test-design-log-publish.sh:1-148
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Plan-listed scenarios (jq missing PR exists path worktree recovery) not covered by harness Regression in admin-merge list fallback or jq requirement slips past CI until manual /design run Add harness cases for jq-off PATH pr create failure plus pr list recovery and optional cleanup assertions
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: scripts/design-log-publish.sh:186-194;scripts/design-log-publish.sh:219-222
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] find stderr discarded; empty staging can reach success-like stdout Find permission errors yield no files; early exit can report PUBLISH_OK true with no PR despite nonempty tmpdir Fail closed on find errors or assert minimum artifact set before declaring publish success
- **Suggested revision**: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] risk-integration: <TMPDIR>/round-1/diff.txt
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Precomputed diff file was empty Reviewer could not use launcher-provplied diff without git fallback Fix session export of diff.txt for future reviews
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: scripts/design-log-publish.sh:86-88;scripts/design-log-publish.md:40-42
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] dry-run emits PUBLISH_OK=true without git/gh/jq/origin-HEAD preflight despite contract claiming required-tool validation (minus jq). CI or wrappers treat dry-run as a publishability gate; immediate non-dry run fails on missing jq/gh or non-git cwd, producing false greens or wasted operator steps. Align behavior with docs by adding read-only preflight checks before PUBLISH_OK=true, or narrow the contract to argv plus tmpdir presence only.
- **Suggested revision**: Address the concern above.

### FINDING_18: correctness: scripts/design-log-publish.sh:64-70
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] --issue accepts 0 while messaging claims positive integer. Callers pass issue 0; later gh or larch-log errors are noisier and less uniform than an upfront validation failure. Explicitly reject 0 with the same machine-parseable failure path as other invalid issues.
- **Suggested revision**: Address the concern above.

### FINDING_19: security: scripts/design-log-publish.sh:194-205
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] find lacks -- before user-supplied DESIGN_TMPDIR roots. Rare pathological tmpdir names starting with - could be misparsed as find flags, skipping or mis-staging files. Use find -- "$DESIGN_TMPDIR" and find -- "$DESIGN_TMPDIR/render-cache" before predicates.
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: scripts/design-log-publish.sh:128-130
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] set -e causes non-zero exit without PUBLISH_OK on worktree bootstrap failures git worktree add / mktemp / mkdir failure yields bare shell exit; /design cannot parse stdout and may treat as crash Wrap bootstrap in explicit handler that emits emit_publish_result false and exit 0
- **Suggested revision**: Address the concern above.

### FINDING_21: risk-integration: scripts/design-log-publish.sh:217-225
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] set -e uncaught failures after staging (mv git add) break stdout contract mv or git add failure exits non-zero without machine lines Guard with if ! blocks that emit PUBLISH_OK=false exit 0
- **Suggested revision**: Address the concern above.

### FINDING_22: correctness: skills/design/SKILL.md:809-815
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Contradictory PLAN_WRITE_OK and recovery text for step 3 vs steps 4-6 Operators may skip needed reconcile steps or assume rename/publish ran when plan write failed Clarify abort ordering after failed plan-block-write; fix partial-mutation wording
- **Suggested revision**: Address the concern above.

### FINDING_23: correctness: scripts/design-log-publish.sh:64-70
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] --issue 0 accepted despite positive-integer message Scripts forward issue 0 into larch-log/gh paths that expect real issues Reject zero explicitly
- **Suggested revision**: Address the concern above.

### FINDING_24: risk-integration: scripts/design-log-publish.md:122-124 vs scripts/design-log-publish.sh:86-88
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Dry-run contract promises tool validation not implemented Dry-run reports success in environments missing git/gh/jq Update doc or add non-mutating probes
- **Suggested revision**: Address the concern above.

### FINDING_25: correctness: scripts/session-setup.sh:238-244 + skills/design/SKILL.md
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Fallback SESSION_ID can violate publish slug charset Publish skipped on exotic hostname without SESSION_ID-empty guidance Sanitize fallback id or document limitation
- **Suggested revision**: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] code-quality: (session launcher)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Empty precomputed diff file for stated session path Reviewer had to use git diff vs origin/main Launcher should materialize diff or pass correct path
- **Suggested revision**: Address the concern above.

### FINDING_27: correctness: skills/design/SKILL.md:179,809-815
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Step 5b and the clarify router describe rename plus design-log-publish immediately after plan-block-write without an explicit success-only gate; step 7 text also suggests steps 4-6 may run or partially mutate when step 3 fails. An orchestrator that sets PLAN_WRITE_OK from step 7 but still executes bullets 4-6 after a failed or skipped plan-block-write can mark the issue [PLANNED], open a log PR, or confuse operators about GitHub state while the larch:plan block is missing or stale. Add explicit if-plan-block-write-succeeded ordering for REPO, rename, and publish in both Step 5b and the clarify path; rewrite the step 7 parenthetical to match real failure modes only.
- **Suggested revision**: Address the concern above.

### FINDING_28: correctness: scripts/design-log-publish.sh:209-223
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] --issue validation allows 0, which is not a positive integer per the plan’s gh issue contract. gh or downstream tooling may receive issue 0 and fail or behave oddly depending on GitHub API behavior. Reject issue numbers that do not match ^[1-9][0-9]*$.
- **Suggested revision**: Address the concern above.

### FINDING_29: correctness: scripts/design-log-publish.sh:217-223
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Slug validation duplicates larch_log_validate_slug instead of invoking or centralizing it as the plan text states. Future edits to slug rules in lib-larch-log.sh could drift from design-log-publish.sh until a bug surfaces. Refactor to a shared non-exiting validator or align the written plan to describe duplicated predicate explicitly.
- **Suggested revision**: Address the concern above.

### FINDING_30: [OUT_OF_SCOPE] risk-integration: <TMPDIR>/round-1/diff.txt
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Precomputed diff path was empty; merge-base log vs local main was empty because HEAD is main. Reviewer had to substitute origin/main for the patch; launcher hygiene only. Regenerate or populate the sidecar diff for future reviews.
- **Suggested revision**: Address the concern above.

### FINDING_31: [OUT_OF_SCOPE] architecture: feature_description (supplied)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Feature description mentions creating a branch when /design starts; twelve-item implementation plan omits that scope. No contradiction with the written implementation plan, but product intent may be incomplete versus the narrative. If branch-at-start is required, add it as an explicit plan item and implement separately.
- **Suggested revision**: Address the concern above.

### FINDING_32: **correctness** `scripts/design-log-publish.sh:175-178` — `design_publish_stage_file` treats `larch_log_redact_file` as a normal function that returns non-zero on failure, but `larch_log_redact_file` in `scripts/lib-larch-log.sh:78-86` calls `larch_log_fail`, which **exits the whole process** (status 1/2) after printing `LOG_WRITTEN=false` / `ERROR=...` lines to stdout. That contradicts the script header (`scripts/design-log-publish.sh:13-14`) promising parseable `PUBLISH_OK=...` plus **exit 0** for operational failures, and can break callers that parse stdout only for `KEY=value` pairs. **Suggested fix:** Run redaction in a subshell and capture/redirect its stdout, add a non-exiting redact helper used only here, or duplicate the pipeline with `|| return 1` instead of routing through `larch_log_fail`.
- **Reviewer**: dyn-log-publish-safety-output.txt
- **Concern**: - **correctness** `scripts/design-log-publish.sh:175-178` — `design_publish_stage_file` treats `larch_log_redact_file` as a normal function that returns non-zero on failure, but `larch_log_redact_file` in `scripts/lib-larch-log.sh:78-86` calls `larch_log_fail`, which **exits the whole process** (status 1/2) after printing `LOG_WRITTEN=false` / `ERROR=...` lines to stdout. That contradicts the script header (`scripts/design-log-publish.sh:13-14`) promising parseable `PUBLISH_OK=...` plus **exit 0** for operational failures, and can break callers that parse stdout only for `KEY=value` pairs. **Suggested fix:** Run redaction in a subshell and capture/redirect its stdout, add a non-exiting redact helper used only here, or duplicate the pipeline with `|| return 1` instead of routing through `larch_log_fail`.
- **Suggested revision**: Address the concern above.

### FINDING_33: **risk-integration** `scripts/design-log-publish.sh:117-122,225-240` — After a successful `git commit` in the disposable worktree, a failing `git push` hits `emit_publish_result false` and `exit 0`, which still runs the `EXIT` trap `wt_cleanup` that **`git worktree remove --force`s** the only checkout holding that commit (push never updated `origin`), so the flushed, redacted tree can be discarded while the source tmpdir may no longer match what was committed. **Suggested fix:** On push failure after commit, either skip automatic worktree removal until logs are copied back to `$DESIGN_TMPDIR` or another ref, or move the commit onto a recovery ref in `$REPO_ROOT` before tearing down the worktree.
- **Reviewer**: dyn-log-publish-safety-output.txt
- **Concern**: - **risk-integration** `scripts/design-log-publish.sh:117-122,225-240` — After a successful `git commit` in the disposable worktree, a failing `git push` hits `emit_publish_result false` and `exit 0`, which still runs the `EXIT` trap `wt_cleanup` that **`git worktree remove --force`s** the only checkout holding that commit (push never updated `origin`), so the flushed, redacted tree can be discarded while the source tmpdir may no longer match what was committed. **Suggested fix:** On push failure after commit, either skip automatic worktree removal until logs are copied back to `$DESIGN_TMPDIR` or another ref, or move the commit onto a recovery ref in `$REPO_ROOT` before tearing down the worktree.
- **Suggested revision**: Address the concern above.

### FINDING_34: **risk-integration** `scripts/design-log-publish.sh:237-265` — If `git push` succeeds but `gh pr create` fails and `gh pr list ... --state open` returns nothing (auth/API glitch, transient GitHub error, or branch state not matching an open PR), the script exits with `PUBLISH_OK=false` while **`origin/larch-log-design-<RUN_ID>` can remain** with no merged PR, leaving shared remote state for operators to reconcile (the contract in `scripts/design-log-publish.md:46-52` only calls out the merge-admin case, not create/list failure after push). **Suggested fix:** Emit an explicit stderr breadcrumb with the remote branch name and, when merge/create is impossible, document or optionally run a guarded `git push origin :refs/heads/<branch>` after operator confirmation, or surface a single structured `RECOVERY_BRANCH=...` key for automation.
- **Reviewer**: dyn-log-publish-safety-output.txt
- **Concern**: - **risk-integration** `scripts/design-log-publish.sh:237-265` — If `git push` succeeds but `gh pr create` fails and `gh pr list ... --state open` returns nothing (auth/API glitch, transient GitHub error, or branch state not matching an open PR), the script exits with `PUBLISH_OK=false` while **`origin/larch-log-design-<RUN_ID>` can remain** with no merged PR, leaving shared remote state for operators to reconcile (the contract in `scripts/design-log-publish.md:46-52` only calls out the merge-admin case, not create/list failure after push). **Suggested fix:** Emit an explicit stderr breadcrumb with the remote branch name and, when merge/create is impossible, document or optionally run a guarded `git push origin :refs/heads/<branch>` after operator confirmation, or surface a single structured `RECOVERY_BRANCH=...` key for automation.
- **Suggested revision**: Address the concern above.

### FINDING_35: **security** `scripts/design-log-publish.sh:154-172` — Only basenames matching `*.meta` or `*-output*.json` receive structured sidecar trimming before `larch_log_redact_file`; every other regular file is copied whole into `trim_tmp`, so JSON (or other structured artifacts) that still carry a top-level `.result` or other high-entropy transcript fields but use a different naming pattern never hit `larch_redact_strip_json_result`, yet still flow to `redact-tmpdir-paths.sh` / `redact-secrets.sh` and can be merged publicly if those redactors do not model those fields. That is a completeness gap relative to the documented intent to strip `.result` from JSON sidecars and to the parity target of `scripts/larch-log.sh`’s round staging (which also limits JSON trimming to a basename case, but design’s public `--admin` merge path newly concentrates risk on whatever filenames `/design` actually emits). **Suggested fix:** Treat every `*.json` staging candidate as JSON for trimming (e.g. run `larch_redact_strip_json_result` on all `*.json` files, fail closed when JSON is invalid and trimming is required), or enumerate design-tmpdir basenames in tests and expand the case arms until coverage matches reality.
- **Reviewer**: dyn-redaction-completeness-output.txt
- **Concern**: - **security** `scripts/design-log-publish.sh:154-172` — Only basenames matching `*.meta` or `*-output*.json` receive structured sidecar trimming before `larch_log_redact_file`; every other regular file is copied whole into `trim_tmp`, so JSON (or other structured artifacts) that still carry a top-level `.result` or other high-entropy transcript fields but use a different naming pattern never hit `larch_redact_strip_json_result`, yet still flow to `redact-tmpdir-paths.sh` / `redact-secrets.sh` and can be merged publicly if those redactors do not model those fields. That is a completeness gap relative to the documented intent to strip `.result` from JSON sidecars and to the parity target of `scripts/larch-log.sh`’s round staging (which also limits JSON trimming to a basename case, but design’s public `--admin` merge path newly concentrates risk on whatever filenames `/design` actually emits). **Suggested fix:** Treat every `*.json` staging candidate as JSON for trimming (e.g. run `larch_redact_strip_json_result` on all `*.json` files, fail closed when JSON is invalid and trimming is required), or enumerate design-tmpdir basenames in tests and expand the case arms until coverage matches reality.
- **Suggested revision**: Address the concern above.

### FINDING_36: **risk-integration** `scripts/design-log-publish.sh:13-14,174-178` and `scripts/lib-larch-log.sh:78-86` — `design_publish_stage_file` calls `larch_log_redact_file`, whose failure path invokes `larch_log_fail` and exits the process with a non-zero status before `emit_publish_result` runs, contradicting the script’s own contract that expected failures emit `PUBLISH_OK=false` on stdout and exit `0`. Orchestrators that only parse stdout on success, or treat any non-zero exit as an unexpected shell failure, can mis-handle a load-bearing redaction failure even though the worktree is unlikely to be committed in that path. **Suggested fix:** Stop routing through `larch_log_fail` for this caller—either duplicate the small `"$redact_tmp" <"$input" | "$redact_secrets" >"$output"` pipeline with explicit `|| { emit_publish_result false; exit 0; }`, or add a soft-fail variant of `larch_log_redact_file` that returns status without calling `larch_log_fail`.
- **Reviewer**: dyn-redaction-completeness-output.txt
- **Concern**: - **risk-integration** `scripts/design-log-publish.sh:13-14,174-178` and `scripts/lib-larch-log.sh:78-86` — `design_publish_stage_file` calls `larch_log_redact_file`, whose failure path invokes `larch_log_fail` and exits the process with a non-zero status before `emit_publish_result` runs, contradicting the script’s own contract that expected failures emit `PUBLISH_OK=false` on stdout and exit `0`. Orchestrators that only parse stdout on success, or treat any non-zero exit as an unexpected shell failure, can mis-handle a load-bearing redaction failure even though the worktree is unlikely to be committed in that path. **Suggested fix:** Stop routing through `larch_log_fail` for this caller—either duplicate the small `"$redact_tmp" <"$input" | "$redact_secrets" >"$output"` pipeline with explicit `|| { emit_publish_result false; exit 0; }`, or add a soft-fail variant of `larch_log_redact_file` that returns status without calling `larch_log_fail`.
- **Suggested revision**: Address the concern above.

### FINDING_37: [OUT_OF_SCOPE] security
- **Reviewer**: dyn-redaction-completeness-output.txt
- **Concern**: - **security** `SECURITY.md:115-116` (durable run-store bullet) — States that schema v2 `manifest.json` records `operator_cwd` / `operator_repo_root` as local absolute paths, which conflicts with the `write_manifest_file` placeholder behavior described earlier in the same file (`"<OPERATOR_CWD>"` / `"<REPO_ROOT>"`); this documentation tension around committed manifests is not specific to `design-log-publish.sh`’s staging loop and appears broader than the new publish path alone.
- **Suggested revision**: Address the concern above.

### FINDING_38: [OUT_OF_SCOPE] security
- **Reviewer**: dyn-redaction-completeness-output.txt
- **Concern**: - **security** `.gitleaks.toml` / `SECURITY.md:98` — The `larch-logs/` gitleaks path allowlist means merged design logs are not regex-scanned at commit/PR time the way most tree paths are; reliance on the redaction pipeline was already the stated posture for that subtree, but it amplifies any trimming-pattern gaps above.
- **Suggested revision**: Address the concern above.

### FINDING_39: **correctness** `scripts/tracking-issue-write.sh:110-133` and `scripts/tracking-issue-write.sh:516-521` — The `planned` / `[PLANNED] ` additions are aligned with the existing rename pipeline: `state_to_prefix` emits the same canonical prefix string that `strip_lifecycle_prefix` removes, and the idempotency path’s `CUR_CANON_PREFIXES` case arm matches that same literal prefix after redaction, so a second `rename --state planned` on an already-canonical `[PLANNED] <tail>` title stays a no-op (`RENAMED=false`) without double-prefixing. **Suggested fix:** None.
- **Reviewer**: dyn-prefix-lifecycle-output.txt
- **Concern**: - **correctness** `scripts/tracking-issue-write.sh:110-133` and `scripts/tracking-issue-write.sh:516-521` — The `planned` / `[PLANNED] ` additions are aligned with the existing rename pipeline: `state_to_prefix` emits the same canonical prefix string that `strip_lifecycle_prefix` removes, and the idempotency path’s `CUR_CANON_PREFIXES` case arm matches that same literal prefix after redaction, so a second `rename --state planned` on an already-canonical `[PLANNED] <tail>` title stays a no-op (`RENAMED=false`) without double-prefixing. **Suggested fix:** None.
- **Suggested revision**: Address the concern above.

### FINDING_40: **correctness** `scripts/lib-title-markers.sh:43-55` — The new `[PLANNED] ` branch mirrors the other lifecycle branches: it matches only titles beginning with the managed `[PLANNED] ` prefix (including the single ASCII space) and inserts the signal marker immediately after that prefix using `${title#\[PLANNED\] }`, consistent with `strip_lifecycle_prefix`’s `${t#\[PLANNED\] }` in `tracking-issue-write.sh`. Bash 3.2 `case` globs match these literals as intended (verified behavior matches the other bracketed prefixes). **Suggested fix:** None.
- **Reviewer**: dyn-prefix-lifecycle-output.txt
- **Concern**: - **correctness** `scripts/lib-title-markers.sh:43-55` — The new `[PLANNED] ` branch mirrors the other lifecycle branches: it matches only titles beginning with the managed `[PLANNED] ` prefix (including the single ASCII space) and inserts the signal marker immediately after that prefix using `${title#\[PLANNED\] }`, consistent with `strip_lifecycle_prefix`’s `${t#\[PLANNED\] }` in `tracking-issue-write.sh`. Bash 3.2 `case` globs match these literals as intended (verified behavior matches the other bracketed prefixes). **Suggested fix:** None.
- **Suggested revision**: Address the concern above.

### FINDING_41: [OUT_OF_SCOPE] code-quality
- **Reviewer**: dyn-prefix-lifecycle-output.txt
- **Concern**: - **code-quality** `CHANGELOG.md` — Release/history prose for the tracking-issue rename subcommand still describes only `in-progress|done|stalled` in places; this branch does not touch `CHANGELOG.md`, so the drift is pre-existing relative to this diff, but operators relying on the changelog alone may still miss the new `planned` state until a future doc pass.
- **Suggested revision**: Address the concern above.

### FINDING_42: **risk-integration** `scripts/test-design-log-publish.sh:39-45` — The `gh` stub always exits `0` for `pr merge`, so CI never proves the failure contract in `scripts/design-log-publish.sh:270-281` (non‑zero merge still cleans up worktree, emits `PUBLISH_OK=false`, and preserves `PR_NUMBER`/`PR_URL`). **Suggested fix:** Extend the stub with an env‑gated branch (for example `GH_STUB_MERGE_RC=1`) that makes `pr merge` fail, run one publish invocation that gets past `pr create`, and assert stdout contains `PUBLISH_OK=false` plus the expected `PR_NUMBER=` while `pr merge` appears in `GH_STUB_LOG`.
- **Reviewer**: dyn-harness-coverage-output.txt
- **Concern**: - **risk-integration** `scripts/test-design-log-publish.sh:39-45` — The `gh` stub always exits `0` for `pr merge`, so CI never proves the failure contract in `scripts/design-log-publish.sh:270-281` (non‑zero merge still cleans up worktree, emits `PUBLISH_OK=false`, and preserves `PR_NUMBER`/`PR_URL`). **Suggested fix:** Extend the stub with an env‑gated branch (for example `GH_STUB_MERGE_RC=1`) that makes `pr merge` fail, run one publish invocation that gets past `pr create`, and assert stdout contains `PUBLISH_OK=false` plus the expected `PR_NUMBER=` while `pr merge` appears in `GH_STUB_LOG`.
- **Suggested revision**: Address the concern above.

### FINDING_43: **risk-integration** `scripts/test-design-log-publish.sh:35-37` — Every happy path forces `pr create` to print a PR URL, so the fallback that reparses `PR_NUM` via `gh pr list` / `gh pr view` in `scripts/design-log-publish.sh:260-267` is never exercised; mistakes in `grep`/`sed` URL parsing or `gh pr list` JSON/`jq` handling would not fail the harness. **Suggested fix:** Add a second stub variant where `pr create` exits non‑zero or prints output without a `https://…/pull/N` line while `pr list` still returns `[{"number":101}]` and `pr view` returns JSON with `url`, then assert a successful publish (or at least correct `PR_NUMBER`/`PR_URL` extraction) after merge.
- **Reviewer**: dyn-harness-coverage-output.txt
- **Concern**: - **risk-integration** `scripts/test-design-log-publish.sh:35-37` — Every happy path forces `pr create` to print a PR URL, so the fallback that reparses `PR_NUM` via `gh pr list` / `gh pr view` in `scripts/design-log-publish.sh:260-267` is never exercised; mistakes in `grep`/`sed` URL parsing or `gh pr list` JSON/`jq` handling would not fail the harness. **Suggested fix:** Add a second stub variant where `pr create` exits non‑zero or prints output without a `https://…/pull/N` line while `pr list` still returns `[{"number":101}]` and `pr view` returns JSON with `url`, then assert a successful publish (or at least correct `PR_NUMBER`/`PR_URL` extraction) after merge.
- **Suggested revision**: Address the concern above.

### FINDING_44: **risk-integration** `scripts/test-design-log-publish.sh:117-132` — The “worktree isolation” story is only indirectly covered by pulling `main` and checking merged files; there are no assertions that the disposable worktree and `larch-log-design-*` branch are gone, that `git worktree list` is clean, or that the consumer clone had an empty porcelain state aside from the expected fast‑forward—so regressions in `worktree remove` / `branch -D` / trap cleanup in `scripts/design-log-publish.sh:108-116` and `273-277` could slip through while artifacts still appear on `main` in this synthetic remote layout. **Suggested fix:** After the happy path, assert `git -C "$clone" worktree list` shows only the primary checkout, `git -C "$clone" branch --list 'larch-log-design-*'` is empty (or matches pre‑run), and `git -C "$clone" status --porcelain` is empty before/after `pull` as appropriate.
- **Reviewer**: dyn-harness-coverage-output.txt
- **Concern**: - **risk-integration** `scripts/test-design-log-publish.sh:117-132` — The “worktree isolation” story is only indirectly covered by pulling `main` and checking merged files; there are no assertions that the disposable worktree and `larch-log-design-*` branch are gone, that `git worktree list` is clean, or that the consumer clone had an empty porcelain state aside from the expected fast‑forward—so regressions in `worktree remove` / `branch -D` / trap cleanup in `scripts/design-log-publish.sh:108-116` and `273-277` could slip through while artifacts still appear on `main` in this synthetic remote layout. **Suggested fix:** After the happy path, assert `git -C "$clone" worktree list` shows only the primary checkout, `git -C "$clone" branch --list 'larch-log-design-*'` is empty (or matches pre‑run), and `git -C "$clone" status --porcelain` is empty before/after `pull` as appropriate.
- **Suggested revision**: Address the concern above.

### FINDING_45: [OUT_OF_SCOPE] **`scripts/test-tracking-issue-write.sh:11` and `97-146`** — The harness still fails fast if `tracking-issue-write.sh` is missing/non‑executable, and the new `planned` rename plus idempotent cases tie failures to concrete title/`RENAMED=`/`TITLE_CAPTURE` expectations (wrong prefix logic or an erroneous `gh issue edit` would trip the assertions or nonzero exit from the stub).
- **Reviewer**: dyn-harness-coverage-output.txt
- **Concern**: - **`scripts/test-tracking-issue-write.sh:11` and `97-146`** — The harness still fails fast if `tracking-issue-write.sh` is missing/non‑executable, and the new `planned` rename plus idempotent cases tie failures to concrete title/`RENAMED=`/`TITLE_CAPTURE` expectations (wrong prefix logic or an erroneous `gh issue edit` would trip the assertions or nonzero exit from the stub).
- **Suggested revision**: Address the concern above.

### FINDING_46: [OUT_OF_SCOPE] **`scripts/test-design-log-publish.sh:92-96` and `134-146`** — Invalid `--run-id` and invalid `*-output*.json` sidecars are covered with injected bad inputs and `PUBLISH_OK=false` expectations, which does exercise distinct failure paths from the happy path.
- **Reviewer**: dyn-harness-coverage-output.txt
- **Concern**: - **`scripts/test-design-log-publish.sh:92-96` and `134-146`** — Invalid `--run-id` and invalid `*-output*.json` sidecars are covered with injected bad inputs and `PUBLISH_OK=false` expectations, which does exercise distinct failure paths from the happy path.
- **Suggested revision**: Address the concern above.

### FINDING_47: [OUT_OF_SCOPE] **`skills/fix-issue/scripts/test-find-lock-issue.sh:676-701`** — Fixture `5b` adds integration coverage that `[PLANNED]` titles are treated as machine‑managed for lock eligibility, consistent with the prefix change in `find-lock-issue.sh`.
- **Reviewer**: dyn-harness-coverage-output.txt
- **Concern**: - **`skills/fix-issue/scripts/test-find-lock-issue.sh:676-701`** — Fixture `5b` adds integration coverage that `[PLANNED]` titles are treated as machine‑managed for lock eligibility, consistent with the prefix change in `find-lock-issue.sh`.
- **Suggested revision**: Address the concern above.

