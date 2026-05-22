### FINDING_1: correctness: scripts/design-log-publish.sh:128-130
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] git worktree add is unchecked while set -e is enabled; failure exits non-zero before emit_publish_result. Network or ref errors when adding the disposable worktree cause abrupt shell exit without PUBLISH_OK=false, breaking the documented stdout contract for callers parsing KEY=value lines. Wrap worktree add like other mutating steps: on failure larch_err, emit_publish_result false, exit 0, let EXIT trap clean up.
- **Suggested revision**: Address the concern above.


### FINDING_10: correctness: scripts/design-log-publish.sh:64-70
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Issue validation allows 0 while messages call it a positive integer. Call with --issue 0 passes validation though GitHub has no issue 0. Reject 0 or adjust documented wording to match validation.
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


### FINDING_17: risk-integration: scripts/design-log-publish.sh:86-88;scripts/design-log-publish.md:40-42
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] dry-run emits PUBLISH_OK=true without git/gh/jq/origin-HEAD preflight despite contract claiming required-tool validation (minus jq). CI or wrappers treat dry-run as a publishability gate; immediate non-dry run fails on missing jq/gh or non-git cwd, producing false greens or wasted operator steps. Align behavior with docs by adding read-only preflight checks before PUBLISH_OK=true, or narrow the contract to argv plus tmpdir presence only.
- **Suggested revision**: Address the concern above.


### FINDING_18: correctness: scripts/design-log-publish.sh:64-70
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] --issue accepts 0 while messaging claims positive integer. Callers pass issue 0; later gh or larch-log errors are noisier and less uniform than an upfront validation failure. Explicitly reject 0 with the same machine-parseable failure path as other invalid issues.
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


### FINDING_27: correctness: skills/design/SKILL.md:179,809-815
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Step 5b and the clarify router describe rename plus design-log-publish immediately after plan-block-write without an explicit success-only gate; step 7 text also suggests steps 4-6 may run or partially mutate when step 3 fails. An orchestrator that sets PLAN_WRITE_OK from step 7 but still executes bullets 4-6 after a failed or skipped plan-block-write can mark the issue [PLANNED], open a log PR, or confuse operators about GitHub state while the larch:plan block is missing or stale. Add explicit if-plan-block-write-succeeded ordering for REPO, rename, and publish in both Step 5b and the clarify path; rewrite the step 7 parenthetical to match real failure modes only.
- **Suggested revision**: Address the concern above.


### FINDING_28: correctness: scripts/design-log-publish.sh:209-223
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] --issue validation allows 0, which is not a positive integer per the plan’s gh issue contract. gh or downstream tooling may receive issue 0 and fail or behave oddly depending on GitHub API behavior. Reject issue numbers that do not match ^[1-9][0-9]*$.
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


### FINDING_4: risk-integration: scripts/design-log-publish.sh:186-205
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] find pipelines append || true masking find failures. Permission or IO errors enumerating DESIGN_TMPDIR can drop all files silently and still complete merge with partial artifacts. Remove unconditional || true for find or check exit status and fail publish when enumeration fails.
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


### FINDING_7: correctness: scripts/design-log-publish.sh:16-17,130
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Unguarded git worktree add under set -e breaks the PUBLISH_OK stdout contract on expected git failures. Example: origin ref missing or worktree add fails; script exits non-zero with no PUBLISH_OK= line so Step 5b cannot parse a controlled failure. Wrap worktree add in explicit if ! …; then emit_publish_result false; exit 0; fi (and keep cleanup in trap).
- **Suggested revision**: Address the concern above.


### FINDING_8: correctness: skills/design/SKILL.md:809-815
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Wrong reconciliation text when plan-block-write fails: warns steps 4–6 may have mutated GitHub though they are sequenced after step 3. Operator follows Step 5b after plan-block-write failure and believes rename/log publish already ran, causing incorrect manual cleanup. Reword failure guidance to match real ordering or explicitly skip steps 4–6 on step-3 failure.
- **Suggested revision**: Address the concern above.


