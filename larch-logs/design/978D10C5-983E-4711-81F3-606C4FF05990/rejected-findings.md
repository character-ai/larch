### [Plan Review] FINDING_2

### FINDING_2: Readability-style Read directive unprotected during whole-file compression
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Line 43 (`Read skills/design/references/readability-style.md before composing the outline.`) sits outside the frozen schema fence and is not in the Approach preserve list or Edge cases (only the design-log publish warning is named). A whole-file density pass can delete or inline-merge it while frozen prompts still pass, so outlines may omit the readability contract (em-dash ban, brevity axes) despite acceptance requiring zero outline-gate behavior change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add the readability-style Read directive to Approach byte-stable preserve text or an Edge case ("do not remove the readability-style Read line"). Keep tightening limited to surrounding prose.


### [Plan Review] FINDING_3

### FINDING_3: Entry-guard skip breadcrumbs and approve/auto-approve success lines unprotected during compression
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: After round 2, Cancel hygiene literals are enumerated and `rg`-gated, but Entry guard skip breadcrumbs and approve/auto-approve success lines remain compression targets. A pass can paraphrase the three `⏩ 1d.7: outline — skipped …` lines (lines 23–25), `✅ 1d.7: outline approved — proceeding to plan drafting` (line 100), and `⏩ 1d.7: outline — auto-approved (--skip-approve)` (line 93) while `AskUserQuestion` labels and Cancel hygiene pass checks. That breaks zero-behavior-change acceptance and can desync the auto-approve breadcrumb duplicated in `skills/design/SKILL.md:250`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add these operator-visible literals to Approach byte-stable preserve (same treatment as Cancel hygiene) and extend post-edit rg gates beyond the three Cancel lines to cover at least the skip/approve/auto-approve breadcrumbs and the Refine free-form question.


### [Plan Review] FINDING_4

### FINDING_4:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/references/design-outline.md:21-89
- **Concern**: [SCOPE-REDUCTION] Plan mandates unconditional tightening of Entry guard, Inputs, and Architectural guideline presentation though issue scope limits density work to Approve/Refine/Cancel prompt and Refine-loop prose. Scenario: Issue scope targets only Approval prompt, Refine loop, and Cancel hygiene (~696 est. tokens). The ~382-token / 15% file gate needs ~55% compression in those sections, which is achievable without editing high-branch resume routing or `present-note` branching. Files to modify still requires tightening Entry guard and guideline presentation unconditionally, inviting semantic drift on paths the issue marked density-only and out of scope for semantics change
- **Proposed resolution**: Reframe the Files section: compress Approval prompt, Refine loop, and Cancel hygiene first; touch Entry guard, Inputs, guideline presentation, downstream docs, and invariants only if the per-file `est_tokens` gate still fails after safe issue-scoped compression


