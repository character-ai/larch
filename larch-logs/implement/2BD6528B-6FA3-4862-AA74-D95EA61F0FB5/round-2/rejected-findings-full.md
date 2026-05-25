### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: Inconsistent job-token separators complicate triage
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `ci-failed-jobs` KV output and `ship-pr` temporary paths use inconsistent `job:shard` vs `job-shard` formatting, making incident correlation harder.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: Mixed unfixable test does not prove lint ran before bail
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The mixed gitleaks+lint unfixable test does not assert that the lint local command ran and was fixed before the gitleaks bail, so a miswire could still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: lint-fix prompt display does not escape command metacharacters
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `lint-fix-loop.sh` interpolates `target_cmd_display` inside inline markdown backticks without escaping. If argv-file inputs are ever widened beyond the fixed dispatcher, backticks or newlines could alter prompt structure for the external coder.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: `_stage_and_push_ci_fixes` behavior is under-documented for per-job path
- **Reviewer(s)**: dyn-refactor-completeness-output.txt
- **Severity**: latent
- **Concern**: `_stage_and_push_ci_fixes` is not just a push primitive; when `checks_site` is non-empty it also runs the full relevant-checks gate. The per-job success path calls it that way after Phase B verification, which may be intended defense-in-depth but should be documented or split if mapped-job verification is meant to be sufficient.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-refactor-completeness-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Duplicate CI job mapping can drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: CI job-name mapping is duplicated between `ci-failed-jobs.sh` job classification and `ship-pr.sh` per-job argv dispatch, while drift tests only pin one side. A CI job rename or addition can pass the existing drift test but fail or misroute at runtime.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Per-job TSV values are used in paths without revalidation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `ship-pr.sh` builds `IMPLEMENT_TMPDIR` path prefixes from TSV `job_name` and `shard` fields without reapplying the validation used by `ci-failed-jobs.sh`. A tampered TSV row could use path traversal in generated args or log filenames before `lint-fix-loop` consumes them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: Per-job push trusts gh failed-job listing completeness
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: The per-job-only push path assumes `gh run view` lists all failed jobs. If secret-scan jobs such as `gitleaks` or `trufflehog` are omitted, the path could skip vendor recovery and push while remote secret-scan jobs remain failed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

