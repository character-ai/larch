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

### FINDING_2: Shell state quote/unquote helpers are duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Quote/unquote logic is triplicated across Bash files and also mirrored in Python, so future quoting rule changes require coordinated edits across multiple readers/writers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Quoted finalize-state values can trigger false stall recovery
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: Some Step 18 / stall-recovery reads still consume shell-quoted `finalize-state.sh` values literally, so values like `'false'` may be treated as truthy and spuriously enter stall recovery after restore/Python writes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From dyn-bash-parity-output.txt: Address the concern above.

### FINDING_4: Deny-clause order drifted from the plan
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The deny-clause order was swapped relative to the plan’s preserve-ordering note, making future deny precedence harder to audit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Ordering test is brittle
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The `awk` line-number ordering pin can fail on comment-only edits even when behavior is unchanged.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: Dynamic Codex coverage is duplicated across harnesses
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Unit and integration tests duplicate dynamic Codex coverage, so every contract tweak must update two harnesses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] Artifact matcher case statement is growing monolithic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: The pre-existing `round_artifact_included()` case statement grows with each artifact family, making allow/deny precedence harder to audit over time.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] Unrelated Python ship/finalize work broadens review scope
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-artifact-retention-output.txt
- **Severity**: latent
- **Concern**: The branch bundles substantial Python ship/finalize/run-log changes with the smaller dynamic Codex retention edit, making focused review harder.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From dyn-artifact-retention-output.txt: Address the concern above.

### FINDING_9: Retry-output deny changes behavior relative to main
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-artifact-retention-output.txt
- **Severity**: important
- **Concern**: The new `dyn-*-codex-output-retry*.txt` deny runs before the broad output allow, excluding retry transcripts that main would include. That contradicts behavior-preserving acceptance unless retry exclusion is documented as intentional.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-artifact-retention-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] Broad output catch-all remains a backstop
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: The broad `*-output-*.txt` allow still serves as a fallback for unlisted artifact shapes; this is pre-existing and unchanged.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_11: Retry exclusion is incompletely asserted by tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Tests do not fully assert retry deny behavior: they do not require the retry deny to precede the broad allow, and write-round coverage omits retry `.meta`, `.json`, and `.cap-hit` sidecars.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] Raw dynamic Codex transcripts inherit partial redaction coverage
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Committed dynamic Codex raw transcript bodies are an intentional forensic surface and may contain repo snippets, internal URLs, PII, or opaque tokens beyond what `redact-secrets.sh` covers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

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

### FINDING_15: [OUT_OF_SCOPE] Wider Python modules still hardcode origin/main
- **Reviewer(s)**: dyn-ship-driver-output.txt
- **Severity**: latent
- **Concern**: Other Python cutover modules still hardcode `origin/main`, which is a broader Phase 7 parity gap predating this branch’s partial default-branch adoption.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ship-driver-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] Python lacks a port of round_artifact_included
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: latent
- **Concern**: Run-log round filtering remains Bash-only in `larch-log.sh`; there is no Python parity implementation if Python later owns `write-round`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] Design and implement run-log retention policies remain split
- **Reviewer(s)**: dyn-artifact-retention-output.txt
- **Severity**: nit
- **Concern**: Design-run artifact inclusion remains a separate unchanged surface from implement-run retention, preserving a pre-existing policy split.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-retention-output.txt: Address the concern above.

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

### FINDING_20: [OUT_OF_SCOPE] OOS disposition checkpoint reads quoted finalize-state fallbacks raw
- **Reviewer(s)**: dyn-ci-compat-output.txt
- **Severity**: latent
- **Concern**: `oos-disposition-checkpoint.sh` still reads `finalize-state.sh` fallback values with raw `grep`/`cut`, so quoted fallback values could mis-route fork/unavailability gating or NDJSON discovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-compat-output.txt: Address the concern above.
