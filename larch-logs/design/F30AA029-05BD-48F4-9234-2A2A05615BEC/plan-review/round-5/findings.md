### FINDING_1:
- **Reviewer(s)**: Cursor-Arch, Codex-Pragmatic, Cursor-Requirements, Cursor-dyn-shell-state, Codex-dyn-harness-wiring
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:47-54
- **Concern**: Step 0 post-invoke parent rehydration snippet is missing the closing `fi` for the outer `if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ]` block. Scenario: The proposed fence is invalid bash; Step 0 initial/resume subprocesses fail at parse time before bootstrap routing runs
- **Proposed resolution**: Add `fi` immediately before `export CLAUDE_PLUGIN_ROOT` so the outer conditional closes and export sits after both nested `if` blocks

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md planned Step 0 fence (plan.txt:47-54)
- **Concern**: Planned parent rehydration block is missing the outer fi. Scenario: Both Step 0 initial and dirty-tree resume fences get an unterminated if and fail before parse-bootstrap-routing-envelope.sh
- **Proposed resolution**: Insert fi before export CLAUDE_PLUGIN_ROOT in the planned block and apply the same fixed block to both fences

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-timing-rehydration.sh:153-156; scripts/test-implement-timing-rehydration.md:10-15; skills/implement/SKILL.md:770-795
- **Concern**: Planned Step 5 fence merge removes one canonical plugin-root source guard but leaves hard-coded cardinality unchanged. Scenario: Deleting the standalone telemetry fence and merging it with the run-step5-review fence drops the source guard count from 42 to 41, so the planned make test-implement-timing-rehydration run fails
- **Proposed resolution**: Update the harness and sibling doc expected source-guard count to 41 as part of the Step 5 merge, or keep the second guarded fence if the count must stay 42

### FINDING_4:
- **Reviewer(s)**: Cursor-Edge, Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:46-54
- **Concern**: Step 0 post-invoke rehydration block missing closing fi for outer CLAUDE_PLUGIN_ROOT guard. Scenario: Step 0 initial/resume Bash fence fails to parse; parse-bootstrap-routing-envelope never runs
- **Proposed resolution**: Add fi before unconditional export CLAUDE_PLUGIN_ROOT in both Step 0 fences

### FINDING_5:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-timing-rehydration.sh:155-156
- **Concern**: Step 5 fence merge drops one plugin-root guard but harness still expects 42. Scenario: make test-implement-timing-rehydration fails despite listed acceptance target
- **Proposed resolution**: Add plan step to bump expected plugin_root_source_count to 41 and sync SKILL.md line 115 inventory if kept

### FINDING_6:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-implement-bootstrap-invoke.sh:133-139
- **Concern**: Self-derive sandbox case may still run through run_wrapper which exports CLAUDE_PLUGIN_ROOT. Scenario: New test passes without proving unset-env self-derive from item 1
- **Proposed resolution**: Invoke wrapper with CLAUDE_PLUGIN_ROOT unset outside run_wrapper (e.g. env -u) and assert stub reached with derived root

### FINDING_7:
- **Reviewer(s)**: Codex-Edge, Codex-Innovation, Codex-Requirements, Codex-dyn-shell-state
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:317-318 and 386-388
- **Concern**: Proposed Step 0 parent rehydration snippet is missing the outer fi. Scenario: Both initial and dirty-tree resume Step 0 fences would hit a Bash syntax error after bootstrap success, before sourcing parse-bootstrap-routing-envelope.sh, so item 1 still blocks orchestration
- **Proposed resolution**: Add the missing fi after the inner plugin-root.env source block and before export CLAUDE_PLUGIN_ROOT in both insertions, or collapse the rehydration to a single guarded source line

### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:308
- **Concern**: [SCOPE-REDUCTION] Item 1 wrapper self-derive does not fix the initial Step 0 invoke path when CLAUDE_PLUGIN_ROOT is unset. Scenario: On first entry IMPLEMENT_TMPDIR and plugin-root.env do not exist so pre-bootstrap guards are no-ops; ${CLAUDE_PLUGIN_ROOT}/scripts/implement-bootstrap-invoke.sh expands to /scripts/implement-bootstrap-invoke.sh and fails before wrapper self-derive runs — the exact #3448 item 1 symptom
- **Proposed resolution**: Add a pre-invoke CLAUDE_PLUGIN_ROOT default in the Step 0 initial fence (issue alternate: explicit ${CLAUDE_PLUGIN_ROOT:-<plugin-root>} line) or invoke implement-bootstrap-invoke.sh via a literal absolute script path; wrapper-only export is necessary but not sufficient

### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-timing-rehydration.sh:155
- **Concern**: Merging Step 5 fences drops one canonical plugin-root.env source guard without updating the pinned count of 42. Scenario: Plan deletes one of two Step 5 guards (42→41) but test-implement-timing-rehydration is in the required test list and will fail make test-implement-timing-rehydration
- **Proposed resolution**: Update the expected plugin_root_source_count (and document why) or retain a canonical guard so the count stays 42; prefer reusing the canonical one-liner in Step 0 post-invoke instead of a bespoke grep-only block

