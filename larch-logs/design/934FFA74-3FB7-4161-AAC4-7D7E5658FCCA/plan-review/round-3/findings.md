### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1014-1028
- **Concern**: Step 3 has two entry bash fences but the plan only names a single Step 3 entry host for the folded step-1e write. Scenario: Gate A Ready for review goes straight to Step 3. If step-1e is folded only into the emit-design-plan-preview fence, the timing prelude fence at 1014-1018 still runs first with pause-check but no step-1e. A pause between those fences or a resume snapshot taken after the timing fence can lack step-1e and replay Gate A instead of continuing review
- **Proposed resolution**: Pin the folded step-1e write to the first bash fence after <!-- step:3 (timing prelude), before its pause-check; mirror that host in assert_folded_sentinel_writes via extract_first_bash_fence_after. Optionally idempotently repeat in the preview fence

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1446-1455
- **Concern**: Step 5c publish fence remains a surviving source-env Bash fence without a pause-check. Scenario: The plan adds Step 5c marker logic inside this fence, but a pause requested after Gate C and before publish would still run design-publish.sh, potentially writing the plan, renaming the issue, and publishing logs instead of saving a pause snapshot
- **Proposed resolution**: Add the canonical pause-check immediately after the source-env line and before set +e/design-publish.sh, and have the updated structure test cover this indented fence.

### FINDING_3:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-pause-save.sh:170-188; skills/design/SKILL.md:1014-1028
- **Concern**: Step 3 folded step-1e write is not enough to make direct-review pause resume at Step 3. Scenario: design-pause-save.sh derives STEP from existing sentinels, not current control flow. If Step 3 entry only writes step-1e, a clean direct-review snapshot can resume at Step 2a because step-2a/2b are missing, while a Gate C/Gate A re-review with stale step-3+ sentinels can resume past review.
- **Proposed resolution**: Add a route shape the saver can distinguish before Step 3 pause-check: either reset downstream review/finalization sentinels and ensure prior plan-production sentinels exist when plan.txt exists, or add an explicit Step 3 re-entry marker that design-pause-save.sh honors. Extend the pause-resume test to cover a prior Gate C stale-sentinel direct-review case.

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:572-604
- **Concern**: Plan defers `.completed/step-1d.5` from the Step 1d.5 success/sk boundary to the Step 2a entry host fence. Scenario: `design-pause-save.sh` picks STEP by walking `step-name-registry.tsv` for the first missing `.completed/step-*` marker. Today `step-1d.5` is written when Step 1d.5 finishes (line 572), so a pause during Step 1d.7 or the Step 1e skip path resumes at `1d.7`/`1e`. After the fold, those segments have no Bash boundary and `step-1d.5` stays absent until Step 2a, so pause-save emits `STEP=1d.5` and `/design` replays brainstorm instead of outline/Gate-A work
- **Proposed resolution**: Keep the existing Step 1d.5 success-boundary write (one line, no timing prelude); fold only `step-1c`, `step-1d`, `step-1d.7`, and `step-1e`. Drop `step-1d.5` from the Step 2a folded batch and from the `step-1d.5 → Step 2a entry` row in `assert_folded_sentinel_writes`

### FINDING_5:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1446-1449
- **Concern**: Step 5c publish fence is an indented surviving source-env Bash fence, but the plan's Step 5c changes do not add the pause-check line while the structure-test plan starts recognizing indented fences. Scenario: Updated structure tests can fail, or a pause requested before design-publish.sh is ignored until after final publish/rename work
- **Proposed resolution**: Add the canonical design-pause-save check immediately after the source-env line in the Step 5c design-publish.sh fence, before set +e / _publish_out, and keep the gated step-5c write after PLAN_WRITE_OK=true

