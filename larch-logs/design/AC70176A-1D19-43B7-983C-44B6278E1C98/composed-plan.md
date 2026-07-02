## Plan

## Approach

Implement the accepted scope with minimum necessary changes.

1. Rebalance registry roles.
   - Change `review.fix_coder` to Codex, then Cursor, then Claude.
   - Change `review.findings_aggregator` and `design.plan_findings_aggregator` to Codex-primary single slots.
   - Set their Codex slot `model_role` to `review` so they resolve to `gpt-5.4-mini`.
   - Remove `design.plan_revision` from `ROLE_DEFAULTS`.

2. Add a write-capable Claude review-fix tier.
   - Add `python/cli.py agent launch-claude-review-fix` as a dedicated write-capable launcher mirroring `launch-claude-lint-fix` (`--allowedTools Read,Edit,Write`, default model `claude-sonnet-4-6`, no read-only preamble).
   - Keep `launch-claude-review` read-only for reviewers and voters only.
   - Add `_run_coder_claude()` beside the Cursor and Codex review-fix runners; dispatch through `agent launch-claude-review-fix`.
   - Use the same prompt body and output-copy contract as other review-fix runners.
   - Add `"claude": _run_coder_claude` to `runner_by_tool`.
   - Keep the existing `main-agent-required` fallback after all automated tiers fail.

3. Fix review-fix waterfall no-edit fallthrough.
   - In `apply_findings_with_coder`, when an automated tier exits successfully but `_collect_round_stage_paths` is empty, `continue` to the next `review.fix_coder` tier after failed-attempt cleanup instead of returning `CODER_STATUS=no-changes`.
   - Reserve `main-agent-required` for registry exhaustion (all Codex→Cursor→Claude tiers tried without applied edits or hard failures).
   - Preserve the existing `commit_failed` branch that already `continue`s when staging/commit fails.
   - Do not treat a successful no-edit Claude launch as terminal success.

4. Preserve aggregator model-role propagation.
   - When `review_aggregate.py` writes the aggregator slot NDJSON, include `model_role` when the registry slot provides it.
   - This makes Codex aggregator dispatch use the `review` model role instead of the default Codex model.

5. Move /design plan revision inline and repair Step 3 loop resume.
   - Stop launching `python/cli.py plan revise-waterfall` from `plan_review.py`.
   - For rounds with accepted in-scope findings that are not yet Gate-B-applied:
     - Emit `per-round-approval-required` when `approve_requested=true` and return immediately.
     - Emit `main-agent-apply-required` when `approve_requested=false` and return immediately.
     - Do not `continue` into `awaiting-apply` on the default accepted-finding path.
   - Refactor `_run_apply()` into a Gate-B resume helper only:
     - Keep zero-accepted and empty-findings short-circuits.
     - Preserve the `plan_changed` + `postapply_ready` / `awaiting-post-apply` dedup-only shortcut (no revise launch).
     - Remove all `revise-waterfall` and `RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH` handling.
   - Rewrite `awaiting-apply` and `awaiting-revise` phase handlers:
     - When `.gate-b-postapply-ready-N` is absent, re-emit `main-agent-apply-required` or `per-round-approval-required` instead of calling the gutted `_run_apply`.
     - When `.gate-b-postapply-ready-N` is present, route to `awaiting-post-apply` / existing post-apply handling without revise.
     - Remove `awaiting-revise` as an active revise entry; treat legacy `awaiting-revise` like `awaiting-apply` bail or postapply redirect.
   - Reuse the existing prompt-side Gate B apply body for both paths.
   - Preserve zero-accepted behavior, continuation, cap handling, MAV, postplan operator handling, dedup resume, and settled post-apply phase handling.
   - After Gate B settle succeeds for a round, call `_write_design_round_meta` (or `progress write-design-round-meta`) before resuming `awaiting-continuation`.
   - Remove `RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH` support with the retired external waterfall.

6. Add prompt-side pre-apply snapshot contract for Gate B.
   - In `approval-gates.md` Apply-all body, require copying `$DESIGN_TMPDIR/plan.txt` to `$DESIGN_TMPDIR/plan-pre-apply-round-N.txt` before any Gate B Write, matching `_snapshot_plan` semantics.
   - Replace the in-loop revise-waterfall snapshot paragraph with this prompt-side contract.
   - `_run_dedup` restore on dedup failure must continue to use the pre-apply snapshot.

