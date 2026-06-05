### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:104-651-677-815
- **Concern**: Plan folds step-2a/step-2a.5 hosts to Step 2a.5/2b preludes (items 8-10) but never pins SIMPLE entry-fence marker writes or updates Anti-pattern #1. Scenario: SIMPLE skip-to-2b checks both markers in Step 2a entry/2a.2 before Step 2b; Step 2b prelude runs too late, so removing entry-fence writes breaks fresh SIMPLE runs and conflicts with Anti-pattern #1’s “primary SIMPLE-tier write site” contract
- **Proposed resolution**: Explicitly keep `.completed/step-2a` and `.completed/step-2a.5` in the Step 2a entry SIMPLE block (items 7-8); limit items 9-10 to HARD/degraded paths; update Anti-pattern #1 and lines 651/677-679/815 to match

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/discussion-rounds.md:54; skills/design/scripts/step-name-registry.tsv:6
- **Concern**: No-brainstorm folded path can leave step-1d.5 missing even though the registry still requires it. Scenario: The plan says the no-brainstorm route may skip the Step 1d.5 prelude and Step 2a only repairs step-1c, step-1d, step-1d.7, and step-1e. Any later pause-save then sees step-1d.5 as the first missing registry step and resumes back to brainstorm.
- **Proposed resolution**: Either keep running the retained Step 1d.5 entry guard so its skipped-path boundary writes step-1d.5, or have the Step 2a entry fence write step-1d.5 only when brainstorm_requested is not true. Add a pause-resume test for no-brainstorm after Step 2a.

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1260; skills/design/scripts/design-publish.sh:395-408
- **Concern**: Non-architectural skip sentinel does not clear a stale architecture-diagram.md. Scenario: After a Gate C loop, an earlier architectural pass can leave a non-empty architecture-diagram.md. If a later plan classifies as non-architectural and only writes architecture-diagram.skipped, design-publish.sh still prefers the non-empty diagram file and republishes stale Architecture instead of clearing it.
- **Proposed resolution**: In the branch-local non-architectural skip fence, remove architecture-diagram.md and architecture-diagram.candidate.md before touching architecture-diagram.skipped, or change design-publish.sh so the skipped sentinel wins over a stale diagram file.

### FINDING_4:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-pause-save.sh:171-186; skills/design/references/approval-gates.md:183-184
- **Concern**: Folded Step 3 entry only writes step-1e, but pause resume still keys off stale later .completed markers from prior Gate C cycles. Scenario: On Gate C Discuss further or Re-run review, prior step-3 through step-4 markers can already exist while step-4b is withheld. If a pause is requested at the proposed Step 3 entry fence, design-pause-save can pick step-4b instead of step-3, resuming at Gate C and skipping the required fresh review
- **Proposed resolution**: For Step 3 re-entry routes, clear stale downstream sentinels for the review-to-Gate-C span before the pause-check, or add an explicit resume-step override. Add the regression with existing step-3/3.5/3.6/3b/4 markers and missing step-4b.

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:12-18
- **Concern**: Conditional load gate for a short style block. Scenario: Each /design composition site must branch on step type; a missed gate loads style during byte-stable work or skips it for user-facing prose
- **Proposed resolution**: Always inject the block at the user-facing composition steps named in skills/design/SKILL.md; drop the separate When-to-load rule

### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md planned Step 2a entry; plan.txt:32-35; skills/design/references/discussion-rounds.md:54-71; scripts/design-pause-save.sh:180-185
- **Concern**: No-brainstorm folded sentinel set omits step-1d.5. Scenario: The documented no-brainstorm path can skip Step 1d.5 and go 1d→1d.7. Step 2a then writes step-1c, step-1d, step-1d.7, and step-1e before pause-check, but pause-save scans registry order and will still choose missing step-1d.5, so a pause at Step 2a resumes backward into the skipped brainstorm step instead of forward.
- **Proposed resolution**: Add the minimal conditional skipped-step marker: when brainstorm is not requested and Step 2a is repairing folded discussion markers, write .completed/step-1d.5 before pause-check, or write it at the 1d→1d.7 skip boundary. Pin this in the folded-order structure test and pause/resume regression.

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:104
- **Concern**: Plan revises step sentinel hosts but does not update consolidated NEVER #1. Scenario: NEVER #1 still tells the orchestrator HARD step-2a/2a.5 success-boundary marker writes remain valid after those boundaries are replaced by folded prelude hosts and the zero-sketch branch fence
- **Proposed resolution**: Add a SKILL.md plan bullet to rewrite NEVER #1 HARD wording to the folded hosts (Step 2a.5 prelude, Step 2b prelude, zero-sketch branch fence) while keeping the SIMPLE Step 2a entry carve-out

