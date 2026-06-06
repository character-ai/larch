### FINDING_1: Step 0 parent rehydration snippet is missing the outer `fi`
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements, Codex-Arch, Codex-Edge, Codex-Pragmatic, Codex-Requirements, Cursor-Edge, Cursor-dyn-shell-fence-flow, Cursor-dyn-contract-sync, Cursor-Innovation, Cursor-dyn-harness-wiring, Cursor-dyn-scope-control, Codex-dyn-shell-fence-flow, Codex-dyn-harness-wiring, Codex-dyn-contract-sync
- **Severity**: important
- **Concern**: The planned Step 0 parent rehydration block opens an outer `if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ]; then` but only closes the nested `plugin-root.env` check, leaving both initial and dirty-tree resume Step 0 Bash fences syntactically invalid before routing parse can run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements: Close the outer if before export: after the inner fi add fi, then export CLAUDE_PLUGIN_ROOT (initial and dirty-tree resume insertion points)
  - From Codex-Arch, Codex-Edge, Codex-Pragmatic, Codex-Requirements: Close the outer if before export CLAUDE_PLUGIN_ROOT in the proposed block.
  - From Cursor-Edge, Cursor-dyn-shell-fence-flow, Cursor-dyn-contract-sync: Close the outer `if` before `export CLAUDE_PLUGIN_ROOT` (export should run unconditionally after the conditional source)
  - From Cursor-Innovation, Cursor-dyn-harness-wiring: Add fi before export CLAUDE_PLUGIN_ROOT so the block reads: outer if → parse _inv_tmpdir → inner if source plugin-root.env → fi → fi → export CLAUDE_PLUGIN_ROOT
  - From Cursor-dyn-scope-control: Add the missing closing fi for the outer if before export CLAUDE_PLUGIN_ROOT and verify both initial and resume fences shellcheck clean
  - From Codex-dyn-shell-fence-flow: Add the missing outer `fi` before `export CLAUDE_PLUGIN_ROOT` in both proposed insertions; keep `export CLAUDE_PLUGIN_ROOT` outside the guard.
  - From Codex-dyn-harness-wiring: Add the missing outer fi before export CLAUDE_PLUGIN_ROOT, leaving export outside the if so already-set values are exported too
  - From Codex-dyn-contract-sync: Add the closing fi before export CLAUDE_PLUGIN_ROOT in both inserted blocks, or use a one-line guarded source form

### FINDING_2: Step 5 fence merge desynchronizes pinned rehydration guard counts
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Cursor-Pragmatic, Cursor-dyn-harness-wiring, Codex-Pragmatic, Cursor-dyn-scope-control, Cursor-dyn-shell-fence-flow, Codex-dyn-shell-fence-flow, Codex-dyn-harness-wiring, Codex-dyn-contract-sync
- **Severity**: important
- **Concern**: The Step 5 fence merge changes the canonical plugin-root rehydration guard structure, likely reducing the exact `plugin-root.env` source-guard count from 42 to 41 and possibly adding a new loud guard, while the timing rehydration harness and adjacent SKILL.md prose still pin the old cardinality.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Update the literal expected count and adjacent SKILL.md count text to 41 as part of the same Step 5 edit.
  - From Codex-Edge: Update the expected plugin_root_source_count to the post-change count, or keep the guard cardinality unchanged if that is intentional
  - From Cursor-Pragmatic, Cursor-dyn-harness-wiring: Decrement pinned guard count to 41 and update skills/implement/SKILL.md:115 site-count prose in the same PR
  - From Codex-Pragmatic: Update the expected count and matching SKILL.md prelude count, or preserve the guard count intentionally
  - From Cursor-dyn-scope-control: Omit the new : guard (canonical plugin-root.env source is enough post-Step-0) or extend test-implement-timing-rehydration.sh in the same PR with updated pinned counts
  - From Cursor-dyn-shell-fence-flow: Add `scripts/test-implement-timing-rehydration.sh` to the plan (expected count 41, or document why 42 still holds); or retain a second guard line in the merged fence if the count must stay 42
  - From Codex-dyn-shell-fence-flow: Add `scripts/test-implement-timing-rehydration.sh` and the Bash prelude count line to the plan, lowering the expected/source-site count to 41.
  - From Codex-dyn-harness-wiring: Update the expected plugin_root_source_count and sibling cardinality prose to the new count, or keep two guards if preserving 42 is intentional
  - From Codex-dyn-contract-sync: Add scripts/test-implement-timing-rehydration.sh to the plan and update the expected count, and the SKILL prelude count if kept, to the final count after the merge likely 41

### FINDING_3: New `test-append-execution-issue` target lacks explicit shard wiring
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-dyn-harness-wiring, Cursor-dyn-contract-sync
- **Severity**: important
- **Concern**: The plan adds a `test-append-execution-issue` Makefile target but does not name the concrete `test-harnesses-N` shard, risking `test-harness-shards-coverage` failure and unclear implementation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add test-append-execution-issue to a specific test-harnesses-N line (e.g. test-harnesses-14) and .PHONY in the plan
  - From Cursor-dyn-harness-wiring: Name the shard explicitly (e.g. test-harnesses-14 alongside test-append-tool-failure) in the Makefile ### UPDATED section
  - From Cursor-dyn-contract-sync: Name the target shard explicitly (e.g. `test-harnesses-14` alongside `test-append-tool-failure`) in the Makefile subsection

