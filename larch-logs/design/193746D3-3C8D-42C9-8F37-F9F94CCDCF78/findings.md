### FINDING_1:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:175-209
- **Concern**: Pre-Step-0 upgrade to simple is only mental state while Step 0b still parses the original --trivial argv. Scenario: With /design --trivial --brainstorm, selecting Upgrade to --simple can still let Step 0b see --trivial in $ARGUMENTS and write run-params as the trivial zero-sketch tier, contradicting the operator choice
- **Proposed resolution**: Add an explicit resolved_tier override contract: Pre-Step-0 sets it, Step 0b parser must ignore the original --trivial when it is set, and structural tests should pin the override path

### FINDING_2:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:188
- **Concern**: The plan says --brainstorm fires on already-planned ad-hoc Q&A, but does not change the already-planned router contract. Scenario: The existing already-planned branch can choose ad-hoc Q&A only and exit without reaching Step 1d.5, so the promised unconditional brainstorm behavior is not implemented for that path
- **Proposed resolution**: Either remove that promised edge-case behavior or add explicit Step 0b routing for ad-hoc Q&A that materializes run-params with brainstorm_requested=true and invokes the Step 1d.5 loop before the Q&A exit

### FINDING_3:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/shared/external-reviewers.md:24-38
- **Concern**: Runtime external failures in brainstorm proceed with fewer slots instead of following the existing per-slot fallback standard. Scenario: A Cursor or Codex timeout after launch reduces the intended 3-agent ideation panel to 2 or 1 outputs, while the repo standard says failed external slots should fall through replacement rather than shrink panel shape
- **Proposed resolution**: On non-OK collector status, log the failure and run a Claude replacement for that brainstorm slot, writing the same output path before synthesis; only proceed with fewer outputs if the replacement also fails

### FINDING_4:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: code-quality
- **Location**: Makefile:4-79,agent-lint.toml:804-818
- **Concern**: The new test-brainstorm-prompts harness is not wired into Makefile shards or agent-lint exclusions. Scenario: make lint either never runs the new regression harness, or agent-lint flags the skill-local Makefile-only test script and sibling md as dead or orphaned
- **Proposed resolution**: Add a Makefile .PHONY target, recipe, and exactly one test-harnesses-N shard entry; add the new .sh and .md to the existing skills/design/scripts test exclusions in agent-lint.toml

### FINDING_5:
- **Reviewer(s)**: unknown-slot
- **Severity**: nit
- **Focus area**: architecture
- **Location**: README.md:58-61,docs/skills.md:48-54
- **Concern**: Public /design flag documentation is omitted for the new public --brainstorm surface. Scenario: Consumers reading the canonical README or docs/skills argument list will not discover the flag or its --trivial mutual-exclusion behavior
- **Proposed resolution**: Update README.md and docs/skills.md argument strings and prose; consider docs/workflow-lifecycle.md if it remains a public command summary

### FINDING_6:
- **Reviewer(s)**: unknown-slot
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: scripts/write-run-params.md:13-29
- **Concern**: The run-params schema sibling contract is not updated for brainstorm_requested. Scenario: The script contract continues to list only partition_requested even though the writer emits a new schema field, making future maintenance and harness expectations drift
- **Proposed resolution**: Update scripts/write-run-params.md and scripts/test-write-run-params.md alongside the script and tests to document --brainstorm-requested and the emitted brainstorm_requested boolean

### FINDING_7:
- **Reviewer(s)**: Codex-Arch, unknown-slot
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: Makefile:4-79; <TMPDIR>/plan.txt:51-53
- **Concern**: The new test-brainstorm-prompts.sh harness is planned but not registered in Makefile or a test-harnesses shard. Scenario: CI and make lint will not run the new prompt-token guard, and make test-brainstorm-prompts will not exist
- **Proposed resolution**: Update Makefile .PHONY, add a test-brainstorm-prompts target invoking skills/design/scripts/test-brainstorm-prompts.sh, and add that target to one test-harnesses-N shard

### FINDING_8:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/references/brainstorm.md (planned); skills/design/references/sketch-launch.md:7
- **Concern**: Planned Agent fallback collection relies on subagents writing deterministic output files, which conflicts with the existing Agent-tool pattern where inline Agent outputs are returned to the parent. Scenario: When Cursor or Codex is unavailable, synthesis reads cursor-brainstorm-output.txt/codex-brainstorm-output.txt/claude-brainstorm-output.txt that may not exist or may not be authoritative, causing lost brainstorm output or false all-failed behavior
- **Proposed resolution**: Make the parent session capture each Agent return and Write it to the deterministic output path before synthesis; keep collect-agent-results.sh only for external Cursor/Codex outputs