7. Restore pre-apply snapshot on Gate B settle dedup failure.
   - In `design-step35-settle.sh`, when `--site gate-b` and `plan-review gate-b-dedup --dedup` exits `1` (`SETTLE_NEXT_ACTION=dedup-revise`), copy `$DESIGN_TMPDIR/plan-pre-apply-round-$GATE_B_ROUND.txt` back to `$DESIGN_TMPDIR/plan.txt` before emitting the action row and exiting.
   - Use the wrapper's resolved `GATE_B_ROUND` (`--round-num`, then `FINAL_ROUND_NUM`, `STEP3_REVIEW_ROUND_NUM`, `ROUND_NUM`).
   - Restore only when the snapshot file exists; do not write `.gate-b-postapply-ready-N`.
   - Match `_run_dedup` restore semantics so inline Gate B apply cannot leave a mutated `plan.txt` across a dedup-revise bail.

8. Delete the dead plan-revision CLI surface.
   - Remove `("plan", "revise-waterfall")` from CLI dispatch and machine-stdout allowlists.
   - Remove `revise_plan_with_waterfall_main` and revision-only helpers/tests that no longer have callers.
   - Keep plan-quality helpers still used by other plan commands.

9. Update docs, skill instructions, and integration harnesses.
   - Replace stale "revise-waterfall applies findings" text with "Gate B applies findings inline in the invoking /design agent."
   - Update role rows to describe new registry orders and Codex aggregator model role.
   - Remove docs for the retired `RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH` override.
   - Document settle dedup-failure snapshot restore in `design-step35-settle.md` and Gate B prose.
   - Retarget `scripts/test-design-multi-round-integration.sh` for inline Gate B apply/resume semantics.
   - Verify `SECURITY.md` already matches the new boundary; edit only if stale or contradictory text remains.

## Files to modify/create

### NEW: python/larch/agents launch surface for `agent launch-claude-review-fix`

- Add `launch_claude_review_fix_main` beside `launch_claude_lint_fix_main`.
- Mirror lint-fix argv shape: `--prompt-body-file`, `--output`, `--timeout` (default `1800`), optional `--model` (default `claude-sonnet-4-6`).
- Use a review-fix preamble ("apply accepted review findings to the working tree; do not commit or push") and `--allowedTools Read,Edit,Write`.
- Do not reuse `launch-claude-review` or its read-only subprocess preamble.
- Record `claude-review-fix` timing via the same vendor-task pattern as other coder tiers.

### UPDATED: python/larch/cli.py

- Register `("agent", "launch-claude-review-fix")`.
- Remove the `("plan", "revise-waterfall")` dispatch entry.
- Remove `("plan", "revise-waterfall")` from machine stdout keys.
- Keep other `plan` and `agent` commands unchanged.

### UPDATED: python/larch/core/config.py

- Change `review.fix_coder` order to `("codex", "cursor", "claude")`.
- Update its `doc_fallback`.
- Remove the `design.plan_revision` role row.
- Change both findings aggregator slots to `tool="codex"` and `model_role="review"`.
- Update aggregator `doc_fallback` strings to describe Codex-primary full waterfall behavior.

### UPDATED: python/larch/review/coder_runner.py

- Add `_run_coder_claude()`.
- Call `agent launch-claude-review-fix` with:
  - `--output` pointing to `coder-claude.log`.
  - `--prompt-body-file` using the same review-fix prompt file as other tiers.
  - `--timeout 1800`.
  - `--timing-task-kind claude-review-fix`.
- Copy successful Claude output to `tool_log`.
- Record timing consistently with other review-fix tiers.
- Add Claude to `runner_by_tool` in Codex→Cursor→Claude registry order.
- In `apply_findings_with_coder`, replace the successful empty-`stage_paths` early return with `continue` to the next registry tier after the same cleanup path used for failed launches.
- Emit `CODER_STATUS=no-changes` only when explicitly required by legacy callers outside the waterfall; the waterfall itself must not terminate on no-edit success before the last tier is exhausted.
- After all tiers are exhausted without applied edits, keep the existing `_record_main_agent_required_vendor_task` + `main-agent-required` result.

### UPDATED: python/larch/review/review_aggregate.py

- Include `"model_role": slot.model_role` in `aggregator-slots.ndjson` when non-empty.
- Keep output path, prompt file, role selection, validation retry, and fallback behavior unchanged.

### UPDATED: python/larch/review/plan_review.py

