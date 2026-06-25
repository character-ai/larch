## Decision 1: Fix direction on HEAD drift
- **Question**: On HEAD drift at pin time, deliver a current-HEAD note (a) or visibly report why it could not (b)?
- **Resolution**: Option (b) — report the drop visibly. Do NOT re-author the assessment (LLM/prompt-side; out of scope) and do NOT mechanically re-pin the staged assessment (that would deliver a stale, pre-drift assessment that can mask new deviations). When the durable note cannot be delivered for the shipped HEAD, surface a clear notice in its place.
- **Source**: user

## Decision 2: Where the dropped-note notice appears
- **Question**: Where should the "guideline note dropped due to HEAD drift" notice be surfaced?
- **Resolution**: Both the PR body and the final report (final-summary.md), mirroring the two surfaces where a delivered note would otherwise appear.
- **Source**: user

## Decision 3: Overlap with #5335 [DESIGNING]
- **Question**: #5335 co-locates in python/architectural_guidelines.py (reader path). Serialize via a blocked-by edge or proceed independently?
- **Resolution**: Proceed independently. Function surfaces are disjoint (read_guidelines/present-note vs pin/stage); #5337 additionally owns ship.py / final_report.py / pr_body.py, which #5335 does not touch. No dependency edge wired.
- **Source**: user

## Decision 4: Notice trigger (codebase-derived)
- **Question**: Does the visible notice fire only on HEAD drift, or whenever a staged assessment exists but the durable note is not delivered for the shipped HEAD?
- **Resolution**: Primary trigger is HEAD drift (staged fingerprint no longer validates against the shipped HEAD). Fire the notice whenever a staged assessment exists (STATUS=present) but the durable note cannot be delivered/consumed for the shipped HEAD, tagging the reason (HEAD-drift is the dominant case). This honors the "no silent drop" intent without expanding past the staged-assessment path.
- **Source**: codebase

## Hard constraints
- Preserve the existing happy path: when the staged fingerprint validates against the shipped HEAD, the note is pinned and delivered to the PR body + final report exactly as today.
- No notice when ARCHITECTURAL_GUIDELINES.md is absent/invalid or when no staged assessment was ever produced (no new noise).
- Mechanical and self-contained in Phase B (ship.py) + report composition (final_report.py / pr_body.py). Do NOT add a prompt-side orchestrator round-trip and do NOT modify the implement SKILL.md Phase A reassessment flow.
- Redaction (redact_pr_body) must still apply to any surfaced content.

## Non-goals
- Re-authoring the architectural assessment against current HEAD.
- Mechanically re-pinning the stale staged assessment to a new HEAD.
- Changing when/how Phase A stages the assessment (write_staged_assessment) or the prompt-side reassessment-on-drift contract.