### FINDING_9:
- **Reviewer(s)**: Codex-Arch
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: scripts/write-run-params.md:13-19; scripts/test-write-run-params.md:5-12
- **Concern**: The run-params schema change omits the script sibling contract docs that currently document only partition_requested and explicitly say to update them with schema changes. Scenario: Post-merge docs for the writer and harness will be stale, making future callers and reviewers miss brainstorm_requested semantics
- **Proposed resolution**: Add scripts/write-run-params.md and scripts/test-write-run-params.md to the plan and document --brainstorm-requested, the emitted brainstorm_requested boolean, and the new harness assertions

### FINDING_10:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:412
- **Concern**: New brainstorm external launches lack dirty-tree recovery. Scenario: The proposed Cursor/Codex brainstorm slots can mutate the worktree; without the same post-collection sidecar/checkpoint gate used by sketches, Step 1d.5 can silently continue on a polluted tree
- **Proposed resolution**: Add a brainstorm collection boundary that consults ${OUTPUT}.dirty-tree sidecars, runs check-mid-run-dirty-tree.sh --mode checkpoint, writes dirty-tree-detected.env with STAGE=brainstorm-collection, and prompts once via a .dirty-tree-prompted-brainstorm-collection sentinel

### FINDING_11:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:29
- **Concern**: Anti-halt step sequence still skips 1d.5. Scenario: The global continuation reminder currently says 1c→1d→1e; after adding Step 1d.5 this conflicts with the new required path and can cause an executor to jump directly to Gate A
- **Proposed resolution**: Update the anti-halt sequence to 1c→1d→1d.5→1e and add a structural assertion so future step insertions keep the sequence aligned

### FINDING_12:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:177-195
- **Concern**: Trivial-plus-brainstorm upgrade relies on an unpinned mental override. Scenario: After the Upgrade to --simple choice, $ARGUMENTS still contains --trivial; the Step 0b parser/tier mapping can still classify the run as trivial unless the effective tier override is explicit and tested
- **Proposed resolution**: Define an effective_tier variable set by Pre-Step-0, require Step 0b to use it instead of raw argv tier flags when present, and add a structure or harness check for --trivial --brainstorm upgrade producing simple/full run params

### FINDING_13:
- **Reviewer(s)**: unknown-slot, unknown-slot
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: Makefile:38-40
- **Concern**: New brainstorm prompt harness is not wired into lint. Scenario: The plan creates skills/design/scripts/test-brainstorm-prompts.sh but does not add a Makefile target/shard or docs entry, so make lint and CI never execute the new regression coverage
- **Proposed resolution**: Add test-brainstorm-prompts to .PHONY, one test-harnesses-N shard, a Makefile target, and docs/linting.md

### FINDING_14:
- **Reviewer(s)**: unknown-slot
- **Severity**: nit
- **Focus area**: architecture
- **Location**: scripts/write-run-params.md:13-29
- **Concern**: Run-params schema docs omit brainstorm_requested. Scenario: The script schema changes, but the sibling contract still documents only partition_requested and explicitly says to update it on schema changes
- **Proposed resolution**: Update scripts/write-run-params.md usage/schema/update notes to include --brainstorm-requested and brainstorm_requested false-by-default semantics

### FINDING_15:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:294-305
- **Concern**: Step 1d.5 does not require loading brainstorm-prompts.md before using BRAINSTORM prompt tokens. Scenario: The executor can read only brainstorm.md, encounter unresolved <BRAINSTORM_*_PROMPT> placeholders, and launch Cursor/Codex/Claude with literal placeholders or invented prompt text
- **Proposed resolution**: Add a mandatory read of skills/design/references/brainstorm-prompts.md before prompt-file rendering, mirroring the sketch-prompts.md then sketch-launch.md ordering, and pin it in test-design-structure.sh

### FINDING_16:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:317-362
- **Concern**: Plan conflicts on whether Step 2a consumes brainstorm.md. Scenario: The summary and brainstorm consumer contract name Step 2a as a reader, but the proposed SKILL.md edits explicitly leave Step 2a unchanged; sketches may ignore the user-refined brainstorm framing while Step 2b later uses it, producing a plan grounded in sketches for a stale interpretation
- **Proposed resolution**: Either add an optional brainstorm.md read into Step 2a sketch prompt context before launches, or remove Step 2a from every brainstorm consumer contract and document that sketches intentionally ignore brainstorm context

