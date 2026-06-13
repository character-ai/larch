### FINDING_1: Step 5 progress/done lifecycle and timing marks omitted from Python port
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: Folding `scripts/run-step5-review.sh` into the `review-and-fix step5` verb without porting loop-mode progress/done clearing on entry, EXIT-trap write on every loop exit, resume timing marks, and Step 5 timing integration breaks the launcher progress contract. `python/progress_report.py` uses the done marker to stop rendering Step 5 as in progress; dropping it regresses live progress after shell deletion (including the #3878 Monitor self-exit contract).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add an explicit step5 parity item to preserve the loop-mode progress/done lifecycle and Step 5 timing mark in the Python driver, with pytest coverage for done-marker fallthrough.
  - From Cursor-Innovation: Fold those wrapper behaviors explicitly into review-and-fix step5 (or a thin launcher helper) and add pytest cases mirroring scripts/test-run-step5-review.sh ledger/progress assertions
  - From Cursor-Pragmatic: Add explicit step5 requirements for loop-mode progress/done marker resolve_run_id stall-recovery-report on coder-main-agent-required and STEP5_REVIEW_LEDGER KVs on main-agent-vote-required
  - From Cursor-Requirements: In the step5 verb section explicitly port loop-mode progress/done clear-on-entry and write-on-exit (any exit path) from scripts/run-step5-review.sh:160-164 and :255-261


### FINDING_2: Step 5 escalation ledger and stall-recovery contract omitted
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The planned step5 fold omits `run-step5-review.sh` tail behaviors: `STEP5_REVIEW_LEDGER_*` emission on `main-agent-vote-required`, `stall-recovery-report.sh` record-escalation on `coder-main-agent-required`, and aligned dispatcher/site metadata. Deleting the launcher without porting these breaks stall-recovery, duplicate-recording rules, escalation evidence, and downstream stall classification documented in `skills/implement/SKILL.md` and `skills/implement/references/stall-recovery.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an explicit step5 requirement: preserve main-agent-vote-required ledger-ready KVs, invoke stall-recovery-report.sh (or equivalent) on coder-main-agent-required, and keep dispatcher/site metadata aligned with skills/implement/references/stall-recovery.md
  - From Cursor-Innovation: Fold those wrapper behaviors explicitly into review-and-fix step5 (or a thin launcher helper) and add pytest cases mirroring scripts/test-run-step5-review.sh ledger/progress assertions
  - From Cursor-Pragmatic: Add explicit step5 requirements for loop-mode progress/done marker resolve_run_id stall-recovery-report on coder-main-agent-required and STEP5_REVIEW_LEDGER KVs on main-agent-vote-required
  - From Cursor-Requirements: When folding run-step5-review.sh into step5 document and port the post-review status branches at scripts/run-step5-review.sh:285-330 unchanged


### FINDING_3: Stale-reference sweep omits live tracked files still citing deleted shell paths
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Requirements
- **Severity**: important
- **Concern**: The plan adds deleted paths to `python/migrated-scripts.tsv` and runs `lint-retired-scripts`, but omits several tracked files that still contain those exact paths (e.g. `AGENTS.md`, `SECURITY.md`, `agent-lint.toml`, `skills/review/SKILL.md`, `skills/implement/references/step5-review-branches.md`, launcher docs/harnesses). After deletion, `make lint` can fail on stale references, and security/skill docs can still point at removed helpers outside the documented trust boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add these files to the update list. Replace old shell references with the Python CLI/module/test surfaces, update codex-exec auth lint coverage for python/review_and_fix.py, and run lint-retired-scripts plus lint-codex-exec-auth.
  - From Codex-Innovation: Add an explicit repo-wide stale-reference pass before deleting/manifesting the shell paths, and include missing live surfaces such as AGENTS.md, SECURITY.md, agent-lint.toml, skills/review/SKILL.md, skills/implement/references/step5-review-branches.md, scripts/lib-external-launcher-common.md, scripts/test-lib-external-launcher-common.sh, scripts/write-implement-round-meta.md, python/lint_codex_exec_auth.py, and remaining rg hits outside deleted files
  - From Codex-Requirements: Add SECURITY.md to the plan and update only the affected review-and-fix path references to the Python module or CLI while preserving the existing trust-boundary semantics


### FINDING_4: Codex exec auth lint not planned for new Python dispatch site
- **Reviewer(s)**: Codex-Arch, Codex-Innovation
- **Severity**: important
- **Concern**: The Codex dispatch migration in `python/review_and_fix.py` lacks a lint/auth plan for the new raw Codex exec site. `python/lint_codex_exec_auth.py` currently allowlists only `python/agents.py`; a direct `["codex","exec"]` port will fail `make lint` or bypass the documented auth inventory.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add these files to the update list. Replace old shell references with the Python CLI/module/test surfaces, update codex-exec auth lint coverage for python/review_and_fix.py, and run lint-retired-scripts plus lint-codex-exec-auth.
  - From Codex-Innovation: Route Codex through an existing importable launch-codex-exec/auth helper, or add python/review_and_fix.py to the Python allowlist with matching tests and inventory docs in the same change


### FINDING_5: Planned Step 5 fence bypasses `larch-run.sh` rehydration contract
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: Replacing the Step 5 fence with a direct `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py"` call bypasses the post-Step-0 `larch-run.sh` contract that recovers `CLAUDE_PLUGIN_ROOT` on resume. This can fail when the prompt env is missing and violates the fence-shape harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Use bash "$IMPLEMENT_TMPDIR/larch-run.sh" python/cli.py review-and-fix step5 --implement-tmpdir "$IMPLEMENT_TMPDIR" --mode loop --starting-round 1 for prompt-side /implement fences; keep direct python3 calls inside wrappers that already rehydrate CLAUDE_PLUGIN_ROOT


### FINDING_6: MAV branch still dispatches deleted `review-and-fix.sh` shell path
- **Reviewer(s)**: Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: `skills/implement/references/step5-review-branches.md` still tells the orchestrator to parse status from `run-step5-review.sh` and dispatch `skills/review-and-fix/scripts/review-and-fix.sh --mode mav-apply`. After the plan deletes both shell entrypoints, the `main-agent-vote-required` handoff path breaks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Update this reference to invoke python/cli.py review-and-fix step5 --mode mav-apply with the same context flags
  - From Cursor-Requirements: Add ### UPDATED: skills/implement/references/step5-review-branches.md replacing run-step5-review.sh and review-and-fix.sh with python/cli.py review-and-fix step5 --mode mav-apply (and loop) plus the same context flags the launcher forwarded
  - From Codex-Requirements: Add skills/implement/references/step5-review-branches.md to the plan and update the MAV branch to call python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" review-and-fix step5 --mode mav-apply with the same accepted-findings and context args


### FINDING_7: Token-propagation harness still invokes deleted `review-and-fix.sh`
- **Reviewer(s)**: Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The plan omits `skills/implement/scripts/test-implement-review-token-propagation.sh`, which `make lint` still runs via the Makefile. After `review-and-fix.sh` is deleted, the target fails and the nested review token-propagation contract is no longer verified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Retarget the harness to python/cli.py review-and-fix step5 or fold the same case into python/test_review_and_fix.py while preserving the Make target name
  - From Codex-Requirements: Retarget this harness to the new review-and-fix step5 CLI or fold equivalent assertions into python/test_review_and_fix.py, and update the Make target accordingly




### FINDING_2: Pre-scout eligibility gate omitted from port plan
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan omits the pre-scout eligibility gate that currently wraps `--pre-scouted-manifest` forwarding. Without requiring both `step2-external-scout-eligible.txt` and `SCOUT_CODER_STATUS=ok`, step5 can pass `--pre-scouted-manifest` on ineligible runs and change review-core dynamic slot behavior versus today.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add an explicit step5 parity rule: forward --pre-scouted-manifest only when the eligibility marker exists and SCOUT_CODER_STATUS is ok; omit the flag for mav-apply as today


### FINDING_3: Per-round round-meta and log flush omitted from port plan
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan omits `write-implement-round-meta.sh` and `flush_round_log_after_coder` per-round log flush. After each review round the shell driver writes `round-meta.json` then `run-log write-round`; `render-review-phase-detail.sh` gates the Review Phase Detail table on `round-meta.json` (#4038) and committed run logs expect per-round artifact copies.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Port the same ordering in step5/apply round completion: call write-implement-round-meta.sh (proc.run is fine) before run-log write-round; add pytest asserting round-meta.json exists when classification/tally inputs exist


### FINDING_4: Step 5 loop post-round gates not named in port contract
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: Step 5 loop post-round gates are not named in the port contract. The absorbed loop drives `STEP5_REVIEW_STATUS` via `lint-fix-attempt-cap` (with #3592 final re-verify), `bulk-skip-ratio-cap`, and non-terminal `prune-skipped` continuation. The plan only says "Step 5 loop state machine" and "convergence heuristic" without these branches. A Python loop can omit them and change stall vs continue behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add an explicit Step 5 loop parity checklist: lint-fix attempt-cap with final checks re-verify, bulk-skip-ratio gate, and `prune-skipped` increment-without-stall below cap. Pin each in `python/test_review_and_fix.py`.


### FINDING_5: `--prune-ledger` forwarding not specified in port plan
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: `--prune-ledger` forwarding to review core is not specified. Implement Step 5 passes `--prune-ledger "$IMPLEMENT_TMPDIR/reviewer-prune-ledger.tsv"` on every `review core` call. Harness `test-review-and-fix.sh` asserts this argv. The plan preserves dynamic archetypes and degraded retry but is silent on prune-ledger. Missing it breaks rounds 3-4 mechanical pruning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: When building `core_args`, always forward `--prune-ledger` from the implement tmpdir. Add a pytest argv assertion matching the harness prune-ledger check.


### FINDING_7: MAV apply replacement bypasses larch-run launcher
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: MAV apply replacement bypasses larch-run despite prompt-side resume contract. A resumed Step 5 MAV branch can run with `CLAUDE_PLUGIN_ROOT` absent, so direct `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" review-and-fix step5 --mode mav-apply` fails before applying accepted findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Use bash "$IMPLEMENT_TMPDIR/larch-run.sh" python/cli.py review-and-fix step5 --mode mav-apply ... in the prompt-side branch, or keep direct python3 only inside a rehydrating shell wrapper



### FINDING_1: In-process `review_core()` must not interleave `REVIEW_CORE_*` KVs on Step 5 stdout
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: Bash isolates `review-core` contract output by redirecting stdout to `round-N/review-core.env` and parsing KVs from that file. An in-process `review_pipeline.review_core()` path that relays legacy stdout through `logging_util.emit` on the same FD3 as Step 5 can emit premature `REVIEW_CORE_*` lines on the Step 5 stream, breaking token-aware `STEP5_REVIEW_STATUS` parsing for the `/implement` orchestrator and token-propagation tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an explicit capture contract before porting: buffer review_core contract output to round-N/review-core.env without re-emitting it on the step5 stream (subprocess capture, temporary emit sink, or a dedicated review_pipeline capture helper); pin with a test that asserts step5 stdout lacks REVIEW_CORE_STATUS while the env file contains it
  - From Cursor-Innovation: Wrap review_core invocation to capture proc/run_legacy output into review-core.env without emitting intermediate review-core KVs on step5 stdout; parse from the file like bash; only emit the loop-selected STEP5 or REVIEW_AND_FIX envelope


### FINDING_2: Absorbed Step 5 launcher omits explicit single-round mode contract
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `scripts/run-step5-review.sh` defaults to `--mode single` when `--round-num` is set without `--mode loop`, mapping to `review-and-fix --mode diff`. Harness coverage in `scripts/test-run-step5-review.sh` and several argv/pre-scout cases depend on that path, but the plan documents only `step5 --mode loop` and `--mode mav-apply`. A Python port without an equivalent contract breaks harness parity and direct single-round invocation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Harness parity and any direct single-round invocation break; pytest port of test-run-step5-review loses coverage targets Add step5 --mode single (or equivalent --round-num without loop) to the CLI contract helper list and tests mirroring current launcher argv assembly including --mode diff --round-cap 5 forwarding


### FINDING_3: Loop per-round KV suppression and `IRF_LAST_*` handoff not named in plan
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `review-implement-step5-loop.sh` sets `IRF_SUPPRESS_EMIT_KV=1` before `_implement_round_body`, reads `IRF_LAST_*` fields and `review-and-fix.env` instead of per-round stdout, and `step5_emit_final_envelope` consumes that state. Porting without an explicit suppress-and-handoff contract can emit full `REVIEW_AND_FIX_*` KV sets every round, corrupting the single `STEP5_REVIEW_STATUS` envelope and resume routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Porting without an explicit suppress-and-handoff contract emits full REVIEW_AND_FIX_* KV sets every round corrupting the single STEP5_REVIEW_STATUS envelope and resume routing Document and test the suppress emit plus structured round result handoff equivalent to IRF_SUPPRESS_EMIT_KV and IRF_LAST_* including review-and-fix.env persistence for loop iterations


### FINDING_4: Degraded-panel retry must clear unsettled reviewer-prune ledger rows
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: After a degraded in-round retry, when `reviewer_prune_status_records` returns false (for example terminal statuses like `main-agent-vote-required` or `panel-failed`), bash calls `clear_reviewer_prune_round` via zero-row `reviewer-prune.sh record`. Omitting this in a Python port leaves stale prune-ledger rows for retried rounds, which can break rounds 3–4 mechanical panel pruning and change panel shape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Omitting the clear leaves stale prune-ledger rows for retried rounds breaking rounds 3-4 mechanical panel pruning Port reviewer_prune_status_records and clear_reviewer_prune_round and add pytest coverage alongside existing degraded-panel retry tests
  - From Cursor-Pragmatic: Port reviewer_prune_status_records and clear_reviewer_prune_round (zero-row scripts/reviewer-prune.sh record) into python/review_and_fix.py and add pytest coverage for the degraded-retry plus non-settling status path
  - From Cursor-Requirements: Port `clear_reviewer_prune_round` / `reviewer_prune_status_records` behavior into `python/review_and_fix.py` Step 5 per-round logic and add a pytest case for degraded retry with a no-record terminal status


### FINDING_5: `flush_review_batches` best-effort flushes on stall/terminal paths not named in plan
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The Step 5 loop calls `flush_review_batches` (code-review-tally, review-findings-full, reviewer-prune-ledger batches) on many non-happy exits. The plan only details per-round `round-meta.json` plus `run-log write-round`, so a Python port can drop partial-run log batches on stall, cap, or MAV exits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Explicitly port `flush_review_batches` and preserve its calls from every current loop bail branch; extend pytest or retargeted harness coverage for at least one early stall path


### FINDING_6: Stale-reference / documentation cutover incomplete for retired Step 5 shell paths
- **Reviewer(s)**: Cursor-Requirements, Codex-Generic
- **Severity**: important
- **Concern**: After deleting `review-and-fix.sh` and `run-step5-review.sh`, tracked docs, rules, and harness references can still point operators and linters at removed paths, violating the feature DoD stale-reference sweep. Affected surfaces include `.claude/rules` (`gh-body-file.md`, `launcher-argv-test-coverage.md`, `external-tool-launcher-parity.md`), `scripts/lib-submodule-prohibition.md`, `scripts/run-relevant-checks-captured.md`, `docs/vendor-agent-diagnostics-audit.md`, `skills/implement/scripts/step-5-resume.md`, and related tracked hits outside archived logs and the retired-script manifest.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add UPDATED sections for those rule files: retarget Codex-auth and launcher-harness reminders to `python/review_and_fix.py` / `python/cli.py review-and-fix step5` and drop deleted shell paths from `paths:` frontmatter where applicable
  - From Codex-Generic: Add an explicit repo-wide git grep stale-reference step and update or intentionally retire every tracked hit outside archived logs and the retired-script manifest


### FINDING_8:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: security
- **Location**: python/lint_codex_exec_auth.py:20,185-187; python/agents.py:1768-1845
- **Concern**: [SCOPE-REDUCTION] Plan allows a new raw codex exec allowlist instead of requiring the existing authenticated launcher. Scenario: Adding python/review_and_fix.py to ALLOWED_PYTHON_FILES would make lint skip raw codex exec calls in the new fixer and could bypass temp CODEX_HOME, auth args, retries, sidecars, and usage capture
- **Proposed resolution**: Require review_and_fix.py to dispatch Codex through the existing agent launch-codex-exec path or an importable wrapper around it; do not add a blanket Python allowlist entry




### FINDING_1: In-process review_core KV capture unspecified
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The C2 plan calls `review_pipeline.review_core()` in-process but does not define how `REVIEW_CORE_*` contract KVs are captured into `round-N/review-core.env` and kept off the Step 5 orchestrator stdout stream. Today `review-and-fix.sh` redirects a review-core subprocess to `review-core.env` (e.g. line 1471), while `review_pipeline.run_legacy()` relays legacy stdout through `logging_util.emit()` on the shared machine-contract stream (`review_pipeline.py:32-33`). In-process calls without an explicit capture sink will interleave review-core KVs onto Step 5 stdout, breaking orchestrator parsing and loop-suppression tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an explicit capture helper (context manager around logging_util.emit/contract_stream, or a review_core_captured() wrapper) that writes all review-core KVs to review-core.env and blocks them from Step 5 stdout; document it beside the direct review_core call.
  - From Cursor-Innovation: Add a capture path before cutover: e.g. review_pipeline.run_legacy(..., emit_sink=...) or review_core_capture() writing round-N/review-core.env, with tests mirroring test_run_legacy_relays_stdout_kv monkeypatch pattern. Wire review_and_fix.step5 to use it on every review-core call.
  - From Cursor-Pragmatic: Add an explicit capture contract: wrap the review_core call with an emit sink that writes only review-core KVs to round-N/review-core.env and does not forward them to the Step 5 contract stream; add the planned regression test against this wrapper not just subprocess stdout redirection


### FINDING_2: MAV apply path contract omitted from Python port plan
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The plan names `--mode mav-apply` but does not spell out behaviors implemented today by `run_implement_mav_apply` in `review-implement-step5-loop.sh` (lines 473–503): writing `pre-coder-head.txt` under relocated `pre_coder_snapshot_dir` (not under `round_dir`), chmod 0444 on head files, skipping the full tracked snapshot, and emitting `REVIEW_AND_FIX_STATUS=mav-apply-done` (plus `CODER_STATUS`). Porting the loop without this branch breaks MAV handoff and bulk-skip/substantial gates that read relocated heads (`test-review-and-fix.sh` `mav-apply-relocated-pre-head`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add an explicit `step5 --mode mav-apply` subsection: port `run_implement_mav_apply` snapshot relocation, 0444 head files, `mav-apply-done`/`CODER_STATUS` stdout, and pytest parity for `mav-apply-relocated-pre-head`.



### FINDING_1: Step 5 ledger dispatcher token and stall-recovery allowlist must stay aligned
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Porting `run-step5-review.sh` into Python `step5` must preserve a single canonical `STEP5_REVIEW_LEDGER_DISPATCHER` value and keep `stall-recovery-report.sh` `safe_dispatcher_value` in sync. Today tests assert the literal `run-step5-review`, and `record-escalation --dispatcher run-step5-review` feeds that ledger. Replacing or deleting the bash launcher without updating the allowlist, escalation `--dispatcher`, and ledger emission together can redact valid dispatcher tokens, reject valid escalation rows, and break stall-evidence parity exercised by `test-run-step5-review.sh` and stall recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: When folding run-step5-review.sh into step5, preserve the record-escalation block and emit STEP5_REVIEW_LEDGER_DISPATCHER=run-step5-review on MAV and coder-main-agent-required fallback paths unless stall-recovery-report.sh is updated in the same change
  - From Cursor-Pragmatic: Add `skills/implement/scripts/stall-recovery-report.sh` to the cutover list; choose one dispatcher value for the Python `step5` owner; update allowlist, `STEP5_REVIEW_LEDGER_DISPATCHER`, and `record-escalation --dispatcher` together; port the ledger tests in `python/test_review_and_fix.py`


### FINDING_2: Loop suppression must not allow bare process exit before the final Step 5 envelope
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: With `IRF_SUPPRESS_EMIT_KV` active, the Step 5 loop expects `_implement_round_body` to return and the composer to emit a final `STEP5_REVIEW_STATUS` envelope via `step5_emit_final_envelope`. Bare `exit 2` paths (jq missing, findings validation, `mirror_oos_markdown` cp failure, dynamic-archetypes validation, MODE/tmpdir validation in `review-and-fix.sh`) terminate the process first, leaving `/implement` Step 5 with no parseable status. A Python `step5 --mode loop` that maps the same failures to `sys.exit(2)` repeats the contract gap seen in prior run logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Loop-mode round body still uses bare process exit on infrastructure failures while suppression is active When `IRF_SUPPRESS_EMIT_KV` is set the loop calls `_implement_round_body` and expects a return plus a final `STEP5_REVIEW_STATUS` envelope. Bare `exit 2` paths (jq missing, findings validation, `mirror_oos_markdown` cp failure, dynamic-archetypes validation) terminate the process before `step5_emit_final_envelope`, leaving `/implement` Step 5 with no parseable status. Prior run logs flagged this contract gap. In the Python `step5 --mode loop` controller, never `sys.exit` from per-round work while composing the final envelope. Map these failures to a stall terminal status, emit one `STEP5_REVIEW_STATUS` block (and done marker), then exit with the preserved rc.
  - From Cursor-Pragmatic: In the Python loop equivalent of `_implement_round_body`, when suppression is active convert infrastructure validation failures into a structured error return that `step5_emit_final_envelope` maps to `stall` (or the current shell status), never bare process exit


### FINDING_3: Escalation failure stderr sidecar and fail-open ledger keys must be ported
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: `run-step5-review.sh` tees child stderr to a temp file and passes it as `--failure-detail-log` when `record-escalation` fails, emitting fallback `STEP5_REVIEW_LEDGER_FAILURE_DETAIL_LOG` and a `Tool Failure: record-escalation` entry. A Python `step5` that only streams stderr to the terminal can lose failure-detail paths and break the fail-open ledger contract exercised in `scripts/test-run-step5-review.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In `step5`, preserve a stderr capture file for the review/fix phase; on `record-escalation` failure emit the same fallback `STEP5_REVIEW_LEDGER_*` keys and execution-issues breadcrumb; add pytest coverage mirroring the CMAR fail-open cases


### FINDING_4: In-process review-core needs an explicit test injection seam
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: `test-review-and-fix.sh` stubs review via `REVIEW_AND_FIX_REVIEW_CORE_SH`. The plan moves to `review_pipeline.review_core()` in-process but only vaguely says to preserve env overrides. Without an explicit injectable seam, pytest cannot cheaply stub review-core outcomes and parity work risks reintroducing subprocess `cli.py review core`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In `review_pipeline` or `review_and_fix`, add a test-only hook or parameter to substitute `review_core` / capture output; port harness cases by monkeypatching that seam; forbid `proc.run(... review core ...)` in `step5`


### FINDING_5: Folded launcher hard preflight gates are not enumerated in the plan
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: `run-step5-review.sh` hard-fails on unreadable `session-env.sh`, missing/empty `plan.txt`, missing `feature-description.txt`, and unresolved `RUN_ID` before invoking review-and-fix. The plan only says "resolve conventional files" for `step5`, so a partial port can start Step 5 without those gates and fail later inside review core with weaker errors.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add an explicit preflight checklist to `step5`: readable session env, non-empty `plan.txt`, present `feature-description.txt`, resolved `RUN_ID`, and `CODEX_PRESENT`/`CURSOR_PRESENT` boolean validation; pytest negative cases for each gate


### FINDING_6: Loop terminal stdout must emit the full `step5_emit_final_envelope` KV bundle
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: `/implement` Step 5 parses `STALL_TRACKING`, `STALL_REASON`, `ROUNDS_COMPLETED`, `FINAL_ROUND_NUM`, `FINAL_REVIEW_AND_FIX_STATUS`, `CODER_STATUS`, `FILES_CHANGED_HINT`, and `EFFECTIVE_ROUND_CAP` from the loop child stdout. The plan names a final `STEP5_REVIEW_STATUS` envelope but not the full `step5_emit_final_envelope` KV set.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: In step5 loop mode require the same terminal KV bundle as step5_emit_final_envelope and add pytest asserting all keys on complete stall cap-hit and handoff exits


### FINDING_7: Direct in-process `review_core` must preserve `IMPLEMENT_TMPDIR` environment parity
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: When C1b still delegates via `run_legacy`, review core skips implement run-log `write-round` and emit-tally implement-tmpdir plumbing, so Step 5 loses artifacts even though `review-core.env` is captured.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Set IMPLEMENT_TMPDIR in a temporary environment around review_pipeline.review_core(core_args), restore it in finally, and test that review_core sees it


### FINDING_8: `commit-fixes` parity omits Step 7 token/timing side effects
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: After shell deletion, review-and-fix commit-fixes can emit `COMMITTED`/`SHA` but stop marking Step 7 review-fix commits, regressing token/timing reports.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Add commit_fixes parity for session-env rehydration plus best-effort token mark and timing mark with LARCH_TIMING_SKILL=implement before committing, with a focused test



