# Review Round 1

- Mode: `diff`
- 19 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: coder-main-agent-required emitted as stall-tracked handoff
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `coder-main-agent-required` is a recoverable main-agent handoff, but `step5()` passes `stall_tracking=True` into `_emit_step5_envelope`, so `/implement` treats it as a stall instead of routing to the coder-waterfall branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Pass `stall_tracking=false` and `stall_reason=""` for both handoff statuses
  - From codex-specialist-correctness-output.txt: Emit `STALL_TRACKING=false` and empty stall reason for `coder-main-agent-required` while still recording escalation evidence.
  - From codex-specialist-testing-output.txt: Emit `STALL_TRACKING=false` and empty `STALL_REASON` for handoff statuses and pin with envelope tests.


### FINDING_10: Empty dynamic-archetype config defaults to 3 instead of 0
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: When `LARCH_DYNAMIC_ARCHETYPES_MAX` is unset, `_dynamic_archetypes()` forwards `--dynamic-archetypes 3` for implement-tmpdir sessions, changing reviewer composition and cost versus the prior empty/default behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Only forward a configured dynamic-archetype value; otherwise let review core default to 0.


### FINDING_11: Make harness targets run identical smoke pytest; deleted bash coverage not replaced
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-migration-surface-output.txt
- **Severity**: important
- **Concern**: Many absorbed Make targets (`test-review-and-fix-dispatch`, `-convergence`, `-parsers`, `-step5-starting-round`, `-step5`, `-record-timing`, `-step5-loop-timing`, `-commit-fixes`, `-check-changes`, `-write-rejected`) all run the same unfiltered `python3 -m pytest python/test_review_and_fix.py -q`, but that file has only ~8 smoke tests. CI shards still run those target names, so the migration surface reports green while retired bash contract coverage (MAV, escalation ledger, lint-cap, bulk-skip, starting-round, timing, etc.) is largely gone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Expand pytest coverage per Make target to match the plan enumerated cases
  - From cursor-specialist-testing-output.txt: Port plan-listed scenarios into pytest before merge; align Make section targets with distinct test subsets.
  - From dyn-migration-surface-output.txt: Either port the plan's pytest matrix with `-k` section filters per Make target, or collapse/rename targets and update `scripts/test-harness-shards-coverage.sh` so CI does not imply section-specific regression coverage that is not executed.