### FINDING_17:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: security
- **Location**: skills/design/SKILL.md:412,489
- **Concern**: Brainstorm external collection omits the dirty-tree checkpoint used by other external design phases. Scenario: Cursor or Codex brainstorm slots run through launch-review.sh and can accidentally modify the worktree despite the prompt; without a post-collection check, /design continues into Gate A and sketches with undetected mid-run pollution
- **Proposed resolution**: Add the same dirty-tree sidecar plus check-mid-run-dirty-tree.sh checkpoint after brainstorm collection, with STAGE=brainstorm-collection and a one-shot .dirty-tree-prompted-brainstorm-collection sentinel

### FINDING_18:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:101-103,177-196
- **Concern**: The --trivial plus --brainstorm upgrade path relies on mental state while leaving --trivial in ARGUMENTS. Scenario: After the user selects Upgrade to --simple, Step 0b still re-parses unchanged argv and can bind the tier as trivial, writing sketch_budget=0 with brainstorm_requested=true despite the intended simple upgrade
- **Proposed resolution**: Specify that Step 0b must ignore the argv --trivial token when the Pre-Step-0 upgrade flag is set and must bind classification SIMPLE, sketch_budget=2, review_budget=full; add a structural pin for the override wording

### FINDING_19:
- **Reviewer(s)**: Codex-Edge, unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/discussion-rounds.md:58-70
- **Concern**: Brainstorm prompt rendering assumes discussion-round1.md exists. Scenario: The common Step 1d short-circuit path may print the skip breadcrumb without writing discussion-round1.md; concatenating feature-description.txt plus discussion-round1.md can fail or cause the executor to fabricate missing context
- **Proposed resolution**: Treat discussion-round1.md as optional in brainstorm.md prompt rendering: read it only when it exists and is non-empty, otherwise render prompts from feature-description.txt alone

### FINDING_20:
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: Makefile:393-394
- **Concern**: New test-brainstorm-prompts.sh is not wired into Makefile or a harness shard. Scenario: The proposed offline harness can be committed but never run by bash scripts/relevant-checks.sh or make lint, so prompt-token drift is not caught
- **Proposed resolution**: Add a test-brainstorm-prompts target, include it in .PHONY, assign it to exactly one test-harnesses-N shard, and update any required harness documentation or lint exclusions

### FINDING_21:
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: .claude/rules/script-md-siblings.md:7-12
- **Concern**: Planned script behavior changes omit sibling documentation updates. Scenario: scripts/write-run-params.sh, scripts/test-write-run-params.sh, scripts/lib-timing-kinds.sh, and scripts/test-design-structure.sh are changed, but the plan only creates the new brainstorm harness sibling; existing sibling contracts will be stale and violate the repo rule to update docs with behavior changes
- **Proposed resolution**: Update scripts/write-run-params.md, scripts/test-write-run-params.md, scripts/lib-timing-kinds.md, and scripts/test-design-structure.md where their documented schema, coverage, timing-kind, or structural-test contracts change

### FINDING_22:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/references/brainstorm.md:Collection
- **Concern**: Missing dirty-tree checkpoint for new external brainstorm launches. Scenario: Cursor/Codex brainstorm slots use launch-review.sh, which can produce dirty-tree sidecars, but the proposed collection step does not mirror existing sketch and dialectic dirty-tree probes; a tool-side file mutation can silently pollute the design run before Gate A and sketches
- **Proposed resolution**: Add the same post-collection dirty-tree sidecar consult plus check-mid-run-dirty-tree.sh --mode checkpoint with STAGE=brainstorm-collection and a .dirty-tree-prompted-brainstorm-collection guard; pin it in test-design-structure.sh

### FINDING_23:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/brainstorm.md:Panel launch matrix
- **Concern**: Agent fallback outputs are assumed to be file-written by subagents. Scenario: The existing sketch contract says Agent-tool fallback outputs are returned to the parent session, not collected via sentinel files; if brainstorm fallback subagents do not reliably write cursor-brainstorm-output.txt/codex-brainstorm-output.txt/claude-brainstorm-output.txt, synthesis may read missing files and treat successful Agent returns as failures
- **Proposed resolution**: Make the parent orchestrator treat Agent returns as authoritative and Write those returned texts to deterministic output files before synthesis, matching the sketch/dialectic inline-Agent pattern; log Agent failures explicitly

