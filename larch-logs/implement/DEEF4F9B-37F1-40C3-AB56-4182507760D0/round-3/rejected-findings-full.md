### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: Duplicate SIMPLE sentinel write fences can drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: The SIMPLE sentinel writes are duplicated in the Step 2a entry fence and Step 2a.5 repair fence, creating drift risk if future edits update ordering or filenames in only one place.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: Routing guard can miss bare Step 3b-to-Step 4 routing on mixed lines
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The routing guard skips whole lines containing the completion-boundary phrase, even if the same line also contains an unsafe bare Step 3b-to-Step 4 route.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: Compatibility tests inline-copy SKILL fence logic
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-harness-output.txt
- **Severity**: latent
- **Concern**: Legacy pause/resume fixtures copy compatibility-fence shell logic instead of sharing or parsing the authoritative SKILL fences, allowing test behavior to drift from runtime prose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-harness-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: Step 4 FINALIZE compatibility guard trusts symlink sentinel
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Step 4 checks `.completed/finalize` with `-f` but does not refuse symlinks, so local tmpdir tampering could bypass artifact validation before Gate C/publish.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: Passive-summary auto-continue routing is ambiguous
- **Reviewer(s)**: dyn-routing-output.txt
- **Severity**: latent
- **Concern**: Passive-summary auto-continue lists Step 3b, the completion boundary, and “the next Step 3 entry” ambiguously, which can be read as routing backward instead of forward through Step 4/Gate C.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-routing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_23: Step 2a.5 marker-only branch lacks shell failure checking
- **Reviewer(s)**: dyn-shell-fences-output.txt
- **Severity**: latent
- **Concern**: The Step 2a.5 marker-only repair branch writes completion markers without `set -e` or explicit status checks, so disk/permission failures may leave the run believing repair succeeded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-fences-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_24: SIMPLE guard literal is fragile
- **Reviewer(s)**: dyn-shell-fences-output.txt
- **Severity**: latent
- **Concern**: The SIMPLE guard compares against an unquoted literal pattern in the Step 2a entry and 2a.5 repair fences, which the reviewer flagged as fragile and harness-pinned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-fences-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_27

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_27: New structure-test helpers lack negative self-tests
- **Reviewer(s)**: dyn-harness-output.txt
- **Severity**: latent
- **Concern**: Several new structure-test helpers only have positive pins, so inverted awk logic or broken failure detection could remain green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_28

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_28: Routing guard verb matching can false-positive on substrings
- **Reviewer(s)**: dyn-harness-output.txt
- **Severity**: nit
- **Concern**: The route guard matches `enter` as a bare substring, so words like `re-enter`, `entering`, or `center` may trigger false positives on lines mentioning Step 3b and Step 4.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: FINALIZE failure handling is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: FINALIZE failure handling appears in both Step 3b and Step 4 compatibility guards, creating drift risk for warning text or exit behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

