### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/check-plan-size.sh:20-24
- **Concern**: Contiguous metadata scan stops at the first non-trailer line above `diff_lines:` with no blank-line exception. Scenario: Committed `/design` plans almost always put a blank line immediately before `diff_lines:` (including this plan). A designer following that habit who adds `diff_added:` / `mechanical_churn:` above the blank gets silent legacy fallback: e.g. `mechanical_churn: true` + `diff_lines: 4700` still hard-triggers on total churn
- **Proposed resolution**: Specify upward scan may skip one empty line directly above `diff_lines:` before collecting trailers; add harness case (trailers, blank, `diff_lines:`); document in Step 2b / `check-plan-size.md` Edge cases

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/check-plan-size.sh:81-90
- **Concern**: Proposed line-count contract keeps counting optional metadata trailers as plan body. Scenario: A plan with 800 real body lines plus diff_added/mechanical_churn above diff_lines reports PLAN_LINES >800 and fires Split/Cancel even though optional metadata should not affect the unchanged plan-body gate
- **Proposed resolution**: Subtract the final optional metadata-block line count when computing PLAN_LINES, or compute plan_body_lines after parsing the block; add a boundary test with 800 body lines plus optional trailers

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge, Codex-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/references/discussion-rounds.md:126
- **Concern**: Post-plan discussion revision path is omitted from the trailer-preservation plan. Scenario: Gate A discussion can revise plan.txt, rerun EMIT_PLAN and Step 2b.5, and drop diff_added/diff_deleted/mechanical_churn, silently reverting a mechanical/deletion-heavy plan to legacy diff_lines gating
- **Proposed resolution**: Update discussion-rounds.md plan-revision authority to preserve or recompute optional plan-size trailers above final diff_lines, matching Gate B/waterfall guidance

### FINDING_4:
- **Reviewer(s)**: Cursor-Edge, Codex-Edge
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/scripts/check-plan-size.sh:81-90
- **Concern**: Optional metadata lines still count as PLAN_LINES. Scenario: The plan says keep the existing plan_lines computation exactly, so a 798-line plan plus diff_added/diff_deleted/mechanical_churn reports PLAN_LINES=801 and hard-triggers the plan-body gate solely because metadata was added
- **Proposed resolution**: After parsing the final metadata block, exclude those optional trailer lines from PLAN_LINES or explicitly revise the contract/tests to state that metadata counts toward the 800-line body gate

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/scripts/check-plan-size.sh:81-90
- **Concern**: skills/design/scripts/check-plan-size.md:16-17. Scenario: Optional metadata trailers count toward PLAN_LINES
- **Proposed resolution**: Keeping plan_lines as trailer_nr-1 means each diff_added/diff_deleted/mechanical_churn line consumes plan-body budget; a ~798-line plan plus three trailers can trip plan_lines>800 while the same body without trailers would not Document in check-plan-size.md/flags.md that metadata lines count toward PLAN_LINES, or subtract the parsed metadata block from plan_lines after trailer scan (small change after line 90, not a lines-1-90 rewrite)

### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/check-plan-size.sh:81-87
- **Concern**: Optional metadata trailers remain counted as PLAN_LINES. Scenario: The plan keeps the current plan_lines computation, so a 798-line plan plus diff_added, diff_deleted, mechanical_churn, and diff_lines reports PLAN_LINES=801 and falsely trips the unchanged plan-body hard gate
- **Proposed resolution**: Compute PLAN_LINES as physical lines before the final metadata block when optional trailers are present, while preserving legacy behavior when absent

### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/references/discussion-rounds.md:126
- **Concern**: Post-plan discussion rewrites are not covered by trailer preservation. Scenario: A mechanical or deletion-heavy plan can keep trailers through Gate B, then lose them during a user discussion revision and fall back to legacy diff_lines gating
- **Proposed resolution**: Extend the same preserve-or-recompute rule to the post-plan discussion revision path, keeping optional trailers directly above final diff_lines

### FINDING_8:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/references/discussion-rounds.md:126
- **Concern**: Plan omits the post-plan discussion revision surface from the trailer-preservation updates. Scenario: The discussion sub-round may directly rewrite plan.txt, then re-run ACTION=EMIT_PLAN and Step 2b.5. Without updating this prompt surface, a mechanical/deletion-heavy plan can lose diff_added, diff_deleted, or mechanical_churn during discussion-driven revision and fall back to the legacy diff_lines hard gate.
- **Proposed resolution**: Add skills/design/references/discussion-rounds.md to the UPDATED list and revise its plan revision authority text to preserve or recompute diff_added, diff_deleted, and mechanical_churn in the final metadata block above diff_lines when it rewrites plan.txt.

### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-check-plan-size.sh:67-94
- **Concern**: No harness case where diff_added is present and under 2000 while diff_lines exceeds 1500. Scenario: Settled rule is additions-keyed hard diff when diff_added is present else legacy diff_lines > 1500. Listed cases cover diff_added boundaries deletions exempt and legacy diff_lines: 1501 without diff_added but not diff_added: 500 with diff_lines: 3000. Implementer could regress to total-churn gating while new trailers look valid.
- **Proposed resolution**: Add one case with diff_added under 2000 and diff_lines above 1500 asserting HARD_TRIGGER_FIRED=false TRIGGER_REASONS empty and DIFF_ADDED set.