### FINDING_24:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:177-208
- **Concern**: The --trivial plus --brainstorm upgrade path relies on mental state while Step 0b still parses unchanged argv. Scenario: After the Pre-Step-0 Upgrade to --simple choice, $ARGUMENTS still contains --trivial; the proposed text says Step 0b reads mental state, but the actual Step 0b contract still parses tier flags from argv and maps trivial to sketch_budget=0/review_budget=quick, so brainstorm can be skipped or run with the wrong tier semantics
- **Proposed resolution**: Specify a concrete override variable or rewritten parsed-token list for Step 0b, and update the parser prose/tests to prove --trivial --brainstorm upgraded writes design_classification=SIMPLE, sketch_budget=2, review_budget=full, brainstorm_requested=true

### FINDING_25:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: code-quality
- **Location**: Makefile:4-79
- **Concern**: New test-brainstorm-prompts.sh is not registered in the harness graph. Scenario: The plan adds a new offline harness but does not update Makefile .PHONY, a test target, or any test-harnesses-N shard; make lint runs test-harnesses, so the new prompt-token test will not execute in the normal validation path
- **Proposed resolution**: Add a Makefile target for test-brainstorm-prompts, include it in .PHONY and one test-harnesses-N shard, and update docs/linting.md if this repo expects public harness documentation

### FINDING_26:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:358-444; skills/design/references/sketch-prompts.md:15-19
- **Concern**: Brainstorm output is not actually fed into the sketch agents. Scenario: When the user selects a non-obvious framing in Step 1d.5, Step 2a still launches sketches from the original feature description and discussion-round1 only, so approach-synthesis and dialectic can anchor on the stale interpretation before Step 2b later reads brainstorm.md
- **Proposed resolution**: Add brainstorm.md as an input to Step 2a prompt rendering when it exists and is non-empty, or write the selected brainstorm decisions into discussion-round1 before Gate A so existing sketch prompt construction sees them

### FINDING_27:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: Makefile:4-79; Makefile:388-394
- **Concern**: The new test-brainstorm-prompts.sh harness is planned but not wired into make lint. Scenario: The harness can exist and pass locally only when run manually, while CI and bash scripts/relevant-checks.sh via make lint never execute it, so prompt-token regressions can ship
- **Proposed resolution**: Add Makefile updates: .PHONY test-brainstorm-prompts, a recipe invoking skills/design/scripts/test-brainstorm-prompts.sh through harness-timer, and exactly one test-harnesses-N shard entry; update docs/linting.md if this repo expects new harness docs

### FINDING_28:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: scripts/write-run-params.md:13-19; scripts/write-run-params.md:27-29
- **Concern**: The write-run-params contract sibling is omitted from the schema change. Scenario: The plan adds --brainstorm-requested and a brainstorm_requested JSON field to scripts/write-run-params.sh, but the sibling contract would still document only partition_requested, leaving future callers and script-md sync checks with stale schema guidance
- **Proposed resolution**: Add scripts/write-run-params.md to the updated files and document the new optional flag, default false behavior, emitted brainstorm_requested boolean, and edit-in-sync coverage with test-write-run-params.sh

### FINDING_29:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:177-195
- **Concern**: `--brainstorm` can still pair with a tier-gate-selected trivial tier. Scenario: When argv has `--brainstorm` but no tier flag, Step 0b still offers `trivial`; choosing it writes `brainstorm_requested=true` with `sketch_budget=0`, bypassing the proposed `--trivial` + `--brainstorm` mutex.
- **Proposed resolution**: When `brainstorm_requested=true`, remove `trivial` from the tier gate or run the same Upgrade-to-simple / Cancel prompt after a trivial tier-gate choice before writing run-params.

### FINDING_30:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:294-305
- **Concern**: Prompt token file is not load-bound for Step 1d.5. Scenario: The plan creates `brainstorm-prompts.md` but the Step 1d.5 insertion only mandates reading `brainstorm.md`; executors can render prompt files with unresolved `<BRAINSTORM_*_PROMPT>` tokens.
- **Proposed resolution**: Add a mandatory read of `skills/design/references/brainstorm-prompts.md` before prompt rendering, either in SKILL.md Step 1d.5 or as the first nested directive inside `brainstorm.md`, mirroring the sketch-prompts/sketch-launch contract.

### FINDING_31:
- **Reviewer(s)**: unknown-slot
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/write-run-params.md:13-29
- **Concern**: `run-params.json` schema docs are omitted from the schema change. Scenario: The plan adds `brainstorm_requested` to `write-run-params.sh` but leaves the sibling contract documenting only `partition_requested`, despite its explicit edit-in-sync rule for schema changes.
- **Proposed resolution**: Update `scripts/write-run-params.md` with the new optional flag, emitted JSON field, default false behavior, and harness coverage.

