### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: Predicate ordering for lifecycle plus brainstorm titles is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The harness does not simulate the mandatory Step 0b 2.5 predicate short-circuit order. A future reorder could pass structure checks while breaking combined titles such as `[DESIGNING] Brainstorm: foo`, where lifecycle rejection should take precedence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_11: Bare Brainstorm title fixture is missing
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The brainstorm hit fixtures omit the standalone title `Brainstorm`. A regression that breaks end-of-string matching for the bare prefix could pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: Title-prefix brainstorm auto-enable lacks explicit user confirmation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Step 0b sub-step 2.5 enables external brainstorm slots from the issue title alone. In a multi-writer repo, another collaborator could rename an issue with a `Brainstorm:` prefix, causing `/design` to launch Cursor/Codex brainstorm flows without an explicit argv opt-in from the operator.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Bash title-skip mirror can drift from jq archival filter
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `title_skipped_by_bash_mirror` re-implements archival prefix semantics instead of deriving them from `LARCH_TITLE_ARCHIVAL_PREFIX_JQ_FILTER`. Future changes to the jq filter could leave the bash mirror stale while tests still pass, letting production list filtering diverge from the harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: Harness does not cover stale CLAUDE_PLUGIN_ROOT fallback
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `scripts/test-lib-title-eligibility.sh` does not exercise `list-issues.sh` plugin root resolution when `CLAUDE_PLUGIN_ROOT` is stale. A broken repo-root fallback could fail at runtime while the title eligibility harness still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_9: nocasematch restore may leak shell option state
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `shopt -p nocasematch` restore handling may be unreliable on Bash 3.2, allowing `nocasematch` to leak in a long-lived sourced shell after lifecycle checks. That can affect later `=~` checks unexpectedly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

