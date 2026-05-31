### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: No Phase 4 bash-parity harness for checks module
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Unlike redact/retry modules per AGENTS.md quality bar, Phase 4 has no bash-parity harness. Semantic stub tests can diverge from `run_captured_cmd_then_fix_loop` or `lint-fix-loop.sh` until Phase 7 cutover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add table-driven parity vectors against bash normalize_rcc_max_iter or extend scripts/test-lint-fix-loop.sh with optional Python comparisons.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: target_cmd_display embedded with minimal sanitization
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: CI-derived display strings with newlines/backticks in fixer instructions can override untrusted-log framing and steer the fixer.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Enforce single-line display strings length limits and neutral quoting; parity-harden beyond control-char grep


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_21: run_lint_fix leaves per-attempt mkdtemp dirs under lint-fix-loop
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Multi-iteration implement sessions can accumulate codex/cursor artifact directories under session tmpdir without cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add best-effort rmtree in finally after dispatch completes, or match bash cleanup policy explicitly.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Monolithic checks.py module hard to maintain for Phase 5+
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: ~1465-line module mixes capture, fix loop, dispatch, and git side effects. Extending in later phases without regressions is risky; split into capture vs dispatch modules with thin public re-exports after tests lock parity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Duplicate StubRunner in test_checks.py vs test_git.py
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Duplicate `StubRunner` implementations may drift if one stub gains behavior the other lacks. Extract a shared test stub helper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: run_lint_fix session root inference without validate_tmpdir
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `run_lint_fix` derives session root as `parent` of `run_parent` and expects a `lint-fix-loop` subdirectory. If `run_parent` is set to the session root, direct API callers get `checks-log-invalid` or wrong confinement. `run_parent` is not validated with `validate_tmpdir` before dispatch, so misconfiguration can allow fixer dispatch without session-prefix guarantees.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Validate run_parent ends with lint-fix-loop and parent passes validate_tmpdir, or accept explicit tmpdir parameter.
  - From cursor-specialist-security-output.txt: Call validate_tmpdir on the derived session directory before run_lint_fix dispatch


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

