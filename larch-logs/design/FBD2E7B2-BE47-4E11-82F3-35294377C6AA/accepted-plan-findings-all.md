### FINDING_1: Preserve ship-pr-ci internal handoffs through site-gated routing
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: `run_lint_fix` is shared by pre-ship repair-loop sites and `ship-pr-ci-*` callers. Globally remapping no-tools, dispatch failure, or tier exhaustion away from `main-agent-required` would change the existing Step 6/8 ship-pr internal-lint-fix handoff, despite Step 8 being out of scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In `checks_lint_fix.py`, limit non-structural exhaustion remapping to pre-ship sites (`step3`, `step5*`, `step6`); preserve current `main-agent-required` + ship-pr ledger tokens for `ship-pr-ci-*`. Add explicit test bullets retaining ship-pr `run_lint_fix` expectations
  - From Cursor-Innovation: Add an explicit site-routing table: either carve out `ship-pr-ci-*` to keep the existing internal NEEDS_USER handoff, or list the required `ship_result.py`/Step 8 outcome updates and replace the ship-pr ledger tests in `test_checks.py`.
  - From Cursor-Pragmatic: Gate exhaustion and no-tools FixOutcome by site: keep main-agent-required plus NEEDS_USER_SHIP_PR_INTERNAL_LINT_FIX ledger for ship-pr-ci-*; apply stall/no-changes routing only to pre-ship sites


### FINDING_2: Define the non-structural FixOutcome contract
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The plan removes exhaustion-to-`main-agent-edit` routing but does not fully specify replacement statuses for pre-ship no-tools, dispatch-failure, budget-exceeded, and all-tier-exhaustion paths. Existing `main-agent-required` returns can still leak into inline repair through `_handle_fix_outcome` and `_repair_loop_action`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Specify and test: non-structural all-tier exhaustion returns `no-changes` (or another non-`main-agent-required` status) so `run_check_fix_loop` can recheck and reach `no-changes-stale`/`exhausted` → `NEXT_ACTION=stall`; keep structural fast-fail on `main-agent-required`
  - From Cursor-Innovation: Specify the non-escalating `FixOutcome.status` when all configured tiers were attempted with no useful delta (for example `no-changes` so the outer loop can reach `LOOP_STATUS=exhausted`/`NEXT_ACTION=stall`), and add a test replacing `test_run_lint_fix_all_tools_timeout`.
  - From Cursor-Pragmatic: Specify pre-ship non-structural tier exhaustion and no-tools must return no-changes or failed (not main-agent-required); restrict _repair_loop_action main-agent-edit to structural fast-fail failure_reason values only; add tests for step6 no-tools and all-tools-timeout
  - From Cursor-Requirements: In checks_lint_fix.py, state explicitly that only complexity-baseline and structural-ruff fast-fail paths (plus any other named structural cases) may return main-agent-required; map all-tools-unavailable, tier UNAVAILABLE/EXHAUSTED, budget exceeded, and dispatch failure without useful delta to failed (or another non-main-agent-required terminal status) so _repair_loop_action can return stall


### FINDING_3: Handle all-tools-unavailable before the waterfall
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: The pre-loop path where Claude, Codex, and Cursor are all unavailable is not covered by the proposed remapping. It can still return `main-agent-required` before any waterfall attempt and bypass the new stall contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an explicit bullet: for pre-ship sites with zero selectable tiers, return the same non-structural exhausted outcome as tier failure (outer stall), not `main-agent-required`; keep ship-pr internal handoff behavior site-gated per the ship-pr row above


### FINDING_4: Continue across recoverable tier failures and terminate after full exhaustion
- **Reviewer(s)**: Cursor-Requirements, Codex-dyn-Waterfall State Auditor
- **Severity**: major
- **Concern**: Changing tier selection alone may leave `_handle_fix_outcome()` terminating the waterfall on the first failed, timed-out, authentication, launcher, missing-binary, or no-op attempt. The plan must distinguish recoverable per-tier outcomes from structural failures and define the terminal result after all tiers are consumed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: After next_untried_tier reports EXHAUSTED/UNAVAILABLE or the total budget is exhausted with no useful delta, return failed (with failure_reason from Piece 1 selectors) rather than no-changes; reserve no-changes for a single tier that ran cleanly and produced no repo delta before advancing to the next tier inside the same invocation
  - From Codex-dyn-Waterfall State Auditor: Specify distinct recoverable per-tier outcome handling, including timeout, authentication, missing-binary, launcher failure, and no-op, and require `_handle_fix_outcome()` or an equivalent loop-level reducer to continue after those outcomes while stopping only for structural/integrity failures or a useful delta.


