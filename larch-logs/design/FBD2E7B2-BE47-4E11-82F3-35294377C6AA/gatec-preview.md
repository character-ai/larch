## Final Design Plan

The plan is very large. Showing the full plan body below.

## Plan

# Lint-fix waterfall hardening

## Approach

- Treat the shared Piece 1 contracts as prerequisites. Use `config.FIXER_LANE_TIMEOUT_SEC`, `external_defaults.fixer_lane_budget_sec("implement.lint_fix_coder")`, and `external_defaults.next_untried_tier()` instead of local timeout and tier-loop constants.
- Keep `run_lint_fix` site-aware because it is shared by pre-ship repair-loop callers and `ship-pr-ci-*` callers. Apply the new non-structural stall contract only to pre-ship sites (`step3`, `step5*`, and `step6`); preserve the existing `ship-pr-ci-*` `main-agent-required` outcome and `NEEDS_USER_SHIP_PR_INTERNAL_LINT_FIX` ledger/handoff semantics without changing Step 8 orchestration.
- Define the pre-ship non-structural terminal vocabulary as these exact, closed `failure_reason` tokens:
  - `lint-fix-no-selectable-tier`
  - `lint-fix-all-tiers-no-useful-delta`
  - `lint-fix-budget-exhausted`
- A recoverable single-tier result—timeout, missing binary, authentication/preflight failure, launcher failure, or clean no-op—is recorded and reduced inside the same `run_lint_fix` invocation. It is not returned to `_handle_fix_outcome()` as a terminal main-agent escalation.
- When no selectable tiers remain before dispatch, all dispatched selectable tiers have produced no useful delta, or the lane-reservation budget cannot reserve another full lane, return `FixOutcome(status="failed", failure_reason=<one of the exact non-structural tokens>)` for pre-ship sites.
- Preserve terminal failure reasons and tier-ledger paths through the result model. `FixOutcome` carries the named `failure_reason` and bounded `tier_ledger_path`; `LoopResult` carries the last terminal failure reason and bounded ledger path. `_handle_fix_outcome()` copies both values without collapsing a failed outcome into an ambiguous generic loop status.
- `_repair_loop_action()` maps only the closed pre-ship non-structural reason set above to `stall`. It must not infer stall from a generic failed status, a legacy `no-changes` status, or arbitrary failure text. Named structural fast-fail reasons, including complexity-baseline and structural-ruff failures, may map to `main-agent-edit`; `ship-pr-ci-*` retains its existing site-gated internal-handoff behavior.
- Retain `no-changes` only as an internal per-tier classification while the waterfall selects another tier. Do not use it as an ambiguous final pre-ship outcome.
- Track attempted tiers explicitly. Initialize a lane-reservation pool from `fixer_lane_budget_sec("implement.lint_fix_coder")`; before each dispatch, reserve exactly one full `config.FIXER_LANE_TIMEOUT_SEC` lane from that pool. Decrement the pool by the reservation, not wall-clock time spent in repository capture, validation, ledger writing, or other between-tier orchestration. This preserves eligibility for every configured tier even when earlier tiers consume their full lane timeout plus normal orchestration overhead.
- Every dispatched tier receives the full `config.FIXER_LANE_TIMEOUT_SEC` launcher timeout. If the reservation pool cannot reserve a complete lane, do not launch a shortened final tier; return `lint-fix-budget-exhausted` for pre-ship sites.
- Select tiers only through `next_untried_tier()`, passing the already-probed `claude_present`, `codex_present`, and `cursor_present` flags. Treat no selectable tier before the first dispatch as `lint-fix-no-selectable-tier`; treat exhaustion after one or more dispatched tiers with no useful delta as `lint-fix-all-tiers-no-useful-delta`.
- Create an isolated per-attempt run directory beneath the lint-fix run root, keyed by ordered attempt sequence and selected tier. Bind each launcher’s stdout/stderr/log paths, redacted-log validation, execution-issue evidence, and ledger row to that attempt directory so later tiers cannot overwrite earlier `claude-lint-fix`, Codex, or Cursor artifacts.
- Inspect and validate repository state after every dispatched tier, including non-zero and timeout exits. Capture exact pre-dispatch state per attempt, including HEAD, branch, index/worktree content for already-dirty tracked paths, and content/state for already-dirty untracked paths, so useful edits to an initially dirty path are detected rather than discarded as path-set no-ops.
- Continue to the next tier after recoverable no-useful-delta outcomes. Stop dispatching only after a useful validated delta or a structural, forbidden-path, branch, HEAD, repository-capture, tmpdir, integrity, isolated-run-artifact, or redaction failure.
- When an attempt produces useful edits, including partial edits from a non-zero or timed-out launcher, stop dispatching and return the edits to the existing checks loop. Let that loop rerun checks before deciding whether another repair iteration is needed.
- Apply existing forbidden-path, branch, HEAD, and redaction guards before accepting a tier’s edits. Structural or integrity failures remain terminal and fail-closed.
- Persist one ordered bounded row per attempted tier at `$IMPLEMENT_TMPDIR/lint-fix-loop/lint-fix-tier-ledger.tsv`. Use a tab-separated, headered schema with bounded/redacted fields: `sequence`, `tier`, `outcome_class`, `exit_status`, `elapsed_ms`, `useful_delta`, and `execution_issue_kind`. Append exactly once after each dispatch classification; never write raw prompts, check output, unredacted tool logs, or raw per-attempt paths to the ledger.
- Preserve available redacted per-attempt tool logs and write categorized execution-issue records through the existing execution-issue mechanism for timeout, authentication/preflight, missing-binary, launcher, and similar anomalous failures. Associate those records with the isolated attempt artifacts.
- Emit `FAILURE_REASON=<exact named token>` and `LINT_FIX_TIER_LEDGER_PATH=<path>` in terminal pre-ship `NEXT_ACTION=stall` envelopes. Keep existing escalation `LINT_FIX_LEDGER_*` keys structural-only; do not revive main-agent escalation ledgers for ordinary exhaustion.
- Remove pre-ship exhaustion and stale-no-change promotion to `NEXT_ACTION=main-agent-edit`. Keep that action only for explicit pre-ship structural `main-agent-required` cases, while retaining the existing ship-pr internal handoff behavior.
- Do not change Step 8 CI orchestration, ship-pr waterfall membership, or tier order.

