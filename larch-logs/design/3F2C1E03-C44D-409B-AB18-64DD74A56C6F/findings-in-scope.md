### FINDING_1: Design Step 5c happy path still emits only the cost line
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Codex-Edge, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-callsite-scanner, Codex-dyn-callsite-scanner, Cursor-dyn-path-existence-verifier
- **Severity**: important
- **Concern**: The plan misses `skills/design/SKILL.md` Step 5c item 10, which independently keeps the happy-path `/design` post-publish flow on a cost-line-only top-chat emit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add item 10 to UPDATED list; replace with full-body verbatim + non-empty gating matching ~288
  - From Cursor-Edge: Add Step 5c item 10 to the design SKILL.md edit list: replace cost-line-only language with the same full-body verbatim contract and non-empty gate used at line ~288
  - From Codex-Edge: Update Step 5c item 10 to use the same non-empty final-summary.md full-body verbatim emission contract as the Final summary block fence
  - From Cursor-Innovation: Add a fourth edit: replace item 10’s `contains - **Cost**:` / `emit that single verbatim cost line` with non-empty `final-summary.md` + full-body verbatim emit, aligned with the post-publish fence
  - From Codex-Innovation: Replace item 10’s final sentence with the same non-empty full-body verbatim emit rule, or remove the duplicate local instruction and explicitly refer to the `### Final summary block` top-chat contract
  - From Cursor-Pragmatic: Add Step 5c item 10 to the design edit list; mirror the full-body verbatim emit + non-empty gate used at line 288
  - From Codex-Pragmatic: Update Step 5c item 10 in the plan to emit the non-empty final-summary.md full body verbatim, not just the Cost line
  - From Cursor-Requirements: Add Step 5c item 10 to the design SKILL.md edit list: replace the cost-line-only sentence with the same full-body verbatim read/emit contract and non-empty file gate used at the other sites
  - From Codex-Requirements: Add Step 5c item 10 to the plan, replacing cost-line-only instruction with non-empty final-summary.md full-body verbatim emission, and add a negative/positive test pin covering this exact callsite
  - From Cursor-dyn-callsite-scanner: Add a fourth design edit for item 10: require full-body verbatim emit from $DESIGN_TMPDIR/final-summary.md (non-empty gate per edge cases) and add a matching grep pin in test-render-cost-line-callsites.sh
  - From Codex-dyn-callsite-scanner: Add this callsite to the skills/design/SKILL.md updates and replace it with the same non-empty final-summary.md full-body verbatim emission contract.
  - From Cursor-dyn-path-existence-verifier: Add a fourth edit at Step 5c item 10 mirroring the full-body verbatim contract and non-empty gate used at ~288

### FINDING_2: Implement anti-halt terminal boundary still says cost-line-only
- **Reviewer(s)**: Cursor-Arch, Codex-Edge, Codex-Innovation, Cursor-dyn-callsite-scanner, Codex-dyn-callsite-scanner, Codex-Pragmatic
- **Severity**: important
- **Concern**: The top-level `/implement` terminal-boundary instruction at `skills/implement/SKILL.md:14` still tells the orchestrator to emit only the mandatory cost line after Step 17, conflicting with the planned full-body summary contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Update terminal boundary to full-body verbatim emission per Step 17
  - From Codex-Edge: Update the terminal boundary clause to say Step 17 follows NEVER #20 by emitting the full summary-final.md body verbatim, then continuing to Step 18
  - From Codex-Pragmatic: Update the terminal boundary sentence to reference NEVER #20's full-body verbatim summary emission

### FINDING_3: Emit gates remain tied to Cost-line presence instead of non-empty summary files
- **Reviewer(s)**: Cursor-Arch, Cursor-dyn-callsite-scanner, Cursor-dyn-path-existence-verifier
- **Severity**: important
- **Concern**: Several planned emit sites still key off `- **Cost**:` even though the intended edge-case contract is to emit any non-empty persisted summary body. Cost-absent but otherwise valid summaries can be skipped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Replace `- **Cost**:` gate with non-empty file gate at ~288, ~30, 982, ~1021
  - From Cursor-dyn-callsite-scanner: Replace Cost-line presence preconditions with non-empty file checks at all orchestrator emit sites; keep .step17-printed touch on Cost only if intentional
  - From Cursor-dyn-path-existence-verifier: Change post-publish gating from `contains a line beginning with - **Cost**:` to `[ -s "$DESIGN_TMPDIR/final-summary.md" ]` consistently at ~288 and item 10

