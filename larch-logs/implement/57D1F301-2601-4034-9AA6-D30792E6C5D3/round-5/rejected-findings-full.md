### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: Optional trailers enable diff-gating downgrade without independent verification
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: New optional trailers let the plan author downgrade diff hard gating without external verification. An agent can write understated `diff_added` or `mechanical_churn:true` on a multi-thousand-line plan; Step 2b.5 and `plan-review-loop` proceed without Split/Cancel though legacy total churn would have hard-blocked. Treat as an explicit operator-accepted trust boundary, or add independent measurement / retain hard prompt when `diff_lines` exceeds the legacy threshold.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: Empty snapshot forbids first-time optional trailer introduction after revision
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: An empty snapshot forbids any new optional trailers after revision. A legacy plan revised to first emit `mechanical_churn` / `diff_added` for relief fails preservation until the operator pre-seeds trailers before rewrite. Document as policy or relax the empty-snapshot rule to allow intentional first-time trailer introduction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_18: Empty keys_file skips pre-dedup restore on validation failure
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: An empty `keys_file` skips pre-dedup restore on validation failure. On a rare dedup path, `plan.txt` can remain deduped with spurious trailers when validation fails and `keys_file` was empty. Always snapshot the plan before dedup `mv`, or restore from dedup input on any validation failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Redundant Bash 08/09 filter duplicates awk rules in check-plan-size
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Bash-side 08/09 rejection in `check-plan-size.sh` duplicates awk metadata-block rules. The duplicate path increases drift risk if awk rules change without updating Bash. Remove the redundant Bash filter or document it as defensive-only with awk as the single source of truth.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Leading-zero and 08/09 trailer behavior under-documented for designers
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Leading-zero and 08/09 trailer handling extends beyond strict digit grammar in plan prose. Plans with `diff_added: 002001` or `diff_added: 08` may behave differently than designers expect from Step 2b. Document normalized decimal rules in Step 2b and `flags.md` designer guidance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

