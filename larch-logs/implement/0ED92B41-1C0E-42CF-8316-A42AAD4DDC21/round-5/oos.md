### OOS_1: [OUT_OF_SCOPE] test_checks.py single large module
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Test file rivals implementation size in a single module—harder to navigate over time, introduced by this feature not a pre-existing regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_10: [OUT_OF_SCOPE] Python omits _lint_fix_set_stderr_tail_stem on agent failure
- **Reviewer(s)**: dyn-dispatch-argv-parity-output.txt
- **Severity**: nit
- **Concern**: Bash calls `_lint_fix_set_stderr_tail_stem` on codex/cursor failure; Python only calls `_write_failed_agent_stderr_tail`—may affect downstream stderr-tail stem wiring, not argv shape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dispatch-argv-parity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_11: [OUT_OF_SCOPE] codex artifact pre-delete timing vs bash lock order
- **Reviewer(s)**: dyn-dispatch-argv-parity-output.txt
- **Severity**: latent
- **Concern**: Pre-delete of codex artifacts runs before `_run_with_serial_lock`; bash deletes after lock acquire—unlikely unless another process races on the same `run_dir`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dispatch-argv-parity-output.txt: Address the concern above.

---

**Subsumed (not emitted as findings):** Input **FINDING_40** (FD close ordering vs `runner.run` blocking)—reviewer concluded no change required; optional comment only, not a behavioral risk. Input **FINDING_42** in-scope test gap is covered by **FINDING_9**.

Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_2: [OUT_OF_SCOPE] lint-literal-counts larch-logs exclusion
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `larch-logs` markdown exclusion is ancillary branch hygiene, not Phase 4 checks scope; already flagged in `python/README.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### OOS_3: [OUT_OF_SCOPE] test-ship-pr.sh does not exercise Python checks
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Bash RCC loop harness does not exercise Python checks module—pre-existing; Python/bash divergence possible until Phase 7 cutover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_4: [OUT_OF_SCOPE] README classify_launch_failure doc tension
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: README documents no `classify_launch_failure` on local path—pre-existing doc/plan wording tension only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_5: [OUT_OF_SCOPE] bash compose_prompt unredacted log metadata
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Bash `compose_prompt` exposes unredacted log path metadata and raw log tail in fixer prompt—pre-existing live path; mitigated when ship-pr passes `.redacted.log`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_6: [OUT_OF_SCOPE] target_cmd_display backtick injection in fixer prompt
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `target_cmd_display` backtick injection in fixer prompt—malicious CI job display string could distort fixer instructions; same pattern in Python.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_7: [OUT_OF_SCOPE] proc.run FD mode CommandResult capture contract
- **Reviewer(s)**: dyn-subprocess-fd-contract-output.txt
- **Severity**: nit
- **Concern**: When callers pass a raw FD, `CommandResult.stdout` / `stderr` are always `''`; safe for current `checks.py` readers but breaks nominal `str` capture contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-subprocess-fd-contract-output.txt: Document FD mode in the `Runner` protocol or return a sentinel / optional bytes field.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_8: [OUT_OF_SCOPE] FD redirect test gap noted only in dyn review
- **Reviewer(s)**: dyn-subprocess-fd-contract-output.txt
- **Severity**: latent
- **Concern**: Pre-existing framing: no `test_proc.py` coverage of FD redirect branch; parity test in `test_checks_bash_parity.py` is the right catch once `proc.run` is fixed—subsumed for in-scope action by FINDING_9.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-subprocess-fd-contract-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_9: [OUT_OF_SCOPE] cursor wrapped prompt rstrip newline divergence
- **Reviewer(s)**: dyn-dispatch-argv-parity-output.txt
- **Severity**: nit
- **Concern**: After the `X` sentinel, `wrapped.rstrip("\n")` can strip trailing newlines that bash keeps via `${_wrapped_prompt%X}` only—low risk per script contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dispatch-argv-parity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

