### FINDING_1: Repeated parser subprocesses slow tally runs
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `tally-plan-review.sh` repeatedly invokes `parse-judge-vote-and-rating.sh` per finding/voter with no cache, multiplying subprocess cost on large ballots and repeated CI harness runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: Vote tally helpers are duplicated and drifting
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `count_votes_for_id` duplicates newer parser-based counting logic, leaving maintainers with multiple vote-counting paths that may diverge between plan review, code review, and documentation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] Parser-based vote counting lacks parity with legacy vote extraction
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Plan-review tally now uses parser-derived votes while other paths still rely on `vote_for_id`; without systematic parity fixtures, edge-case voter lines can produce different accepted/rejected results, TSV values, or `/design` versus `/review` behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_4: Axis enum definitions are duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Axis enums are duplicated between the parser and voter prompt rendering, so renaming an axis in one place can silently break prompt/parser compatibility.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: lib-vote-tally docs omit main-agent-vote-required
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `classify_result` documentation and tests do not fully lock the new `main-agent-vote-required` outcome for zero-eligible rows, risking downstream callers or regressions that still assume `rejected`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] Code-review tally does not accept main-agent-vote-required
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `tally-code-votes.sh` only accepts the older result labels, so a future zero-eligible code-review path returning `main-agent-vote-required` would abort instead of handling the result.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] Failed tally can leave a misleading header-only TSV
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `tally-plan-review.sh` resets `findings-classification.tsv` before successful completion, so abort paths can leave or publish a header-only TSV that consumers may treat as a valid empty/zero-finding result.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_8: Parser records ratings even when the vote token is invalid
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Malformed anchored vote lines can produce empty vote cells but populated rating-axis cells, making TSV rows look partially valid while tally counts the judge as errored.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_9: Plan text still describes zero-judge rows as rejected
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The issue plan or acceptance text still expects `rejected` for zero-judge rows while the code emits `main-agent-vote-required`, causing downstream filters, analytics, or harness expectations to disagree with landed semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_10: Parser exit and empty-ID cases lack direct tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `parse-judge-vote-and-rating.sh` lacks direct tests for unreadable files and missing ID lines, so failures can be masked by callers that tolerate parser errors.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: Classification output path can overwrite outside DESIGN_TMPDIR
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `--findings-classification-out` lacks containment and symlink checks, allowing a caller-supplied absolute path or destination symlink to truncate or overwrite files outside the design session directory.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_12: Voter file paths can read arbitrary host files
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `--voter SLOT:PATH` accepts any readable non-symlink file, so a misconfigured tally can ingest arbitrary host-file lines and publish derived forensic rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_13: Main-agent vote instructions omit rating-axis tokens
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Main-agent adjudication instructions do not require the same rating-axis tokens as panel judges, so main-agent re-tally can populate votes while leaving rating columns empty and uncertainty inferred.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_14: Missing ballot ID lines are reported as uncertain
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: When no anchored ballot ID line exists, the parser emits `PARSED_UNCERTAIN=true`, conflating absent vote lines with explicit or inferred judge uncertainty.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_15: Plan-review loop does not reconcile classification TSV after tally failure
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `plan-review-loop.sh` handles tally errors without normalizing the classification TSV state, so stub and real tally failures can leave different artifacts that diverge from `voting-tally.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_16: Hyphen-glued vote/rating tokens drop rating axes
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Axis parsing only recognizes whitespace-separated tokens after the vote, so lines like `YES-CORRECTNESS=...` record the vote but drop rating axes and infer uncertainty.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_17: MainAgent fallback populates v1 forensic columns
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: When panel slots are empty, the MainAgent voter file is mapped into `v1`, conflicting with the stated convention that MainAgent is not mapped to any `vN` column and confusing `v1=Claude` semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_18: Dispatcher traceability points at the wrong prompt file
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The plan listed `dispatch-plan-voters.sh` for prompt extension even though prompt text lives in `render-voter-prompt.sh`, making traceability look incomplete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] Symlink enumeration differs from plan wording
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `design-log-publish.sh` finds symlinks and rejects them during validation rather than excluding them up front, which is not a functional gap but differs from the plan sketch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
