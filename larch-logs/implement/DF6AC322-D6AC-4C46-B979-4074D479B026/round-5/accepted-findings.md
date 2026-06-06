### FINDING_1: Dynamic Codex phased pattern disagrees with docs/acceptance
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-artifact-retention-output.txt
- **Severity**: important
- **Concern**: Docs/plan text describe `phase*.txt`, but the explicit matcher uses `phase[0-9]*.txt`. Non-numeric phased outputs remain included only through the broad `*-output-*.txt` fallback, so future narrowing could silently drop artifacts the contract claims are explicitly retained.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-artifact-retention-output.txt: Address the concern above.


### FINDING_11: Retry exclusion is incompletely asserted by tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Tests do not fully assert retry deny behavior: they do not require the retry deny to precede the broad allow, and write-round coverage omits retry `.meta`, `.json`, and `.cap-hit` sidecars.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_13: Python OOS gate still scans main instead of repo default branch
- **Reviewer(s)**: dyn-ship-driver-output.txt
- **Severity**: important
- **Concern**: `_oos_gate()` hardcodes `origin/main` / `upstream/main` even though PR creation and CI monitoring use `gh.default_branch()`, so non-`main` repos may scan the wrong commit range for OOS disposition breadcrumbs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ship-driver-output.txt: Address the concern above.


### FINDING_14: Malformed ship state can reset merge-loop counters
- **Reviewer(s)**: dyn-ship-driver-output.txt
- **Severity**: important
- **Concern**: `_state_file_kv()` returns `{}` on `ShipError`, so unreadable or unparsable `ship-pr-state.sh` can reset persisted loop counters and weaken iteration-cap safety across resumes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ship-driver-output.txt: Address the concern above.


### FINDING_18: Python secret-scrub warning is hidden by quiet routing
- **Reviewer(s)**: dyn-ci-compat-output.txt
- **Severity**: important
- **Concern**: `_warn_secret_scrub()` no longer forces operator-visible stderr output under quiet mode, diverging from Bash and hiding a credential-rotation warning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-compat-output.txt: Address the concern above.


### FINDING_19: Python CI-monitor warnings are hidden by quiet routing
- **Reviewer(s)**: dyn-ci-compat-output.txt
- **Severity**: important
- **Concern**: `_warn_stderr()` no longer forces stderr under quiet mode, so CI-monitor suspend/degradation warnings can be swallowed from the operator terminal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-compat-output.txt: Address the concern above.


### FINDING_3: Quoted finalize-state values can trigger false stall recovery
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: Some Step 18 / stall-recovery reads still consume shell-quoted `finalize-state.sh` values literally, so values like `'false'` may be treated as truthy and spuriously enter stall recovery after restore/Python writes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From dyn-bash-parity-output.txt: Address the concern above.


### FINDING_9: Retry-output deny changes behavior relative to main
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-artifact-retention-output.txt
- **Severity**: important
- **Concern**: The new `dyn-*-codex-output-retry*.txt` deny runs before the broad output allow, excluding retry transcripts that main would include. That contradicts behavior-preserving acceptance unless retry exclusion is documented as intentional.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-artifact-retention-output.txt: Address the concern above.