### FINDING_10:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/references/discussion-rounds.md:126
- **Concern**: Plan covers Gate B and waterfall rewrites but is silent on the post-plan Gate A discussion path that may directly rewrite plan.txt before re-running ACTION=EMIT_PLAN and Step 2b.5. Scenario: A mechanical or deletion-heavy plan can keep diff_added diff_deleted mechanical_churn through initial review, then a user discussion revision can drop those optional trailers and regress the next size check to legacy diff_lines hard-gating
- **Proposed resolution**: Add a minimal UPDATED entry for skills/design/references/discussion-rounds.md requiring any post-plan direct plan.txt revision to preserve or recompute diff_added diff_deleted and mechanical_churn in the final metadata block above diff_lines before re-running ACTION=EMIT_PLAN

### FINDING_11:
- **Reviewer(s)**: Cursor-dyn-trailer-grammar-drift, Codex-dyn-trailer-grammar-drift
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/check-plan-size.md:10-31
- **Concern**: Proposed authoritative machine-contract docs leave optional trailer grammar implicit. Scenario: Current diff_lines strictness is anchored to emit-plan.sh at line 15, but the proposed update only says optional trailers use the same grammar; it does not require documenting the exact anchored regexes, mechanical_churn false handling, first non-trailer scan stop, or malformed-as-absent behavior in the authoritative contract.
- **Proposed resolution**: Make check-plan-size.md spell out the three accepted full-line regexes, that upward scanning stops at the first line above diff_lines that is not one of those trailer regexes, and that duplicate keys use the last match inside that contiguous block.

### FINDING_12:
- **Reviewer(s)**: Cursor-dyn-trailer-grammar-drift, Codex-dyn-trailer-grammar-drift
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:800-805,869-890; skills/design/references/flags.md:30-64; skills/design/references/approval-gates.md:131-162
- **Concern**: Plan-authoring and rewrite surfaces omit strict grammar and last-match/block-stop constraints. Scenario: SKILL.md is the prompt that creates plan.txt, and Gate B rewrites it; if these surfaces only say trailers go above diff_lines, a rewrite can preserve a blank-separated, malformed, or duplicated trailer block that check-plan-size.sh will ignore or resolve differently, causing legacy hard-gate behavior after a mechanical/deletion-heavy plan.
- **Proposed resolution**: Add a short cross-reference at each authoring/rewrite surface: optional size trailers must stay in the final contiguous metadata block defined by check-plan-size.md; malformed variants are ignored; duplicate keys use the last trailer in that block.

### FINDING_13:
- **Reviewer(s)**: Cursor-dyn-revision-trailer-spec
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:61-65 / skills/design/scripts/revise-plan-with-waterfall.sh:126-143
- **Concern**: UPDATED revise-plan subsection does not name compose_prompt() or a prompt insertion point; no draft trailer-preservation rule text. Scenario: Implementer must discover compose_prompt() and guess which printf/Hard rules line to extend; prompt-only mitigation is not implementable without ambiguity
- **Proposed resolution**: Add to plan: extend compose_prompt() (lines 126-143), append one Hard rules printf after line 134 with concrete text (preserve diff_added/diff_deleted/mechanical_churn in final metadata block above diff_lines: unless intentionally recomputed; include example lines)

### FINDING_14:
- **Reviewer(s)**: Codex-dyn-revision-trailer-spec
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:61-65; skills/design/scripts/revise-plan-with-waterfall.sh:126-142; skills/design/scripts/revise-plan-with-waterfall.sh:625-638
- **Concern**: The waterfall revision spec says to preserve or recompute optional trailers, but only names generic prompt adjustment and does not say whether compose_prompt hard-rules text is enough or whether successful candidates must be checked after apply.. Scenario: The current script can accept a revised plan that still passes emit-plan with only final diff_lines, so an implementer could update the prompt text while dropped diff_added diff_deleted mechanical_churn still silently survive the waterfall.
- **Proposed resolution**: Specify the minimal deterministic contract: edit compose_prompt's hard-rules text at lines 126-142 and add a post-apply check before success that, when the original plan had any optional size trailers, the revised final metadata block still contains preserved or recomputed optional trailers above final diff_lines; reject and restore otherwise. Do not add a recomputation engine.

### FINDING_15:
- **Reviewer(s)**: Codex-dyn-revision-trailer-spec
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:104-112; scripts/test-revise-plan-with-waterfall.sh:43-49
- **Concern**: The testing strategy allows a documented spot-check for the revision preservation path and does not name the existing revise-plan waterfall harness or the failing preservation scenario.. Scenario: A prompt-only implementation can pass check-plan-size tests and relevant checks while the waterfall still drops optional trailers after Gate B or between review rounds.
- **Proposed resolution**: Require one focused automated case in scripts/test-revise-plan-with-waterfall.sh: start with a plan containing diff_added, diff_deleted, mechanical_churn, and diff_lines; have one candidate drop the optional trailers and verify it is rejected or falls through; have the winning candidate preserve them above final diff_lines.
