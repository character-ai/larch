## Goal
Implement issue #3680: [IMPLEMENTING] sh-to-py C3a1: design plan-review loop core.

## Implementation Plan
## Plan

## Approach

The supplied approach synthesis is `NO_SKETCHES`, so draft from repo inspection and the approved outline only.

Implement the C3a1 port as a hard cutover:

1. Add two stdlib-only modules:
   - `python/plan_review_panel.py` for panel dispatch and voter dispatch.
   - `python/plan_review.py` for loop core, tally, Step 3 state, round snapshots, timing, Gate B dedup, emit/finalize/preview, retally env, drift baseline, artifact allowlists, and escalation evidence staging.

2. Register a `plan-review` CLI domain in `python/cli.py`.

3. Update live bash wrappers and docs to call `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" plan-review ...` directly.

4. Preserve byte-stable contracts:
   - `LOOP_STATUS` values.
   - `STEP3_REVIEW_LOOP_STATUS` values.
   - `.step3-review-result.env`.
   - `.step3-plan-review-result.env`.
   - `review-round-count.txt` persist-before-launch and rollback semantics.
   - `plan-review/round-N/` artifact structure.
   - FD 3 `emit_kv` behavior through `logging_util`.

5. Port tests to pytest, run old shell harnesses once as parity after cutover, then delete absorbed scripts, sibling `.md` files, and absorbed shell harnesses.

6. Append retired paths to `python/migrated-scripts.tsv`, using the actual migration issue number.

## Files to modify/create

### NEW: python/plan_review_panel.py

Implement panel/voter dispatch functions with injectable subprocess seams.

Include:

- `dispatch_panel(...)`.
- `dispatch_voters(...)`.
- JSONL/NDJSON manifest helpers.
- Dynamic archetype prompt assembly from `scout-plan-manifest.json`.
- Static slot matrix:
  - Round 1: Cursor and Codex specialists when present.
  - Round 2+: Cursor specialists plus generic Codex when both vendors are present.
  - Codex specialists as replacements when Cursor is absent.
  - Generic Claude fallback when both externals are absent.
- Prune filtering through the existing reviewer-prune command until that domain is migrated.
- Waterfall dispatch through the existing `scripts/dispatch-with-waterfall.sh`.
- Voter prompt rendering through existing Python rendering helpers or direct `python/cli.py render voter` invocation.
- Parallel Claude voter launch without polling.
- Parse-rate retry through `python/voting.py`.
- `plan-voter-paths.txt` and voter status block emission.

Keep output KVs identical to the absorbed scripts.

### NEW: python/plan_review.py

Implement the loop and mechanical helpers.

Include importable functions for:

- `run_step3_review(...)`.
- `run_step3_loop(...)`.
- `run_plan_review_round(...)`.
- `tally_plan_review(...)`.
- `emit_plan(...)`.
- `finalize_plan(...)`.
- `emit_design_plan_preview(...)`.
- `gate_b_dedup_plan(...)`.
- `persist_retally_step3_env(...)`.
- `step3_state(...)`.
- `record_plan_review_round_timing(...)`.
- `round_artifact_included(...)`.
- `round_revise_artifact_included(...)`.
- `round_revise_artifact_excluded(...)`.
- `drift_baseline_write_once(...)`.
- `step3_record_report_evidence(...)` — escalation evidence staging previously supplied by `review-design-step3-loop.sh`; called by `run_step3_review` on `.step3-review-result.env` read failure so `design-step3-review.sh` no longer needs to source the deleted script.

Use `plan_quality` functions in-process for revision, optional trailers, and plan-size related helpers. Do not shell out to retired C3a2 surfaces.

Keep `dedup-plan-lines.py` in place. Call it via import or subprocess. Preserve `LARCH_DEDUP_PLAN_LINES_PY`.

Add small internal helpers for:

- Safe env reads and atomic env writes.
- Symlink rejection for result envs and artifacts.
- Single-line scope-anchor validation.
- Round phase file handling.
- Snapshot copy allowlists.
- Cumulative accepted findings and OOS merge/dedup.
- Review-round count parsing and rollback.
- Large-plan preview threshold normalization.

