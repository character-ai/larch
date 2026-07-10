### [rejected] FINDING_3

**Rejected subtype:** dismissed (0 YES)

### FINDING_3: G-Cfg-1 slimming drops the module-private carve-out
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Marking G-Cfg-1 slim drops the module-private one-site Deviate carve-out from normalized prompt output, so design/implement/review agents may treat legitimate one-site constants as guideline deviations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add the module-private exception to the Mechanized line or leave G-Cfg-1 unmarked.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** dismissed (0 YES)

### FINDING_4: G-Bash-3 slimming drops the documented narrower-runtime carve-out
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Marking G-Bash-3 slim drops the documented-narrower-runtime Deviate carve-out from normalized prompt output, so agents may flag scripts intentionally excluded from the Bash 3.2 sweep as portability violations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Restate the narrower-runtime exception in the Mechanized line or keep full normalization for G-Bash-3.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** dismissed (0 YES)

### FINDING_6: Blank `- Mechanized:` payloads are treated as valid
- **Reviewer(s)**: dyn-dyn-payload-normalization
- **Severity**: minor
- **Concern**: `_MECHANIZED_RE` can match whitespace-only payloads, so a blank `- Mechanized:` line is accepted as a valid marker and `_append_guideline_entry` emits an empty mechanization line while dropping following `Why` / `Deviate when` prose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-payload-normalization: Treat a mechanized match as valid only when `mechanized.group(1).strip()` is non-empty; otherwise ignore the line and keep collecting `Why` / `Deviate when` as on the unmarked path (or fail closed during `read_guidelines` validation).


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

