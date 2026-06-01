### FINDING_10: [OUT_OF_SCOPE] Missing plan-listed tests for new `ci_monitor` paths
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Plan testing-strategy cases for verify-failed retry, monitor `evaluate_failure` terminals, short-circuit rollback, and other new paths are absent from `python/test_ci_monitor.py`. Regressions may ship without pytest signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add the plan testing-strategy cases


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_19: [OUT_OF_SCOPE] Double `gh run view` on successful `read_failed_jobs` via `gh.failed_jobs`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Extra API calls under failure load; architectural deduplication opportunity, noted as not a test gap in this PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Deduplicate parse path using first failed_jobs_read result.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_20: [OUT_OF_SCOPE] No Python-vs-bash subprocess parity harness for `ci_monitor` decide/poll
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Phase 6 relies on Python table tests only; drift from `ci-decide.sh` possible until Phase 7.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Optional thin bash parity script at cutover.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_24: [OUT_OF_SCOPE] Bash CI rollback uses same unvalidated git paths
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Pre-existing in `ship-pr.sh`; same fixer trust model as Python port.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address in shared helper when cutting over Phase 7 driver


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_25: [OUT_OF_SCOPE] `pip install` without hash pinning in `prepare_python_toolchain`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Compromised requirements file at repo root could run arbitrary install commands on fix host; out of scope for Phase 6.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Out of scope for Phase 6; use pinned hashes if hardening dev CI fix path later


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0 Result=exonerated


### FINDING_30: [OUT_OF_SCOPE] No text fallback for `gh pr checks` in Python `gather_status`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Older `gh` without JSON could mis-classify CI; defer to Phase 7 cutover or port text fallback from `ci-status.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Defer to Phase 7 cutover or port text fallback


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_31: [OUT_OF_SCOPE] Missing tests for rollback, transient fallthrough, empty run_id gaps
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Regressions in fix-path recovery (inter-tier rollback, transient fallthrough, empty run_id) may ship unnoticed; overlaps thematically with in-scope test gaps but flagged out-of-scope by reviewer.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add tests for inter-tier rollback transient fallthrough empty run_id

Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


