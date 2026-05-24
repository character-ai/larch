## Decision 1: Voter prompt scope (which voter blocks change)
- **Question**: Should both Voter 1 (Claude Code Reviewer subagent) and Voter 2/3 (Codex / Cursor / Claude replacements) prompts in `skills/design/references/plan-review.md` adopt the new multi-paragraph YES↔EXONERATE framing?
- **Resolution**: Yes — both prompt strings get the new framing. No asymmetry between voter slots.
- **Source**: user

## Decision 2: Wording fidelity
- **Question**: Adopt the proposed prose from the issue body verbatim, or refine during the design pass?
- **Resolution**: Verbatim. Keep the canonical anchor sentence `When in doubt between YES and EXONERATE, prefer EXONERATE` stable.
- **Source**: user

## Decision 3: Harness assertion
- **Question**: Should `scripts/test-dispatch-plan-voters.sh` get a new assertion that the generated voter prompt contains the canonical phrase?
- **Resolution**: Yes — add a grep-style assertion against the rendered prompt file (covers the dispatcher prose; the SKILL.md / plan-review.md prose is statically inspected).
- **Source**: user

## Decision 4: plan-review-quick.md update
- **Question**: Should `plan-review-quick.md` also receive the YES↔EXONERATE framing?
- **Resolution**: Yes — update the acceptance-guidance prose in the quick-mode procedure section to mirror the same proportionality framing (no separate voter panel exists in quick mode; the analog spot is the "Accept/Reject/OOS" guidance line).
- **Source**: user

## Decision 5: Out-of-scope (hard constraints)
- **Question**: What is explicitly out-of-scope?
- **Resolution**: No changes to vote tally logic, voter selection, panel composition, 2-of-3 threshold, voter downweighting, or 4th-voter additions. No changes to code-review voters in `dispatch-code-voters.sh` (tracked separately under #L6-issue).
- **Source**: feature description

## Decision 6: Hard constraints (must preserve)
- **Question**: What must not break?
- **Resolution**: The structural "Output ONLY vote lines" contract in `dispatch-plan-voters.sh` (lines 50-60) — finding-ID + YES/NO/EXONERATE line shape unchanged. Existing `grep -cE` parser at line 80 remains valid. The Competition notice blockquote in `plan-review.md` is byte-preserved (tested by `scripts/test-design-structure.sh`).
- **Source**: codebase
