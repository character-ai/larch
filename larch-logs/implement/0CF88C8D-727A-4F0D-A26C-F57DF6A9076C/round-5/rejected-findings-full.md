### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: Public filing can expose accepted OOS vulnerability details without security tokens
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Accepted legacy/scope-drift OOS blocks without explicit security-routing tokens are now normalized and filed publicly. A vulnerability-shaped OOS finding without `focus-area: security` or `[security]` heading could become a public GitHub issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: Gate counter misses prose-only security markers
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `oos-non-security-block-count.awk` excludes only some security forms and may count accepted OOS with unfenced `focus-area = security` prose as non-security if producer screening is bypassed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_22: Reader regex behavior exceeds documented plan literals
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Reader backstops match `[OOS]` shorthand and trailing OUT_OF_SCOPE tags beyond the plan’s literal `FINDING_N: [OUT_OF_SCOPE]` form, making plan-to-code traceability incomplete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_24: Serializer writes output non-atomically and can leave partial public sinks
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Severity**: latent
- **Concern**: `flush_block` writes incrementally to `$OUTPUT_FILE` and exits on classifier failure. A mid-file failure after earlier blocks can leave a partially written public sink.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-portability-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_28

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_28: Emit-to-ship tests do not compare awk and Python counts on final sinks
- **Reviewer(s)**: dyn-parity-output.txt
- **Severity**: latent
- **Concern**: The review→ship path now has separate awk and Python counting authorities, but chained emit-tally tests do not compare both counts on final `oos-accepted-review.md` artifacts before ship.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-parity-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_29

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_29: Emit-tally tests miss malformed or missing `OOS_ACCEPTED_COUNT`
- **Reviewer(s)**: dyn-harness-wiring-output.txt
- **Severity**: latent
- **Concern**: `emit-tally` coerces absent or non-numeric `OOS_ACCEPTED_COUNT` to zero, which can route through serialize/truncate and wipe a pre-populated normalized sink. Tests only cover clean integer counts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-wiring-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Security routing classifier is duplicated across surfaces
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-portability-output.txt, dyn-parity-output.txt
- **Severity**: latent
- **Concern**: Security routing/classification logic is duplicated across tally, serializer, Python, and gate-counting paths, with slightly different rules and failure handling. Future drift could make one layer hold/filter a security block while another counts or serializes it publicly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-bash-portability-output.txt: Address the concern above.
  - From dyn-parity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Missing mixed security plus public OOS tally round test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: There is no test for a round containing both security-held and public accepted OOS. A regression could mis-set public OOS counts or leak security-routed blocks into public sinks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: Missing awk/Python parity coverage for legacy OOS counting
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-parity-output.txt, dyn-harness-wiring-output.txt
- **Severity**: latent
- **Concern**: Legacy header counting was extended in both awk and Python, but tests assert most cases separately rather than mechanically comparing both counters on the same fixtures. Regex drift could pass isolated suites while ship/gate behavior diverges.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-parity-output.txt: Address the concern above.
  - From dyn-harness-wiring-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: Missing issue filing regression for normalized OOS sinks
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Normalized OOS headers may parse and pass gates but still fail in `/issue` batch/combine/cap/dependency paths, yielding `OOS filed: 0` at runtime.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

