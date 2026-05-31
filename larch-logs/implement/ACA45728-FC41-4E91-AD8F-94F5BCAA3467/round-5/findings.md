Normalizing the reviewer inputs into merged in-scope findings and separate OOS blocks, preserving verbatim revision text where reviewers supplied it.
### FINDING_1: launch-cursor-implement post-failure tail prefers SIDECAR over diag
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-flow-output.txt, dyn-fd-routing-output.txt, dyn-tail-redaction-output.txt, dyn-cleanup-retention-output.txt
- **Severity**: important
- **Concern**: On agent failure (`LAUNCHER_EXIT != 0`) at `scripts/launch-cursor-implement.sh:325-333`, the launcher calls `write_failed_agent_stderr_tail` with `_FAILURE_OUTPUT` defaulting to non-empty `$SIDECAR_LOG` (wrapper `2>&1` capture) and only falls back to `${TRANSCRIPT_PATH}.diag` when the sidecar is empty. Under `--capture-stdout-only`, `run-external-agent.sh` has usually already written a redacted `${TRANSCRIPT_PATH}.stderr-tail` from `.diag`. The post-loop write can replace actionable agent stderr with wrapper-heavy content (and `write_failed_agent_stderr_tail` may remove an existing tail when rendering fails). The manifest-`bailed` block at 354-361 correctly prefers `.diag` first; the post-agent path does not. This weakens chat surfacing on the cursor-implement lane and conflicts with the plan’s “no extra producer on the agent path” rule.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-flow-output.txt: Mirror the bailed-manifest source order (prefer `${TRANSCRIPT_PATH}.diag`, then `$SIDECAR_LOG`), or skip the post-loop write when `[[ -s "${TRANSCRIPT_PATH}.stderr-tail" ]]` after `run-external-agent` has already produced a tail—matching the plan’s “no additional producer on the agent path” rule for cursor-implement.
  - From dyn-fd-routing-output.txt: Treat `run-external-agent` as the producer on the agent path: skip the post-loop write when `[[ -s "${TRANSCRIPT_PATH}.stderr-tail" ]]`, or prefer `${TRANSCRIPT_PATH}.diag` over `$SIDECAR_LOG` when both are non-empty (matching the manifest-`bailed` block at `354-361` and the plan’s “verify mode first / no clobber” rule). Keep explicit `write_failed_agent_stderr_tail` only for pre-agent paths (model-args, preflight) where `run-external-agent` never runs.
  - From dyn-tail-redaction-output.txt: For `--capture-stdout-only`, skip the post-loop write when `${TRANSCRIPT_PATH}.stderr-tail` is already non-empty, or mirror `select_failed_agent_stderr_source` (prefer `.diag`, then sidecar only if `.diag` is empty) so producer writes cannot clobber the redacted `.diag`-based tail.
  - From dyn-cleanup-retention-output.txt: Mirror `run_cursor` in `scripts/lint-fix-loop.sh:302-309` and the manifest-`bailed` path in `skills/implement/scripts/step2-implement.sh:1080-1086`: call `write_failed_agent_stderr_tail` only when `[[ ! -s "${TRANSCRIPT_PATH}.stderr-tail" ]]`, and when a fallback write is needed prefer `${TRANSCRIPT_PATH}.diag` over `$SIDECAR_LOG`.

### FINDING_2: Duplicated STDERR_TAIL_PATH / CODER_LOG_FILE stem resolution
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/ship-pr.sh:150-162` and `skills/review-and-fix/scripts/review-implement-step5-loop.sh:76-84` duplicate STDERR_TAIL_PATH / CODER_LOG_FILE stem resolution. Two copies must stay in sync when the KV contract changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Optional shared `resolve_stderr_tail_stem_from_kv_output` in `lib-failed-agent-stderr-tail.sh`.

### FINDING_3: ship-pr re-parses tail KVs in empty-LINT_FIX_STATUS branch
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/ship-pr.sh:150-162`: `run_lint_fix_loop_capture` re-parses tail KVs in the empty-`LINT_FIX_STATUS` branch. Extra awk blocks duplicate `_surface_lint_fix_stderr_tail` logic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Route through `_surface_lint_fix_stderr_tail` only or factor one parse helper.