## Files to modify/create

### UPDATED: python/larch/implement/checks_run_relevant.py

- Extend `FixOutcome` with bounded fields for `failure_reason` and `tier_ledger_path`, preserving defaults for unrelated callers.
- Extend `LoopResult` with bounded fields for the terminal/last `failure_reason` and `tier_ledger_path`.
- Keep the result-model additions minimal and backward-compatible: they carry routing and evidence metadata only and do not alter unrelated checks-result semantics.
- Ensure the result model can preserve the exact named pre-ship exhaustion token and bounded ledger pointer from `run_lint_fix()` through `_handle_fix_outcome()`, `_repair_loop_action()`, and terminal repair-loop stdout.

### UPDATED: python/larch/implement/checks_lint_fix.py

- Remove `_RUN_EXTERNAL_TIMEOUT` and `_LINT_FIX_TOTAL_BUDGET_SECONDS`.
- Pass `config.FIXER_LANE_TIMEOUT_SEC` to Claude, Codex, and Cursor launchers.
- Derive the complete lane-reservation budget with `fixer_lane_budget_sec("implement.lint_fix_coder")`.
- Replace the direct `tool_order()` loop with attempted-tier selection through `next_untried_tier()`, passing `claude_present=claude_present`, `codex_present=codex_present`, and `cursor_present=cursor_present`.
- Add explicit site classification for pre-ship (`step3`, `step5*`, `step6`) versus `ship-pr-ci-*` callers. Preserve current ship-pr `main-agent-required` and ship-pr internal-lint-fix ledger behavior; do not alter the Step 8 caller contract.
- Define constants for the exact closed pre-ship non-structural reason set:
- Before each dispatch, reserve one full `config.FIXER_LANE_TIMEOUT_SEC` from the derived lane-reservation budget. Charge the reservation pool only for dispatched lanes, excluding bounded repository-state capture, validation, classification, log handling, and ledger-write overhead. If the pool lacks a full lane, do not dispatch a shortened final tier; return the site-gated budget-exhausted outcome.
- Create a fresh sequence- and tier-scoped attempt `run_dir` for every dispatch. Pass only that attempt directory to the selected launcher and bind its redacted logs and execution-issue evidence to that attempt so artifact filenames from later tiers cannot overwrite or misattribute earlier-tier evidence.
- Distinguish recoverable tier outcomes from terminal outcomes:
  - Record and continue after timeout, missing binary, authentication/preflight failure, launcher failure, and successful no-op attempts with no validated useful delta.
  - Accept useful worktree, index, untracked-file, or committed deltas from successful, non-zero, and timeout attempts, subject to the existing post-dispatch integrity guards.
  - Stop fail-closed for structural, repository-state, forbidden-path, branch, HEAD, tmpdir, isolated-artifact, invalid-log, and redaction failures.
