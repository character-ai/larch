### [rejected] FINDING_1

**Rejected subtype:** dismissed (0 YES)

### FINDING_1: vN_severity scoring wording
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: important
- **Concern**: The plan-correctness notice appears to award +2 for accepted in-scope blocker/major findings without clearly preserving the strict-majority vN_severity rule or stating that body severity does not affect points, which could let panels score findings incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** dismissed (0 YES)

### FINDING_2: severity floor keeps latent NO
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-prompt-contract
- **Severity**: important
- **Concern**: The severity-floor prompt no longer explicitly says latent plus merely-real findings stay NO, and it also drops the `nits never clear necessity` guardrail, which can produce false YES votes for real-but-non-execution-path defects.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From dyn-dyn-prompt-contract: Restore the dropped clauses verbatim in the severity-floor sentence, or add a focused regression test that asserts both strings and keep them in the rendered voter prompt.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** dismissed (0 YES)

### FINDING_3: severity rubric test no longer pins rubric prose
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing, dyn-dyn-prompt-contract
- **Severity**: important
- **Concern**: The severity rubric test now checks only the header and enum token, so the rubric-definition prose and default-deny floor can drift without failing CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-prompt-contract: Assert the full severity-floor sentence (including `Default-deny`, nit handling, and latent rules) and at least one rubric definition such as `` `blocker` = data loss ``; keep the existing frozen grammar tests separate.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** dismissed (0 YES)

### FINDING_4: real OOS findings stay NO
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-prompt-contract
- **Severity**: important
- **Concern**: The plan-fidelity archetype no longer explicitly defaults real-but-out-of-scope findings to NO, so legitimate out-of-scope defects could be mis-voted as in-scope work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-prompt-contract: Put back an explicit default-deny rule for real-but-out-of-scope ballot items, e.g. `Default NO for real-but-out-of-scope findings; route them Out-of-Scope instead.`


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** dismissed (0 YES)

### FINDING_7: dynamic body untrusted boundary assertions
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: The generated dynamic-agent-body test no longer asserts the scout untrusted boundary text, so later edits could remove the untrusted-data / ignore-commands / output-format-instructions contract silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add asserts for untrusted-data / ignore-commands / output-format-instructions text in dynamic body


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** dismissed (0 YES)

### FINDING_8: canonical-list anchor in description mode
- **Reviewer(s)**: dyn-dyn-prompt-contract
- **Severity**: important
- **Concern**: Description-mode specialist prompts no longer require canonical-list anchoring or the `even if they look related` carve-out, which can weaken scope classification for related files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-prompt-contract: Restore the mandatory canonical-list anchor and the `even if they look related` qualifier in `_render_specialist_text` description mode.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