### FINDING_5: Detect useful content changes in already-dirty paths
- **Reviewer(s)**: Codex-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: Comparing only path sets cannot detect a useful edit to a file that was already dirty before a tier started. Such edits may be treated as no-ops, causing later tiers to run and checks not to rerun.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Capture baseline worktree and index content for dirty paths, compare it after each tier, and treat content changes beyond that baseline as a useful delta. Add a focused test for a tier editing an already-dirty file.
  - From Codex-Requirements: Revise the plan to distinguish pre-existing dirtiness from new content changes. Capture exact repository state before each tier, detect changes to already-dirty tracked and untracked files, and add a focused test proving such edits stop dispatch and rerun checks


### FINDING_7: Reserve a full lane timeout before dispatch
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Concern**: Checking the total budget only after a tier returns can launch a final tier without enough remaining time for its full configured lane timeout, violating the budget edge case.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: State in `checks_lint_fix.py`: before each `next_untried_tier` dispatch, abort the waterfall when remaining budget is below `config.FIXER_LANE_TIMEOUT_SEC`; add a focused test for the last-tier budget reservation


### FINDING_8: Define durable per-tier ledger and execution-issue persistence
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-dyn-Waterfall State Auditor
- **Severity**: major
- **Concern**: Acceptance requires one bounded, ordered ledger row per attempted tier plus categorized execution-issue evidence, but the plan specifies neither a durable artifact nor its schema, writer, propagation, redaction, or terminal-output contract. Existing scalar `FixOutcome`/`LoopResult` and aggregate stdout fields can lose earlier-tier evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add one plan bullet naming the artifact (for example under `$run_parent` or `$IMPLEMENT_TMPDIR/lint-fix-loop/`) and its column grammar; mirror it in `test_checks.py` assertions
  - From Codex-Arch: Add an explicit per-tier ledger artifact and execution-issue writer contract in the plan. Specify its path, bounded row schema, append/ordering behavior, propagation through `FixOutcome` and `LoopResult`, and redaction guarantees. Extend the focused tests to verify that records from every attempted tier survive through the final repair-loop output.
  - From Cursor-Innovation: Pin a minimal contract: for example append rows to `$IMPLEMENT_TMPDIR/lint-fix-tier-ledger.tsv` (or reuse the `fixer-rounds.tsv` column shape) and, on terminal `NEXT_ACTION=stall`, emit one bounded pointer KV such as `LINT_FIX_TIER_LEDGER_PATH=...` without reviving main-agent escalation ledger semantics.
  - From Codex-Innovation: Specify the per-tier ledger artifact and execution-issue writer contract, including bounded fields, redaction rules, tmpdir location, and how the repair-loop output exposes or preserves those records; add an assertion for the artifact contents and ordering
  - From Cursor-Pragmatic: Define a bounded per-tier artifact (for example lint-fix-loop/lint-fix-tier-ledger.tsv under run_parent) with tier, outcome class, exit code, elapsed, useful_delta columns; keep terminal stdout ledger only for structural main-agent-required
  - From Codex-dyn-Waterfall State Auditor: Define a bounded per-tier ledger artifact and its stdout/path contract, add the corresponding fields or artifact reference to `FixOutcome` and `LoopResult`, and require `_handle_fix_outcome()` plus final routing to preserve all attempted-tier rows.


### FINDING_11: Pass actual binary-presence flags to tier selection
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Concern**: `next_untried_tier` defaults `claude_present=True`, while the caller separately probes binary availability. Without passing those flags through, a missing Claude binary may still be selected after refactoring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: In the UPDATED checks_lint_fix.py bullets, require next_untried_tier(..., claude_present=claude_present, codex_present=codex_present, cursor_present=cursor_present) using the same presence flags already bound for dispatch


### FINDING_1: Result-model propagation is missing from the firm file list
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The plan requires propagating the tier-ledger path and terminal exhaustion reason through `FixOutcome`, `LoopResult`, `_handle_fix_outcome()`, `_repair_loop_action()`, and terminal repair-loop output, but omits `python/larch/implement/checks_run_relevant.py`, where the result dataclasses are defined. Without explicit result-model fields and propagation, the ledger pointer and failure reason can be lost, forcing ad-hoc side channels or preventing the required terminal evidence from being emitted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `python/larch/implement/checks_run_relevant.py` as an updated file and add the bounded ledger-path fields to both result types.
  - From Codex-Arch: Add `python/larch/implement/checks_run_relevant.py` to the plan and specify the new bounded ledger-path fields on both result types, their propagation, and terminal emission.
  - From Cursor-Innovation: Add `### UPDATED: python/larch/implement/checks_run_relevant.py` extending `FixOutcome`/`LoopResult` with bounded `tier_ledger_path` and terminal routing fields consumed by `checks_lint_fix.py` and tests
  - From Codex-Innovation: Include the shared result-model file in the plan, or define an equivalent propagation mechanism. Add fields for the terminal failure reason and tier-ledger path to `FixOutcome` and `LoopResult`, copy them in `_handle_fix_outcome`, and use the reason in `_repair_loop_action` while emitting the path in the repair-loop envelope
  - From Cursor-Pragmatic: Add `### UPDATED: python/larch/implement/checks_run_relevant.py` with tier_ledger_path on FixOutcome, terminal failure_reason on LoopResult, and _handle_fix_outcome/_repair_loop_action wiring that preserves them through repair-loop stdout
  - From Codex-Pragmatic: Add `### UPDATED: python/larch/implement/checks_run_relevant.py` with the minimal ledger-path fields on `FixOutcome` and `LoopResult`; copy the value in existing outcome reduction without changing other callers.
  - From Cursor-Requirements:


