### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: Cleanup retention uses whole-day `find -mtime` semantics
- **Reviewer(s)**: dyn-cleanup-semantics-output.txt
- **Severity**: latent
- **Concern**: Retention now follows `find -mtime +N` (integral 24-hour day rounding at `find` start) instead of the prior strict `(now - mtime) > RETENTION_DAYS * 86400` second boundary. Entries near the end of the retention window can be classified differently (off by up to roughly one day depending on platform `find` behavior).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cleanup-semantics-output.txt: If second-precision parity matters, keep top-level `find` for performance but filter candidates with an explicit `stat`/`test` against `RETENTION_DAYS * 86400`, or document that cleanup uses whole-day `find` semantics and align `LARCH_CLEANUP_RETENTION_DAYS` wording in `SECURITY.md` / `cleanup.md`.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: Doc vs Awk mismatch on `08`/`09` and `block_len`
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `lib-plan-optional-trailers.md` says regex-matching lines join the block, but Awk excludes `08`/`09` before `block_len`. Aligning Awk with the prose would break `check-plan-size` and octal-rejected parse expectations unless behavior is documented explicitly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Engineer aligns awk with prose and counts octal lines in block_len breaking check-plan-size and octal-rejected parse expectations Document that 08/09 match regex but are not added to block/block_len


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: Harness omits explicit `exit 0`
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Harness omits explicit `exit 0` required by the plan file spec; minor divergence from stated harness contract only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Append exit 0 after PASS echo


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: `write_fixture` unused `shift`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `write_fixture` performs `shift` but never uses remaining parameters, adding noise when reading the fixture API.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove the unused shift or document the intended multi-arg contract


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: `assert_eq_lines` bypasses `fail()` helper
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `assert_eq_lines` exits directly instead of routing through `fail()`, unlike `assert_has_key` and sibling harnesses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Route assert_eq_lines failures through fail() after printing got/want diff


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