### FINDING_4: plan-review collector `_collect_rc` captured but unused
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-flow-output.txt
- **Severity**: important
- **Concern**: `skills/design/scripts/plan-review-loop.sh:757-766`: `set +e` / `_collect_rc=$?` / `set -e` around the collect `$(…)` substitution allows stderr to tee to FD 2/4 while capturing stdout when `collect-agent-results.sh` exits non-zero, but `_collect_rc` is never read. On collector crash or exit 1 with empty stdout, the loop may continue with empty `_collect_out` instead of failing closed (e.g. `panel-failed`); downstream may treat that as vacuous collect / `degraded-empty-collector` while FD-2 tail may still print. The dead assignment is noisy; the behavioral gap is fail-open on hard collector failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove `_collect_rc` or wire it into collector failure handling.
  - From cursor-specialist-correctness-output.txt: Branch on `_collect_rc` or treat empty parse as collector failure consistent with panel-failed paths.
  - From cursor-specialist-testing-output.txt: Add empty-stdout failing collector stub; assert loop status/counts and use `_collect_rc` if required.
  - From cursor-specialist-edge-cases-output.txt: After capture, fail closed when `_collect_rc != 0` and `_collect_out` is empty/unparseable (`panel-failed`), or restore abort semantics without losing tee-to-FD-2.
  - From dyn-bash-flow-output.txt: After capture, branch on `_collect_rc` (e.g. treat non-zero with no parseable records as collect failure / `panel-failed`, while still allowing non-zero when stdout contains failure records or when `-s "$_collect_err"` shows actionable stderr—the harness case at `skills/design/scripts/test-plan-review-loop.sh:2892-2912` emits stdout then `exit 1`).

### FINDING_5: manifest-bailed path writes tail without existing-file guard
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `scripts/launch-cursor-implement.sh:354-361`: manifest `bailed` path writes tail without checking for an existing `${TRANSCRIPT_PATH}.stderr-tail`. `LAUNCHER_EXIT=0` with bailed manifest could overwrite a tail from `run-external-agent`. Should mirror step2 guard: only write when `! -s ${TRANSCRIPT_PATH}.stderr-tail`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Only write when `! -s ${TRANSCRIPT_PATH}.stderr-tail`.

### FINDING_6: Missing harness for sidecar clobbering diag-based tail
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `skills/implement/scripts/test-cursor-implementer.sh:864-909`: agent-failure test does not cover non-empty sidecar clobbering diag-based tail. Regression could pass even if launcher overwrites good diag tail with sidecar-only content.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add stub case: probe only in `.diag`, decoy lines in `SIDECAR_LOG`; assert tail contains probe.

### FINDING_7: plan-review stderr-tail test does not cover quiet / FD-4 path
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `skills/design/scripts/test-plan-review-loop.sh:610-620,2116-2130`: plan-review stderr-tail test always disables quiet via `run_loop`. Quiet `/design` runs tee collector stderr to FD 4; harness only asserts FD 2, so a regression on the FD-4 tee path would not fail CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a quiet-mode case (`larch_quiet_init`, no `LARCH_QUIET_DISABLE`) asserting the marker on the FD-4 capture path.