### FINDING_8:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:32-35; skills/design/references/discussion-rounds.md:54; skills/design/scripts/step-name-registry.tsv:4-8
- **Concern**: No-brainstorm folded writes still omit step-1d.5. Scenario: When brainstorm is off, discussion-rounds routes Step 1d directly to Step 1d.7, but the registry orders 1d.5 before 1d.7. Step 2a would write 1c, 1d, 1d.7, and 1e before pause-save, leaving step-1d.5 missing, so a pause at or after Step 2a resumes at 1d.5 and replays/skips backward instead of continuing forward.
- **Proposed resolution**: Add an idempotent skipped-brainstorm step-1d.5 write for the no-brainstorm path before any Step 2a pause-check, or route no-brainstorm through the retained Step 1d.5 entry guard so its boundary-local skipped write runs; pin this in structure and pause/resume tests.

### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt
- **Concern**: Plan artifact at the session path could not be read (tooling unavailable). Scenario: Requirements/Completeness review cannot verify goals acceptance criteria constraints wiring or validation steps against the proposed change
- **Proposed resolution**: Re-run this reviewer slot once plan.txt is readable; do not treat this pass as plan approval

### FINDING_10:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1260-1295; skills/design/scripts/design-publish.sh:395-408
- **Concern**: Step 3b skip-sentinel plan is silent on stale opposite artifacts. Scenario: The plan makes architecture-diagram.skipped branch-local, but a Gate C loop can reuse the same DESIGN_TMPDIR after the plan changes class. A prior non-architectural pass can leave architecture-diagram.skipped behind, so a later architectural sanitizer or generation failure still makes design-publish.sh clear Architecture. A prior architectural pass can leave architecture-diagram.md behind, so a later non-architectural skip can publish the stale diagram instead of clearing it.
- **Proposed resolution**: Revise Step 3b to clear stale artifacts at the classifier branch: on non-architectural skip, remove architecture-diagram.md before touching architecture-diagram.skipped; on architectural paths, remove architecture-diagram.skipped before generation/failure/success handling. Add a structure test for these branch-local cleanup lines.

### FINDING_11:
- **Reviewer(s)**: Cursor-dyn-resume-state
- **Severity**: important
- **Focus area**: correctness
- **Location**: .cache/larch/sessions/claude-design-larch2-vY2hn5/plan.txt
- **Concern**: Review slot could not read plan.txt or any repository files (all Read/Grep/Glob/Shell attempts failed). Scenario: resume-state validation is skipped; pipeline may treat the slot as clean or drop it with no pause/resume contract check
- **Proposed resolution**: Re-run this review slot after plan.txt and repo reads succeed; do not merge on a salvaged empty result

### FINDING_12:
- **Reviewer(s)**: Codex-dyn-resume-state
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:32-36; skills/design/references/discussion-rounds.md:52-55; skills/design/scripts/step-name-registry.tsv:4-10
- **Concern**: Step 2a's no-brainstorm repair omits step-1d.5 even though the unchanged discussion reference can bypass Step 1d.5 entirely. Scenario: With brainstorm off, Step 1d can route straight to Step 1d.7; Step 2a then writes 1c, 1d, 1d.7, and 1e but not 1d.5, so pause-save's registry order resumes at 1d.5 instead of 2a
- **Proposed resolution**: Conditionally write step-1d.5 in the Step 2a entry repair only when brainstorm was not requested or .brainstorm-done exists, or instead make the Step 1d.5 entry guard always run and write its boundary marker on the skip path

