### FINDING_1: Preserve fallback-phase failure accounting when relaxing static dispatch failure handling
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: Relaxing `STATIC_DISPATCH_OK` short-circuiting can omit Claude fallback/static phase failures from failed-slot threshold accounting, allowing a partially failed panel to be reported clean.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Keep the relaxation narrowly scoped to no-fallback dropped-peer cases with DROPPED_SLOTS_FILE, or add explicit phase2/phase3 failed static rows from waterfall/Claude outputs into the threshold input before removing the STATIC_DISPATCH_OK short-circuit


### FINDING_2: Dropped slots are counted but not surfaced or preserved for operators
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Concern**: Dropped no-fallback reviewer rows may be included in threshold math but remain silent in operator-facing diagnostics/log artifacts, making lost reviewer coverage hard to debug.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Have review-core consume the forwarded DROPPED_SLOTS_FILE before threshold and append per-slot External Reviewer Issues or persist the sidecar in round logs; keep the proposed threshold counting unchanged


### FINDING_3: Round-log harness assertions conflict with codex-specialist meta exclusion
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan excludes codex-specialist base output sidecars from round logs but does not update tests that still require those `.meta` files, causing the harness to fail after the intended deny change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add test-larch-log-write-round.sh to the plan Files section: flip line 106 to assert_not_file for codex-specialist-*-output.txt.meta (and drop or relocate the line 128 CMD_JSON strip check); keep assert_file only for phased *-output-*.txt.meta if still included; document the parity in scripts/larch-log.md alongside the new deny arm


### FINDING_4: Static archetype coverage can disappear when both same-slug peers drop
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: Threshold-only dropped-slot recovery can allow review to proceed even when both vendor peers for a static archetype fail, leaving an entire specialist coverage area absent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: When overriding STATIC_DISPATCH_OK or running threshold math, fail or degrade when a surviving static archetype has zero successful peer outputs; only treat a dropped peer as recoverable when its same-slug opposite vendor peer succeeded


### FINDING_5: Scout prompt can invite reserved slugs that validator rejects
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: Updating the scout prompt to list only four active static slugs without naming reserved historical slugs can cause generated dynamic archetypes to use reserved names and then fail validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Keep the active-static wording at 4, but also tell the scout that structure and plan-fidelity are reserved historical slugs and must not be emitted; keep this prompt list in sync with the jq reserved list


### FINDING_6: Renderer contract doc must describe reviewer-testing plan injection exception
- **Reviewer(s)**: Codex-Pragmatic, Codex-Requirements
- **Severity**: latent
- **Concern**: The renderer contract documentation would still describe `--plan-file` as diff-mode-only, contradicting the planned reviewer-testing behavior for description mode and non-generic diff modes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Add scripts/render-specialist-prompt.md to the update list and document the reviewer-testing exception for non-generic diff modes and description mode
  - From Codex-Requirements: Add scripts/render-specialist-prompt.md to the plan and document the reviewer-testing-only plan-injection exception for description and non-generic diff modes


### FINDING_7: Mandatory PLAN_FILE guard text still names plan-fidelity
- **Reviewer(s)**: Cursor-dyn-waterfall-contracts
- **Severity**: nit
- **Concern**: After folding plan-fidelity into reviewer-testing, the missing-plan guard message can still claim plan-fidelity is always dispatched, misrepresenting the static panel.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-waterfall-contracts: In the dispatch-panel.sh edit, replace the plan-fidelity wording with reviewer-testing / static-panel plan injection (keep PLAN_FILE required if dispatch still passes --plan-file)


### FINDING_8: Dropped reviewer dirty-tree sidecars are omitted from recovery
- **Reviewer(s)**: Codex-dyn-waterfall-contracts
- **Severity**: important
- **Concern**: No-fallback dropped reviewer outputs can be excluded from dirty-tree recovery inputs, allowing mutations from a failed dropped peer to remain unreverted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-waterfall-contracts: Keep dropped outputs out of collection, but join DROPPED_SLOTS_FILE slot/tool records against PANEL_MANIFEST and pass existing dropped output dirty-tree sidecars through recovery before threshold; avoid changing the shared waterfall TSV unless necessary