### FINDING_8: step2 dispatcher stderr-tail tests are cursor-only
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-fixture-isolation-output.txt
- **Severity**: latent
- **Concern**: `skills/implement/scripts/test-step2-dispatch.sh:1675-1773` (tests 22–23): step2 consumer stderr-tail coverage is cursor-only. Codex-implement failures could regress in `step2-implement.sh` while cursor tests stay green; codex producer work in `test-codex-implementer.sh` is not mirrored at the dispatcher choke point (`emit_bailed` / manifest-bailed at `266-277,1080-1087`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add codex stub cases mirroring tests 22/23 for dispatcher stderr surfacing.
  - From dyn-fixture-isolation-output.txt: Add a codex stub failure case (runtime + optional manifest-bailed) that captures dispatcher stderr and asserts the probe token, matching the cursor tests.

### FINDING_9: lint-fix-loop case 10 does not assert `run_cursor` return code
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-lint-fix-loop.sh:987-1015`: case 10 does not assert `run_cursor` return code. Plan asked to guard false-success return semantics; integration status alone may not catch a reverted `return "$cursor_rc"`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Invoke `run_cursor` directly in a fixture and assert non-zero exit before dual-failure assertions.

### FINDING_10: step5 spaces-in-path parse test omits emit
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `skills/review-and-fix/scripts/test-review-and-fix.sh:2399-2412`: spaces-in-path `STDERR_TAIL_PATH` parse test omits emit. Stems with spaces could parse correctly but fail at emit time in production Step 5.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Call `step5_surface_lint_stderr_tail` after parse and assert probe on stderr capture.

### FINDING_11: codex model-args tail test is existence-only
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `skills/implement/scripts/test-codex-implementer.sh:3205-3224`: model-args tail test is existence-only. Weaker than agent-failure cases; redaction/bounds regression on early-exit path could slip through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Assert known stderr substring plus redaction tokens in `${TRANSCRIPT}.stderr-tail`.

### FINDING_12: step2 test numbering / comments mismatch
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `skills/implement/scripts/test-step2-dispatch.sh:1675-1725`: test numbering/comments mismatch actual setup. Maintainer confusion only; no direct CI breakage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Renumber 22 before 23 and fix comments to describe stub stderr vs pre-written files.

### FINDING_13: Broader chat surfacing of partially redacted stderr tails
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `scripts/ship-pr.sh:116-129`: broader chat surfacing of stderr tails extends partially redacted tool output into orchestrator context. A failed CI/lint-fix/implement run could place hostnames, opaque tokens, or instruction-like stderr into Claude’s `/implement` session despite redaction. Tails should be treated as untrusted diagnostics in skills; sensitive runs may need `LARCH_FAILED_AGENT_STDERR_TAIL_LINES=0` documented.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Treat tails as untrusted diagnostics in skills; document `LARCH_FAILED_AGENT_STDERR_TAIL_LINES=0` for sensitive runs.

### FINDING_14: emit path trusts on-disk `.stderr-tail` without re-redacting
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `scripts/lib-failed-agent-stderr-tail.sh:189-199`: emit path trusts on-disk `.stderr-tail` without re-redacting. A writer that can create `${stem}.stderr-tail` under the session tmpdir could bypass write-time redaction before `emit_failed_agent_stderr_tail_larch_err`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Re-render at emit or validate tail provenance before `emit_failed_agent_stderr_tail_larch_err`.

### FINDING_15: lint-fix `STDERR_TAIL_PATH` stem vs on-disk tail mismatch
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `scripts/lint-fix-loop.sh` stem handling is inconsistent: `_lint_fix_set_stderr_tail_stem` (26-35, 425-430, 893-902) can record `STDERR_TAIL_PATH` when no `${stem}.stderr-tail` exists (dispatch-failed / empty wrapper), so `ship-pr` / step5 emit is a no-op while operators see `main-agent-required` without chat tail; conversely, requiring a non-empty `.stderr-tail` before recording the stem can omit `STDERR_TAIL_PATH` when agent rc is non-zero but the tail file is empty after `write_failed_agent_stderr_tail`. Operators need a single contract: emit stem only when surfacing can succeed, or set stem on non-zero agent rc after write regardless of file size with caller non-empty guards.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Only emit `STDERR_TAIL_PATH` when `-s "${stem}.stderr-tail"`; remove or narrow the empty-stem fallback.
  - From cursor-specialist-plan-fidelity-output.txt: Set stem on non-zero agent rc after `write_failed_agent_stderr_tail` regardless of file size; keep caller non-empty guards.

### FINDING_16: empty failure source can delete existing `.stderr-tail` on auth retry
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `scripts/launch-cursor-implement.sh:325-333`: final `write_failed_agent_stderr_tail` on empty `_FAILURE_OUTPUT` can delete an existing `.stderr-tail` (lib removes prior tail when rendering fails). Auth-retry loop: last attempt may have empty sidecar/diag after clears; step2/ship-pr chat surfacing is silent despite earlier actionable stderr. Same pattern may apply on codex-implement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Skip write when source is empty and `.stderr-tail` already exists; or retain last good tail across retries.

### FINDING_17: Step 3/6 lint-fix callers do not surface tails in caller scope
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `skills/implement/SKILL.md` (Step 3/6 lint-fix): steps still call `lint-fix-loop.sh` directly; only `ship-pr` and step5 loop surface tails in caller scope. Prompt-side lint-fix after relevant-checks failure: `STDERR_TAIL_PATH` on stdout is ignored; acceptance “end-to-end to chat” is false for those sites.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add caller-scope surfacing helper or SKILL instructions to parse `STDERR_TAIL_PATH` and emit via lib.

### FINDING_18: Misleading comment on `.stderr-tail` preservation across auth retry
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `scripts/launch-cursor-implement.sh:316-318`: comment claims `.stderr-tail` is preserved across auth retry; `run-external-agent` clears it each attempt. Future maintainer may skip needed tail-preservation logic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Reword comment to match `run-external-agent` startup `rm` behavior.

### FINDING_19: ship-pr first-fixer-non-health may omit tail when launcher failed
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `scripts/ship-pr.sh:2324-2328`: first-fixer-non-health (vendor exit 0, no commits) surfaces stderr tail only if a pre-existing `.stderr-tail` file is present. Agent failure with `LAUNCHER_EXIT!=0` but no `.stderr-tail` artifact can bail via first-fixer-non-health without any chat-surfaced tail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Surface from the winning-tier stem when `launcher_exit!=0` or failure capture has diagnostics, not only when `-s tier.stderr-tail`.

### FINDING_20: lint-fix uses `cursor.log` as stderr tail fallback under capture-stdout
- **Reviewer(s)**: dyn-tail-redaction-output.txt
- **Severity**: latent
- **Concern**: `scripts/lint-fix-loop.sh:302-308`: on `run_cursor` failure, if `${run_dir}/cursor.log.stderr-tail` is missing, fallback calls `write_failed_agent_stderr_tail "$run_dir/cursor.log" "$run_dir/cursor.log"`. Under `--capture-stdout`, `cursor.log` is agent stdout / last-message transcript, not stderr; when `.diag` is empty this mislabels agent output as failure stderr and pushes it through chat surfacing (`STDERR_TAIL_PATH` → `ship-pr` / Step 5). Redaction limits bytes/lines but not semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-tail-redaction-output.txt: Restrict fallback sources to `${run_dir}/cursor.log.diag`, then `cursor.preflight.log` / wrapper logs that are actually stderr; never use `$run_dir/cursor.log` as a tail source in `--capture-stdout` mode. If no stderr source exists, omit the write and leave `STDERR_TAIL_PATH` unset.

### FINDING_21: test-ship-pr does not exercise real CI launcher producers
- **Reviewer(s)**: dyn-fixture-isolation-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-ship-pr.sh:5975-6525`: new #3227 cases exercise `_surface_ci_stderr_tail` and `run_lint_fix_loop_capture` only when stub launchers or stub `lint-fix-loop.sh` pre-create `${stem}.stderr-tail` (or print `STDERR_TAIL_PATH=`). They never invoke real `launch-codex-ci.sh` / `launch-cursor-ci.sh` producer paths, so a regression that stops writing `${OUTPUT}.stderr-tail` in CI launchers would not fail these tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-fixture-isolation-output.txt: Add at least one hermetic case that runs copied real CI launcher scripts (with a PATH-stubbed agent) through the fix-loop/recovery choke point and asserts both producer write and caller-scope emit, mirroring `test-codex-implementer.sh` for the implement lane.

### FINDING_22: step5 harness does not drive terminal lint-fix loop arms
- **Reviewer(s)**: dyn-fixture-isolation-output.txt
- **Severity**: latent
- **Concern**: `skills/review-and-fix/scripts/test-review-and-fix.sh:2355-2424`: new step5 parser tests call `step5_surface_lint_stderr_tail` in isolation with pre-seeded `${stem}.stderr-tail` files. They do not drive `run_implement_loop` through a terminal lint-fix arm in `review-implement-step5-loop.sh:276-324`, so removing those call sites would not fail the harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-fixture-isolation-output.txt: Add a minimal step5-loop fixture (stubbed `lint-fix-loop.sh` capture + terminal `case` path) that asserts the tail marker reaches orchestrator-visible stderr immediately before `step5_emit_final_envelope` / `exit 2`.

### FINDING_23: implement harness “bounds” cases duplicate lib tests
- **Reviewer(s)**: dyn-fixture-isolation-output.txt
- **Severity**: latent
- **Concern**: `skills/implement/scripts/test-codex-implementer.sh:3176-3203` and `skills/implement/scripts/test-cursor-implementer.sh:3351-3378`: “stderr-tail-bounds” cases source `lib-failed-agent-stderr-tail.sh` and call `write_failed_agent_stderr_tail` directly, duplicating `test-lib-failed-agent-stderr-tail` rather than asserting caps/redaction on stderr produced by launcher failure paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-fixture-isolation-output.txt: Drop the direct-lib bounds duplicate or replace it with a launcher-failure assertion that `${TRANSCRIPT}.stderr-tail` respects `LARCH_FAILED_AGENT_STDERR_TAIL_LINES` and the byte cap after a stub emits >30 lines to `$SIDECAR_LOG`.

### FINDING_24: `LARCH_CURSOR_MODEL` leaks across lint-fix-loop cases
- **Reviewer(s)**: dyn-fixture-isolation-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-lint-fix-loop.sh:997-1027`: cases 10–11 use bare `export LARCH_CURSOR_MODEL=stub-cursor-model` at harness scope without `unset` after the case, leaking state into later cases if the file grows or cases are reordered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-fixture-isolation-output.txt: Scope the export to the `run_case` invocation (inline env prefix, as done for auth test vars) or `unset LARCH_CURSOR_MODEL` immediately after case 11.

### OOS_1: [OUT_OF_SCOPE] CHANGELOG / plugin.json release alignment
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `CHANGELOG.md`, `.claude-plugin/plugin.json`: #3227 in Unreleased while 47.0.13 documents #3229 cleanup. Release notes may not match the version bump on merge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Align version section with the merged feature set when cutting release.

### OOS_2: [OUT_OF_SCOPE] #3229 cleanup harness on same branch
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `skills/cleanup/scripts/test-cleanup.sh`: #3229 cleanup harness changes on same branch. Unrelated retention/find-failure edits increase shard runtime and review noise for #3227-only reviewers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Treat as separate review scope or split PR if policy requires.

### OOS_3: [OUT_OF_SCOPE] `LARCH_FAILED_AGENT_STDERR_TAIL_LINES=0` not re-tested on new consumers
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-lib-failed-agent-stderr-tail.sh`: disable knob not re-tested on new consumers. `LARCH_FAILED_AGENT_STDERR_TAIL_LINES=0` might still noop correctly via lib, but lane-specific wiring is unverified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Optional: one consumer smoke per lane with `lines=0` asserting no chat fence.

### OOS_4: [OUT_OF_SCOPE] cleanup cache enumeration fail-open (#3229)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `skills/cleanup/scripts/cleanup.sh:21-31`: cache enumeration `find` failure is fail-open (#3229). Stale session dirs may retain ephemeral argv/sidecars longer than retention policy implies.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Fail closed or warn+abort enumeration pass; separate from #3227.

### OOS_5: [OUT_OF_SCOPE] Pre-existing `LINT_FIX_STATUS` awk space truncation
- **Reviewer(s)**: dyn-bash-flow-output.txt
- **Severity**: nit
- **Concern**: `scripts/ship-pr.sh:151` still parses `LINT_FIX_STATUS` with awk `print $2`, so values containing spaces would truncate; new `STDERR_TAIL_PATH` / `CODER_LOG_FILE` paths correctly use `substr` after `=`.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_6: [OUT_OF_SCOPE] Pre-existing `ship-pr.sh` omits `set -e`
- **Reviewer(s)**: dyn-bash-flow-output.txt
- **Severity**: nit
- **Concern**: `scripts/ship-pr.sh` intentionally omits `set -e`; new `_surface_*` helpers use `|| true` consistently, so they do not change that contract.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_7: [OUT_OF_SCOPE] Unrelated commits on branch (#3229, version, larch-logs)
- **Reviewer(s)**: dyn-bash-flow-output.txt
- **Severity**: nit
- **Concern**: Commits on this branch include unrelated cleanup/docs (`#3229`, version bump, larch-logs); stderr-tail findings above are limited to #3227 surfacing changes.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_8: [OUT_OF_SCOPE] Step 5 quiet / FD routing if review-and-fix stderr redirected
- **Reviewer(s)**: dyn-fd-routing-output.txt
- **Severity**: latent
- **Concern**: `skills/review-and-fix/scripts/review-and-fix.sh:7-14`: Step 5 lint stderr surfacing uses `emit_failed_agent_stderr_tail_larch_err` with `LARCH_QUIET_DISABLE=1` in parent loop (real FD 2). Not introduced by #3227 wiring; future wrapper redirecting review-and-fix stderr to a file would swallow Step 5 tails unless surfacing moves to a caller with unredirected FD 4.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_9: [OUT_OF_SCOPE] Auth-retry may leave prior attempt’s tail (forensics vs stale noise)
- **Reviewer(s)**: dyn-fd-routing-output.txt
- **Severity**: nit
- **Concern**: `scripts/launch-cursor-implement.sh:314-318`: auth-retry clears sidecar/diag but may preserve `.stderr-tail`; later attempt failing with empty diag can leave prior attempt’s tail for step2. May be desirable forensics or stale noise; not a new FD-routing defect from this branch.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_10: [OUT_OF_SCOPE] plan-review collector tee vs production redaction location
- **Reviewer(s)**: dyn-tail-redaction-output.txt
- **Severity**: nit
- **Concern**: `skills/design/scripts/plan-review-loop.sh:758-763` still tees collector raw stderr to FD 2/4; production redaction for panel failures lives in `collect-agent-results.sh` §3.8. Branch regression test documents existing unredacted stub stderr on FD 2 rather than introducing a new emit path.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_11: [OUT_OF_SCOPE] `emit_kv SIDECAR_LOG=` still exposes full unredacted sidecar path
- **Reviewer(s)**: dyn-tail-redaction-output.txt
- **Severity**: latent
- **Concern**: `emit_kv SIDECAR_LOG=…` on implement failure paths (unchanged contract) still exposes a filesystem path to the full, unredacted sidecar; branch adds redacted `.stderr-tail` surfacing but does not narrow that KV surface.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_12: [OUT_OF_SCOPE] Positive note: producer/consumer wiring and redaction harness
- **Reviewer(s)**: dyn-tail-redaction-output.txt
- **Severity**: nit
- **Concern**: Producer/consumer wiring otherwise routes chat emission through `emit_failed_agent_stderr_tail_larch_err` on `${stem}.stderr-tail` artifacts, honors empty-stem guards in `ship-pr` and Step 5, and adds harness checks that synthetic `sk-ant-*` tokens are redacted in codex/cursor implement tails.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_13: [OUT_OF_SCOPE] Optional `_collect_rc` wiring (dyn-cleanup duplicate)
- **Reviewer(s)**: dyn-cleanup-retention-output.txt
- **Severity**: latent
- **Concern**: `skills/design/scripts/plan-review-loop.sh:757-766`: `set +e` / `_collect_rc=$?` allow collector stderr tee on non-zero exit; `_collect_rc` never consulted afterward; behavior still depends on parsed stdout records. Consider wiring into degraded/panel-failed classification if hard collector failure should not be inferred solely from empty parse output. (Overlaps in-scope FINDING_4; listed separately as reviewer-marked OOS.)
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cleanup-retention-output.txt: Consider wiring `_collect_rc` into existing degraded/panel-failed classification if hard collector failure should not be inferred solely from empty parse output.

### OOS_14: [OUT_OF_SCOPE] cleanup cache vs `/tmp` enumeration asymmetry (intentional)
- **Reviewer(s)**: dyn-cleanup-retention-output.txt
- **Severity**: nit
- **Concern**: `skills/cleanup/scripts/cleanup.sh:99-110` vs `55-61`: cache pass enumerates all top-level session entries; `/tmp` pass pre-filters with top-level `-mtime +N`. Documented in `cleanup.md` and tested; intentional, not a regression.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_15: [OUT_OF_SCOPE] cleanup nested-scan fail-safe — no additional defects
- **Reviewer(s)**: dyn-cleanup-retention-output.txt
- **Severity**: nit
- **Concern**: `skills/cleanup/scripts/cleanup.sh:26` and `test-cleanup.sh:39-57`: nested-scan fail-safe and `-maxdepth 5` boundary align with docs and tests. No additional cleanup correctness defects found in branch diff for those behaviors.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_16: [OUT_OF_SCOPE] lint-fix-loop cases 10–11 intentional split
- **Reviewer(s)**: dyn-fixture-isolation-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-lint-fix-loop.sh:268-308` case 10 pre-seeds `${output}.stderr-tail` in stub to test “do not clobber”; case 11 covers diag fallback. Matches plan producer/consumer separation; not a defect.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_17: [OUT_OF_SCOPE] plan-review shared stub mutation ordering
- **Reviewer(s)**: dyn-fixture-isolation-output.txt
- **Severity**: nit
- **Concern**: `skills/design/scripts/test-plan-review-loop.sh:2115-2130` mutates shared `$STUB/collect-agent-results.sh` like existing helpers; end-of-file placement limits ordering risk today.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_18: [OUT_OF_SCOPE] Pre-existing harness patterns (global quiet, REPO_ROOT launchers)
- **Reviewer(s)**: dyn-fixture-isolation-output.txt
- **Severity**: nit
- **Concern**: Pre-existing harness patterns (e.g. `test-codex-implementer.sh` invoking production launchers from `REPO_ROOT`; `test-ship-pr.sh:6` global `LARCH_QUIET_DISABLE=1`) were not introduced by this branch’s stderr-tail work.
- **Suggested revisions (informational for voters; coder decides)**:

---

**Merge summary**: 55 raw slots → **24 in-scope** `FINDING_*` blocks and **18** `OOS_*` blocks. Largest merges: launcher SIDECAR/diag clobber (8 reviewers), `_collect_rc` (5), step2 codex gap (2), lint-fix stem contract (2). Highest-severity in-scope cluster: **important** on launcher tail clobber/preservation (FINDING_1, 15, 16), collector fail-open (FINDING_4), and lint-fix `STDERR_TAIL_PATH` contract (FINDING_15).
