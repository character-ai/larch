### FINDING_2: Optional sanitizer pre-check must not mutate Step 5c-owned artifacts
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-dyn-Prompt Contract Auditor
- **Severity**: major
- **Concern**: The optional Step 5b.5 sanitizer pre-check lacks an explicit read-only and non-authoritative contract. If it invokes the legacy wrapper or promotes, moves, deletes, or writes Step 5c-owned artifacts, it can create the completion sentinel, emit sanitizer warnings, cause Step 5c to return early, or cause the diagram to be skipped before authoritative sanitization and promotion occur.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add explicit pre-check rules: read-only probe only (e.g. python/cli.py mermaid sanitize --input candidate --from-md with output discarded); never invoke design-step3b-sanitize.sh; never promote the candidate or write .completed/step-5b.5 before Step 5c; pre-check result is non-authoritative
  - From Cursor-Pragmatic: In finalize-step5.md Step 5b.5 and SKILL.md Step 5b.5, require any optional pre-check to call `python/cli.py mermaid sanitize --input "$DESIGN_TMPDIR/architecture-diagram.candidate.md" --from-md` with stdout/stderr captured only to a tmpdir log; forbid `design-step3b-sanitize.sh`, candidate promotion, sentinel writes, and chat validity recaps; Step 5c remains the sole promote/skip authority
  - From Cursor-dyn-Prompt Contract Auditor: In finalize-step5.md Step 5b.5 and skills/design/SKILL.md Step 5b.5: allow only a read-only optional python/cli.py mermaid sanitize probe; forbid design-step3b-sanitize.sh; forbid writing .completed/step-5b.5 architecture-diagram.md architecture-diagram.skipped or moving/deleting the candidate before Step 5c; forbid chat **⚠ 5b.5:** sanitizer warnings from pre-check
  - From Cursor-dyn-Prompt Contract Auditor: In the proposed `finalize-step5.md` Step 5b.5 section and `skills/design/SKILL.md` Step 5b.5 prose, add an explicit immutability contract: optional pre-check may only read/validate the candidate in place (e.g. `python/cli.py mermaid sanitize --input …` with stdout parsed silently); it must not invoke `design-step3b-sanitize.sh`; it must not write `.completed/step-5b.5`, `architecture-diagram.md`, or `architecture-diagram.skipped`; it must not move or delete `architecture-diagram.candidate.md`; it must not print validity recaps or `**⚠ 5b.5:` sanitizer warnings. Revise the candidate silently or proceed to Step 5c.


### FINDING_3: Structural tests should pin the pre-check immutability contract
- **Reviewer(s)**: Cursor-Innovation, Cursor-dyn-Prompt Contract Auditor
- **Severity**: minor
- **Concern**: The structural harness covers anti-narrative and sanitizer-fence rules but does not prevent future prompt edits from reintroducing the legacy sanitizer wrapper or pre-Step-5c writes to sentinel and diagram artifacts, leaving Step 5c authority unprotected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Extend test-design-structure.sh with not_contains/forbid rules that optional pre-check must not reference design-step3b-sanitize.sh and must not promote candidates or write .completed/step-5b.5 before Step 5c
  - From Cursor-dyn-Prompt Contract Auditor: Add contains/not_contains pins in test-design-structure.sh for no design-step3b-sanitize.sh on the Step 5b.5 orchestrator path and for prose forbidding pre-Step-5c writes to `.completed/step-5b.5 architecture-diagram.md` and `architecture-diagram.skipped`


### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:37-41
- **Concern**: [SCOPE-REDUCTION] Shared every file-authoring-step anti-narrative rule exceeds binding issue scope. Scenario: The scope anchor targets Step 5b.5 diagram narration only. Step 5b.5 SKILL tightening plus finalize-step5.md mirroring already stop the reported lead-ins, sanitizer narration, and transition recap without adding a cross-skill file-authoring contract that touches plan, outline, brainstorm, and clarify writes.
- **Proposed resolution**: Limit the mandatory anti-narrative contract to Step 5b.5 (and its finalize-step5.md mirror) unless a second concrete narration site is named. Keep the harness-rendered tool-line carve-out in SKILL verbosity either way. ## Findings ### 1. Anti-halt continuation blocks vs free-form recaps (correctness, major) The issue’s bad transcript is a **free-form** Step 5c recap listing compose/validate/redact/publish/rename work. That is different from the existing anti-halt contract in `skills/shared/subskill-invocation.md`, which requires blockquoted `> **Continue to Step N IMMEDIATELY.**` lines. The plan’s `finalize-step5.md` update forbids prose that announces “continuation to Step 5c” without distinguishing: - forbidden chat narration (the reported failure mode), and - required anti-halt blockquotes already present at ```593:593:skills/design/SKILL.md```. The failure-modes section warns about overbroad suppression of breadcrumbs and warnings, but not about anti-halt continuation machinery. That gap is a real implementer hazard on a correctness path. **Suggested revision:** Scope quiet-authoring to **chat-emitted Claude-authored prose**; explicitly preserve anti-halt `> **Continue to...**` blockquotes; pin both the ban and the preservation in `scripts/test-design-structure.sh`. ### 2. Global file-authoring rule is broader than the issue (architecture, minor, scope reduction) The binding scope anchor says the unwanted lines are “in this specific part of `/design`” (Step 5b.5). The plan’s shared rule for “every `/design` file-authoring step, including plan and diagram writes” adds contract surface beyond what is needed to stop the reported diagram narration. Step 5b.5-specific SKILL tightening plus the `finalize-step5.md` mirror are sufficient for the stated problem. The global rule is preventive hardening, not required for completeness of the anchored feature. **Suggested revision:** Keep the change localized to Step 5b.5 unless another concrete narration site is identified. Still add the harness-vs-Claude-authored distinction in SKILL verbosity.


### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:37-41
- **Concern**: [SCOPE-REDUCTION] Plan broadens beyond the issue's Step 5b.5-only scope anchor. Scenario: The binding issue asks to drop narration in this specific part of `/design` (Step 5b.5 diagram flow). The plan applies a shared rule to every file-authoring step (plan, diagram, and others), increasing prompt surface and regression risk (failure mode: overbroad wording suppressing required breadcrumbs) for uncertain gain beyond the demonstrated failure
- **Proposed resolution**: Narrow firm changes to Step 5b.5 plus finalize-step5.md unless other steps are shown to emit the same narration; if keeping the shared rule, enumerate covered steps and explicit exceptions (Step 2b plan print, required breadcrumbs, warnings, operator prompts) in the SKILL.md verbosity block ### 1. risk-integration — Optional pre-check must stay side-effect-free (`finalize-step5.md`, `design-step3b-sanitize.sh`) The plan allows an optional sanitizer pre-check but does not say how to run it. The legacy wrapper is dangerous here: on success it promotes the candidate and writes `.completed/step-5b.5`; on failure it prints bounded warnings to chat. That conflicts with “Step 5c owns authoritative sanitization” and can recreate the issue’s noisy pre-Step-5c path. The issue’s bad run used direct `python/cli.py mermaid sanitize`, which is the safe pattern; the plan should mandate that pattern and forbid the wrapper for pre-check. ### 2. correctness — Step 2b structured plan print needs an explicit exception (`SKILL.md:324`) Anti-narrative guidance should target lead-ins (“I’ll write the plan…”), validation narration, and transition recaps. Step 2b still requires printing the full plan under `## Implementation Plan` for reviewers. The plan’s edge cases mention structured outputs in general but do not pin this Step 2b contract in the firm `UPDATED` section. ### 3. architecture — [SCOPE-REDUCTION] Shared rule exceeds the issue’s stated boundary The scope anchor is Step 5b.5 diagram narration, not all `/design` file writes. A shared rule is defensible, but it is extra complexity relative to the demonstrated problem. Prefer Step 5b.5-focused wording unless broader narration is evidenced elsewhere.


### FINDING_7:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md (planned change; plan.txt:11-12)
- **Concern**: [SCOPE-REDUCTION] The shared rule expands the change from the specified Step 5b.5 diagram flow to every `/design` file-authoring step. Scenario: The issue explicitly targets narration around diagram candidate authoring and sanitizer checking. Applying new silence rules to plan writes and unrelated authoring paths changes established behavior without being required and may suppress useful context outside this flow
- **Proposed resolution**: Limit the rule and its structural tests to Step 5b.5 diagram candidate authoring and optional sanitizer pre-check narration; retain existing behavior for other file-authoring steps


### FINDING_8:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: architecture
- **Location**: plan.txt:11-12,27
- **Concern**: [SCOPE-REDUCTION] The shared rule for every `/design` file-authoring step exceeds the issue's explicit focus on the Step 5b.5 diagram sequence. Scenario: The plan would change narration across unrelated plan and artifact writes, potentially suppressing useful output outside the named diagram flow
- **Proposed resolution**: Limit the quiet-authoring contract and its structural assertions to Step 5b.5 diagram candidate authoring, optional sanitizer pre-check, and transition to Step 5c


### FINDING_2: Read-only pre-check may mutate the authoritative candidate
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: major
- **Concern**: The edge-case text permits the optional read-only pre-check to revise the candidate, contradicting the pre-check’s non-mutating contract and allowing a non-authoritative probe to alter Step 5c’s input or Step 5c-owned artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Rewrite the edge case: the pre-check never modifies the candidate or any Step 5c-owned artifact; on failure it is ignored and Step 5c remains authoritative. If re-authoring is allowed, say only the orchestrator may silently rewrite the candidate once with no sanitizer narration, still without writing sentinels, promoted/skipped files, or warnings.
  - From Codex-Pragmatic: Replace “It may revise the candidate” with an explicit statement that the pre-check must not revise or otherwise mutate the candidate


### FINDING_3: Global execution-issues exception may reauthorize Step 5b.5 sanitizer warnings
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: The global execution-issues exception still pairs diagram generation with sanitizer rejection at Step 5b.5, which can be read as authorizing sanitizer-rejection warnings and bounded execution-issues writes that the quiet pre-check contract intends to reserve for Step 5c.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Narrow line 111 to generation failures only, or add an explicit Step 5b.5 carve-out that sanitizer-rejection logging is Step 5c publish-owned only. Pin the narrowed wording in test-design-structure.sh so prompt edits cannot resurrect pre-check warning authority.


### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: architecture
- **Location**: plan.txt:Approach;skills/design/SKILL.md
- **Concern**: [SCOPE-REDUCTION] Optional Step 5b.5 sanitizer pre-check adds complexity without clearing the issue's minimum-change bar. Scenario: The binding scope targets Claude-authored narration in the Step 5b.5 diagram sequence. The issue transcript also shows harness-visible `Ran N shell commands` and failed ad-hoc sanitize invocations. Step 5c already owns authoritative sanitize/promote/skip via `python/larch/design/design_publish.py::_sanitize_diagram_candidate`. A silent pre-check still adds orchestrator Bash surface, preserves uncontrollable harness noise, and reopens wrong-flag probing without changing publish behavior.
- **Proposed resolution**: Drop the optional pre-check from SKILL.md, finalize-step5.md, and structural tests. Require: write candidate silently, emit only required `🔶`/`⚠ 5b.5` lines plus the anti-halt blockquote, then continue to Step 5c. Add a negative harness assertion that Step 5b.5 prose does not invoke `python/cli.py mermaid sanitize` before Step 5c.