### FINDING_32:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:412
- **Concern**: Proposed Step 1d.5 launches external Cursor/Codex reviewers but omits the dirty-tree sidecar checkpoint used after other external design boundaries. Scenario: A brainstorm external can dirty the worktree before the free-form loop and Gate A; the run then continues against polluted files without the existing recovery prompt
- **Proposed resolution**: Mirror the Step 2a.3 sidecar scan and check-mid-run-dirty-tree recovery after brainstorm collection, with a brainstorm-specific STAGE and prompted sentinel

### FINDING_33:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:177-193
- **Concern**: The --trivial plus --brainstorm Upgrade to --simple path is described as in-memory only while Step 0b still parses tier flags from unchanged ARGUMENTS. Scenario: After the operator chooses Upgrade, Step 0b can still see --trivial and persist sketch_budget=0/review_budget=quick, contradicting the requested simple brainstorm flow
- **Proposed resolution**: Define an explicit tier override that Step 0b must honor when parsing ARGUMENTS, ignoring --trivial and writing SIMPLE/sketch_budget=2/review_budget=full after upgrade

### FINDING_34:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/sketch-launch.md:5-7
- **Concern**: The proposed Claude fallback asks subagents to write brainstorm output files while the role prompts say Do NOT modify files and existing fallback convention returns content to the parent. Scenario: All-Claude or mixed fallback paths may leave expected brainstorm output files missing, causing synthesis to drop fallback ideas or treat the panel as failed
- **Proposed resolution**: Keep fallback agents read-only; have them return their brainstorm text, then have the parent orchestrator Write the returned text to the slot output files before synthesis

### FINDING_35:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: Makefile:4
- **Concern**: Plan adds test-brainstorm-prompts.sh but does not wire it into Makefile shards/docs or the Makefile-only agent-lint exclusions, and omits the write-run-params contract doc update. Scenario: The new harness may never run under make lint or may be flagged as a dead script; scripts/write-run-params.md will still document only partition_requested after the schema adds brainstorm_requested
- **Proposed resolution**: Add a Makefile target, PHONY/shard entry, docs/linting row, agent-lint exclusion if needed, and update scripts/write-run-params.md alongside the schema change

### FINDING_36:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:76; skills/design/SKILL.md:366-444
- **Concern**: Plan explicitly does not wire brainstorm.md into Step 2a sketches, despite the feature decision that Step 2a reads brainstorm.md. Scenario: Sketch prompts and approach-synthesis can ignore the user's brainstorm-selected framing, so downstream architecture may anchor on pre-brainstorm context
- **Proposed resolution**: Add Step 2a changes so sketch prompt rendering/launch context reads non-empty $DESIGN_TMPDIR/brainstorm.md additively, and add structure/manual tests that verify sketch prompts or synthesis include brainstorm context when --brainstorm is set

### FINDING_37:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:5,41,144,156,184-185; skills/design/SKILL.md:619-629; skills/design/scripts/plan-review-loop.sh:160-174; skills/design/scripts/render-plan-review-prompt.sh:90-108
- **Concern**: Plan omits Step 3 plan-review consumption of brainstorm.md, although the feature decision says Step 3 reads it. Scenario: Requirements reviewers cannot compare the proposed plan against brainstorm-derived constraints or accepted framings, so plan review can miss drift introduced between brainstorm and the final plan
- **Proposed resolution**: Add a Step 3 integration path, such as extending plan-review-loop/dispatch-plan-review-panel/render-plan-review-prompt or the feature context passed to reviewers to include brainstorm.md as untrusted additive context, and add a regression check for that prompt/context path

### FINDING_38:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:19-26; skills/design/references/sketch-launch.md:5-8
- **Concern**: Planned Claude Agent fallback contract says subagents write deterministic output files, conflicting with the existing Agent-tool fallback pattern where the parent receives returned text and then collects it. Scenario: When Cursor or Codex is unavailable, synthesis may read cursor-brainstorm-output.txt, codex-brainstorm-output.txt, or claude-brainstorm-output.txt before any authoritative file exists, causing false missing-output/all-failed behavior
- **Proposed resolution**: Revise brainstorm.md to require the parent orchestrator to capture each Agent return and Write it to the deterministic output path before synthesis; reserve collect-agent-results.sh for external Cursor/Codex outputs only