- Remove `_run_apply()`'s external revise-waterfall launch and override lookup.
- Keep zero-accepted and empty-findings branches unchanged.
- Keep the `plan_changed` + `postapply_ready` / `awaiting-post-apply` dedup-only branch as a no-revise path into `_run_dedup`.
- For non-empty accepted findings that have not already been prompt-side applied, emit bail status and return; do not enter in-loop apply.
- In the main loop after `LOOP_STATUS=complete`, route accepted findings directly to:
  - `per-round-approval-required` when `approve_requested`, then return.
  - `main-agent-apply-required` otherwise, then return.
- Rewrite `awaiting-apply` and `awaiting-revise` to re-bail to Gate B when `.gate-b-postapply-ready-N` is absent, or advance to post-apply/dedup when the marker exists.
- After successful Gate B post-apply settle (`.gate-b-postapply-ready-N` present and post-apply completes), call `_write_design_round_meta` before `awaiting-continuation`.
- Keep post-apply resume paths that handle `.gate-b-postapply-ready-N`, dedup, postplan, continuation, and operator brakes.
- Ensure default auto-apply UX is unchanged from the user's perspective: no prompt under default mode, but the applying agent is the invoking /design agent.

### UPDATED: python/larch/design/plan_quality.py

- Remove `revise_plan_with_waterfall_main`.
- Remove revision-only helpers that become unused after the CLI deletion.
- Keep shared plan validation, command parsing, optional trailer, auto-fix, and plan-size helpers.

### UPDATED: skills/design/scripts/design-step35-settle.sh

- On Gate B dedup failure (`dedup_rc=1`, before `SETTLE_NEXT_ACTION=dedup-revise`), restore `$DESIGN_TMPDIR/plan-pre-apply-round-$GATE_B_ROUND.txt` to `$DESIGN_TMPDIR/plan.txt` when the snapshot exists.
- Do not write `.gate-b-postapply-ready-$GATE_B_ROUND` on this path.
- Keep existing dedup success, postapply, pause, and `SETTLE_NEXT_ACTION` contracts unchanged.

### UPDATED: skills/design/scripts/design-step35-settle.md

- Document Gate B dedup-failure snapshot restore and its parity with `_run_dedup`.
- Note that prompt-side Gate B apply must create `plan-pre-apply-round-N.txt` before settle runs.

### UPDATED: python/tests/core/test_external_role_defaults.py

- Update expected role order for `review.fix_coder`.
- Remove `design.plan_revision` from expected pinned waterfall roles.
- Assert both findings aggregators use `tool == "codex"` and `model_role == "review"`.
- Keep out-of-scope role assertions unchanged.

### UPDATED: python/tests/agents/test_external_dispatch.py

- Update review-fix role-order probes to include Claude.
- Add or adjust a test proving the Claude runner is attempted after Codex and Cursor fail.
- Assert the Claude review-fix dispatch uses `agent launch-claude-review-fix`, not `launch-claude-review`.
- Update aggregator tests to assert the generated slot row carries `model_role: "review"` for Codex.

### UPDATED: python/tests/review/test_review_and_fix.py

- Mock `_run_coder_claude` in `apply_findings_with_coder` waterfall tests.
- Assert Codex→Cursor→Claude attempt order before `main-agent-required`.
- Assert Claude tier uses `launch-claude-review-fix`.
- Add waterfall coverage: Codex fails, Cursor fails, Claude succeeds with exit 0 but no stage paths → `main-agent-required`, not `no-changes`.
- Add coverage: Codex no-edit success → Cursor attempted; Cursor no-edit success → Claude attempted.
- Update failure/cleanup assertions that change when Claude is a third automated tier and when no-edit success no longer terminates early.

### UPDATED: python/tests/review/test_plan_review.py

- Replace revise-waterfall happy-path tests with inline-apply routing tests.
- Assert default accepted findings produce `STEP3_REVIEW_LOOP_STATUS=main-agent-apply-required` and leave `plan.txt` unchanged for prompt-side Gate B.
- Assert `--per-round-approval` still produces `per-round-approval-required`.
- Add resume tests for `awaiting-apply` / legacy `awaiting-revise` re-bailing to Gate B instead of calling deleted revise logic.
- Preserve and test the `plan_changed` + `postapply_ready` dedup-only shortcut.
- Add assertion that accepted-finding rounds write `round-meta.json` after Gate B post-apply success.
- Keep tests for zero accepted findings, continuation, post-apply resume, dedup failure, cap handling, and degraded panel provenance.
- Remove use of `RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH`.

### UPDATED: python/tests/design/test_plan_quality.py