### FINDING_4: Implement Step 17/18 mechanics remain cost-line based
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Edge, Codex-Innovation, Codex-Pragmatic, Codex-Requirements, Cursor-dyn-callsite-scanner, Codex-dyn-callsite-scanner, Cursor-dyn-path-existence-verifier, Codex-dyn-path-existence-verifier, Codex-dyn-test-pin-exactness
- **Severity**: important
- **Concern**: The plan updates prose toward full-body summary emission, but the Step 17/18 Bash snippets still mark printed state and detect re-emits using only cost-line presence or cost-line deltas. Non-cost summary changes can be missed, and non-empty summaries without a Cost line are handled inconsistently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Unify gating on non-empty summary-final.md or split render vs top-chat sentinels
  - From Cursor-Arch: Add full-file `cmp -s` (or body snapshot vars) beside `_wfr_prev_cost`/`_wfr_new_cost`
  - From Cursor-Arch: Touch `.step17-printed` only after orchestrator emit succeeds, or add separate top-chat sentinel
  - From Codex-Arch: Update the plan to modify the Step 17/18 Bash snippets too: mark the sentinel based on non-empty summary-final.md after the orchestrator full-body emit, snapshot the full pre-Step-18 body, compare with cmp -s after rerender, and rename variables from cost to summary/body to match the contract
  - From Codex-Edge: Revise the Step 18 Bash block to copy or hash summary-final.md before render, compare the full post-render body with cmp -s or equivalent, and update tests to pin full-body comparison instead of _wfr_prev_cost / _wfr_new_cost
  - From Codex-Innovation: Update the Step 18 fenced Bash to snapshot/cmp the whole `summary-final.md` body, set an `_wfr_emit_body` guard, and touch `.step17-printed` only when a non-empty body was emitted; update all old cost-guard pins, not only the prose pins
  - From Codex-Pragmatic: Update the Step 18 block to snapshot summary-final.md before render, compare the full post-render body with cmp -s or equivalent, and gate the full-body emit/touch on non-empty body plus body changed or Step 17 missing
  - From Codex-Requirements: Update these snippets to snapshot and compare the whole summary-final.md with cmp -s or equivalent, gate markers on non-empty file body, and update the callsite harness to fail on remaining _wfr_prev_cost/_wfr_new_cost-only logic
  - From Cursor-dyn-callsite-scanner: Scope Bash refactor: snapshot summary-final.md before Step 18 render, cmp -s after, drive _wfr_emit_cost from full-body diff; align variable names and test pins
  - From Codex-dyn-callsite-scanner: Explicitly update these snippets in the plan: gate Step 17 printed state on a non-empty summary-final.md, snapshot the full body before Step 18, compare the full body after render with cmp or equivalent, and rename cost-specific variables.
  - From Cursor-dyn-path-existence-verifier: Rewrite the Step 18 Bash block to snapshot full `$IMPLEMENT_TMPDIR/summary-final.md` (e.g. `cp` to a pre-step18 sentinel) and set emit/print flags with `cmp -s` on full bodies; align `.step17-printed` touch with the new emit guard
  - From Codex-dyn-path-existence-verifier: Update the Step 18 Bash block to snapshot/compare $IMPLEMENT_TMPDIR/summary-final.md as a full file, then update the test pins at scripts/test-render-cost-line-callsites.sh:40-44 to assert the new body-compare mechanism instead of cost-only variables
  - From Codex-dyn-test-pin-exactness: Revise the plan to update all relevant exact pins: replace the Step 17 cost-line gate with a non-empty summary-final.md/body-emitted sentinel check, replace _wfr_emit_cost/_wfr_prev_cost/_wfr_new_cost pins with full-body snapshot/cmp wording, and keep the new prose pins synchronized with the SKILL.md edits.

