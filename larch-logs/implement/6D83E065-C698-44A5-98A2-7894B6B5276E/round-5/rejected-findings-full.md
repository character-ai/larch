### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: Design OOS path resolution is duplicated and can miss design-export files
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Design OOS path resolution is implemented in multiple places and lacks regression coverage for stale `DESIGN_TMPDIR` versus design-export fallback. Divergence can reopen the design-export miss class and cause checkpoint gates to count the wrong files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: Python materialization persists `OOS_PENDING=true` too early
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_materialize_manifest_oos` writes `OOS_PENDING=true` before materialization succeeds and may not clear it on success, causing persisted state to block later ship or PR-create paths even after disposition is satisfied.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_15: Manifest security routing under-detects title and prose-only security signals
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-public-redaction-output.txt
- **Severity**: important
- **Concern**: Manifest OOS routing only reliably keys off structured focus-area signals, so security-sensitive content in title or prose-only description markers can be materialized into public accepted-OOS artifacts and issue bodies.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-public-redaction-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: Manifest security classification uses raw or inconsistently normalized fields
- **Reviewer(s)**: dyn-public-redaction-output.txt
- **Severity**: important
- **Concern**: Security routing classifies raw `focus_area` and description strings before the same normalization/sanitization used for public writes. Leading whitespace or documentation mismatch can cause security-marked observations to bypass the private sidecar.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-public-redaction-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: OOS ndjson discovery diverges across shell, checkpoint, and Python paths
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-oos-flow-output.txt, dyn-python-parity-output.txt
- **Severity**: important
- **Concern**: `oos-issues.ndjson` discovery is duplicated and inconsistent across ship drivers and checkpoint code. Missing or ambiguous `RUN_ID` handling can either block valid OOS disposition or attach evidence from the wrong run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-oos-flow-output.txt, dyn-python-parity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Public OOS redaction is not centralized or mechanically enforced
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Public OOS redaction is partly prompt-enforced and partly reimplemented locally. Token drift or missed orchestration steps could leak internal URLs or secrets into public issue bodies.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_5: `write_description` subshell loop repeats description prefixes
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `write_description` uses a piped `while` loop whose state changes occur in a subshell, so multi-line descriptions can receive repeated `- **Description**:` prefixes and mis-parse at filing time.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Tool failure appending can duplicate or miss entries
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `_append_execution_tool_failure` can append manually even after `append-tool-failure.sh` succeeds if substring matching misses, creating duplicate or inconsistent Tool Failures state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Scoped load-directive tests rely on fragile awk windows
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Load-directive tests use proximity windows that can pass despite separating mandatory load lines from their entry points, allowing future SKILL.md edits to silently drop CI protection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: Materializer is invoked twice per site unnecessarily
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Step 2 and PR prep run the materializer once for `--count-only` and again for full output, duplicating manifest parsing and jq work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