### FINDING_39:
- **Reviewer(s)**: unknown-slot
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: <TMPDIR>/plan.txt:94-112; scripts/write-run-params.md:13-19; scripts/test-write-run-params.md:5-19
- **Concern**: The run-params schema and harness docs are not listed for update even though brainstorm_requested is a new emitted JSON field and test coverage is changing. Scenario: Post-merge script sibling docs will still document only partition_requested and old harness coverage, making future schema consumers miss brainstorm_requested
- **Proposed resolution**: Add scripts/write-run-params.md and scripts/test-write-run-params.md to the plan and document --brainstorm-requested, the emitted brainstorm_requested boolean, and the new harness assertions

### FINDING_40:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:366-370,599-648
- **Concern**: Plan drops required brainstorm consumers. Scenario: Round 1 Decision 3 requires Step 2a sketches, Step 2a.5 dialectic, Step 2b plan, and Step 3 plan review to read brainstorm.md; the plan explicitly leaves Step 2a unchanged and excludes Step 3 while saying Step 2b only.
- **Proposed resolution**: Revise the plan to update Step 2a prompt rendering/sketch launch context and Step 3 plan-review prompt/driver inputs to include brainstorm.md additively when non-empty, and add validation for those consumers.

### FINDING_41:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:188,274-307
- **Concern**: Already-planned ad-hoc route is not wired to Step 1d.5. Scenario: Decision 6 requires --brainstorm to fire on both replace and ad-hoc Q&A already-planned branches; inserting Step 1d.5 only in the normal Step 1d to Gate A path does not guarantee the ad-hoc branch reaches it.
- **Proposed resolution**: Add explicit Step 0b branch semantics for ad-hoc Q&A: after the user selects ad-hoc and brainstorm_requested is true, run the Step 1d.5 brainstorm body once before the ad-hoc Q&A/exit path; cancel still exits without brainstorm.

