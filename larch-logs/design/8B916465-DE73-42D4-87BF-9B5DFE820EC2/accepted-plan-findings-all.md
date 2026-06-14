### FINDING_1: Anti-halt emit contract missing from plan update list and lacks delivery-channel prohibition
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements, Cursor-Pragmatic, Cursor-dyn-prompt-contract
- **Severity**: important
- **Concern**: The plan’s enumerated final-summary emit-site updates omit `skills/design/SKILL.md`’s anti-halt continuation reminder (~line 29). That paragraph still authorizes marker-based verbatim emission from completed task output with only a Read fallback note and no explicit prohibition on Bash/Python/sed/awk (or other tool stdout) for user-visible delivery. Orchestrators that treat anti-halt text as authoritative can still extract via tool calls and reproduce the collapsible-tool-output / missing `## Review Phase Detail` failure mode.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add the anti-halt paragraph to the design SKILL update list and mirror the same explicit delivery-channel prohibition there
  - From Cursor-Pragmatic: Add skills/design/SKILL.md anti-halt continuation reminder (~line 29) to the explicit emit-site update list with the same Read-to-orchestrator-text prohibition used elsewhere
  - From Cursor-dyn-prompt-contract: Add skills/design/SKILL.md:29 to the update list with the same explicit rule block as other emit sites (Read for context only; write extracted body as orchestrator chat text; no tool stdout for user-visible delivery)




### FINDING_2: Mandatory final-summary enumeration omits Review Phase Detail
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Design SKILL.md mandatory-body lists (e.g. around lines 349, 867, 882–884) name title, mode, duration, cost, tokens, and top-level bullets but not `## Review Phase Detail` (round table and per-round Gantt charts). The reported failure reproduced only Duration/Cost/Plan-review bullets while claiming verbatim emit. The current bullet inventory can be read as exhaustive, so orchestrators may lawfully omit the review-phase appendix even when markers contain it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add ## Review Phase Detail (round table and per-round Gantt charts) to every design final-summary mandatory-body enumeration alongside title, mode, duration, cost, and tokens; state that partial top-level bullets alone are a contract violation

**Merge note:** FINDING_1 targets test harness locality (`scripts/test-design-structure.sh` / `test-implement-structure.sh`); FINDING_2 targets SKILL.md contract prose (`skills/design/SKILL.md`). Same user-visible symptom, different fixes and code paths, so not merged.



### FINDING_1: Design SKILL.md emit sites still authorize stdout/Bash extraction instead of Read → orchestrator chat text
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Multiple final-summary emit contracts in `skills/design/SKILL.md` still say extract from `design-step5c.sh` **stdout** (abort path ~863, Step 5c item 5 ~867, Final summary block ~349, post-5c no-recap ~882–884) and reference `REPORT_GATE_SIDECARS_FILE` via stdout/`Read`/`cat`, while other sites say "completed task output." An orchestrator can treat stdout wording as permission to run Bash or `python3 -` against tool output, reintroducing collapsible-tool delivery and partial emission (e.g. top-level bullets only, omitting `## Review Phase Detail`) even if a delivery-channel ban is added elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: At every final-summary emit site (863, 867, 349, 882-884), replace stdout with completed background-task output consumed via Read, then write orchestrator chat text; forbid re-parsing via Bash or Python even for KV lines like REPORT_GATE_SIDECARS_FILE
  - From Cursor-Pragmatic: Add the shared Read-to-orchestrator-text rule at this site and replace stdout wording with Read of the completed background task output (then marker slice), matching Step 5c item 5 / Final summary block




### FINDING_1: Legacy final-summary prose pins in test-design-structure.sh not retired
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan adds new final-summary delivery-channel pins but leaves `assert_step5_fold_and_summary_markers` positive `contains` checks at lines 656–657 that still require legacy marker-extraction wording in `skills/design/SKILL.md`. After SKILL prose is rewritten to Read-to-orchestrator-text, `make test-design-structure` will fail even when the feature is implemented correctly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Update assert_step5_fold_and_summary_markers: replace lines 656-657 with pins for the new delivery-channel and mandatory-body inventory strings (or drop them if covered by the new Python/grep checks)
  - From Cursor-Pragmatic: In `### UPDATED: scripts/test-design-structure.sh`, explicitly replace lines 656-657 (or repoint them) to pin the new delivery-channel phrases (`Read of the completed background-task output`, `orchestrator chat markdown` / `orchestrator text`, `## Review Phase Detail`) instead of the old extraction/fallback strings; keep wrapper marker assertions unchanged




### FINDING_1: Implement SKILL still anchors final-summary body on `--print-stdout`
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: `skills/implement/SKILL.md` NEVER #17 (line 63) and Step 17 prose (line 818) still describe the structured summary block as coming from `write-final-report.sh --print-stdout`, but `step-18b-final-report.sh` intentionally omits `--print-stdout` (per `step-18b-final-report.md`). The "How to apply" section already points at `summary-final.md` orchestrator emit, but the opening NEVER sentence and Step 17 cost-line paragraph contradict that. Orchestrators may treat Step 17 Bash stdout as the authorized body source and skip full verbatim chat emission (including `## Review Phase Detail`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: When editing NEVER #17 and Step 17 (~818), explicitly retire `--print-stdout` as a body source; state that summary-final.md is rendered by write-final-report.sh and must be loaded only via Read then emitted as orchestrator chat text


### FINDING_2: Design Final summary block item 4 conflates Step 5c with cancellation fence
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: In `skills/design/SKILL.md` at line 349, the `### Final summary block` emit instruction opens with "After Step 5c `design-publish.sh` returns…" even though line 337 explicitly says this single-phase fence does **not** run on the Gate-C happy path (Gate-C uses `design-publish.sh` internally). Item 4 partially rewords extraction but keeps the Step 5c opening sentence and `PLAN_WRITE_OK` branches. Cancellation-path orchestrators may read the wrong completed-task output (Step 5c instead of `design-step-final-summary.sh`) or skip the notification body from the actual fence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In item 4 scope Final summary block (~349) to design-step-final-summary.sh only: remove the Step 5c opening sentence and PLAN_WRITE_OK branches; anchor emit on Read of that fence's completed background-task output (or final-summary.md fallback).



