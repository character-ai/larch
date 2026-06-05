### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: `PRESENCE_INPUT_EMPTY` stdout order is not tested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: No degraded-tools gate test asserts that `BOTH_DOWN` precedes `PRESENCE_INPUT_EMPTY`, so consumers depending on the documented KV order could break without CI catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: Design gate bootstrap/test pins omit the durable current-design symlink path
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash32-output.txt
- **Severity**: latent
- **Concern**: The `/design` gate and structure tests center on `$DESIGN_TMPDIR/source-env.sh` and do not fully accept or bootstrap from `current-design-env-$PPID.sh`, so a fresh Bash block can abort before reading durable env, or a valid symlink-based implementation can fail structure tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash32-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: Empty-presence bug path can still fall through to normal BOTH_DOWN prompting
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `PRESENCE_INPUT_EMPTY=true` is only treated as a warning signal; callers that pass empty presence flags may still run the normal BOTH_DOWN interactive prompt, preserving the original blocking behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: Shared `PRESENCE_INPUT_EMPTY` contract is not reconciled across review/research
- **Reviewer(s)**: dyn-kv-streams-output.txt
- **Severity**: latent
- **Concern**: The shared degraded-tools contract now describes `PRESENCE_INPUT_EMPTY` handling, but `/review` and `/research` gate paragraphs were left unchanged, creating ambiguity about whether those skills must log the same rehydration warning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-kv-streams-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: PR line-count failures are rendered as `N/A` without execution-issues breadcrumbs
- **Reviewer(s)**: dyn-pr-metrics-output.txt
- **Severity**: latent
- **Concern**: `write-final-report.sh` collapses helper failures, missing helpers, malformed KV, auth outages, and no-PR cases into `Lines (PR diff): N/A` without recording a warning, weakening post-run diagnosis.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pr-metrics-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: `compute-pr-line-counts.sh` discards GitHub API stderr
- **Reviewer(s)**: dyn-pr-metrics-output.txt
- **Severity**: latent
- **Concern**: When `gh api` fails, stderr is redirected to `/dev/null`, so operators cannot distinguish auth, rate-limit, 404, or network failures behind `LINES_STATUS=unavailable` / `REASON=gh-failed`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pr-metrics-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Shared degraded-tools documentation/example can drift from durable rehydration requirements
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `skills/shared/external-reviewers.md` documents the separate-block rehydration rule and `PRESENCE_INPUT_EMPTY` symptom, but the example/pins may still allow maintainers to copy or regress guidance that reintroduces empty presence inputs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: `write-final-report.sh` duplicates KV parsing with weaker `awk -F=` behavior
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `read_lines_kv` duplicates an existing KV parser and can misparse values containing `=`, increasing maintenance risk in the bundled PR-metrics work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: `PRESENCE_INPUT_EMPTY` warning breadcrumbs are not structurally pinned
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `/implement` and `/design` prose requires logging warnings when `PRESENCE_INPUT_EMPTY=true`, but structure tests do not pin the warning/execution-issues handling, so future edits could silently remove the operator-visible signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