### FINDING_42:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/references/sketch-launch.md:7,skills/design/SKILL.md:374-416
- **Concern**: Agent fallback output contract conflicts with read-only prompts. Scenario: The proposed brainstorm prompts tell agents Do NOT modify files, but the plan relies on Claude Agent slots writing cursor/codex/claude brainstorm output files; existing sketch fallback convention collects Agent return text in the parent, so synthesis may find missing files or force agents to violate their prompt.
- **Proposed resolution**: Keep brainstorming subagents read-only: have Agent slots return text, then the parent orchestrator writes the returned text to $DESIGN_TMPDIR/*-brainstorm-output.txt before synthesis, or use a subprocess launcher designed to write output files.

### FINDING_43:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: code-quality
- **Location**: Makefile:4,50-79,393-394
- **Concern**: New brainstorm prompt harness is not registered. Scenario: The plan adds skills/design/scripts/test-brainstorm-prompts.sh and claims make lint/relevant checks, but does not add a Makefile target or test-harnesses shard entry, so the new regression harness will not run under make lint.
- **Proposed resolution**: Add test-brainstorm-prompts to .PHONY, define the target with harness-timer, place it in a test-harnesses-N shard, and document it in docs/linting.md if following existing harness conventions.

### FINDING_44:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:25,189
- **Concern**: The proposed brainstorm.md collector block is not specified with the exact foreground banner and in-fence comment required by the linter. Scenario: scripts/lint-foreground-markers.sh:15-16 defines exact strings, lines 25 and 294-301 enforce collect-agent-results.sh anchors, and lines 337-351 scan tracked markdown fences; plan.txt:25 only names the collector inline and plan.txt:189 says it should carry markers, but the NEW brainstorm.md spec never places the exact banner immediately above the fenced bash block or the exact comment within five in-fence lines before the collect-agent-results.sh anchor, so an implementation following the normative section could fail make lint-foreground-markers
- **Proposed resolution**: Add an explicit collector fence to the NEW skills/design/references/brainstorm.md section with the exact banner line above the opening fence and # Foreground required: see BASH_AUTHORING.md §4 directly before ${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh; state launch-review.sh blocks intentionally keep run_in_background true and need no foreground marker because scripts/lint-foreground-markers.sh does not denylist launch-review.sh

### FINDING_45:
- **Reviewer(s)**: Codex-dyn-foreground-marker-audit
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:11-26,189; scripts/lint-foreground-markers.sh:15-16,18-28,296-301
- **Concern**: The proposed NEW skills/design/references/brainstorm.md does not explicitly place the exact foreground banner above the collect-agent-results.sh fenced bash block or the exact in-fence comment within five lines before the collect-agent-results.sh anchor.. Scenario: The linter scans tracked skills/design/references/*.md fences and denylists collect-agent-results.sh; an implementer following the plan can add the collector fence without the literal banner/comment, causing make lint-foreground-markers to fail with missing banner and/or missing comment. The plan's line 189 says the block should carry markers, but does not specify exact strings or positions.
- **Proposed resolution**: Revise the brainstorm.md plan section to include the literal banner **⚠ Foreground required — do NOT set `run_in_background: true`.** immediately above the collector fence and # Foreground required: see BASH_AUTHORING.md §4 inside the fence within the five preceding lines before every collect-agent-results.sh invocation. Note that launch-review.sh is not in the current lint denylist, so these foreground markers are required for the collector fence, not the background launch fences.

### FINDING_46:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:213-236
- **Concern**: Plan mentions the primary write-run-params call and the jq merge recovery, but not the no-file recovery write-run-params callsite. Scenario: If the initial run-params write fails on a --brainstorm --partition run and no run-params.json exists, the recovery call reconstructs the file through write-run-params.sh; without --brainstorm-requested true, the new default false silently skips Step 1d.5 on the next disk read. I found no other gate-retry or mid-run resume path that independently reconstructs run-params.json; later paths re-read the preserved file.
- **Proposed resolution**: Update the whole recovery block, not just the jq merge: guard on partition_requested OR brainstorm_requested, merge both true fields when a file exists, and pass --brainstorm-requested true in the no-file write-run-params fallback; add a regression for --brainstorm --partition no-file recovery.

### FINDING_47:
- **Reviewer(s)**: unknown-slot, Codex-dyn-run-params-consumers
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: scripts/write-run-params.md:13-29
- **Concern**: Plan changes the run-params schema and writer CLI but omits the sibling contract doc that explicitly says to update it when schema changes. Scenario: The landed writer would accept --brainstorm-requested and emit brainstorm_requested, while the shipped contract still documents only partition_requested and says the emitted schema always includes only that optional boolean.
- **Proposed resolution**: Update scripts/write-run-params.md alongside scripts/write-run-params.sh and scripts/test-write-run-params.sh to document --brainstorm-requested, its default false behavior, validation, and emitted brainstorm_requested boolean.

### FINDING_48:
- **Reviewer(s)**: Codex-dyn-run-params-consumers
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:213-240
- **Concern**: The recovery plan is underspecified for brainstorm-only runs because the current fallback block is gated on partition_requested. Scenario: If the primary write-run-params.sh call fails during /design --brainstorm --simple without --partition and the implementer only adds brainstorm_requested inside the existing partition block, recovery never runs; run-params.json remains missing or lacks brainstorm_requested and Step 1d.5's run-params-only guard silently skips brainstorm on resume/re-entry
- **Proposed resolution**: Specify the outer recovery predicate as partition_requested OR brainstorm_requested, merge both booleans atomically when a file exists, recreate the file with both --partition-requested and --brainstorm-requested values when absent, and emit independent jq-unavailable warnings for each requested flag

### FINDING_49:
- **Reviewer(s)**: Codex-dyn-run-params-consumers
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:177-208
- **Concern**: The plan claims --brainstorm fires on the already-planned ad-hoc Q&A branch, but the only proposed Step 1d.5 insertion is in the full-flow path after Step 1d. Scenario: The already-planned router branches before the tier to run-params.json writer; selecting ad-hoc Q&A can exit or answer inline without ever writing brainstorm_requested or reaching Step 1d.5, so the requested brainstorm silently does not run
- **Proposed resolution**: Define the ad-hoc branch contract explicitly: either remove that edge-case claim, or make the branch write run-params.json with --brainstorm-requested true and invoke the brainstorm step before ad-hoc Q&A/exit

### FINDING_50:
- **Reviewer(s)**: Codex-dyn-run-params-consumers
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:200-208,228-236
- **Concern**: The proposed tests do not pin either prompt-side write-run-params.sh callsite to pass --brainstorm-requested. Scenario: The writer-level tests can pass because omitted callers default brainstorm_requested to false; if the SKILL.md primary writer or recovery writer call misses --brainstorm-requested, valid JSON is produced and Step 1d.5 skips without a test failure
- **Proposed resolution**: Add scripts/test-design-structure.sh checks for --brainstorm-requested "$brainstorm_requested" on the primary Step 0b writer, --brainstorm-requested true or the current boolean in the recovery writer, and a jq merge expression that sets .brainstorm_requested = true

### FINDING_51:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:55-79; skills/design/SKILL.md:29
- **Concern**: The plan adds Step 1d.5 but does not update the SKILL.md anti-halt transition list or put the explicit brainstorm carve-out in SKILL.md itself. Scenario: Current anti-halt text applies to all sub-step transitions and only subordinates itself to explicit directives in THIS file; a reference-only override can be missed or overgeneralized
- **Proposed resolution**: Update skills/design/SKILL.md:29 to include 1d→1d.5→1e and add a local carve-out sentence: only non-terminal brainstorm refinement turns may end after synthesis; sentinel or skip immediately continues to Step 1e

### FINDING_52:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:16,39-40
- **Concern**: Termination handling conflicts with the blanket re-print-and-end-turn loop language. Scenario: When the user says ready, the written loop can still be read as mutate brainstorm.md, re-print synthesis, and end the turn, delaying the sentinel write and Step 1e despite the anti-halt rule
- **Proposed resolution**: Specify branch order: first classify the user message; if terminal, write .brainstorm-done and continue to Step 1e in the same turn without reprinting synthesis or ending the turn

### FINDING_53:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:39,174
- **Concern**: Termination vocabulary is too broad and overlaps with normal design-discussion phrasing. Scenario: A user can type "next idea", "not ready", "before we proceed", "looks good but add X", or "go to sketches after we cover Y" and the agent may falsely terminate the brainstorm loop
- **Proposed resolution**: Add disambiguation rules: terminate only on a standalone or primary-intent cue with no negation, condition, or requested refinement; ambiguous messages continue refinement or ask a two-option confirmation

### FINDING_54:
- **Reviewer(s)**: unknown-slot
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:16,39; skills/shared/orchestrator-never.md:5
- **Concern**: The intentional turn boundary does not explicitly preserve the ScheduleWakeup NEVER rule. Scenario: An implementer could treat await user's next free-text message as permission to schedule a wakeup or narrate loop-sleep behavior, weakening the shared single-iteration orchestrator rule
- **Proposed resolution**: Add to brainstorm.md's anti-halt override: this is a passive user-response turn boundary only; MUST NOT call ScheduleWakeup, start sleep or polling prose, or invent any resume mechanism

### FINDING_55:
- **Reviewer(s)**: Codex-dyn-never-rule-compliance
- **Severity**: important
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:16,69-75; skills/design/SKILL.md:29; skills/shared/subskill-invocation.md:90-92; skills/shared/orchestrator-never.md:5-7
- **Concern**: The proposed anti-halt override lives mainly in the new brainstorm reference, but the top-level /design anti-halt banner currently says exceptions must be explicit directives in THIS file and still enumerates 1c→1d→1e without Step 1d.5.. Scenario: The main agent may follow SKILL.md:29 after printing Brainstorm Synthesis and immediately continue to Step 1e, skipping the user brainstorm loop; or future edits may treat the reference-file override as a broad loophole for ending turns after other visible outputs.
- **Proposed resolution**: Update skills/design/SKILL.md:29 as part of the plan: add 1d→1d.5→1e to the transition list and define a single narrow exception that only Step 1d.5 may end the turn after the exact Brainstorm Synthesis print while .brainstorm-done is absent. State that no ScheduleWakeup, summary, handoff, or status recap is allowed, and that after sentinel write the normal anti-halt rule resumes and Step 1e must start immediately. Pin this with test-design-structure.sh.

### FINDING_56:
- **Reviewer(s)**: Codex-dyn-never-rule-compliance
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:39-40; skills/design/references/approval-gates.md:21-24,36,53-57; skills/design/references/discussion-rounds.md:44-46
- **Concern**: The termination vocabulary includes common discussion words such as ready, proceed, looks good, next, and semantically equivalent cues without enough disambiguation for a free-form brainstorming loop.. Scenario: A user can write normal refinement text like "next, compare the fallback scope", "this looks good for CLI but not hooks", or "not ready; proceed with another angle"; semantic detection may write .brainstorm-done and advance to Gate A prematurely.
- **Proposed resolution**: Require an unambiguous termination intent: prefer a structured AskUserQuestion after each synthesis with Continue brainstorming / Proceed to Gate A, or require a standalone command such as /ready or a message whose primary intent is proceed. Explicitly treat negated, quoted, conditional, or refinement-bearing uses of the listed words as continued discussion, mutate brainstorm.md, and re-print synthesis instead of writing the sentinel.
