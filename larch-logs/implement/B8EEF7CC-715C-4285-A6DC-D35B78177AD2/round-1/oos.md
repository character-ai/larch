### FINDING_11: [OUT_OF_SCOPE] Version race gate remains active after bump removal
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `_version_race_gate` still runs during merge despite the bump path being retired, adding unnecessary merge failures or complexity for version-shaped subjects.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_12: [OUT_OF_SCOPE] Python selector docs conflict with state-file/JSON routing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-state-machine-output.txt, dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: `skills/implement/SKILL.md` documents Python JSON routing only partially while Step 8+ still centers bash `ship-pr.sh`/`ship-pr-state.sh`, risking stale or missing `FAILED_RUN_ID`, redundant state writes, or failure to invoke the Python path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-state-machine-output.txt, dyn-bash-parity-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_16: [OUT_OF_SCOPE] No test pins manifest-before-report ordering
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-runlogs-output.txt
- **Severity**: important
- **Concern**: `flush_logs_post` lacks tests asserting manifest `status=done`/`pr_number` are written before final report generation, so fail-closed ordering can regress silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-runlogs-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_4: [OUT_OF_SCOPE] Checks phase ignores session tool availability
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-state-machine-output.txt, dyn-bash-parity-output.txt, dyn-runtime-cli-output.txt
- **Severity**: important
- **Concern**: `run_ship()` hardcodes Codex/Cursor availability as true, so degraded sessions may dispatch unavailable external fixers instead of following bash Step 0/session-env routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-state-machine-output.txt, dyn-bash-parity-output.txt, dyn-runtime-cli-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_40: [OUT_OF_SCOPE] Postbump rebase conflicts may invoke fixers unlike bash
- **Reviewer(s)**: dyn-finalize-output.txt
- **Severity**: latent
- **Concern**: Python postbump may use conflict-resolution fixers during rebase, whereas bash Step 8b bails on rebase conflicts without in-phase fixers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-finalize-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_45: [OUT_OF_SCOPE] Exit-code/default-bash observations are non-defect but still untested
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: nit
- **Concern**: Review notes that Outcome exit-code mapping and default `LARCH_SHIP_PR_IMPL=bash` appear preserved, but full merged postmerge behavior is not exercised.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_46: [OUT_OF_SCOPE] Python teardown is not yet wired live
- **Reviewer(s)**: dyn-finalize-output.txt
- **Severity**: nit
- **Concern**: `python/finalize.teardown` is not invoked by `ship.py` today; teardown parity gaps matter primarily for future cutover and tests while live Step 18 still uses bash.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-finalize-output.txt: Address the concern above.

Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_6: [OUT_OF_SCOPE] Driver acceptance and CLI/state-machine tests are too thin
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-state-machine-output.txt, dyn-ci-merge-output.txt, dyn-runtime-cli-output.txt
- **Severity**: important
- **Concern**: `python/test_ship.py` lacks most plan-mandated e2e/driver scenarios, including draft/forked/PR-only paths, transient and needs-user handbacks, CI goto-rebase, cap exhaustion, re-entry, merge retry, and CLI argv/env seams.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-state-machine-output.txt, dyn-ci-merge-output.txt, dyn-runtime-cli-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_7: [OUT_OF_SCOPE] Pre-PR log flushing can run twice
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-finalize-output.txt
- **Severity**: important
- **Concern**: Both `finalize.postbump` and the driver pre-PR phase call `flush_logs_pre`, risking redundant commits/reporting compared with bash’s single pre-push refresh flow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-finalize-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_8: [OUT_OF_SCOPE] Legacy exit constants can be confused with Outcome routing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-runlogs-output.txt, dyn-ci-merge-output.txt, dyn-runtime-cli-output.txt
- **Severity**: latent
- **Concern**: Legacy `EXIT_BAIL`/`EXIT_STALL` constants share numeric values with newer Outcome exit mappings, making future misrouting easy even if current routing uses `OUTCOME_EXIT_MAP`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-runlogs-output.txt, dyn-ci-merge-output.txt, dyn-runtime-cli-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