### FINDING_13:
- **Reviewer(s)**: Codex-dyn-resume-state
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:43; skills/design/SKILL.md:1258-1263; skills/design/scripts/design-publish.sh:395-408
- **Concern**: Branch-local architecture-diagram.skipped writes do not clear a stale skip sentinel when a later Gate C loop takes the architectural path. Scenario: A run can first classify a plan as non-architectural and write architecture-diagram.skipped, then later revise to an architectural plan; if diagram generation or sanitizer fails, no architecture-diagram.md is produced and design-publish still sees the stale skipped sentinel and clears Architecture despite the latest plan being architectural
- **Proposed resolution**: At Step 3b architectural-branch entry, remove any stale $DESIGN_TMPDIR/architecture-diagram.skipped before generation/failure handling, and pin this in the structure test so only the current non-architectural branch leaves the skip sentinel in place

### FINDING_14:
- **Reviewer(s)**: Codex-dyn-structure-harness
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:1681-1715
- **Concern**: Folded sentinel checks can remain permissive if they inherit the current bare token grep. Scenario: A comment or prose literal containing .completed/step-X could satisfy presence/order while no shell write occurs
- **Proposed resolution**: Make assert_folded_sentinel_writes match actual non-comment shell write lines like : > "$DESIGN_TMPDIR/.completed/step-X" inside the extracted host fence, then check source-env < write < pause-check

### FINDING_15:
- **Reviewer(s)**: Codex-dyn-structure-harness
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:89-97,146-151,1663-1677; skills/design/SKILL.md:1367-1373,1446-1454
- **Concern**: Existing fence scans only recognize unindented ```bash fences, but key target fences are indented. Scenario: Deleted-prelude guards or publish/Gate C folded-order checks can miss indented fences and pass a broken structure
- **Proposed resolution**: Use the new whitespace-tolerant fence extractor for the folded host checks, deleted-prelude negative guards, and pause-check scan; match both opening and closing fences with optional leading whitespace

### FINDING_16:
- **Reviewer(s)**: Cursor-dyn-operator-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1346-1373 (proposed Step 4 / 4b fold)
- **Concern**: Deferring `.completed/step-4` from the Step 4 success boundary into the merged Gate C `emit-design-plan-preview.sh --variant gatec` fence widens the `STEP=4` resume window through early Step 4b. Scenario: `design-pause-save.sh` picks the first registry step whose sentinel is absent (`scripts/design-pause-save.md:16-20`). Today `step-4` is written right after the rejected-findings report, before Step 4b starts (`skills/design/SKILL.md:1349`). The plan moves that write to the Gate C preview fence (`plan.txt` items 16–17), which runs only after the `4b: gate C` breadcrumb and `approval-gates.md` Presentation setup (`skills/design/SKILL.md:1359-1373`, `skills/design/references/approval-gates.md:171-173`). A pause in that gap still saves `STEP=4`; resume replays Step 4 (rejected findings) instead of Gate C (`STEP=4b`), which is a regression from current semantics
- **Proposed resolution**: Write `step-4` at the Step 4 success boundary (after rejected-findings output, before Step 4b), or in a minimal Step 4b entry prelude (`source-env` → `step-4` → pause-check) before Gate C presentation; keep the merged gatec fence for timing + preview only, or make its `step-4` write idempotent after the earlier boundary write

### FINDING_17:
- **Reviewer(s)**: Codex-dyn-operator-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1147-1148,skills/design/SKILL.md:1375-1378,scripts/design-pause-save.sh:170-187,skills/design/scripts/step-name-registry.tsv:13-18
- **Concern**: Backward Gate B/Gate C loops are not reconciled with the linear pause registry. Scenario: After Gate C Discuss further or Re-run review panel, prior step-3 through step-4 sentinels can remain while step-4b is still missing; a pause at the proposed folded Step 1e or Step 3 boundary would be saved as STEP=4b, so resume can skip the required discussion/re-review and return to final approval with stale review state. Gate B Switch to discussion has the same shape with step-3/step-3.5 sentinels.
- **Proposed resolution**: Add a minimal route-local sentinel reset before backward jumps: clear step-1e and the rerun range for discussion loops, and clear step-3 through step-4b for review reruns, before entering the earlier step. Extend the pause/resume regression with fixtures that seed prior downstream sentinels and assert pause-save resumes at Gate A or Step 3, not Gate C.