### FINDING_6:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1260-1315
- **Concern**: Step 3b skip sentinel is planned for the shared completion boundary without a branch discriminator. Scenario: The Step 3b completion boundary is also used after sanitizer rejection, diagram generation failure, and successful diagram generation. If the new architecture-diagram.skipped write lands there unguarded, Step 5c will treat non-skip diagram failures as intentional non-architectural skips and clear any existing Architecture section.
- **Proposed resolution**: Keep architecture-diagram.skipped branch-local to the non-architectural path, or make the boundary write it only under an explicit skip-only flag; add the structure assertion against that branch-specific placement rather than the whole shared boundary.

### FINDING_7:
- **Reviewer(s)**: Cursor-dyn-sentinel-chain
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:1681-1716
- **Concern**: `assert_step_completion_sentinels` still requires each `.completed/step-*` token inside that step's anchor slice, but the plan relocates many sentinels into foreign host fences. Scenario: After SKILL.md folds sentinels, checks for 1e, 1d.5, 2a.5, 3, 3.5, 4, 4b, and 5d will fail even when `assert_folded_sentinel_writes` passes; implementers may “fix” tests by weakening folded ordering instead of relocating step-local grep
- **Proposed resolution**: Update `assert_step_completion_sentinels` to skip host-absorbed steps (delegate to `assert_folded_sentinel_writes`) or resolve tokens via the plan’s host map; keep step-local grep only for steps that still self-write (5b, 3b, Gate-B-bypass triple writes, postplan `step-2b`/`step-2b.5`, etc.)

### FINDING_8:
- **Reviewer(s)**: Codex-dyn-sentinel-chain
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/discussion-rounds.md:54-71; skills/design/SKILL.md:562-582
- **Concern**: No-brainstorm Step 1d path can bypass the planned Step 1d.5 host fence for step-1c and step-1d. Scenario: The plan folds step-1c and step-1d only into the Step 1d.5 prelude, but discussion-rounds.md still routes Step 1d directly to Step 1d.7 when brainstorm is off. Because the plan also deletes the Step 1d.7 prelude, a pause saved at the Step 2a boundary on that route can still lack step-1c and step-1d and resume too far back.
- **Proposed resolution**: Add step-1c and step-1d as idempotent folded writes in the Step 2a entry fence too, or change the Step 1d no-brainstorm route to always pass through the retained Step 1d.5 skip/prelude host before Step 1d.7.

### FINDING_9:
- **Reviewer(s)**: Cursor-dyn-test-claim-mapping
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:35,62,138
- **Concern**: Step 2b prelude must idempotently write both step-2a and step-2a.5 but assert_folded_sentinel_writes maps only step-2a.5 to the Step 2b host. Scenario: SIMPLE/HARD resumes that depend on Step 2b re-touching step-2a could regress without a failing structure test
- **Proposed resolution**: Add step-2a → Step 2b prelude (before pause-check) to the assert_folded_sentinel_writes host table alongside step-2a.5

### FINDING_10:
- **Reviewer(s)**: Cursor-dyn-test-claim-mapping
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:56-75
- **Concern**: skills/design/SKILL.md:1107-1129. Scenario: assert_folded maps step-3 solely to Step 3.5 prelude while Gate-B-bypass keeps inline triple-sentinel writes in Step 3 branch prose
- **Proposed resolution**: An assert_folded implementation that treats Step 3.5 as the only valid step-3 host can false-fail or fight preserved Gate-B-bypass pins Document that assert_folded applies only to listed host fences; keep Gate-B-bypass prose writes under existing contains pins without requiring pause-check ordering there

### FINDING_11:
- **Reviewer(s)**: Cursor-dyn-test-claim-mapping
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:40,75
- **Concern**: skills/design/SKILL.md:1260,1301-1315. Scenario: Step 3b non-architectural skip moves architecture-diagram.skipped into the FINALIZE completion fence but tests only preserve prose mention and FINALIZE ordering
- **Proposed resolution**: Co-located skip write could move back to orchestrator prose while structure tests still pass Extend assert_step3b_finalize_boundary (or assert_folded) to require architecture-diagram.skipped in the same bash fence as ACTION=FINALIZE before step-3b