### FINDING_10:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:160-186
- **Concern**: Banner dynamic_archetypes_cap uses session-env then ambient LARCH_DYNAMIC_ARCHETYPES_MAX but run-step5-review.sh reads only session-env at scripts/run-step5-review.sh:169. Scenario: Banner can show an ambient-env cap while the launcher path never sees it; only review-and-fix.sh applies the three-tier precedence
- **Proposed resolution**: Accept as cosmetic-only or align banner precedence with run-step5-review.sh (session-env + default 6) to avoid misleading operator copy

### FINDING_11:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:47-54
- **Concern**: Step 0 post-invoke block re-sources plugin-root.env but does not export IMPLEMENT_TMPDIR from _inv_out before routing parse. Scenario: Downstream fences and degraded-tools gate assume exported IMPLEMENT_TMPDIR; parse-bootstrap-routing-envelope.sh sets it from _inv_out but later same-turn Bash blocks may not see it
- **Proposed resolution**: After parsing IMPLEMENT_TMPDIR from _inv_out add IMPLEMENT_TMPDIR="$_inv_tmpdir" and export IMPLEMENT_TMPDIR before sourcing parse-bootstrap-routing-envelope.sh

### FINDING_12:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:47-54
- **Concern**: Step 0 post-invoke parent rehydration fence missing closing fi. Scenario: Orchestrator copies the proposed block verbatim; bash exits with a syntax error before parse-bootstrap-routing-envelope.sh runs on initial and dirty-tree resume paths
- **Proposed resolution**: Add fi before export CLAUDE_PLUGIN_ROOT (or move export inside the inner branch and close both if blocks)

### FINDING_13:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-timing-rehydration.sh:147-151
- **Concern**: Step 5 fence merge drops one IMPLEMENT_TMPDIR assign/export pair but plan omits harness update. Scenario: Merging telemetry into the banner fence reduces IMPLEMENT_TMPDIR assign count by 1 while step-telemetry-mark count stays 4; test-implement-timing-rehydration fails on tmpdir coupling invariant
- **Proposed resolution**: Add UPDATED scripts/test-implement-timing-rehydration.sh (and sibling .md if needed) to decrement expected tmpdir assign/export coupling from 12 to 11 after the Step 5 fence merge

### FINDING_14:
- **Reviewer(s)**: Cursor-dyn-scope-guard
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:42-59
- **Concern**: [SCOPE-REDUCTION] Step 0 parent-shell post-invoke rehydration exceeds the approved outline (item 1 was wrapper-only; approved Surfaces list only `implement-bootstrap-invoke.sh` and explicitly avoided Step 0 SKILL edits). Scenario: The plan adds an 8-line post-invoke block to both initial and dirty-tree resume Step 0 fences plus acceptance criteria, beyond the three scoped DX fixes and contradicting plan Summary line 7 ("No Step 0 SKILL fallback")
- **Proposed resolution**: Drop the Step 0 fence edits; keep item 1 in `scripts/implement-bootstrap-invoke.sh` only. If the parent shell still needs `CLAUDE_PLUGIN_ROOT` for `parse-bootstrap-routing-envelope.sh`, use the issue's cheaper one-line pre-invoke template export at the fence top, or emit `CLAUDE_PLUGIN_ROOT=` on wrapper stdout and add a single parent parse line—not dual-fence post-invoke sourcing

### FINDING_15:
- **Reviewer(s)**: Codex-dyn-scope-guard
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:306-318,364-388
- **Concern**: [SCOPE-REDUCTION] Step 0 parent-shell rehydration exceeds the approved SKILL.md surface and the proposed literal block is malformed. Scenario: The approved scope limits SKILL.md edits to the Step 5 Scripted review loop, but the plan adds a new Step 0 parent-shell contract in both initial and resume fences; if retained, the shown block also lacks the outer closing fi before export CLAUDE_PLUGIN_ROOT, which would break the Step 0 fence before routing parse
- **Proposed resolution**: Delete the Step 0 parent-shell rehydration subsection plus related acceptance/failure-mode bullets and keep Item 1 in scripts/implement-bootstrap-invoke.sh; if parent rehydration is separately approved, add the missing fi and a targeted Step 0 test

### FINDING_16:
- **Reviewer(s)**: Cursor-dyn-harness-wiring
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:Step 0 fence (plan lines 47-54)
- **Concern**: Proposed Step 0 post-invoke parent rehydration block is missing the closing fi for the outer if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] and nests export CLAUDE_PLUGIN_ROOT inside that unclosed if. Scenario: Copying the plan fence verbatim yields a bash syntax error before parse-bootstrap-routing-envelope.sh runs; Item 1 parent-shell fix never executes
- **Proposed resolution**: Close the outer if with fi before an unconditional export CLAUDE_PLUGIN_ROOT (inner if/fi around plugin-root.env source only)

### FINDING_17:
- **Reviewer(s)**: Codex-dyn-harness-wiring
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:770-795; scripts/test-implement-timing-rehydration.sh:154-156
- **Concern**: Step 5 fence merge removes one canonical plugin-root source guard but the plan does not update the hardcoded rehydration-count harness. Scenario: make test-implement-timing-rehydration will see plugin_root_source_count drop from 42 to 41 and fail despite the intended single-fence Step 5 shape
- **Proposed resolution**: Update scripts/test-implement-timing-rehydration.sh to expect the new guard count, or keep two Step 5 fences if that invariant is meant to remain unchanged