### FINDING_5: Test harness still pins old cost-line mechanics and lacks negative coverage
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Pragmatic, Cursor-dyn-callsite-scanner, Cursor-dyn-path-existence-verifier, Codex-dyn-path-existence-verifier, Cursor-dyn-test-pin-exactness, Codex-dyn-test-pin-exactness
- **Severity**: important
- **Concern**: `scripts/test-render-cost-line-callsites.sh` is planned to add or replace some positive prose pins, but still leaves old cost-line mechanical pins and lacks negative greps proving retired cost-line-only instructions are absent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add negative greps plus pins for design:982, design anti-halt, implement:14
  - From Codex-Arch: Update the plan to replace these assertions with full-body assertions: Step 17 gates printed/emitted state on non-empty summary-final.md, Step 18 snapshots and compares the full body, and emit guards no longer depend on _wfr_new_cost/_wfr_prev_cost
  - From Codex-Pragmatic: Update these assertions to pin non-empty summary body detection and full-body snapshot/compare behavior instead of Cost-line grep and _wfr_*_cost variables
  - From Cursor-dyn-callsite-scanner: Either extend plan to refactor Step 18 Bash to full-body snapshot/cmp and update pins 37-44 and 49, or explicitly mark bash mechanics out-of-scope and add pins asserting absence of old cost-line-only orchestrator prose site-wide
  - From Cursor-dyn-path-existence-verifier: Extend the test update section to replace lines 40-44 with pins for the new Step 18 snapshot/`cmp -s` logic and drop cost-line-only `_wfr_*` greps
  - From Cursor-dyn-test-pin-exactness: Add negative pins mirroring test-design-structure.sh:350-353 (if grep -Fq old_prose; then fail) for each retired substring: emit exactly that one line, emit that single verbatim, single extracted - **Cost**:, The cost line is the sole exception, orchestrator emits the single verbatim cost line
  - From Codex-dyn-test-pin-exactness: Add explicit negative greps that fail if the old cost-line-only prose remains in design or implement SKILL.md, covering the anti-halt, post-publish/Step 17, Step 18, and NEVER #20 callsites.

### FINDING_6: Harness documentation remains cost-line oriented
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Requirements
- **Severity**: nit
- **Concern**: The plan changes the behavior enforced by `test-render-cost-line-callsites.sh` but leaves sibling docs and the linting catalog describing the old cost-line/render-cost-line contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Update scripts/test-render-cost-line-callsites.md and the docs/linting.md row to describe the full-body final-summary callsite contract and keep any remaining render-cost-line allowlist wording explicitly scoped to the deprecated standalone helper
  - From Codex-Innovation: Update the sibling doc and pass/fail wording to describe full-block summary callsite contracts, even if the filename is left unchanged for diff size
  - From Codex-Requirements: Update the .md sibling and docs/linting.md target row to describe full-summary body callsite pins and the remaining render-cost-line allowlist separately

### FINDING_7: Stale design vocabulary can preserve a cost-line-only anchor
- **Reviewer(s)**: Cursor-dyn-callsite-scanner
- **Severity**: nit
- **Concern**: `skills/design/SKILL.md:1021` may retain “mandatory verbatim cost-line emit” wording after partial edits, leaving contradictory vocabulary next to updated full-body ordering prose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-callsite-scanner: Rename to mandatory verbatim full-block emit (or equivalent) in the same edit pass as the single extracted line replacement

### FINDING_8: Step 18 needs a durable pre-refresh body snapshot
- **Reviewer(s)**: Cursor-dyn-path-existence-verifier
- **Severity**: important
- **Concern**: The plan requires byte-for-byte Step 18 body comparison but does not specify how prompt-side/orchestrator logic obtains the pre-refresh `summary-final.md` body across the fenced Bash boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-path-existence-verifier: Specify a durable pre-step18 snapshot path (written in the Bash fence before refresh) and require orchestrator emit only when `cmp -s` against refreshed `summary-final.md` fails or `.step17-printed` was absent

### FINDING_9: Step 18 no-summary sentence conflicts with refreshed full-body emit
- **Reviewer(s)**: Cursor-dyn-path-existence-verifier
- **Severity**: latent
- **Concern**: `skills/implement/SKILL.md:1764` still says Step 18 emits no token/timing summary to chat, which can conflict with the proposed Step 18 refreshed full-body top-chat emit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-path-existence-verifier: Replace line 1764 with language that Step 18 may emit the verbatim refreshed `summary-final.md` body under the Step 18 dual-condition guard only

### FINDING_10: Implement overview names the wrong tmpdir final summary path
- **Reviewer(s)**: Codex-dyn-path-existence-verifier
- **Severity**: nit
- **Concern**: The implement overview refers to tmpdir `final-summary.md`, while the canonical observed tmpdir output is `summary-final.md`; `larch-logs/implement/<RUN_ID>/final-summary.md` is a separate persisted artifact.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-path-existence-verifier: Add a small SKILL.md line-10 edit to distinguish $IMPLEMENT_TMPDIR/summary-final.md from larch-logs/implement/<RUN_ID>/final-summary.md
