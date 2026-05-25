### FINDING_1: `--trivial --brainstorm` upgrade can be lost when Step 0b reparses argv
- **Reviewer(s)**: unknown-slot, Codex-Edge, Codex-Pragmatic
- **Severity**: important
- **Concern**: The proposed Upgrade-to-`--simple` path is only described as prompt-side or mental state, while Step 0b still parses unchanged `$ARGUMENTS` containing `--trivial`. This can persist trivial run params despite the operator selecting the simple brainstorm flow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From unknown-slot: Add an explicit resolved_tier override contract: Pre-Step-0 sets it, Step 0b parser must ignore the original --trivial when it is set, and structural tests should pin the override path
  - From unknown-slot: Define an effective_tier variable set by Pre-Step-0, require Step 0b to use it instead of raw argv tier flags when present, and add a structure or harness check for --trivial --brainstorm upgrade producing simple/full run params
  - From Codex-Edge: Specify that Step 0b must ignore the argv --trivial token when the Pre-Step-0 upgrade flag is set and must bind classification SIMPLE, sketch_budget=2, review_budget=full; add a structural pin for the override wording
  - From unknown-slot: Specify a concrete override variable or rewritten parsed-token list for Step 0b, and update the parser prose/tests to prove --trivial --brainstorm upgraded writes design_classification=SIMPLE, sketch_budget=2, review_budget=full, brainstorm_requested=true
  - From Codex-Pragmatic: Define an explicit tier override that Step 0b must honor when parsing ARGUMENTS, ignoring --trivial and writing SIMPLE/sketch_budget=2/review_budget=full after upgrade


### FINDING_10: Step 1d.5 does not require loading brainstorm prompt tokens
- **Reviewer(s)**: Codex-Edge, unknown-slot
- **Severity**: important
- **Concern**: Step 1d.5 mandates reading `brainstorm.md` but not `brainstorm-prompts.md`, allowing unresolved `<BRAINSTORM_*_PROMPT>` placeholders or invented prompt text.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Add a mandatory read of skills/design/references/brainstorm-prompts.md before prompt-file rendering, mirroring the sketch-prompts.md then sketch-launch.md ordering, and pin it in test-design-structure.sh
  - From unknown-slot: Add a mandatory read of `skills/design/references/brainstorm-prompts.md` before prompt rendering, either in SKILL.md Step 1d.5 or as the first nested directive inside `brainstorm.md`, mirroring the sketch-prompts/sketch-launch contract.


### FINDING_11: Brainstorm context is not fed into required downstream consumers
- **Reviewer(s)**: Codex-Edge, Codex-Innovation, unknown-slot, Codex-Requirements
- **Severity**: important
- **Concern**: The plan conflicts on whether Step 2a and Step 3 consume `brainstorm.md`. Required consumers include sketches and plan review, but the proposed edits leave those paths unchanged or exclude Step 3.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Either add an optional brainstorm.md read into Step 2a sketch prompt context before launches, or remove Step 2a from every brainstorm consumer contract and document that sketches intentionally ignore brainstorm context
  - From Codex-Innovation: Add brainstorm.md as an input to Step 2a prompt rendering when it exists and is non-empty, or write the selected brainstorm decisions into discussion-round1 before Gate A so existing sketch prompt construction sees them
  - From unknown-slot: Add Step 2a changes so sketch prompt rendering/launch context reads non-empty $DESIGN_TMPDIR/brainstorm.md additively, and add structure/manual tests that verify sketch prompts or synthesis include brainstorm context when --brainstorm is set
  - From unknown-slot: Add a Step 3 integration path, such as extending plan-review-loop/dispatch-plan-review-panel/render-plan-review-prompt or the feature context passed to reviewers to include brainstorm.md as untrusted additive context, and add a regression check for that prompt/context path
  - From Codex-Requirements: Revise the plan to update Step 2a prompt rendering/sketch launch context and Step 3 plan-review prompt/driver inputs to include brainstorm.md additively when non-empty, and add validation for those consumers.


