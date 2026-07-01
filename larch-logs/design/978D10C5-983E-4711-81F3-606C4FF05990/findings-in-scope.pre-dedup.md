### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/design-outline.md:106-116
- **Concern**: Refine-loop gate semantics are compression targets but absent from byte-stable preserve list and Edge cases. Scenario: The plan lists Refine loop for redundant-prose removal while Approach preserves only AskUserQuestion question/header/option labels. It does not freeze load-bearing rules at lines 111 and 116: empty/non-actionable replies must not approve; free-form messages are not implicit approve/cancel; Refine must not write `.outline-approved`; loop until explicit Approve or Cancel. A ~382-token cut can drop or merge these while frozen literals and cancel-hygiene rg checks still pass, letting empty refinement advance or `.outline-approved` be written on Refine.
- **Proposed resolution**: Add Edge-case bullets (or one Approach preserve bullet) naming these Refine-loop condition/action pairs as frozen semantics; prose may tighten but the rules must remain explicit and unmerged.



### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/design-outline.md:106-114
- **Concern**: Refine-loop operator literals missing from Approach byte-stable preserve list despite planned Refine-loop tightening. Scenario: The Approach list now byte-freezes Cancel hygiene outcome/anchor/cancellation lines after round 2, but Files still mandates Refine-loop tightening while only AskUserQuestion question/header/options are frozen. The free-form refine prompt, `## Updated Design Outline` reprint header, and empty-reply no-approve rule are not named. Compression can paraphrase or drop them while AskUserQuestion literals still pass, changing refine UX and loop termination without failing Cancel rg gates or the per-file token gate.
- **Proposed resolution**: Add Refine-loop literals to the Approach byte-stable preserve list (mirror Cancel hygiene): the free-form question string, `## Updated Design Outline`, empty/non-actionable reply handling, and the re-fire-the-same-approval-prompt rule. Optionally add matching `rg -F` checks beside the Cancel hygiene gate.



### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/design-outline.md:43
- **Concern**: Readability-style load directive unprotected during whole-file compression. Scenario: Line 43 (`Read skills/design/references/readability-style.md before composing the outline.`) sits outside the frozen schema fence and is not in the Approach preserve list or Edge cases (only the design-log publish warning is named). A whole-file density pass can delete or inline-merge it while frozen prompts still pass, so outlines may omit the readability contract (em-dash ban, brevity axes) despite acceptance requiring zero outline-gate behavior change.
- **Proposed resolution**: Add the readability-style Read directive to Approach byte-stable preserve text or an Edge case ("do not remove the readability-style Read line"). Keep tightening limited to surrounding prose.



### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/design-outline.md:21-117
- **Concern**: Entry-guard skip breadcrumbs, approve/auto-approve success lines, and Refine free-form prompt are missing from the Approach byte-stable preserve list. Scenario: After round 2, Cancel hygiene literals are enumerated and rg-gated, but Entry guard and Refine loop are still compression targets. A pass can paraphrase the three `⏩ 1d.7: outline — skipped …` lines, `✅ 1d.7: outline approved — proceeding to plan drafting`, `⏩ 1d.7: outline — auto-approved (--skip-approve)`, and the Refine question while AskUserQuestion labels and Cancel hygiene pass checks. That breaks zero-behavior-change acceptance and can desync the auto-approve breadcrumb duplicated in skills/design/SKILL.md:250.
- **Proposed resolution**: Add these operator-visible literals to Approach byte-stable preserve (same treatment as Cancel hygiene) and extend post-edit rg gates beyond the three Cancel lines to cover at least the skip/approve/auto-approve breadcrumbs and the Refine free-form question.



### FINDING_5:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/references/design-outline.md:21-89
- **Concern**: [SCOPE-REDUCTION] Plan mandates unconditional tightening of Entry guard, Inputs, and Architectural guideline presentation though issue scope limits density work to Approve/Refine/Cancel prompt and Refine-loop prose. Scenario: Issue scope targets only Approval prompt, Refine loop, and Cancel hygiene (~696 est. tokens). The ~382-token / 15% file gate needs ~55% compression in those sections, which is achievable without editing high-branch resume routing or `present-note` branching. Files to modify still requires tightening Entry guard and guideline presentation unconditionally, inviting semantic drift on paths the issue marked density-only and out of scope for semantics change
- **Proposed resolution**: Reframe the Files section: compress Approval prompt, Refine loop, and Cancel hygiene first; touch Entry guard, Inputs, guideline presentation, downstream docs, and invariants only if the per-file `est_tokens` gate still fails after safe issue-scoped compression