- Capture per-tier repository baselines that compare content, not only path membership, for pre-existing dirty tracked and untracked files. Treat a content change beyond that baseline as useful work and stop further dispatch so the checks loop reruns.
- Return `FixOutcome(status="failed", failure_reason=...)` using only the named non-structural exhaustion constants for pre-ship zero-selectable-tier, full attempted-tier exhaustion, and lane-budget-exhausted paths. Populate `tier_ledger_path` whenever the durable ledger has been initialized.
- Preserve `main-agent-required` only for named structural pre-ship failures, including complexity-baseline and structural-ruff fast-fail routes. Preserve current `main-agent-required` behavior for `ship-pr-ci-*` internal handoffs.
- Add the durable `$IMPLEMENT_TMPDIR/lint-fix-loop/lint-fix-tier-ledger.tsv` writer with ordered, headered, bounded/redacted rows: `sequence`, `tier`, `outcome_class`, `exit_status`, `elapsed_ms`, `useful_delta`, and `execution_issue_kind`.
- Write categorized existing execution-issue evidence for anomalous dispatch outcomes from each attempt’s isolated artifacts without including raw prompt, check, or tool-log payloads. Propagate the ledger path and terminal failure reason through `FixOutcome`.
- Update `_handle_fix_outcome()` to copy `FixOutcome.failure_reason` and `FixOutcome.tier_ledger_path` into `LoopResult` without replacing a named exhaustion token with a generic failed status.
- Remove `_populate_no_changes_stale_ledger()`, `_populate_exhausted_ledger()`, and their pre-ship site gate. Make `_repair_loop_action()` use a closed pre-ship allowlist: the three named non-structural exhaustion reasons return `stall`; named structural reasons retain `main-agent-edit`; ship-pr behavior remains site-gated and unchanged.
- In `checks_repair_loop_main()`, emit `FAILURE_REASON` and `LINT_FIX_TIER_LEDGER_PATH` for terminal pre-ship stalls. Retain structural-only escalation ledger keys and do not emit `NEXT_ACTION=main-agent-edit` for ordinary pre-ship waterfall exhaustion.
- Keep stdout grammar compatible for retained keys.

### UPDATED: skills/implement/references/checks-repair-loop.md

- Define a site-routing table for repair outcomes:
  - Pre-ship `step3`, `step5*`, and `step6` `lint-fix-no-selectable-tier`, `lint-fix-budget-exhausted`, and `lint-fix-all-tiers-no-useful-delta` outcomes route to terminal stall semantics.
  - Explicit structural `main-agent-required` outcomes remain fail-closed and may route to `NEXT_ACTION=main-agent-edit`.
  - `ship-pr-ci-*` retains its existing internal `main-agent-required` handoff and is outside this repair-loop routing change.
- Define `NEXT_ACTION=main-agent-edit` as an explicit structural fail-closed route, not a generic waterfall fallback.
- Remove exhausted-loop inline repair instructions and final-failure-log diagnosis flow for pre-ship exhaustion.
- Document that timeout, unavailable tool, authentication failure, launcher failure, budget reservation failure, and no useful change advance within the delegated pre-ship waterfall until a named terminal exhaustion condition is reached.
- State that lane budget reserves one full configured timeout per dispatched tier and excludes bounded orchestration overhead from lane consumption, ensuring the final configured tier remains eligible after prior full-lane attempts.
- State that useful edits, including validated partial edits after a non-zero or timed-out launcher, cause the pinned composite checks launcher to run again.
- Document `FAILURE_REASON` and `LINT_FIX_TIER_LEDGER_PATH` as bounded evidence in pre-ship terminal stall output. Do not describe the tier ledger as a main-agent escalation ledger.
- Document isolated per-tier artifacts as preserving accurate redacted logs and execution-issue evidence across a multi-tier waterfall.
- Preserve Step 3, Step 5, and Step 6 pinned launcher and bgjob wait contracts.

### UPDATED: skills/implement/SKILL.md

- Update checks-repair references that describe `NEXT_ACTION=main-agent-edit` as a normal re-entry path.
- Keep the Checks Failure Entry Macro thin and defer detailed site routing, exact exhaustion tokens, tier outcomes, isolated evidence handling, and terminal-envelope behavior to `checks-repair-loop.md`.
- Clarify at Step 5 that only explicit structural `main-agent-required` outcomes permit main-agent repair. Exhausted delegated pre-ship repair routes to the existing durable stall path with its failure reason and tier-ledger pointer.
- Preserve the existing ship-pr and Step 8 CI orchestration text and do not introduce a Step 8 behavioral change.