### NEW: python/test_plan_review.py

Port the absorbed loop, state, tally, emit, finalize, timing, dedup, retally, preview, and artifact allowlist harness coverage.

Cover at least:

- Missing argv and usage failures.
- `emit-plan` `diff_lines:` parsing.
- `finalize-plan` artifact creation and symlink rejection.
- Step 3 cap behavior.
- `review-round-count.txt` non-numeric fallback.
- Persist-before-launch and rollback on `tally-error` and `degraded-empty-collector`.
- All terminal `LOOP_STATUS` and `STEP3_REVIEW_LOOP_STATUS` values.
- MainAgent vote required handoff.
- Retally env refresh with and without scope anchor.
- Round snapshot shape.
- Round timing idempotency.
- Gate B optional trailer key/value preservation.
- Dedup failure restore.
- Step 3 state cleanup.
- `.step3-review-result.env` read failure triggers `step3_record_report_evidence` evidence staging and does not source `review-design-step3-loop.sh`.

### NEW: python/test_plan_review_panel.py

Port panel and voter dispatch coverage.

Cover at least:

- Static manifest matrix by vendor availability and round.
- Dynamic scout manifest rows.
- Generic Claude fallback when no external tools are present.
- Pruned-empty panel.
- Degraded round calculation.
- Waterfall non-zero exit handling.
- Voter 1 parallel launch result handling.
- Voter 2/3 unavailable and fallback statuses.
- Parse-rate `NOT_SUBSTANTIVE` exclusion.
- Quota/usage warning attribution.
- `plan-voter-paths.txt` output.

### UPDATED: python/cli.py

Add `plan-review` registry entries.

Use direct verbs such as:

- `plan-review run`
- `plan-review panel-dispatch`
- `plan-review voter-dispatch`
- `plan-review tally`
- `plan-review emit`
- `plan-review finalize`
- `plan-review preview`
- `plan-review gate-b-dedup`
- `plan-review persist-retally-env`
- `plan-review step3-state`
- `plan-review record-round-timing`
- `plan-review round-artifact-included`
- `plan-review drift-baseline`

Keep lazy imports.

### UPDATED: skills/design/scripts/design-step3-review.sh

Keep the wrapper bash.

Change only the inner launch from `run-step3-review.sh --mode loop` to:

`python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" plan-review run --design-tmpdir "$DESIGN_TMPDIR" --mode loop`

Forward `--starting-round` when present.

Preserve process-group isolation, stdout capture, result-env parsing, and normalized stdout KVs.

Remove the `source review-design-step3-loop.sh` call that previously loaded `step3_record_report_evidence` on `.step3-review-result.env` read failure. The escalation evidence path is now handled inside `plan_review.py`; `design-step3-review.sh` must not retain any source dependency on the deleted script.

Update user-facing diagnostics that name `run-step3-review.sh` only where stale.

### UPDATED: skills/design/scripts/design-driver.sh

Replace `emit-plan.sh` and `finalize-plan.sh` invocations with `plan-review emit` and `plan-review finalize`.

Preserve `ACTION=EMIT_PLAN` and `ACTION=FINALIZE` behavior.

### UPDATED: skills/design/scripts/design-step2b-drafter.sh

Replace the Step 2b preview call with `plan-review preview --variant step2b`.

Preserve `LARCH_QUIET_DISABLE=1` capture behavior.

### UPDATED: skills/design/scripts/design-step3-entry-preview.sh

Replace `run-step3-review.sh --preview-only` with `plan-review preview --variant step3`.

Keep the driver-owned sentinel behavior if this wrapper currently owns it.

### UPDATED: skills/design/scripts/design-step4b-preview.sh

Replace `emit-design-plan-preview.sh --variant gatec` with `plan-review preview --variant gatec`.

Preserve warning-only invalid tmpdir behavior.

### UPDATED: skills/design/scripts/design-step3-entry-state.sh

Replace `design-step3-state.sh --direct-review-entry` with `plan-review step3-state --direct-review-entry`.

### UPDATED: skills/design/scripts/design-step3-continuation-entry.sh

