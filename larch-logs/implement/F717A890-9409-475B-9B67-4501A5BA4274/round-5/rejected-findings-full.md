### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: Boolean state parsing is duplicated across modules
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Boolean parsing exists separately in `ship.py` and `run_logs.py`, risking inconsistent strictness between hydration and write/read behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: _try_current_branch duplicates git.try_current_branch
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `_try_current_branch()` reimplements existing branch-probe behavior with a broad exception path instead of using `git.try_current_branch()`, increasing the chance of divergent detached-HEAD or checkout handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: Durable state flags can override argv and force gh-skipped routing
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-state-injection-output.txt
- **Severity**: important
- **Concern**: State-file durable flags such as `REPO_UNAVAILABLE` and `FORKED_TARGET` can override argv/context, disable normal GitHub/branch verification, and steer resume into gh-skipped open-pr/merged paths based on tampered state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-state-injection-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: State content is trusted after path confinement
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Although the state file path is confined under tmpdir, the content is still fully trusted for counters, durable flags, and classification before stronger integrity/session binding.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_23: Fresh no-state-file routing lacks an early branch-safety guard
- **Reviewer(s)**: dyn-resume-fsm-output.txt
- **Severity**: important
- **Concern**: When no state file exists, `_resume_plan()` returns fresh without probing the current branch or applying the main/master guard, allowing checks and initial state writes before later postbump safety checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-fsm-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_24: Corrupt state metadata is collapsed into checkout-mismatch refusal
- **Reviewer(s)**: dyn-resume-fsm-output.txt
- **Severity**: latent
- **Concern**: Invalid persisted metadata such as bad `BRANCH_NAME`, `PR_URL`, `MERGE_RESULT`, or `REPO` is surfaced as `checkout-mismatch`, conflating corrupt-state repair with real checkout mismatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-fsm-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Counter persistence is repeated across many state-write call sites
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Many `_write_ship_state()` / `_write_terminal_state()` calls repeat counter kwargs manually even though `ResumeCounters` exists, making it easy for future writes to omit a counter and reset session-wide caps.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_30

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_30: PR_URL validation permits command-substitution-shaped payloads
- **Reviewer(s)**: dyn-state-injection-output.txt
- **Severity**: latent
- **Concern**: `_PR_URL_RE` allows characters such as `$`, `(`, and `)`, so tampered state can preserve command-substitution-looking URLs for future consumers even if current bash readers quote safely.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-injection-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: _resume_plan is too large and centralizes too much classification logic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `_resume_plan()` is a large classifier embedded in an already large driver module, making future resume edge cases and bash-parity precedence harder to audit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Resume tests duplicate large fixtures and monkeypatch stacks
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: New resume tests duplicate substantial state-file fixtures and common monkeypatch setup, increasing maintenance cost and drift risk as more acceptance cases are added.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Iteration-cap stall handling is duplicated in CI-loop branches
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Two CI-loop branches duplicate the same iteration-cap stall write/result handling, so future cap-semantics changes could diverge between paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: ResumePlan duplicates ResumeCounters scalar fields
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `ResumePlan` repeats counter fields instead of composing `ResumeCounters`, requiring coordinated edits across multiple types/factories when counters change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

