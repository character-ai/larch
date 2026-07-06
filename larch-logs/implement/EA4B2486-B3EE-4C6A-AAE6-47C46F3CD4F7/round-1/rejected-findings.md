### [rejected] FINDING_5

**Rejected subtype:** dismissed (0 YES)

### FINDING_5: collect_failed_logs should preserve gh timeout state
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: `collect_failed_logs` collapses `EXIT_TIMEOUT` into generic error handling, so upstream poll logic cannot distinguish a bounded timeout from a different gh failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** dismissed (0 YES)

### FINDING_6: repo slug parsing and prefetch test are too loose
- **Reviewer(s)**: cursor-specialist-testing, cursor-specialist-correctness
- **Severity**: minor
- **Concern**: `resolve_repo` accepts any stdout containing `/` without validating a GitHub slug, and the prefetch test still stubs JSON repo-view output instead of plain slug stdout. That can let malformed gh output poison manifests while parsing regressions stay untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** dismissed (0 YES)

### FINDING_8: baseline suppression should key on kind as well as artifact
- **Reviewer(s)**: dyn-dyn-wire-ratchets
- **Severity**: major
- **Concern**: Baseline suppression and dedupe key only on the artifact string, but manifest identity is `(kind, artifact)`, so one baseline row can suppress the wrong kind or duplicate rows across kinds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-wire-ratchets: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** dismissed (0 YES)

### FINDING_9: direct subprocess gh reads still bypass the new ratchet
- **Reviewer(s)**: dyn-dyn-wire-ratchets
- **Severity**: major
- **Concern**: The A5 lint only catches `runner.run(["gh", ...])` in the gh wrapper layer, so direct `subprocess.run`/`check_output`/`call` argv literals beginning with `gh` can still bypass the timeout invariant on read paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-wire-ratchets: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