Replace `design-step3-state.sh --direct-review-pause-hygiene` with `plan-review step3-state --direct-review-pause-hygiene`.

### UPDATED: skills/design/scripts/design-step3-gate-b-bypass.sh

Replace `design-step3-state.sh --gate-b-bypass` with `plan-review step3-state --gate-b-bypass`.

### UPDATED: scripts/design-pause-save.sh

Replace the Step 3 state helper call with `plan-review step3-state`.

Keep pause-save behavior unchanged.

### UPDATED: skills/design/scripts/design-postplan-emit.sh

Remove the `lib-drift-baseline.sh` source dependency.

Replace `larch_drift_baseline_write_once` with `plan-review drift-baseline write-once`.

Do not migrate unrelated postplan behavior.

### UPDATED: scripts/design-log-publish.sh

Remove the `lib-design-round-artifacts.sh` source dependency.

Replace allowlist checks with local Python CLI calls or an import-backed helper invocation.

Keep publish behavior and artifact policy unchanged.

### UPDATED: scripts/relevant-checks.sh

Retarget changed-file routing for retired plan-review scripts and tests to `python/test_plan_review.py` and `python/test_plan_review_panel.py`.

Remove routing rows for deleted script paths.

### UPDATED: scripts/test-design-structure.sh

Update structure assertions from retired script paths to the new `plan-review` CLI surface.

Keep assertions that verify wrapper boundaries and no direct prompt-side Step 3 loop routing.

### UPDATED: skills/design/scripts/test-step3-review-cap.sh

Retarget cap assertions to `python/plan_review.py` and the `plan-review run` CLI.

Preserve cap breadcrumb and symlink cleanup coverage.

### UPDATED: scripts/test-design-multi-round-integration.sh

Replace direct `run-step3-review.sh` calls with `python3 python/cli.py plan-review run`.

Keep the multi-round scenario and assertions.

### UPDATED: skills/design/scripts/test-gate-b-apply-mode.sh

Replace direct `gate-b-dedup-plan.sh` calls with `plan-review gate-b-dedup`.

Keep Gate B mode assertions.

### UPDATED: Makefile

Remove absorbed shell harness targets from `test-harnesses-*` shards.

Do not leave phony targets that call deleted scripts.

Keep pytest coverage under `make py-test`.

Keep `make lint-retired-scripts` in `make lint`.

### UPDATED: docs/linting.md

Replace shell harness rows with pytest rows for `python/test_plan_review.py` and `python/test_plan_review_panel.py`.

Remove stale references to deleted harness paths.

### UPDATED: docs/python-migration.md

Add a C3a1 decision-log entry.

Note:

- Two-module split.
- Direct `plan-review` CLI cutover.
- `design-step3-review.sh` remains a bash wrapper.
- `dedup-plan-lines.py` stays in place.
- `snapshot-plan-round.sh` is skipped because no standalone source file exists.
- Assessor scripts are out of scope.
- `step3_record_report_evidence` moved into `plan_review.py`; `design-step3-review.sh` source dependency on `review-design-step3-loop.sh` removed.

### UPDATED: docs/workflow-lifecycle.md

Update Step 3 prose from `run-step3-review.sh --mode loop` to `python3 python/cli.py plan-review run --mode loop`.

### UPDATED: docs/configuration-and-permissions.md

Update Step 3 and Gate C preview references to `plan-review preview`.

Preserve the chat-order note semantics.

### UPDATED: docs/issue-anchored-plan.md

Update preview and Step 3 handoff references to the new CLI verbs.

### UPDATED: docs/run-logs.md

Update the plan-review tally and round-artifact producer references to `python/plan_review.py`.

### UPDATED: docs/vendor-agent-diagnostics-audit.md

Replace `scripts/dispatch-plan-voters.sh` and `scripts/lib-design-round-artifacts.sh` rows with the Python module/CLI surface.

### UPDATED: skills/design/SKILL.md

Update Step 3, Gate B, preview, emit, finalize, retally, timing, and testing references.

Keep the agent-lint focus-area anchor.

Do not change prompt semantics beyond the new command paths.

### UPDATED: skills/design/references/plan-review.md