### UPDATED: python/tests/implement/test_checks.py

- Assert all three external launch argv builders use `config.FIXER_LANE_TIMEOUT_SEC`.
- Assert lane-reservation-budget logic reserves one full timeout for every dispatched lint-fix tier and does not charge normal inter-tier capture, validation, classification, or ledger overhead against lane capacity.
- Cover a final-tier case in which prior tiers each consume their full timeout plus simulated orchestration overhead, proving the final configured tier still dispatches with a full configured timeout.
- Cover the insufficient-reservation case, proving it prevents dispatch and returns only `lint-fix-budget-exhausted` for pre-ship callers.
- Cover configured-order selection and attempted-tier tracking through `next_untried_tier()` with the actual Claude, Codex, and Cursor presence flags passed through.
- Cover timeout, missing binary, authentication/preflight failure, launcher failure, and exit-zero no-op advancement to the next available tier within one lint-fix invocation.
- Cover useful worktree, index, untracked, committed, and already-dirty-path content deltas from successful and non-zero/timeout attempts. Verify they stop further dispatch and cause the checks loop to rerun.
- Cover all-tools-unavailable before dispatch, budget exhaustion, and full attempted-tier exhaustion for pre-ship sites. Verify each returns its exact named non-structural terminal failure, propagates through `FixOutcome` and `LoopResult`, emits `NEXT_ACTION=stall`, emits `FAILURE_REASON=<named token>`, emits `LINT_FIX_TIER_LEDGER_PATH`, returns non-zero, and does not emit a main-agent escalation ledger.
- Cover terminal stall envelopes for Step 3, Step 6, and Step 5 durable-bail paths so routing cannot lose the named reason or evidence pointer.
- Replace stale tests that expect Step 3, Step 5, or Step 6 exhaustion and no-change outcomes to produce `NEXT_ACTION=main-agent-edit`.
- Add explicit ship-pr regression tests proving `ship-pr-ci-*` zero-tool, dispatch-failure, and exhaustion outcomes retain the existing `main-agent-required` plus `NEEDS_USER_SHIP_PR_INTERNAL_LINT_FIX` handoff contract.
- Retain and extend tests for structural-ruff, complexity-baseline, forbidden paths, invalid logs, repository-state capture failures, isolated-attempt artifact failures, and redaction failures to prove they remain fail-closed and retain the structural main-agent route where applicable.
- Assert each dispatched tier receives a distinct attempt run directory and that per-tier launcher logs, redacted-log validation, and execution-issue records remain associated with the correct attempt.
- Assert the tier-ledger artifact has one ordered row per dispatched tier, uses the defined bounded/redacted columns, persists all earlier attempts through final repair-loop output, and is exposed through `LINT_FIX_TIER_LEDGER_PATH`.
- Assert anomalous failures create categorized execution-issue records without raw prompt or check payload text.

### UPDATED: scripts/test-implement-structure.sh

- Replace assertions that require generic checks-repair `NEXT_ACTION=main-agent-edit` handling.
- Require the reference and Step 5 prose to distinguish explicit structural escalation from the three named exhausted pre-ship waterfall stall routes.
- Require the reference to preserve the existing ship-pr internal handoff as outside the pre-ship stall remapping.
- Require Step 6 `continue` re-entry to retain `--force-checks true`.
- Forbid prose that directs inline main-agent edits after pre-ship `LOOP_STATUS=exhausted`, `LOOP_STATUS=no-changes-stale`, or any named non-structural delegated-waterfall exhaustion reason.
- Require pre-ship stall documentation to retain both `FAILURE_REASON` and `LINT_FIX_TIER_LEDGER_PATH` as terminal evidence.
- Keep existing checks that prevent duplicated repair-loop orchestration and bare Step 6 launchers.

### UPDATED: scripts/test-implement-fence-shape.sh

- Add checks-related assertions that the SKILL keeps repair-loop execution behind the existing macro/reference instead of adding inline Bash orchestration.
- Preserve `EXPECTED_OLD` and `EXPECTED_NEW` if the SKILL prose changes do not alter Bash fence shape. Update them only if an unavoidable in-scope fence change changes the counted shape.

### UPDATED: docs/configuration-and-permissions.md

