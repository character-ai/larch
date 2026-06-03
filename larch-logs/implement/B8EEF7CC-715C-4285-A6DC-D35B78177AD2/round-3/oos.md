### FINDING_12: [OUT_OF_SCOPE] RecordingRunner helpers are duplicated across tests
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Multiple test modules duplicate `RecordingRunner`, risking helper drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_2: [OUT_OF_SCOPE] Finalize bash-parity coverage is only smoke coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt, dyn-ci-harness-output.txt
- **Severity**: important
- **Concern**: `python/test_finalize_bash_parity.py` is labeled/treated as bash parity but does not invoke `scripts/implement-finalize.sh`, so postbump/postmerge/teardown behavior can drift from bash while tests stay green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt, dyn-ci-harness-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_21: [OUT_OF_SCOPE] Report subprocesses inherit the full environment
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `_report_subprocess_env` forwards the full parent environment to report helpers, so child logging could expose tokens or other secrets.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_25: [OUT_OF_SCOPE] OOS checkpoint can use the wrong RUN_ID
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: OOS checkpoint fallback derives `RUN_ID` from session id rather than parent issue/finalize state, which can miss `oos-issues.ndjson` on rediscovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_36: [OUT_OF_SCOPE] Default bash implementation remains unchanged
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: nit
- **Concern**: The default `LARCH_SHIP_PR_IMPL=bash` is unchanged; many Python-path risks apply only when operators opt into Python.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_39: [OUT_OF_SCOPE] Plan references rebase_and_rebump but code exposes rebase_and_push
- **Reviewer(s)**: dyn-ci-handback-output.txt
- **Severity**: nit
- **Concern**: The plan names `rebase.rebase_and_rebump` for CI goto-rebase, while the current module exposes and uses `rebase_and_push`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-handback-output.txt: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_40: [OUT_OF_SCOPE] transient_rerun_attempted behavior is bash-adjacent and reasonable
- **Reviewer(s)**: dyn-ci-handback-output.txt
- **Severity**: nit
- **Concern**: The in-process transient rerun wiring for `no-changes` appears reasonable and bash-adjacent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-handback-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_41: [OUT_OF_SCOPE] CI-fix fork flags still depend on ship-pr-state.sh in one path
- **Reviewer(s)**: dyn-ci-handback-output.txt
- **Severity**: latent
- **Concern**: OOS checkpoint fallback to finalize state helps Python runs, but autonomous CI-fix step 2 still reads fork flags only from `ship-pr-state.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-handback-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_45: [OUT_OF_SCOPE] Bash teardown shares string-prefix cleanup weakness
- **Reviewer(s)**: dyn-teardown-state-output.txt
- **Severity**: latent
- **Concern**: Bash teardown uses a similar non-canonical cleanup-target pattern; Python inherits the weakness but adds direct `shutil.rmtree`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-teardown-state-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_46: [OUT_OF_SCOPE] Cleanup allowlist omits XDG_CACHE_HOME
- **Reviewer(s)**: dyn-teardown-state-output.txt
- **Severity**: nit
- **Concern**: `finalize.py` omits `XDG_CACHE_HOME` from the cache cleanup allowlist, causing fail-safe cleanup skips for non-default cache layouts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-teardown-state-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_47: [OUT_OF_SCOPE] Positive hardening was observed
- **Reviewer(s)**: dyn-teardown-state-output.txt
- **Severity**: nit
- **Concern**: `write_finalize_state()` newline rejection, JSON stdout redaction, and tracking issue title redaction are positive hardening measures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-teardown-state-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_49: [OUT_OF_SCOPE] docs/linting omits test-merge-parity
- **Reviewer(s)**: dyn-ci-harness-output.txt
- **Severity**: nit
- **Concern**: `docs/linting.md` documents `make test-merge-pr` but not the new `make test-merge-parity` target.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-harness-output.txt: Address the concern above.

Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_7: [OUT_OF_SCOPE] flush_logs_post writes final report before manifest done and lacks ordering tests
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-state-machine-output.txt, dyn-bash-parity-output.txt, dyn-runlog-integrity-output.txt, dyn-teardown-state-output.txt, dyn-ci-harness-output.txt
- **Severity**: important
- **Concern**: `flush_logs_post` can render final reports/ledgers before setting manifest `status=done`/`pr_number`, violating the planned fail-closed ordering; existing tests assert final state but not call order.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-state-machine-output.txt, dyn-bash-parity-output.txt, dyn-runlog-integrity-output.txt, dyn-teardown-state-output.txt, dyn-ci-harness-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_8: [OUT_OF_SCOPE] Legacy exit aliases can confuse outcome routing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-state-machine-output.txt, dyn-bash-parity-output.txt
- **Severity**: nit
- **Concern**: Legacy `EXIT_BAIL`/`EXIT_STALL` constants duplicate newer outcome-map values and are easy to import or reason about incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-state-machine-output.txt, dyn-bash-parity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

