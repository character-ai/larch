### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: PR creation resolution is over-layered
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `pr_create` resolution now spans many layered helpers and extra `gh` calls, making the success path slow, hard to reason about, and difficult to maintain.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_12: Force-push recovery compares against stale pre-recovery head state
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-merge-race-output.txt
- **Severity**: important
- **Concern**: After force-push recovery succeeds and refreshed CI/state checks pass, `merge_pr` still compares the refreshed PR head OID to the stale pre-recovery snapshot and returns `CI_NOT_READY` instead of merging in the same call.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-merge-race-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: Volatile-only behavior lacks full publish-path testing
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Tests do not exercise volatile-only cleanup through the full `flush_logs_pre` publish path, so dirty porcelain or spurious commits could escape isolated helper tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_16: Version guard test is tautological
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-py311-floor-output.txt
- **Severity**: latent
- **Concern**: The Python version guard test checks local comparison logic rather than executing or structurally pinning the actual SKILL shell guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-py311-floor-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: URL validation uses weak substring matching
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `_repo_matches_pr_url` uses substring containment rather than strict URL parsing, weakening the first validation gate for recovered PR URLs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Volatile cleanup logic is dense and hard to review
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Volatile-only flush cleanup implements porcelain parsing and git cleanup inline with dense comprehensions, increasing regression risk in future run-log changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: Volatile cleanup failures expose raw porcelain paths
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Volatile cleanup failure detail includes raw porcelain paths, which can reveal sensitive repository path names in operator-visible JSON.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_22: Volatile cleanup fails closed on unrelated repo dirt
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Volatile-only cleanup requires repo-wide porcelain to be empty after cleanup, so unrelated local edits can stall each CI/rebase refresh iteration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_23: Staged detection may reset too broadly
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `has_staged` checks only `line[0]`, so unusual porcelain states can trigger broad resets that disturb unrelated staged run-log files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_24: OID polling shares retry budget with UNKNOWN merge-state polling
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Force-push OID polling and UNKNOWN merge-state polling share the same retry constant, so one concern can consume the other’s budget.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Merge convergence lacks full single-cycle regression coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Tests do not fully model the intended one-monitor/one-merge green path, so merge-time flush churn or repeated CI monitor loops could regress without failing tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_31

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_31: List-based post-create recovery is not validated
- **Reviewer(s)**: dyn-gh-create-output.txt
- **Severity**: important
- **Concern**: Immediate `pr_for_branch` recovery after create returns a PR without the same `pr_view` head-ref/state validation used for URL recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gh-create-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_36

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_36: Run-log secret scrub warnings bypass quiet routing
- **Reviewer(s)**: dyn-stdio-quiet-output.txt
- **Severity**: latent
- **Concern**: `_warn_secret_scrub` writes directly to stderr, so scrub warnings may not reach the same operator-visible quiet channel as ship/CI breadcrumbs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stdio-quiet-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Python 3.11 floor is fragmented across docs, skills, and local checks
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-py311-floor-output.txt
- **Severity**: latent
- **Concern**: The Python 3.11 runtime floor is duplicated or missing across skill prose, docs, report-token surfaces, Makefile/local checks, and relevant-checks, creating drift and unclear operator expectations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-py311-floor-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

