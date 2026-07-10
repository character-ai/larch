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

### FINDING_5: Step 5 MAV/coder durable-bail routing must survive the stall remap
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: Rewriting pre-ship exhaustion as `NEXT_ACTION=stall` can accidentally route `step5-mav` or `coder-main-agent-required` terminal stalls through generic Step 18 handling, dropping the existing `--record-only` plus Durable Bail path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: A explicit preserve directive: keep the Step 5 MAV/coder `NEXT_ACTION=stall` durable-bail paragraph unchanged when editing section 4; add a structure-test needle requiring it
  - From Cursor-Pragmatic: In the new site-routing table, list step5-mav and coder paths separately: stall remains the repair-loop action, but orchestrator handling stays the existing durable-bail paragraph; add a structure-harness assertion that this override survives the exhausted-to-stall remap

### FINDING_6: Recoverable no-delta attempts must restore their pre-dispatch state
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: Continuing to the next tier after timeout, launcher failure, or no useful change without restoring the captured attempt baseline can leave partial edits, index changes, `HEAD` changes, or untracked files behind. Those remnants can pollute later tiers and produce false useful-delta detection or incorrect exhaustion outcomes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: After classifying a recoverable tier as no useful delta, restore the captured pre-dispatch snapshot (tracked, index, untracked, HEAD) before calling next_untried_tier(); keep fail-closed behavior for structural/forbidden/integrity failures without silent acceptance

### FINDING_7: Each waterfall tier needs isolated run and log artifacts
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: Dispatching multiple tiers inside one `run_lint_fix` invocation while reusing a single `run_dir` can overwrite `claude-lint-fix.txt`, `codex.log`, and `cursor.log`. Ledger rows and execution-issue records may then point to the wrong tier's artifacts or misclassify failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Create a fresh per-attempt run_dir (or sequence-suffixed log paths) for every dispatched tier; bind ledger rows and execution-issue pointers to that attempt's artifacts.

### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/implement/checks_lint_fix.py:685-703
- **Concern**: [SCOPE-REDUCTION] Per-tier content baselines should reuse existing digest capture instead of new parallel machinery. Scenario: The plan requires content-aware dirty-path detection, but `_delta_paths_after_dispatch()` compares path membership only; adding a second bespoke digest scheme duplicates `dispatch_helpers._write_prelaunch_digests()` already used for pre-dispatch content snapshots
- **Proposed resolution**: Reuse or factor the existing SHA-256 digest helper for per-tier pre/post snapshots on already-dirty tracked and untracked paths; treat content hash change as useful delta