### FINDING_9: review-core tests do not prove dropped-slots file reaches threshold checker
- **Reviewer(s)**: Codex-dyn-slot-accounting
- **Severity**: important
- **Concern**: Standalone dispatch and threshold tests can pass even if `review-core` fails to forward `--dropped-slots-file`, leaving dropped no-fallback peers invisible in real review-core threshold math.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-slot-accounting: Add a test-review-core case whose dispatch stub emits DROPPED_SLOTS_FILE and whose threshold stub fails unless it receives --dropped-slots-file with that exact path; keep the existing standalone 1-of-8 and 5-of-8 math tests


### FINDING_10: Prompt-render tests lack non-testing negative coverage for test/generated diff modes
- **Reviewer(s)**: Cursor-dyn-prompt-artifacts
- **Severity**: important
- **Concern**: The planned reviewer-testing plan injection could accidentally leak `<implementation_plan>` into other specialists for test-only or generated-only diffs because current negative assertions cover only docs-only/description cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-prompt-artifacts: Add explicit assert_not_contains cases for reviewer-correctness (or another non-testing agent) with --diff-mode test-only and --diff-mode generated-only plus --plan-file, mirroring the existing docs-only guard


### FINDING_11: Archetype generation rule conflicts with hand-maintained reviewer variants
- **Reviewer(s)**: Codex-dyn-prompt-artifacts
- **Severity**: important
- **Concern**: The path-triggered rule still treats reviewer archetype edits as generated-template changes, conflicting with intentional hand-maintained edits to specialist variants and risking future source-of-truth drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-prompt-artifacts: Update this rule in the plan to distinguish generated agents from hand-maintained specialist variants and mention regenerating agents/pre-rendered bodies after hand-maintained agent edits


### FINDING_12: Quick-mode docs sync harness lacks explicit diagram contract
- **Reviewer(s)**: Cursor-dyn-operator-doc-sync
- **Severity**: important
- **Concern**: The plan references a diagram assertion but does not specify how the sync harness should validate `skills/review/diagram.svg`, so diagram drift could recur while tests stay green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-operator-doc-sync: Add an explicit step: grep `skills/review/diagram.svg` for the canonical phrase `4 specialists per vendor (Cursor + Codex)` (and add `6 Cursor specialists` to `STALE_PHRASES` or a diagram-only negative check); wire it in `run_default` and document it in `scripts/test-quick-mode-docs-sync.md` with a self-test fixture


### FINDING_13: Operator launch breadcrumb must include Codex static count
- **Reviewer(s)**: Cursor-dyn-operator-doc-sync
- **Severity**: important
- **Concern**: Static Cursor/Codex counts are tracked separately, but the operator launch breadcrumb and docs can still report only Cursor static reviewers, misleading both-vendor review debugging.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-operator-doc-sync: Extend the plan to update the breadcrumb to include Codex static count (mirror emitted rows), revise `dispatch-panel.md` line 31, and adjust `test-dispatch-panel.sh` greps accordingly


### FINDING_15: Proposed topology display phrase is rejected by generator validation
- **Reviewer(s)**: Codex-dyn-operator-doc-sync
- **Severity**: important
- **Concern**: The proposed topology value contains parentheses, but the topology generator’s display-text validation rejects that character set, so updating the TSV as planned can break topology generation/checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-operator-doc-sync: Either use a generator-safe topology value and keep `Cursor + Codex` in the composition column, or intentionally allow parentheses in `validate_display_text` and update the generator tests/contracts.


### FINDING_16: Topology ownership contract conflicts with keeping a Step 5 panel row
- **Reviewer(s)**: Codex-dyn-operator-doc-sync
- **Severity**: latent
- **Concern**: The plan keeps a Step 5 review-panel topology row even though generator prose says Step 5 phrases are excluded and owned by quick-mode docs sync, creating conflicting ownership guidance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-operator-doc-sync: Choose one owner. If the topology row stays, rewrite the generator preamble and `.md` out-of-scope section to say quick-mode pins public Step 5 prose while topology also projects the review-panel shape.

