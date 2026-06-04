### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: Breadcrumbs can disappear or bypass expected stderr visibility under quiet mode
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-stream-protocol-output.txt
- **Severity**: important
- **Concern**: BreadcrumbWriter/lib-quiet routing can hide ship-phase and CI poll progress from the operator, especially when `LARCH_QUIET_ACTIVE` is set or FD/log routing is unavailable; tests also miss quiet-active breadcrumb coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-stream-protocol-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_12: Python ship ignores `--no-logs-commit` during pre-rebase flush
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `/implement --no-logs-commit` with `LARCH_SHIP_PR_IMPL=python` can still run `flush_logs_pre` on CI rebase because the flag/state is not propagated or honored.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: Quiet log file path is not bounded
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `LARCH_QUIET_LOG_FILE` can direct quiet-mode breadcrumbs to arbitrary filesystem paths without session-root/path-boundary checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: PR identity recovery trusts `gh` output too readily
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: URL-based PR recovery validates URLs but can still bind shipping to an unintended PR if `gh` output is adversarial/buggy while APIs lag.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_21: Empty untracked run dir bypasses volatile-only skip
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: An empty untracked run tree can still be added/committed, diverging HEAD from the green PR head.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_24: Real-CLI transcript coverage for `gh pr create` is too thin
- **Reviewer(s)**: dyn-gh-cli-output.txt
- **Severity**: latent
- **Concern**: The test for dropping unsupported `--json` uses a one-line fixture and does not exercise realistic gh stdout/stderr prose or real binary argv behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gh-cli-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_26

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_26: Volatile cleanup resets too broad a run-tree prefix
- **Reviewer(s)**: dyn-git-porcelain-output.txt
- **Severity**: latent
- **Concern**: `_cleanup_volatile_run_tree` runs `git reset HEAD -- <rel>` for the entire run directory instead of only volatile paths, creating a wider blast radius if classification is broadened or wrong.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-git-porcelain-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: `pr_for_branch` duplicates PullRequest JSON parsing
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `pr_for_branch` parses PullRequest JSON separately after `_pull_request_from_json`, so list/view parsing can drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: PR URL recovery stack is overly complex
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Multiple overlapping PR URL recovery entrypoints make conflict/success recovery ordering harder to reason about.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Volatile-only skip uses a magic `CommandResult.argv` sentinel
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Callers must know the special `("larch-log-volatile-only",)` tuple contract instead of consuming an explicit outcome/metadata field.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: `_volatile_only_under_run_tree` is a no-op wrapper
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The helper adds indirection without behavior beyond an empty check.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Python-path failure contracts are split
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The orchestrator must special-case Python version guard `STALLED` exit 4 versus driver bug `INTERNAL_ERROR` exit 1 without a shared emitter.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: `_ensure_head_matches_pr` return type has stale `None` handling
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: A redundant `head_match is not None` branch obscures merge control flow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