Update ownership from shell scripts to `python/plan_review.py` and `python/plan_review_panel.py`.

Preserve reviewer prompt, ballot, tally, MainAgent vote, and artifact contracts.

### UPDATED: skills/design/references/approval-gates.md

Replace Gate B dedup, Step 3 loop, retally, timing, and preview command references with `plan-review` verbs.

Keep the shared post-apply pipeline semantics unchanged.

### UPDATED: skills/design/references/discussion-rounds.md

Replace Gate A rewrite dedup references with `plan-review gate-b-dedup`.

### UPDATED: skills/design/references/flags.md

Replace `emit-plan.sh` grammar references with `plan-review emit`.

### UPDATED: scripts/design-log-publish.md

Update the round artifact allowlist authority from `scripts/lib-design-round-artifacts.sh` to `python/plan_review.py`.

### UPDATED: python/migrated-scripts.tsv

Append every retired absorbed `.sh` and sibling `.md` path.

Include:

- `skills/design/scripts/plan-review-loop.sh`
- `skills/design/scripts/plan-review-loop.md`
- `skills/design/scripts/dispatch-plan-review-panel.sh`
- `skills/design/scripts/dispatch-plan-review-panel.md`
- `skills/design/scripts/tally-plan-review.sh`
- `skills/design/scripts/tally-plan-review.md`
- `skills/design/scripts/record-plan-review-round-timing.sh`
- `skills/design/scripts/record-plan-review-round-timing.md`
- `skills/design/scripts/persist-retally-step3-env.sh`
- `skills/design/scripts/persist-retally-step3-env.md`
- `skills/design/scripts/design-step3-state.sh`
- `skills/design/scripts/design-step3-state.md`
- `skills/design/scripts/run-step3-review.sh`
- `skills/design/scripts/run-step3-review.md`
- `skills/design/scripts/review-design-step3-loop.sh`
- `skills/design/scripts/review-design-step3-loop.md`
- `skills/design/scripts/gate-b-dedup-plan.sh`
- `skills/design/scripts/gate-b-dedup-plan.md`
- `skills/design/scripts/lib-drift-baseline.sh`
- `skills/design/scripts/emit-plan.sh`
- `skills/design/scripts/emit-plan.md`
- `skills/design/scripts/finalize-plan.sh`
- `skills/design/scripts/finalize-plan.md`
- `skills/design/scripts/emit-design-plan-preview.sh`
- `skills/design/scripts/emit-design-plan-preview.md`
- `scripts/dispatch-plan-voters.sh`
- `scripts/dispatch-plan-voters.md`
- `scripts/lib-design-round-artifacts.sh`
- `scripts/lib-design-round-artifacts.md`
- Absorbed shell harnesses and their `.md` siblings.

Do not add `snapshot-plan-round.sh`; it is absent.

Do not add assessor scripts.

## Retired test surfaces

Delete after pytest parity exists:

- `skills/design/scripts/test-plan-review-loop.sh`
- `skills/design/scripts/test-plan-review-loop.md`
- `skills/design/scripts/test-dispatch-plan-review-panel.sh`
- `skills/design/scripts/test-dispatch-plan-review-panel.md`
- `skills/design/scripts/test-run-step3-review.sh`
- `skills/design/scripts/test-run-step3-review.md`
- `skills/design/scripts/test-review-design-step3-loop.sh`
- `skills/design/scripts/test-review-design-step3-loop.md`
- `skills/design/scripts/test-tally-plan-review.sh`
- `skills/design/scripts/test-tally-plan-review.md`
- `skills/design/scripts/test-record-plan-review-round-timing.sh`
- `skills/design/scripts/test-record-plan-review-round-timing.md`
- `skills/design/scripts/test-persist-retally-step3-env.sh`
- `skills/design/scripts/test-persist-retally-step3-env.md`
- `skills/design/scripts/test-design-step3-state.sh`
- `skills/design/scripts/test-design-step3-state.md`
- `skills/design/scripts/test-gate-b-dedup-plan.sh`
- `skills/design/scripts/test-gate-b-dedup-plan.md`
- `skills/design/scripts/test-emit-plan.sh`
- `skills/design/scripts/test-emit-plan.md`
- `skills/design/scripts/test-finalize-plan.sh`
- `skills/design/scripts/test-finalize-plan.md`
- `skills/design/scripts/test-emit-design-plan-preview.sh`
- `skills/design/scripts/test-emit-design-plan-preview.md`
- `scripts/test-dispatch-plan-voters.sh`
- `scripts/test-dispatch-plan-voters.md`
- `scripts/test-lib-design-round-artifacts.sh`
- Related absorbed harness docs.