### FINDING_12: Brainstorm prompt rendering assumes `discussion-round1.md` exists
- **Reviewer(s)**: Codex-Edge, unknown-slot
- **Severity**: important
- **Concern**: The common Step 1d skip path may not write `discussion-round1.md`, but brainstorm prompt rendering concatenates it unconditionally.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Treat discussion-round1.md as optional in brainstorm.md prompt rendering: read it only when it exists and is non-empty, otherwise render prompts from feature-description.txt alone


### FINDING_13: `--brainstorm` can still pair with a tier-gate-selected trivial tier
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Concern**: The `--trivial --brainstorm` mutex does not cover the case where argv has `--brainstorm` but no tier flag and the Step 0b tier gate lets the user choose trivial.
- **Suggested revisions (informational for voters; coder decides)**:
  - From unknown-slot: When `brainstorm_requested=true`, remove `trivial` from the tier gate or run the same Upgrade-to-simple / Cancel prompt after a trivial tier-gate choice before writing run-params.


### FINDING_14: Foreground marker requirements are underspecified for the brainstorm collector fence
- **Reviewer(s)**: unknown-slot, Codex-dyn-foreground-marker-audit
- **Severity**: important
- **Concern**: The planned `brainstorm.md` collector block names `collect-agent-results.sh` but does not specify the exact foreground banner and in-fence comment positions required by `lint-foreground-markers.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From unknown-slot: Add an explicit collector fence to the NEW skills/design/references/brainstorm.md section with the exact banner line above the opening fence and # Foreground required: see BASH_AUTHORING.md §4 directly before ${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh; state launch-review.sh blocks intentionally keep run_in_background true and need no foreground marker because scripts/lint-foreground-markers.sh does not denylist launch-review.sh
  - From Codex-dyn-foreground-marker-audit: Revise the brainstorm.md plan section to include the literal banner **⚠ Foreground required — do NOT set `run_in_background: true`.** immediately above the collector fence and # Foreground required: see BASH_AUTHORING.md §4 inside the fence within the five preceding lines before every collect-agent-results.sh invocation. Note that launch-review.sh is not in the current lint denylist, so these foreground markers are required for the collector fence, not the background launch fences.


### FINDING_15: Run-params recovery path can drop `brainstorm_requested`
- **Reviewer(s)**: unknown-slot, Codex-dyn-run-params-consumers
- **Severity**: important
- **Concern**: The plan updates the primary writer and jq merge path but underspecifies the no-file recovery writer and outer recovery predicate. A failed primary write can recreate missing run params without `brainstorm_requested`, causing Step 1d.5 to skip on resume or re-entry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From unknown-slot: Update the whole recovery block, not just the jq merge: guard on partition_requested OR brainstorm_requested, merge both true fields when a file exists, and pass --brainstorm-requested true in the no-file write-run-params fallback; add a regression for --brainstorm --partition no-file recovery.
  - From Codex-dyn-run-params-consumers: Specify the outer recovery predicate as partition_requested OR brainstorm_requested, merge both booleans atomically when a file exists, recreate the file with both --partition-requested and --brainstorm-requested values when absent, and emit independent jq-unavailable warnings for each requested flag


### FINDING_16: Structural tests do not pin `--brainstorm-requested` callsites
- **Reviewer(s)**: Codex-dyn-run-params-consumers
- **Severity**: latent
- **Concern**: Writer-level tests can pass while prompt-side SKILL.md callsites omit `--brainstorm-requested`, producing valid JSON with the default false value and silently skipping Step 1d.5.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-run-params-consumers: Add scripts/test-design-structure.sh checks for --brainstorm-requested "$brainstorm_requested" on the primary Step 0b writer, --brainstorm-requested true or the current boolean in the recovery writer, and a jq merge expression that sets .brainstorm_requested = true


### FINDING_17: Brainstorm loop terminal handling can delay Step 1e
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Concern**: The blanket “re-print synthesis and end turn” loop language can be read to apply even when the user says they are ready, delaying sentinel write and Step 1e.
- **Suggested revisions (informational for voters; coder decides)**:
  - From unknown-slot: Specify branch order: first classify the user message; if terminal, write .brainstorm-done and continue to Step 1e in the same turn without reprinting synthesis or ending the turn


### FINDING_18: Brainstorm termination vocabulary is too broad
- **Reviewer(s)**: unknown-slot, Codex-dyn-never-rule-compliance
- **Severity**: important
- **Concern**: Termination cues such as “ready,” “proceed,” “looks good,” and “next” overlap with normal refinement language, so the loop can end prematurely on negated, conditional, or refinement-bearing messages.
- **Suggested revisions (informational for voters; coder decides)**:
  - From unknown-slot: Add disambiguation rules: terminate only on a standalone or primary-intent cue with no negation, condition, or requested refinement; ambiguous messages continue refinement or ask a two-option confirmation
  - From Codex-dyn-never-rule-compliance: Require an unambiguous termination intent: prefer a structured AskUserQuestion after each synthesis with Continue brainstorming / Proceed to Gate A, or require a standalone command such as /ready or a message whose primary intent is proceed. Explicitly treat negated, quoted, conditional, or refinement-bearing uses of the listed words as continued discussion, mutate brainstorm.md, and re-print synthesis instead of writing the sentinel.


### FINDING_19: Passive brainstorm turn boundary does not explicitly preserve ScheduleWakeup prohibition
- **Reviewer(s)**: unknown-slot, Codex-dyn-never-rule-compliance
- **Severity**: latent
- **Concern**: The intentional user-response turn boundary could be misread as permission to schedule wakeups, sleep, poll, or invent resume mechanics, weakening the shared orchestrator NEVER rule.
- **Suggested revisions (informational for voters; coder decides)**:
  - From unknown-slot: Add to brainstorm.md's anti-halt override: this is a passive user-response turn boundary only; MUST NOT call ScheduleWakeup, start sleep or polling prose, or invent any resume mechanism
  - From Codex-dyn-never-rule-compliance: Update skills/design/SKILL.md:29 as part of the plan: add 1d→1d.5→1e to the transition list and define a single narrow exception that only Step 1d.5 may end the turn after the exact Brainstorm Synthesis print while .brainstorm-done is absent. State that no ScheduleWakeup, summary, handoff, or status recap is allowed, and that after sentinel write the normal anti-halt rule resumes and Step 1e must start immediately. Pin this with test-design-structure.sh.

### FINDING_2: Already-planned ad-hoc Q&A route can skip brainstorm
- **Reviewer(s)**: unknown-slot, Codex-Requirements, Codex-dyn-run-params-consumers
- **Severity**: important
- **Concern**: The plan promises `--brainstorm` for already-planned ad-hoc Q&A, but does not wire that branch to write brainstorm run params or execute Step 1d.5 before the ad-hoc exit path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From unknown-slot: Either remove that promised edge-case behavior or add explicit Step 0b routing for ad-hoc Q&A that materializes run-params with brainstorm_requested=true and invokes the Step 1d.5 loop before the Q&A exit
  - From Codex-Requirements: Add explicit Step 0b branch semantics for ad-hoc Q&A: after the user selects ad-hoc and brainstorm_requested is true, run the Step 1d.5 brainstorm body once before the ad-hoc Q&A/exit path; cancel still exits without brainstorm.
  - From Codex-dyn-run-params-consumers: Define the ad-hoc branch contract explicitly: either remove that edge-case claim, or make the branch write run-params.json with --brainstorm-requested true and invoke the brainstorm step before ad-hoc Q&A/exit


### FINDING_4: New brainstorm prompt harness is not registered in lint/test graph
- **Reviewer(s)**: unknown-slot, Codex-Arch, Codex-Edge, Codex-Innovation, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: `test-brainstorm-prompts.sh` is planned but not wired into `.PHONY`, a Makefile target, exactly one `test-harnesses-N` shard, and related lint/docs exclusions, so normal checks may never run it or may flag it as orphaned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From unknown-slot: Add a Makefile .PHONY target, recipe, and exactly one test-harnesses-N shard entry; add the new .sh and .md to the existing skills/design/scripts test exclusions in agent-lint.toml
  - From Codex-Arch: Update Makefile .PHONY, add a test-brainstorm-prompts target invoking skills/design/scripts/test-brainstorm-prompts.sh, and add that target to one test-harnesses-N shard
  - From unknown-slot: Add test-brainstorm-prompts to .PHONY, one test-harnesses-N shard, a Makefile target, and docs/linting.md
  - From Codex-Edge: Add a test-brainstorm-prompts target, include it in .PHONY, assign it to exactly one test-harnesses-N shard, and update any required harness documentation or lint exclusions
  - From unknown-slot: Add a Makefile target for test-brainstorm-prompts, include it in .PHONY and one test-harnesses-N shard, and update docs/linting.md if this repo expects public harness documentation
  - From Codex-Innovation: Add Makefile updates: .PHONY test-brainstorm-prompts, a recipe invoking skills/design/scripts/test-brainstorm-prompts.sh through harness-timer, and exactly one test-harnesses-N shard entry; update docs/linting.md if this repo expects new harness docs
  - From Codex-Pragmatic: Add a Makefile target, PHONY/shard entry, docs/linting row, agent-lint exclusion if needed, and update scripts/write-run-params.md alongside the schema change
  - From Codex-Requirements: Add test-brainstorm-prompts to .PHONY, define the target with harness-timer, place it in a test-harnesses-N shard, and document it in docs/linting.md if following existing harness conventions.


### FINDING_5: Public docs omit the new `--brainstorm` flag
- **Reviewer(s)**: unknown-slot
- **Severity**: nit
- **Concern**: Public command documentation does not mention the new `--brainstorm` surface or its mutual-exclusion behavior with `--trivial`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From unknown-slot: Update README.md and docs/skills.md argument strings and prose; consider docs/workflow-lifecycle.md if it remains a public command summary


### FINDING_6: Run-params schema sibling docs omit `brainstorm_requested`
- **Reviewer(s)**: unknown-slot, Codex-Arch, Codex-Edge, Codex-Innovation, Codex-Pragmatic, Codex-dyn-run-params-consumers
- **Severity**: latent
- **Concern**: The plan changes `write-run-params.sh` and its emitted JSON schema but omits sibling contract updates documenting `--brainstorm-requested`, default false behavior, validation, emitted `brainstorm_requested`, and harness coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From unknown-slot: Update scripts/write-run-params.md and scripts/test-write-run-params.md alongside the script and tests to document --brainstorm-requested and the emitted brainstorm_requested boolean
  - From Codex-Arch: Add scripts/write-run-params.md and scripts/test-write-run-params.md to the plan and document --brainstorm-requested, the emitted brainstorm_requested boolean, and the new harness assertions
  - From unknown-slot: Update scripts/write-run-params.md usage/schema/update notes to include --brainstorm-requested and brainstorm_requested false-by-default semantics
  - From Codex-Edge: Update scripts/write-run-params.md, scripts/test-write-run-params.md, scripts/lib-timing-kinds.md, and scripts/test-design-structure.md where their documented schema, coverage, timing-kind, or structural-test contracts change
  - From Codex-Innovation: Add scripts/write-run-params.md to the updated files and document the new optional flag, default false behavior, emitted brainstorm_requested boolean, and edit-in-sync coverage with test-write-run-params.sh
  - From unknown-slot: Update `scripts/write-run-params.md` with the new optional flag, emitted JSON field, default false behavior, and harness coverage.
  - From unknown-slot: Add scripts/write-run-params.md and scripts/test-write-run-params.md to the plan and document --brainstorm-requested, the emitted brainstorm_requested boolean, and the new harness assertions
  - From Codex-dyn-run-params-consumers: Update scripts/write-run-params.md alongside scripts/write-run-params.sh and scripts/test-write-run-params.sh to document --brainstorm-requested, its default false behavior, validation, and emitted brainstorm_requested boolean.


### FINDING_7: Agent fallback output contract expects subagents to write files
- **Reviewer(s)**: Codex-Arch, unknown-slot, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The planned Claude Agent fallback relies on deterministic output files, but existing Agent-tool fallback convention returns text to the parent and brainstorm prompts may require read-only behavior. Synthesis can therefore miss successful fallback output or force agents to violate prompts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Make the parent session capture each Agent return and Write it to the deterministic output path before synthesis; keep collect-agent-results.sh only for external Cursor/Codex outputs
  - From unknown-slot: Make the parent orchestrator treat Agent returns as authoritative and Write those returned texts to deterministic output files before synthesis, matching the sketch/dialectic inline-Agent pattern; log Agent failures explicitly
  - From Codex-Pragmatic: Keep fallback agents read-only; have them return their brainstorm text, then have the parent orchestrator Write the returned text to the slot output files before synthesis
  - From unknown-slot: Revise brainstorm.md to require the parent orchestrator to capture each Agent return and Write it to the deterministic output path before synthesis; reserve collect-agent-results.sh for external Cursor/Codex outputs only
  - From Codex-Requirements: Keep brainstorming subagents read-only: have Agent slots return text, then the parent orchestrator writes the returned text to $DESIGN_TMPDIR/*-brainstorm-output.txt before synthesis, or use a subprocess launcher designed to write output files.


### FINDING_8: Brainstorm external collection omits dirty-tree checkpoint
- **Reviewer(s)**: unknown-slot, Codex-Edge, Codex-Pragmatic
- **Severity**: important
- **Concern**: New Cursor/Codex brainstorm launches can dirty the worktree, but the planned collection boundary does not mirror existing dirty-tree sidecar and checkpoint recovery used after other external design phases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From unknown-slot: Add a brainstorm collection boundary that consults ${OUTPUT}.dirty-tree sidecars, runs check-mid-run-dirty-tree.sh --mode checkpoint, writes dirty-tree-detected.env with STAGE=brainstorm-collection, and prompts once via a .dirty-tree-prompted-brainstorm-collection sentinel
  - From Codex-Edge: Add the same dirty-tree sidecar plus check-mid-run-dirty-tree.sh checkpoint after brainstorm collection, with STAGE=brainstorm-collection and a one-shot .dirty-tree-prompted-brainstorm-collection sentinel
  - From unknown-slot: Add the same post-collection dirty-tree sidecar consult plus check-mid-run-dirty-tree.sh --mode checkpoint with STAGE=brainstorm-collection and a .dirty-tree-prompted-brainstorm-collection guard; pin it in test-design-structure.sh
  - From Codex-Pragmatic: Mirror the Step 2a.3 sidecar scan and check-mid-run-dirty-tree recovery after brainstorm collection, with a brainstorm-specific STAGE and prompted sentinel


### FINDING_9: Anti-halt sequence and Step 1d.5 exception are not pinned in SKILL.md
- **Reviewer(s)**: unknown-slot, Codex-dyn-never-rule-compliance
- **Severity**: important
- **Concern**: The top-level anti-halt text still enumerates `1c→1d→1e` and says exceptions must live in `SKILL.md`; a reference-only brainstorm override can be missed, skipped, or overgeneralized.
- **Suggested revisions (informational for voters; coder decides)**:
  - From unknown-slot: Update the anti-halt sequence to 1c→1d→1d.5→1e and add a structural assertion so future step insertions keep the sequence aligned
  - From unknown-slot: Update skills/design/SKILL.md:29 to include 1d→1d.5→1e and add a local carve-out sentence: only non-terminal brainstorm refinement turns may end after synthesis; sentinel or skip immediately continues to Step 1e
  - From Codex-dyn-never-rule-compliance: Update skills/design/SKILL.md:29 as part of the plan: add 1d→1d.5→1e to the transition list and define a single narrow exception that only Step 1d.5 may end the turn after the exact Brainstorm Synthesis print while .brainstorm-done is absent. State that no ScheduleWakeup, summary, handoff, or status recap is allowed, and that after sentinel write the normal anti-halt rule resumes and Step 1e must start immediately. Pin this with test-design-structure.sh.