### FINDING_12: Rejected findings copied to run logs without redaction
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `write_rejected()` copies rejected findings to run logs via `shutil.copyfile` without redacting tmpdir paths or secrets. Untrusted reviewer text containing secret-shaped values or local temp paths can be persisted under `larch-logs/implement/<run>/rejected-findings.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Redact through existing tmpdir-path and secret scrubbers before writing the run-log copy.
  - From codex-specialist-testing-output.txt: Restore redact tmpdir-paths and redact secrets before persisting the copy.


### FINDING_13: MAV branch documents wrong CLI entrypoint
- **Reviewer(s)**: codex-specialist-testing-output.txt, dyn-migration-surface-output.txt
- **Severity**: important
- **Concern**: `step5-review-branches.md` tells the orchestrator to run `python/cli.py review-and-fix apply-findings --mode mav-apply`, but `apply_findings()` only accepts `--findings-file`, `--review-tmpdir`, and `--session-env-path`. MAV behavior lives on `step5 --mode mav-apply`. Following the doc will argparse-fail or skip MAV semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Use `review-and-fix step5 --mode mav-apply` with the required context flags and add a prompt invariant test.
  - From dyn-migration-surface-output.txt: Replace the dispatch line with `bash "$IMPLEMENT_TMPDIR/larch-run.sh" python/cli.py review-and-fix step5 --implement-tmpdir "$IMPLEMENT_TMPDIR" --mode mav-apply --round-num "$FINAL_ROUND_NUM" --findings-file "$ACCEPTED_FINDINGS_FILE"` plus the same session/plan/feature/run-id/codex/cursor flags `step5` already forwards; align `skills/review/SKILL.md:50` the same way.


### FINDING_14: Pre-coder snapshots not relocated outside Codex writable grant
- **Reviewer(s)**: dyn-step5-contract-output.txt
- **Severity**: important
- **Concern**: Pre-coder snapshots are written under `round_dir / "pre-coder-snapshot"` instead of relocated `pre_coder_snapshot_dir()`. MAV apply and normal coder rounds write `pre-coder-head.txt` inside the round directory, breaking the relocated-head contract that bulk-skip/substantiality logic and MAV handoff gates depend on (`SECURITY.md`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-step5-contract-output.txt: Implement `pre_coder_snapshot_dir(round_dir)` in Python (including TMPDIR relocation, stale-file clearing, and `0444` hardening), use it in both `_run_round()` and `--mode mav-apply`, and keep `post-coder-head.txt` under `round_dir` only.


### FINDING_15: Unrecognized round statuses misclassified as success
- **Reviewer(s)**: dyn-step5-contract-output.txt
- **Severity**: important
- **Concern**: `_run_round()` assigns `status = core_status` for anything outside its explicit map, and the loop's default branch emits `STEP5_REVIEW_STATUS=complete` for statuses not in the small stall/handoff sets. A novel or mistyped `REVIEW_CORE_STATUS` would complete Step 5 instead of stalling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-step5-contract-output.txt: Mirror the shell `*)` branch: emit `STEP5_REVIEW_STATUS=stall`, `STALL_TRACKING=true`, `STALL_REASON=round-failed-<status>`, flush review batches best-effort, and return non-zero.


### FINDING_16: Final-round substantial fix-applied reported as complete instead of cap-hit
- **Reviewer(s)**: dyn-step5-contract-output.txt
- **Severity**: important
- **Concern**: On the final round, when `status == "fix-applied"`, Python falls through to `STEP5_REVIEW_STATUS=complete` because the `fix-applied` continue guard requires `round_num < round_cap`. The retired loop still ran checks/lint-fix/substantiality and emitted `cap-hit` when the round was substantial at the cap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-step5-contract-output.txt: After porting the post-round gates, keep the shell rule: on the final round, substantial `fix-applied` must emit `cap-hit`, not `complete`.


### FINDING_17: Escalation evidence stderr sidecar never populated
- **Reviewer(s)**: dyn-step5-contract-output.txt
- **Severity**: important
- **Concern**: `_record_escalation_if_needed()` passes `round-{N}/review-and-fix.stderr` to `stall-recovery-report.sh record-escalation`, but nothing in `step5()` or `_run_round()` writes that file. Fail-open `STEP5_REVIEW_LEDGER_FAILURE_DETAIL_LOG` emission will usually be empty, weakening stall-recovery evidence on `coder-main-agent-required`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-step5-contract-output.txt: Capture Step 5 stderr to the sidecar (or reuse a single implement-tmpdir capture file per invocation) before calling `record-escalation`, matching the old launcher's `--failure-detail-log` contract.


### FINDING_18: launcher-argv-test-coverage rule points at nonexistent harness
- **Reviewer(s)**: dyn-migration-surface-output.txt
- **Severity**: important
- **Concern**: `.claude/rules/launcher-argv-test-coverage.md` `paths:` frontmatter and harness map point at `scripts/test-review-and-fix step5`, which is not a repo file. Contributors changing Step 5 argv will look for a harness that does not exist after shell launcher deletion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-migration-surface-output.txt: Retarget the rule to `python/review_and_fix.py` / `python/test_review_and_fix.py` and name the real Make targets (`test-review-and-fix-step5`, `test-review-and-fix-step5-starting-round`, etc.) instead of the fictitious `scripts/test-review-and-fix step5` path.


### FINDING_19: Coder prompt uses weaker submodule prohibition than canonical contract
- **Reviewer(s)**: dyn-coder-dispatch-output.txt
- **Severity**: important
- **Concern**: `_compose_coder_prompt()` inlines a weaker submodule prohibition than `scripts/lib-submodule-prohibition.sh`. The Python text only says "Do not edit files under these submodule paths", omits "read, create, delete, move", and drops the explicit ban on touching `.git/`, `.gitmodules`, and submodule interiors.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-coder-dispatch-output.txt: Reuse the canonical prohibition text from `lib-submodule-prohibition.sh` (call the shell helper, or extract shared Python prose) so the coder prompt matches the prior "Do NOT read, edit, create, delete, move" wording and includes the `.git/` / `.gitmodules` skip rule.


### FINDING_2: Codex launcher preflight/auth failure treated as coder success
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_run_coder_codex()` treats wrapper rc 0 plus an output file as success even when `launch-codex-exec` wrote an auth/model preflight failure bundle. Accepted findings can be recorded as `no-changes` and Step 5 can complete without applying fixes or handing off to the main agent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Parse `LAUNCHER_EXIT` or a durable success marker and treat missing or nonzero launcher status as coder dispatch failure.
  - From codex-specialist-edge-cases-output.txt: Parse `LAUNCHER_EXIT` from stdout or the `.done` sidecar and require launcher exit 0.