## Edge cases

- Treat invalid or missing `review-round-count.txt` as `0`.
- Persist the pending round before launch.
- Roll back the count on `tally-error`, `LOOP_STATUS=tally-error`, or `degraded-empty-collector`.
- Refuse symlinked result envs, round dirs, and artifact files.
- Never relay stale `SCOPE_ANCHOR_FILE` on tally errors.
- Preserve CR/LF stripping for single-line env values.
- Keep pruned-empty rounds non-degraded and terminal.
- Keep zero-judge MainAgent vote handoff and retally behavior.
- Keep `round-summary.env` and `findings-classification.tsv` paths stable.
- Do not move `dedup-plan-lines.py`.
- Do not migrate Step 3.6 assessor scripts.
- Do not create a standalone `snapshot-plan-round` verb.
- On `.step3-review-result.env` read failure, invoke `step3_record_report_evidence` from `plan_review.py` directly; `design-step3-review.sh` must carry no source dependency on `review-design-step3-loop.sh`.

## Failure modes

- A retired sourced library can break an out-of-scope bash consumer. Mitigate by cutting over `design-postplan-emit.sh` and `design-log-publish.sh` at the narrow source seam before deleting the libraries.
- `design-step3-review.sh` sourcing `review-design-step3-loop.sh` for escalation evidence on env-read failure would break silently after the script is deleted. Mitigate by moving `step3_record_report_evidence` into `plan_review.py` and removing the source call before deletion.
- Subprocess waterfall failures can leave partial outputs. Preserve degraded KVs and continue to tally when existing behavior does.
- Python env writing can accidentally reorder or omit keys. Pin env contents in tests.
- Dynamic scout prompt assembly can leak untrusted text as instructions. Preserve literal-redacted wrapping and escaping.
- Large-plan preview can drift in threshold behavior. Pin default `120`, invalid-value fallback, strict `&gt;` comparison, 40-heading outline cap, and 30-line fallback.
- Round cleanup can delete diagnostics. Preserve prior rounds and clean only the active `round-N` slot.

## Testing strategy

1. Add pytest first:
   - `python -m pytest python/test_plan_review.py python/test_plan_review_panel.py`

2. After CLI cutover but before deleting shell harnesses, run the absorbed harnesses once against the new CLI path where practical.

3. Delete absorbed scripts and harnesses.

4. Run:
   - `make py-test`
   - `make py-lint`
   - `make lint-retired-scripts`
   - `bash scripts/relevant-checks.sh`
   - `make lint`

5. Confirm stale-reference sweep:
   - No tracked file references retired full paths.
   - No same-directory `$SCRIPT_DIR/&lt;retired&gt;.sh` references remain.
   - No docs instruct users to call retired scripts.
   - No remaining source of `review-design-step3-loop.sh` anywhere in `design-step3-review.sh`.

diff_added: 8250
diff_deleted: 12600
mechanical_churn: true
diff_lines: 20850

## Acceptance

- [ ] `python/plan_review.py` and `python/plan_review_panel.py` exist, import cleanly, and expose all CLI verbs under the `plan-review` domain in `python/cli.py`.
- [ ] All absorbed bash scripts and sibling `.md` files are deleted.
- [ ] All bash wrappers (`design-step3-review.sh`, `design-driver.sh`, `design-step3-entry-state.sh`, etc.) call `python3 cli.py plan-review ...` directly.
- [ ] Pytest replaces all absorbed shell harnesses: `make py-test` green.
- [ ] `make lint-retired-scripts` green — no tracked file references retired paths.
- [ ] `make lint` and `make py-lint` green.

diff_lines: 20850

## Test plan
(no test plan section in plan-file)