### FINDING_12:
- **Reviewer(s)**: Cursor-dyn-test-claim-mapping
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:36-37
- **Concern**: skills/design/SKILL.md:1014-1028. Scenario: Gate A direct-review folds step-1e into Step 3 entry but the plan does not name which of two Step 3 entry fences hosts the write
- **Proposed resolution**: step-1e may be written after the first pause-check so pause/resume replays Gate A instead of continuing review Pin step-1e to the first Step 3 timing prelude fence (before its pause-check) and add a matching assert_folded host row

### FINDING_13:
- **Reviewer(s)**: Cursor-dyn-test-claim-mapping
- **Severity**: latent
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:23,74
- **Concern**: scripts/test-design-structure.sh:1661-1678. Scenario: Step 0c gains a bash fence with pause-check but check 21 starts at step 1c
- **Proposed resolution**: Pause-check regression in the new Step 0c fence would not be caught Extend assert_bash_fences_have_pause_check (or add a Step 0c-specific guard) to cover the Step 0c fence

### FINDING_14:
- **Reviewer(s)**: Codex-dyn-test-claim-mapping
- **Severity**: latent
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:35,61-62; scripts/design-pause-save.sh:180-186; skills/design/scripts/step-name-registry.tsv:9-11
- **Concern**: Step 2b's claimed idempotent multi-write is only half-covered by the stated structure test mapping. Scenario: The plan says Step 2b writes both step-2a and step-2a.5, but the test bullet only asserts step-2a.5 at Step 2b; an implementation that omits the Step 2b step-2a repair could pass the proposed tests while a pause with step-2a missing routes back by registry order
- **Proposed resolution**: Add step-2a to the Step 2b prelude assertion alongside step-2a.5, before pause-check.

### FINDING_15:
- **Reviewer(s)**: Cursor-dyn-pause-protocol-safety
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:33-34,61
- **Concern**: Proposed HARD zero-sketch degraded Bash fence sources env and writes step-2a/step-2a.5 but never runs the canonical pause-check line. Scenario: The new fence sits on the 2a→2b short-circuit after both externals are down; without `[ -f "$DESIGN_TMPDIR/.pause-requested" ] && exec … design-pause-save.sh`, a restored or freshly set `.pause-requested` is not honored until a later boundary, and `assert_bash_fences_have_pause_check` will flag any new fence in the Step 2a region that omits the prelude
- **Proposed resolution**: Add the standard two-line prelude (source-env then pause-check) to the zero-sketch fence spec; place step-2a/step-2a.5 writes after source-env and before pause-check; extend `assert_folded_sentinel_writes` mapping line 61 to require pause-check ordering like the other host fences

### FINDING_16:
- **Reviewer(s)**: Codex-dyn-pause-protocol-safety
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1446-1454; scripts/test-design-structure.sh:1661-1678
- **Concern**: Plan brings indented fences such as design-publish.sh into structure extraction but does not add the canonical pause check to the indented Step 5c source-env fence. Scenario: A pause requested before Step 5c publish is not honored before plan publish and rename; if the widened extractor checks source-env fences, the structure test also fails on this fence
- **Proposed resolution**: Add the canonical .pause-requested design-pause-save.sh line immediately after the Step 5c source-env line and before set +e / design-publish.sh, and make the widened pause-check assertion cover indented fences

### FINDING_17:
- **Reviewer(s)**: Codex-dyn-pause-protocol-safety
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:439,562-572
- **Concern**: Plan moves step-1d.5 completion to Step 2a only, but the already-planned ad-hoc Q&A brainstorm path runs Step 1d.5 then exits without Step 2a. Scenario: A pause/save after that terminal brainstorm path sees step-1d.5 missing and resumes by replaying Step 1d.5
- **Proposed resolution**: Keep a boundary-local step-1d.5 write for the Step 0b already-planned Q&A-only terminal branch, or explicitly write it before that branch runs the Final summary block
