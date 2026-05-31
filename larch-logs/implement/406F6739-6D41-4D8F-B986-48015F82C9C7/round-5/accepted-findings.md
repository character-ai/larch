### FINDING_1: risk-integration — uncommitted orchestrator-fence harness breaks CI
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `Makefile` and `SKILL.md` wire `test-step3-orchestrator-fence.sh` into `test-harnesses-9` / `make test-step3-orchestrator-fence`, but the harness is not in the committed tree (untracked or absent at HEAD). Clean checkouts and CI shard 9 fail with “No such file.” Once the script is added, `script-md-siblings` / relevant-checks also require `test-step3-orchestrator-fence.md` alongside other harness stubs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_10: risk-integration — harness not listed in `run-step3-review.md`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `run-step3-review.md` Harness section omits `test-step3-orchestrator-fence.sh` cited in `SKILL.md`, causing doc/harness discovery drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Document test-step3-orchestrator-fence.sh in run-step3-review.md or lib-phase-driver.md once committed.


### FINDING_11: risk-integration — cap-guard prose incomplete on rollback triggers
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Cap-guard prose in `SKILL.md` documents rollback only for `TALLY_PLAN_REVIEW_STATUS=tally-error`, not `LOOP_STATUS` tally-error or degraded-empty-collector handled in `run-step3-review.sh`, so operators following prose only may misdiagnose driver behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Update cap-guard prose to list all rollback triggers consistent with run-step3-review.sh and the branch matrix.


### FINDING_2: correctness — Step 3 orchestrator fence dropped LOOP_STATUS allow-list validation
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: After allowlisted parsing of `.step3-review-result.env` and stdout merge, the orchestrator only treats **empty** `LOOP_STATUS` as `panel-failed`. Invalid or tampered values (e.g. `cap_reached`, corrupted handoff) are not re-normalized against the branch-matrix allow-list, so no matrix arm matches and Gate routing becomes undefined. The same gap applies when stdout fallback is used without a result env file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Re-apply allow-list normalization in the orchestrator after merge; and/or let this invocation's stdout override file for LOOP_STATUS/TALLY when rc!=0 or values disagree.


### FINDING_3: correctness — file-first `.step3-review-result.env` can prefer stale outer state over fresh driver output
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: File-first handoff can keep stale outer `LOOP_STATUS` (e.g. prior `converged`) when the current driver exits non-zero with stdout `LOOP_STATUS=panel-failed`, mis-routing Gate B instead of panel-failed short-circuit. The orchestrator no longer reads `.step3-plan-review-result.env` written at loop completion; if the loop writes inner tally-error but the driver is killed before outer write, a stale outer `complete` can win over inner/`stdout` tally-error and skip rollback and the correct Gate B path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Prefer stdout or inner env for status keys for this invocation; or write outer result env immediately after parsing inner loop output.


### FINDING_7: correctness — `run-step3-review.md` contract order mismatches implementation
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Contract lists pending-round persist before cursor advance; implementation does the opposite, confusing operators tracing round-count vs cursor failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Swap responsibility items 3 and 4 to match run-step3-review.sh.


### FINDING_9: risk-integration — orchestrator-fence harness omits driver exit-2 case
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `test-step3-orchestrator-fence.sh` does not cover driver exit 2 / configuration-error handoff pinned in `SKILL.md`; a regression in SKILL handling of `run-step3-review.sh` exit 2 could ship while driver-only argv tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Extend test-step3-orchestrator-fence.sh (or test-design-structure pins) with an exit-2 handoff case matching the SKILL fence.