### FINDING_2: Full-timeout waterfall budget can prevent the final tier from dispatching
- **Reviewer(s)**: Cursor-Arch, Codex-Requirements
- **Severity**: major
- **Concern**: A total budget equal to `tier_count * FIXER_LANE_TIMEOUT_SEC` does not reserve a full timeout for every configured tier when validation, state capture, ledger writes, classification, and dispatch overhead consume wall-clock time. Earlier tiers can each use their complete timeout while leaving less than one full lane for the final tier, violating the complete-waterfall requirement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Specify budget accounting that excludes orchestration overhead or caps each attempt's charged duration at `FIXER_LANE_TIMEOUT_SEC`, and test full-timeout attempts still leave the final configured tier eligible.
  - From Codex-Requirements: Define budget accounting that excludes between-tier orchestration overhead from lane consumption, or provide bounded overhead headroom while preserving the full-lane pre-dispatch reservation. Add the planned final-tier test with prior tiers consuming their full timeout plus realistic overhead


### FINDING_3: Terminal failure reasons need explicit propagation and a closed pre-ship allowlist
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: `_handle_fix_outcome()` currently collapses failed outcomes into generic statuses and `_repair_loop_action()` lacks a pinned vocabulary for distinguishing recoverable delegated-waterfall exhaustion from structural failures. The plan must preserve the named `failure_reason` and require pre-ship stall routing to match only an explicit non-structural exhaustion set; otherwise exhaustion can still route to `main-agent-edit`, `dispatch-failed`, or an incorrect structural path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add `last_failure_reason` (and tier-ledger path) to `LoopResult`, set them in `_handle_fix_outcome()`, and make `_repair_loop_action()` branch on an explicit pre-ship allowlist of named non-structural exhaustion reasons vs structural routes
  - From Cursor-Pragmatic: Document and implement an explicit pre-ship non-structural set {unavailable, exhausted, lint-fix-budget-exceeded} mapped to stall; reserve main-agent-edit for structural fast-fail reasons and ship-pr-ci-* site-gated handoffs only
  - From Cursor-Requirements: Document the exact terminal failure_reason set in the plan and use only those constants in run_lint_fix returns and _repair_loop_action pre-ship stall routing.
  - From Codex-Innovation: Include the shared result-model file in the plan, or define an equivalent propagation mechanism. Add fields for the terminal failure reason and tier-ledger path to `FixOutcome` and `LoopResult`, copy them in `_handle_fix_outcome`, and use the reason in `_repair_loop_action` while emitting the path in the repair-loop envelope


### FINDING_4: Terminal pre-ship stalls must emit ledger and failure evidence
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: Pre-ship exhaustion is being remapped to `NEXT_ACTION=stall`, but current terminal output emits the tier ledger only for `main-agent-edit` and does not retain or print `FAILURE_REASON`. Without explicit stall-envelope emission, the repair-loop contract loses the authoritative tier-attempt pointer and named exhaustion reason needed by downstream routing and diagnostics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In `checks_repair_loop_main()`, emit `LINT_FIX_TIER_LEDGER_PATH` (and bounded tier-ledger metadata) on pre-ship `NEXT_ACTION=stall`; keep escalation `LINT_FIX_LEDGER_*` keys structural-only
  - From Cursor-Pragmatic: Extend LoopResult/checks_repair_loop_main to print FAILURE_REASON=<named non-structural token> on pre-ship stall alongside LINT_FIX_TIER_LEDGER_PATH; add regression tests that stall envelopes carry the exhaustion token for step3/step6 and step5-mav durable-bail paths


### FINDING_7: Each waterfall tier needs isolated run and log artifacts
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: Dispatching multiple tiers inside one `run_lint_fix` invocation while reusing a single `run_dir` can overwrite `claude-lint-fix.txt`, `codex.log`, and `cursor.log`. Ledger rows and execution-issue records may then point to the wrong tier's artifacts or misclassify failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Create a fresh per-attempt run_dir (or sequence-suffixed log paths) for every dispatched tier; bind ledger rows and execution-issue pointers to that attempt's artifacts.