- Clarify that pre-ship lint-fix gives each configured tier the shared 1800-second timeout and reserves a complete lane from the derived waterfall budget before every dispatch.
- Clarify that normal capture, validation, and evidence-writing overhead does not consume another tier’s reserved launcher lane, so configured tiers remain eligible for their full timeout.
- Document that failed and no-op pre-ship tiers advance, while useful validated edits return to checks.
- Document that per-tier attempt evidence is retained in bounded, redacted ledgers with isolated attempt artifacts and that anomalous failures create execution-issue evidence.
- Remove the statement that the pre-ship waterfall ends in generic `main-agent-required`. State that pre-ship `lint-fix-no-selectable-tier`, `lint-fix-budget-exhausted`, and `lint-fix-all-tiers-no-useful-delta` terminal outcomes stall with `FAILURE_REASON` and `LINT_FIX_TIER_LEDGER_PATH`, while explicit structural failures remain fail-closed.
- State that this pre-ship behavior does not change CI recovery or Step 8 ship-pr policy.

## Edge cases

- Some configured tools may be absent. Pass actual binary-presence flags to selection; for pre-ship sites, zero selectable tiers produce `lint-fix-no-selectable-tier` and stall, while `ship-pr-ci-*` retains its existing internal handoff.
- A launcher may time out or fail after editing files. Capture, inspect, and validate the delta before deciding to advance.
- A tier may create only forbidden or structurally unsafe edits. Reject it through the existing guard and stop fail-closed.
- A tier may commit, modify tracked files, alter the index, add or alter untracked files, or combine these forms. Detect all supported delta shapes, including content changes to paths that were dirty before dispatch.
- Pre-existing dirty paths must not be mistaken for a tier’s useful delta, but a tier’s content change to those paths must be accepted as useful work.
- A successful tier may make no changes. Record the no-op and continue without rerunning checks.
- Earlier full-lane attempts plus normal between-tier overhead must not prevent the final configured tier from receiving its own full lane timeout.
- The reservation pool must not launch a tier unless it can reserve one complete lane timeout.
- Every dispatched tier must have isolated launcher/log artifacts so later attempts cannot overwrite prior evidence or make a ledger row point at another tier’s logs.
- Redacted log validation failures must never enter another tier or leak raw check output into ledgers or execution issues.
- The ledger must retain every dispatched tier in order even when the final outcome is a pre-ship stall or a structural failure.

## Failure modes

- If tier-selection state is invalid, fail loudly rather than silently restarting or skipping a tier.
- If repository state cannot be captured or verified after dispatch, return a structural failure and do not accept the edits.
- If an isolated per-attempt run directory or required bounded evidence cannot be created or validated, record the failure through the existing execution-issue path where possible and do not convert an unsafe result into success.
- If per-tier evidence cannot be written, record the failure through the existing execution-issue path where possible. Do not convert an unsafe result into success.
- If all pre-ship tiers are unavailable or attempted without useful edits, or if lane reservation prevents another dispatch, emit only the matching named non-structural terminal failure and `NEXT_ACTION=stall`, with `FAILURE_REASON` and `LINT_FIX_TIER_LEDGER_PATH`. Never fall through to `NEXT_ACTION=main-agent-edit`.
- Preserve the current `ship-pr-ci-*` internal-lint-fix handoff for equivalent ship-pr failures.
- Preserve existing argument-validation and callback `OSError` stall envelopes.

## Testing strategy

- Run the focused Python tests for `python/tests/implement/test_checks.py`.
- Run focused lint and type checks for `python/larch/implement/checks_lint_fix.py`, `python/larch/implement/checks_run_relevant.py`, and the changed test module.
- Run `scripts/test-implement-structure.sh`.
- Run `scripts/test-implement-fence-shape.sh`.
- Run Markdown lint on the three changed documentation and skill files.
- Verify targeted tests cover result-model propagation, retained structural main-agent routing, pre-ship named non-structural exhaustion, and the unchanged ship-pr internal-handoff route.
- Confirm tests prove full-lane prior attempts plus ordinary orchestration overhead cannot starve the final configured tier.
- Confirm tests prove each attempted tier has non-overwriting isolated artifacts and correctly associated execution-issue evidence.
- Confirm no changed Step 8 files or Step 8 assertions appear in the implementation diff.

## Scope controls

- Do not change `python/larch/core/config.py` or `python/larch/core/external_defaults.py`; Piece 1 already provides the required constants, budget helper, and selector.
- Do not add fixer roles, change tool order, or change model selection.
- Do not alter Step 8 CI fixer orchestration, ship-pr CI recovery, or the `ship-pr-ci-*` internal-handoff contract.
- Do not weaken structural, forbidden-path, redaction, tmpdir, repository-state, or artifact-isolation validation.
- Do not add an inline main-agent fallback after pre-ship waterfall exhaustion.

difficulty: HARD
diff_added: 490
diff_deleted: 155
mechanical_churn: false
oversize_override: operator
diff_lines: 645
