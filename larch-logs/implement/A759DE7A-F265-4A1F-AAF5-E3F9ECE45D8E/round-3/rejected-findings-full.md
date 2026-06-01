### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: cursor sidecar token normalization untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Only codex sidecar normalization is tested; cursor path is not. Shape drift in cursor token scrape could break reporting silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add cursor sidecar normalize_sidecar test.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: duplicate BEHIND/main_advanced coverage across harnesses
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `test_merge.py` and `test_merge_bash_parity.py` both cover BEHIND→`main_advanced`, causing redundant failures that obscure which harness broke.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Consolidate; reserve bash-parity for uncovered scenarios.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_22: ensure_pr may pass uncomposed bodies to pr_create
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `ensure_pr` allows caller-supplied bodies into `pr_create` without the `compose_pr_body` fail-closed guard. A Phase 7 driver could pass secrets that only get best-effort redaction without abort.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Route all PR bodies through compose_pr_body or enforce fail-closed redaction in ensure_pr before pr_create.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_26

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_26: pr_view ShipError swallowed before merge attempt
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `pr_view` `ShipError` is swallowed and merge proceeds. Transient `gh pr view` failure can lead to merge attempts when PR state is unknown.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Retry pr_view or fail closed before merge when PR state unknown.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_32

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_32: no Python append_execution_issue / append_tool_failure writers
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Plan lists bash append helpers under run_logs ports, but Python has no `append_execution_issue` / `append_tool_failure` writers. Phase 7 driver may still shell to bash to record failures during implement unless explicitly deferred.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add append helpers or document explicit deferral to Phase 7 with grep-zero bash caller goal


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_33

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_33: token/timing pre-push refresh uses sidecar scrape not ledger scripts
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Pre-push token/timing refresh uses sidecar scrape rather than `token-report.sh` / `timing-report.sh` with session-env ledgers. Ledger-backed batches may be empty vs bash refresh.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Load session-env keys and port report renderers or document typed-format subset for Phase 7


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_39

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_39: git.remotes() unused; fork push semantics unclear
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `git.remotes()` was added but is unused; plan mentions origin vs upstream fork-aware selection. Dead API surface; future fork push semantics are unclear without wiring or documenting origin-only contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Wire remotes into select_push_remote per bash or document origin-only and remove unused helper

---

**Merge notes (for voters, not part of machine output):**
- Input findings **50–51, 60–62** were positive bash-parity attestations with no defect — excluded.
- Input **55–56, 63–64** were OOS tracking/observation-only — excluded from in-scope list (related test gaps absorbed into FINDING_16 where in-scope).
- **FINDING_36** and **FINDING_37** are related force-push branch identity issues but require distinct fixes (ensure_pr push path vs generic `force_push_recovery` API), so kept separate.
- Generic “Address the concern above” bullets from specialist slots were omitted per aggregator rules.

Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