### FINDING_4: Step 0 export can leave `CLAUDE_PLUGIN_ROOT` empty
- **Reviewer(s)**: Cursor-dyn-shell-fence-flow
- **Severity**: latent
- **Concern**: Even after the rehydration conditional runs, the block can export an empty `CLAUDE_PLUGIN_ROOT` if `plugin-root.env` is missing or empty, causing the later parse-bootstrap source to fail opaquely.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-shell-fence-flow: Gate `export` on `[ -n "${CLAUDE_PLUGIN_ROOT:-}" ]` after sourcing, or abort with the same loud `:?` pattern used elsewhere in Step 0/Step 5 fences

### FINDING_5: Step 5 banner environment precedence conflicts with implementation
- **Reviewer(s)**: Cursor-dyn-harness-wiring
- **Severity**: important
- **Concern**: The planned Step 5 banner derives `dynamic_archetypes_cap` from `session-env` before ambient `LARCH_DYNAMIC_ARCHETYPES_MAX`, which conflicts with `review-and-fix.sh` precedence and the plan’s failure-mode description.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-harness-wiring: Reorder banner derivation to ambient env before session-env (or drop ambient and match run-step5-review.sh session-env-only forwarding)

### FINDING_6: New harness is missing from docs/linting.md
- **Reviewer(s)**: Cursor-dyn-harness-wiring
- **Severity**: nit
- **Concern**: The new `test-append-execution-issue` harness is not listed in `docs/linting.md`, leaving contributor-facing harness documentation stale.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-harness-wiring: Add test-append-execution-issue row to docs/linting.md in the same PR as the Makefile target

### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:311-318,380-388
- **Concern**: [SCOPE-REDUCTION] Step 0 parent rehydration expands the SKILL.md surface beyond the approved Step 5-only edit and contradicts the plan's own "No Step 0 SKILL fallback" statement. Scenario: The PR would touch two Step 0 bootstrap fences and introduce a new plugin-root sourcing path that is not part of the SIMPLE approved scope; as written in the plan, that block is also syntactically incomplete because the outer if lacks a closing fi
- **Proposed resolution**: Drop the Step 0 parent rehydration edit and keep the wrapper self-derive/export fix plus its harness/doc updates; only add a separate tested Step 0 fence change if a post-bootstrap parent-parse failure is reproduced

### FINDING_8:
- **Reviewer(s)**: Cursor-dyn-scope-control
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:298-318
- **Concern**: [SCOPE-REDUCTION] Item 1 leaves pre-bootstrap invoke paths using empty ${CLAUDE_PLUGIN_ROOT}. Scenario: Wrapper self-derive runs only after the script is invoked; on initial Step 0 IMPLEMENT_TMPDIR and plugin-root.env are absent so lines 302-308 expand to /scripts/... and fail before the wrapper self-derive path runs
- **Proposed resolution**: Prefer the issue's cheaper alternative: one template-expanded export CLAUDE_PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-<plugin-root>}" at the top of each Step 0 fence (plus wrapper self-derive); drop post-invoke _inv_out parsing unless still needed after that

### FINDING_9:
- **Reviewer(s)**: Cursor-dyn-scope-control
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:42-59
- **Concern**: [SCOPE-REDUCTION] Step 0 parent-shell rehydration exceeds approved SKILL surface (outline limited changes to Step 5 banner). Scenario: Two new post-invoke blocks duplicate logic across initial and dirty-tree resume fences and expand acceptance beyond the approved outline surfaces
- **Proposed resolution**: Limit SKILL.md Item 1 to a single pre-invoke export line (or document explicit outline amendment); avoid dual-fence _inv_out KV scraping if the template export satisfies parent and child

### FINDING_10:
- **Reviewer(s)**: Cursor-dyn-scope-control
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:145-186
- **Concern**: [SCOPE-REDUCTION] Step 5 edit merges telemetry, dynamic_archetypes_cap derivation, validation, banner printf, and launcher—beyond Item 4's degraded-round CLI need. Scenario: ~40 lines of new fence bash reimplements banner math the issue scoped to prior_degraded_rounds; increases timing-rehydration and structure regression surface for cosmetic copy
- **Proposed resolution**: Keep the lib --count-prior-degraded CLI; either retain prompt-side dynamic_archetypes_cap with a minimal one-line banner fence, or add a narrow run-step5-review.sh --print-banner-values probe instead of inlining full cap precedence in SKILL.md

### FINDING_11:
- **Reviewer(s)**: Codex-dyn-scope-control
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:298-318,364-388
- **Concern**: [SCOPE-REDUCTION] Proposed Step 0 parent-shell rehydration is outside the approved Step 0 surface and the inserted block is missing the outer fi. Scenario: The new Step 0 fence would parse as an unterminated if before routing-envelope parsing; even if fixed, it adds caller fallback behavior the approved outline excluded
- **Proposed resolution**: Remove the Step 0 SKILL.md insertion and keep item 1 to implement-bootstrap-invoke.sh self-derive/export only; if retained despite scope, add the missing fi before export

### FINDING_12:
- **Reviewer(s)**: Codex-dyn-scope-control
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:770-790; scripts/test-implement-timing-rehydration.sh:142-156
- **Concern**: [SCOPE-REDUCTION] Proposed Step 5 rewrite merges telemetry and review launch fences even though item 4 only needs replacing prompt-side banner derivation. Scenario: Deleting one existing plugin-root.env source guard drops the pinned guard count from 42 and makes make test-implement-timing-rehydration fail unless extra test churn is added
- **Proposed resolution**: Leave the telemetry fence at skills/implement/SKILL.md:770-775 intact; only replace the prompt-side banner prose and extend the existing run-step5-review fence to compute and print the banner via the new CLI before invoking run-step5-review.sh
