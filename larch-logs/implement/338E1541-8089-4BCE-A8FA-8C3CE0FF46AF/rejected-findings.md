# Rejected Findings

## Round 1

### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: NEVER #14 harness grep is intentionally narrow (two literals)
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Static greps for only two forbidden spellings can miss alternative direct-write forms to `session-env.sh` while still violating NEVER #14 intent, weakening CI regression detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Expand grep patterns or narrow documented harness guarantee to the literals checked
  - From cursor-specialist-edge-cases-output.txt: Expand forbidden patterns or document the intentional narrow grep as non-exhaustive.

---


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: Incomplete handling/docs for `STEP_FAILED` beyond gate/setup (incl. create-branch)
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Exit-code docs and Step 0 operator messaging focus on `session-entry-gate` / `session-setup`, leaving create-branch and other `STEP_FAILED` tokens under-documented or without the same normalized failure UX, so failures can look like silent `exit 2`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Update exit-code table to include create-branch path and fields emitted on stdout
  - From cursor-specialist-testing-output.txt: Add a failure branch or explicitly document the raw-only handling for create-branch failures
  - From cursor-specialist-edge-cases-output.txt: Add a generic failure branch or explicitly document supported `STEP_FAILED` tokens.

---


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: Missing harness for failing `token-claude-source` / `CLAUDE_SOURCE_OK=false`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Without a stubbed failure case, regressions in token capture or append-tool-failure wiring may not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a stubbed failing token-claude-source case asserting CLAUDE_SOURCE_OK=false and tail expectations

---


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_13: Misleading `_gh_out` name for gate stderr scrape
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The variable name suggests `gh` output rather than gate error scraping, which can mislead debugging.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Rename to a gate-specific identifier

---


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Redundant guard before reading caller dynamic archetypes max
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: An always-true empty check on `dynamic_archetypes_value` adds branches on every run without changing behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove the always-true -z guard on dynamic_archetypes_value.

---


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Step 0 implement-bootstrap prose length vs surrounding imperative style
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Long Step 0 prose in `skills/implement/SKILL.md` increases merge/conflict burden and reader fatigue for limited gain over the script contract doc.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Condense prose and defer detail to implement-bootstrap.md

---


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Umbrella / cross-doc wording vs shipped stderr (`larch_err`) advisory contract
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Umbrella or spec language still points at `emit`/FD-3 for warnings while the implementation documents stderr advisories, risking future “fixes” that move warnings back to FD-3/stdout and break KV purity or quiet-stream consumers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Align issue/umbrella wording with the delivered stderr contract on merge.
  - From cursor-specialist-edge-cases-output.txt: Align implementation with the umbrella contract or revise the umbrella / `implement-bootstrap.md` to bless stderr advisories.
  - From cursor-specialist-plan-fidelity-output.txt: Update umbrella issue text to match implement-bootstrap.md or explicitly dual-path emit under quiet sessions.

---


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: Exit code 2 conflation between argv/usage (`die_usage`) and infrastructure `STEP_FAILED` failures
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Documentation and operator mental models can misread malformed argv (usage) as the same class of Step 0 infrastructure failure that carries `STEP_FAILED` on stdout, because both use exit status 2.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Document argv failures as exit 2 or remove the "(other)" row
  - From cursor-specialist-edge-cases-output.txt: Use a distinct exit status for usage errors or emit an explicit `STEP_FAILED` usage token before exit.

---


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0



## Round 2