- Remove tests dedicated only to `plan revise-waterfall`, its prompt composition, launch order, and patch extraction.
- Keep tests for plan validation, optional trailers, command parsing, auto-fix, and validator behavior.
- Remove or update helper tests only when their helper is deleted.

### UPDATED: skills/design/scripts/test-gate-b-apply-mode.sh

- Add a harness case: Gate B settle with dedup rc `1` restores `plan.txt` from `plan-pre-apply-round-N.txt` when the snapshot exists.
- Assert `.gate-b-postapply-ready-N` is absent after dedup-revise bail.

### UPDATED: scripts/test-design-multi-round-integration.sh

- Drop `RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH` stub wiring and in-loop `REVISE_STATUS=ok` expectations.
- For multi-round accepted-finding flow, expect `STEP3_REVIEW_LOOP_STATUS=main-agent-apply-required` on round 1, then simulate Gate B apply+settle resume (`--phase awaiting-post-apply` or `--phase awaiting-continuation`) before round 2 continuation.
- Keep zero-accepted per-entry integration assertions unchanged.
- Update sibling contract `scripts/test-design-multi-round-integration.md` if present.

### UPDATED: docs/external-reviewers.md

- Remove the `design.plan_revision` registry row or rewrite it as inline Gate B behavior, not an external role.
- Update `review.fix_coder` to Codex→Cursor→Claude, then main-agent-required.
- Document `agent launch-claude-review-fix` as the write-capable Claude review-fix launcher; keep `launch-claude-review` read-only for review/voter lanes.
- Update findings aggregators to Codex→Cursor→Claude through dispatch-waterfall, with Codex `review` model role.
- Note that automated tiers with successful no-edit exits fall through to the next tier or `main-agent-required`.

### UPDATED: docs/workflow-lifecycle.md

- Replace "applying accepted findings with `python/cli.py plan revise-waterfall`" with inline Gate B apply in the invoking /design agent.
- Keep the Step 3 loop, Gate B auto-apply default, and `--per-round-approval` UX descriptions intact.

### UPDATED: docs/python-migration.md

- Remove the line that says Step 3 keeps `RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH`.
- Note that the old `plan revise-waterfall` migration target is retired because Gate B owns plan application inline.

### UPDATED: skills/design/SKILL.md

- Replace Step 3 plan-review driver text that says the Python loop applies accepted findings via `plan revise-waterfall`.
- State that accepted findings now return to Gate B for inline application by the invoking /design agent.
- Keep the immediate-background, notification, resume, and sentinel contracts unchanged.
- Update "happy path revises `plan.txt` inside `python/plan_review.py`" text to say Gate B revises `plan.txt`.

### UPDATED: skills/design/references/approval-gates.md

- Update Gate B "When", mode, shared pipeline, and invariants text.
- Remove claims that script-internal Step 3 happy path applies findings via `plan revise-waterfall`.
- State that all accepted-finding application happens in prompt-side Gate B.
- In Apply-all body, add: before Write, copy `$DESIGN_TMPDIR/plan.txt` to `$DESIGN_TMPDIR/plan-pre-apply-round-N.txt` for the bound Gate B round.
- Replace the in-loop revise-waterfall snapshot paragraph with the prompt-side pre-apply snapshot contract above.
- State that `design-step35-settle.sh` restores the pre-apply snapshot on Gate B dedup failure before `dedup-revise` bail, matching `_run_dedup`.
- Preserve:
  - default auto-apply with no prompt.
  - `--per-round-approval` prompt behavior.
  - zero-findings short-circuit.
  - idempotency guard.
  - settle wrapper and dedup/trailer guard.

### UPDATED: skills/design/references/plan-review.md

- Update single-pass review wording so Step 3 returns for Gate B application when findings are accepted.
- Remove `python/cli.py plan revise-waterfall --patch-format file-replacement` references.
- Keep panel, aggregation, voting, tally, cap, and resume status contracts unchanged.

### MAY_UPDATE: SECURITY.md

- Verify the `/design` plan review apply boundary still describes inline Gate B apply, not in-loop `plan revise-waterfall`.
- Add a short note for `agent launch-claude-review-fix` as the write-capable review-fix launcher if the doc currently implies all Claude agent launches are read-only.
- Keep historical-run-log caveats if they are still accurate.

## Edge cases

