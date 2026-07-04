### FINDING_1: Nested macro fixture still lacks the nested-heading case
- **Reviewer(s)**: Codex-Arch, Codex-Innovation
- **Severity**: important
- **Concern**: The replacement implement macro test still only exercises peer/same-depth heading boundaries, so a bug that clears conditional state on a nested subheading could still pass unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add a nested subheading inside the macro fixture and assert its reference stays in conditional_files until the next peer or shallower heading; keep the existing peer-heading assertion
  - From Codex-Innovation: Add a nested heading under one macro and assert its reference stays conditional until a peer or shallower heading closes the section.


### FINDING_2: Failsafe rephrase must keep the postplan gate
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The planned failsafe-missing-rows wording change could remove the exit-0 guard and the instruction to run the retained terminal postplan path, which would weaken the runtime contract for design-step2b-postplan.sh.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: An implementer following the plan could ship SKILL prose that no longer tells the orchestrator to run design-step2b-postplan.sh on failsafe-missing-rows, or that weakens the exit-0 gate beyond classifier needs Rephrase in one sentence that keeps both runtime verbs, e.g. load references/step2b-drafter-failsafe.md only when exit 0 and the trusted postplan action row is absent, then run the retained terminal postplan path; do not delete the run clause or the exit-0 predicate


### FINDING_3: Implement macro suppression must become conditional tracking
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: Replacing implement macro suppression needs to follow the design-style peer/shallower reset rule and also remove the existing suppressed_section skip; otherwise nested headings or macro-contained mandatory refs remain misclassified or invisible to the ratchet.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Porting the wrong reset rule leaks conditional classification across nested headings inside a macro or ends macro scope too early, breaking the new real-implement scan assertions for checks-repair-loop.md When reusing conditional_section_depth for Checks Failure Entry Macro and Durable Bail to Step 18 Macro, port _update_design_scan_state heading_depth logic (including clearing suppressed_section and the parse-loop continue skip), and add the nested-### fixture called out in edge cases
  - From Cursor-Requirements: In the lint_skill_closure_growth.py plan steps, explicitly remove SUPPRESSED_IMPLEMENT_SECTIONS, ScanState.suppressed_section, the _update_implement_scan_state suppression branch, and the if state.suppressed_section continue guard; register the two implement macro headings in a conditional-section set that drives conditional_section_depth the same way design sections do


### FINDING_1: Design final-summary citations are still invisible to the conditional classifier
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The planned conditional-reference regex only recognizes see/load/read-style clauses with an added only for|when|after|before qualifier, but the design SKILL’s final-summary-emit citations still use follow/follows or defined-in wording. If implementers only append qualifiers without changing the verb, those references will not produce `_directive_matches`, so `skills/shared/final-summary-emit.md` will remain absent from `conditional_files` and the real-design assertion will fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: `Either extend the conditional reference regex to include follow/follows with the same required only for|when|after|before connector (keep IMPLEMENT_FINAL_SUMMARY_RE implement-only and eager), or rephrase every design final-summary-emit citation (including anti-halt line 25 defined-in profile text) to read/load/see plus an explicit qualifier`
  - From Cursor-Innovation: `Rephrase each audited design citation to read/see/load skills/shared/final-summary-emit.md only when|for|after its branch guard, or add a design-only conditional follow-final-summary-emit pattern with force_conditional (not implement's eager narrow match).`
  - From Cursor-Pragmatic: `In skills/design/SKILL.md, rephrase each of the four planned final-summary-emit citations (and any other audit-bound cite) to use read, load, or see with the path in the same clause plus the runtime only for|when|after qualifier, e.g. read skills/shared/final-summary-emit.md only on cancel-title-filter / cancel-reentry-guard routes. Update the design SKILL plan bullet to require that verb change explicitly and drop only add the qualifying clause / do not change underlying instructions for these lines. Do not add design to implement's eager follow narrow pattern.`
  - From Cursor-Requirements: `Either add follow to the conditional verb alternation with the same required only for|when|after|before tail (distinct from implement's unconditional IMPLEMENT_FINAL_SUMMARY_RE eager pattern), or explicitly require rephrasing each design final-summary-emit citation to read/see/load before the path in the same clause as the qualifier. Add a synthetic fixture for follow ... final-summary-emit.md only when ... so the contract cannot regress.`


### FINDING_1: Final-summary qualifiers use unsupported connectors
- **Reviewer(s)**: Codex-Arch, Cursor-Requirements
- **Severity**: important
- **Concern**: The planned conditional-reference regex only recognizes connectors like `only for`, `only when`, `only after`, and `only before`, but the design final-summary examples use `only on` and `only upon`. If those examples are followed as written, the `final-summary-emit.md` citations will not be classified as conditional, and the design closure/assertion for that file can fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: `Change the examples to supported wording such as `only when on the cancel-title-filter / cancel-reentry-guard routes` and `only after reaching Step 5c item 5`, or explicitly add `only on|only upon` to the regex and tests`
  - From Cursor-Requirements: `Use one connector set everywhere: either extend the conditional-reference regex to include only on and only upon, or rewrite the four design final-summary-emit qualifiers to use only when / only after (e.g. only when on cancel-title-filter or cancel-reentry-guard routes; only when reaching Step 5c item 5)`

