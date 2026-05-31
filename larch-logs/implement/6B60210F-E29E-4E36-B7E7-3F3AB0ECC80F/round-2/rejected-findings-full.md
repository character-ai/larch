### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: Duplicated agent output/refusal scan paths
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `python/agents.py` duplicates parse/refusal scans for sidecar vs `output_file`, raising classification drift risk vs bash on a single path.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No distinct verbatim fix per slot; factor shared scan helper.)

---


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: Weak `test_config.py` constant coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Constant coverage in `python/test_config.py` is weaker than plan wording; regressions in new config constants may go unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No distinct verbatim fix per slot; assert full documented constant set.)

---


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: `binary_present` bool API diverges from bash truthiness
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `binary_present` bool API in `python/agents.py` diverges from bash `1`/`true`/`yes` rules; passing string `"0"` skips binary-missing classification in Python.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No distinct verbatim fix per slot; normalize like bash or require bool at API boundary.)

---


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: `launch_tier` invokes `.sh` without explicit `bash`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `launch_tier` runs `scripts/launch-*-ci.sh` without explicit `bash`; non-executable script bits cause `EACCES` from `proc.run`.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No distinct verbatim fix per slot; prepend `bash` to argv or document executable requirement.)

---


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_23: Plan says `ship-pr.sh` untouched but branch edits it
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Plan acceptance says `scripts/ship-pr.sh` is untouched, but the branch edits `_per_job_argv` for python jobs — documentation/acceptance mismatch with additive CI job mapping.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No distinct verbatim fix per slot; update plan/acceptance text to include ship-pr job argv mapping as intentional.)

---

## Out of scope (Piece 2)


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Foundation context/outcome/logging modules unwired
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `python/outcomes.py`, `python/run_context.py`, and `python/logging_util.py` are test-only with no runtime wiring. There is no proof that `StepResult` / `RunContext` / journal APIs work on a real orchestration path before later phases.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No slot provided a fix beyond generic “address concern”; add minimal composition smoke or document API-only status in `python/README.md`.)

---


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Live `ship-pr.sh` adds Python CI job argv mapping
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `_per_job_argv` gains `python-lint` / `python-tests` cases mapping to `make py-lint` / `make py-test`. This contradicts strict “ship-pr untouched” Phase 1 acceptance but is needed for local CI-fix parity; should be an explicit strangler exception or deferred until cutover.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No distinct verbatim fix per slot.)

---


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Operator-path redaction regex looser than bash
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `python/redact.py` operator-path punctuation regexes may be looser than bash `sed` classes in `redact-tmpdir-paths.sh`. Some `/Users/.../...` punctuation-boundary paths may not match bash redaction parity.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No distinct verbatim fix per slot; align `NOT_PATH`/suffix exclusions with bash and extend parity tests.)

---


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: Duplicate `_ensure_success` in `git.py` and `gh.py`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `_ensure_success` is duplicated in `python/git.py` and `python/gh.py`, increasing maintenance when error messaging changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No distinct verbatim fix per slot; share one helper when a third module needs it.)

---


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