### FINDING_3: Review-fix commits stage every dirty path, not coder deltas only
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `_stage_and_commit_round()` stages all dirty tracked/untracked paths via `git status --porcelain` instead of only post-snapshot coder deltas. Pre-existing dirty files (including untracked `.env` or scratch files) can be swept into automated review-fix commits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Port pre-coder tracked/untracked snapshots and stage only coder deltas; fail closed on outside-manifest residue.
  - From codex-specialist-edge-cases-output.txt: Restore pre-coder tracked and untracked snapshots and stage only post-snapshot coder deltas.
  - From codex-specialist-testing-output.txt: Port pre-coder snapshot/carryover staging and fail closed on outside-manifest dirt.


### FINDING_4: Submodule violations counted but not reverted
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, dyn-coder-dispatch-output.txt
- **Severity**: important
- **Concern**: After external coder dispatch, `_submodule_dirty_count()` only counts dirty submodule paths; `post_dispatch_submodule_revert` was not ported. Forbidden submodule edits remain in the working tree and can be picked up by later `commit_fixes --stage-all` (`git add -A`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Port `post_dispatch_submodule_revert` to checkout or remove submodule paths before returning the violation.
  - From codex-specialist-edge-cases-output.txt: Port the post-dispatch revert logic for tracked and untracked submodule paths.
  - From dyn-coder-dispatch-output.txt: Port `post_dispatch_submodule_revert` into Python (revert tracked submodule paths, remove untracked paths under submodules, log to `round_dir/submodule-revert.log`), run it before the violation check, and keep `SUBMODULE_REVERT_COUNT` as paths actually reverted.


### FINDING_5: Step 5 loop omits post-round checks, lint-fix, bulk-skip, and substantiality gates
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-step5-contract-output.txt
- **Severity**: important
- **Concern**: The Python `step5()` loop is a thin wrapper around `_run_round()` and does not port the absorbed `review-implement-step5-loop.sh` post-round contract. After `fix-applied`, the retired shell ran `run-relevant-checks-captured.sh` (`step5-review-fixes`), the `lint-fix-loop.sh` repair loop (including lint-fix-attempt-cap re-verify from #3592), bulk-skip-ratio gating, and the substantiality heuristic. The Python loop only continues on `fix-applied`/`prune-skipped` and otherwise emits a terminal envelope, so checks can pass with a broken tree, lint failures never stall Step 5, and multi-round review behavior diverges from `/implement` Step 5 and `step5-review-branches.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Port the run-relevant-checks-captured and lint-fix-loop state machine with re-verify and terminal stall reasons.
  - From cursor-specialist-edge-cases-output.txt: Port the deleted loop tail into `step5()` loop mode with pytest parity for stall and continue branches
  - From codex-specialist-testing-output.txt: Port the captured relevant-checks and lint-fix state machine with tests for pass, fail, repaired, and cap paths.
  - From dyn-step5-contract-output.txt: Port the full per-round tail from the deleted loop into `step5()` (or a dedicated helper), preserving the same terminal `STEP5_REVIEW_STATUS` / `STALL_REASON` tokens (`relevant-checks-*`, `lint-fix-*`, `bulk-skip-ratio-cap`, `cap-hit`) and exit codes before returning the final envelope.


### FINDING_6: Step 5 resume semantics and mav-resume-past-cap missing
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt, dyn-step5-contract-output.txt
- **Severity**: important
- **Concern**: The Python loop parses `--starting-round` and enters `range(starting_round, round_cap + 1)` with no prior-round env probe. `--starting-round 6` after round 5 emits `cap-hit` instead of `mav-resume-past-cap`; `--starting-round 3` without round 2 can start anyway. `step-5-resume.sh` can re-run review past cap or start from a missing prior round without the documented envelope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Validate prior round env before looping and preserve the old resume-past-cap envelope.
  - From codex-specialist-testing-output.txt: Detect `starting_round > round_cap` with prior artifact and emit `mav-resume-past-cap`.
  - From dyn-step5-contract-output.txt: Port `step5_probe_prior_round_env()`, the entry `mav-resume-past-cap` gate, and the in-loop `round_num > effective_round_cap` handling, emitting the same terminal KV bundle and return codes as the shell loop.


### FINDING_7: OOS and skipped-finding accumulation not ported
- **Reviewer(s)**: codex-specialist-correctness-output.txt, dyn-coder-dispatch-output.txt
- **Severity**: important
- **Concern**: Accepted OOS findings and coder `SKIPPED:` lines are not accumulated. The deleted shell block parsed `SKIPPED: FINDING_N` from `coder-output.log`, classified blocks with `python/cli.py voting is-security-block`, wrote security skips to `skipped-security-findings.md`, and routed non-security skips into accumulated OOS. `skipped_finding_count` is never set (always 0).
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Port accepted OOS accumulation, skipped parsing, security classification, and mirroring.
  - From dyn-coder-dispatch-output.txt: Restore the post-coder skip loop in `_run_round` (or a helper): parse `SKIPPED: FINDING_N` from `coder-output.log`, call `voting.is_security_block` per block, append security skips only to the local `skipped-security-findings.md` audit file, normalize non-security skips into accumulated OOS, fail closed on classifier errors, and add pytest coverage for security vs non-security skip routing.


### FINDING_8: Per-round run-log and review-batch flushes incomplete
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt, dyn-step5-contract-output.txt
- **Severity**: important
- **Concern**: `_run_round()` only calls `write-implement-round-meta.sh`; it does not invoke `run-log write-round` or `flush_review_batches()`. Step 5 rounds can finish without `code-review-tally`, `review-findings-full`, or `reviewer-prune-ledger` batches, breaking run-log completeness and Review Phase Detail inputs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Port `flush_round_log_after_coder` and `flush_review_batches` with best-effort terminal flushes.
  - From codex-specialist-testing-output.txt: Port `flush_review_batches` and run-log write-round after round-meta creation with ordering tests.
  - From dyn-step5-contract-output.txt: Port `flush_review_batches()` and the `run-log write-round` ordering (`round-meta.json` first, then flush) from the deleted shell, including best-effort calls on stall, cap-hit, MAV, and handoff exits.


### FINDING_9: Degraded-panel retry and prune-ledger clearing absent
- **Reviewer(s)**: codex-specialist-correctness-output.txt, dyn-step5-contract-output.txt
- **Severity**: important
- **Concern**: The old round body detected a degraded banner, retried review once, cleared unsettled reviewer-prune rows on unsettled retry outcomes, and fed `DEGRADED_ROUND` into convergence logic. Python only sets `degraded_round` from banner text in the persisted env and never re-invokes review core for a fresh panel.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Port degraded retry state plus `reviewer_prune_status_records` and `clear_reviewer_prune_round`.
  - From dyn-step5-contract-output.txt: Port `degraded_retry_flag` / `degraded_retry_done`, the one-retry review-core redispatch, `clear_reviewer_prune_round()` on unsettled retry statuses, and convergence's non-degraded round lookback.