- If Codex is unavailable, aggregator dispatch should fall back to Cursor, then Claude through the existing dispatch-waterfall behavior.
- If `model_role` is omitted from aggregator slot NDJSON, Codex would silently use the wrong model; test this.
- If any automated review-fix tier exits 0 with no working-tree edits, the waterfall must `continue` to the next tier; only registry exhaustion may emit `main-agent-required`.
- If Claude review-fix exits successfully with no working-tree edits after Codex and Cursor also produced no edits, the waterfall must fall through to `main-agent-required`, not stop at `CODER_STATUS=no-changes`.
- If all review-fix automated tiers fail launches or submodule checks, preserve the existing failure statuses and timing signals before `main-agent-required`.
- If Gate B resumes after an inline apply, do not reapply accepted findings when `.gate-b-postapply-ready-N` exists.
- If `awaiting-apply` or legacy `awaiting-revise` resumes before Gate B apply, re-bail with the correct apply-required status instead of calling deleted revise logic.
- If `plan_changed` is true and `postapply_ready` is set, run dedup-only through the preserved shortcut without revise.
- If Gate B settle dedup returns `dedup-revise` after inline apply, restore `plan-pre-apply-round-N.txt` before bail so resume does not start from a partially rewritten plan.
- If the pre-apply snapshot is missing on dedup failure, settle should still emit `dedup-revise` but skip restore; tests should cover the restore-when-present path.
- If a dedup or postplan brake fires after inline apply, keep the existing Gate B recovery flow.
- If a round has zero accepted findings, do not enter Gate B apply.
- If stale `RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH` is set in a test or environment, it should no longer affect runtime.

## Failure modes

- Using read-only `launch-claude-review` for review-fix would yield false-success `no-changes` and block `main-agent-required`; the dedicated write-capable launcher prevents this.
- Leaving `apply_findings_with_coder`'s no-edit early return in place would let Codex, Cursor, or Claude stop the waterfall while accepted findings remain unapplied.
- Removing `design.plan_revision` can break doc-row tests if docs still expect every old role.
- Deleting `plan revise-waterfall` can break CLI stdout allowlist tests if the machine-key list is not updated.
- Incomplete phase-handler rewrites can leave `awaiting-apply` calling deleted revise logic on resume.
- Omitting Gate B pre-apply snapshots can break `_run_dedup` and settle restore after dedup failure.
- Omitting settle snapshot restore on `dedup-revise` can leave mutated `plan.txt` in place and cause double-apply or wrong resume bytes.
- Omitting `_write_design_round_meta` after Gate B apply can break final-summary/Gantt round consumers.
- Leaving `test-design-multi-round-integration.sh` on revise stubs will fail `make test-harnesses-3`.
- Prompt-side Gate B must preserve optional trailers and `diff_lines`; do not bypass the existing settle wrapper.
- Claude review-fix dispatch may leave dirty changes on failure; keep existing failed-attempt cleanup and submodule revert checks around every tier.

## Testing strategy

Run targeted tests only for changed files:

```bash
python3 -m pytest \
  python/tests/core/test_external_role_defaults.py \
  python/tests/agents/test_external_dispatch.py \
  python/tests/review/test_review_and_fix.py \
  python/tests/review/test_plan_review.py \
  python/tests/design/test_plan_quality.py
```

Then run Gate B settle/apply harness coverage:

make test-gate-b-apply-mode

Then run the multi-round integration harness:

make test-design-multi-round-integration

Then run relevant static checks for the touched Python and Markdown files if dependencies are present:

python3 python/cli.py checks run-relevant

If `checks run-relevant` skips Python lint/test dependencies locally, report that and rely on the explicit pytest command, integration harnesses, and CI for full lint coverage.

## Acceptance

Run targeted tests only for changed files:

```bash
python3 -m pytest \
  python/tests/core/test_external_role_defaults.py \
  python/tests/agents/test_external_dispatch.py \
  python/tests/review/test_review_and_fix.py \
  python/tests/review/test_plan_review.py \
  python/tests/design/test_plan_quality.py
```

Then run Gate B settle/apply harness coverage:

make test-gate-b-apply-mode

Then run the multi-round integration harness:

make test-design-multi-round-integration

Then run relevant static checks for the touched Python and Markdown files if dependencies are present:

python3 python/cli.py checks run-relevant

If `checks run-relevant` skips Python lint/test dependencies locally, report that and rely on the explicit pytest command, integration harnesses, and CI for full lint coverage.

review_status: complete
rounds_completed: 2
diff_added: 350
diff_deleted: 425
mechanical_churn: false
diff_lines: 775
