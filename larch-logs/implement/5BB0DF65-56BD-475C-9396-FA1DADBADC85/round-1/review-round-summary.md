# Review Round 1

- Mode: `diff`
- 8 accepted, 5 rejected (5 exonerated)

## Accepted Findings

### FINDING_1: SECURITY.md missing subprocess JSON-envelope trust-boundary update
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: The launcher contract says security documentation must be synced when argv grammar or sidecar behavior changes. The new spawned-Claude JSON envelope path and `claude_sub` usage accounting are not reflected in `SECURITY.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_14: Claude JSON result failures can be treated as successful and billable across launchers
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, dyn-cli-envelope-output.txt
- **Severity**: important
- **Concern**: When the Claude CLI returns exit `0` with valid JSON but empty/malformed `.result`, extraction failure, or `is_error:true`, the subprocess and CI launchers can leave the raw JSON envelope in `$OUTPUT`, report success, and/or record `claude_sub` usage independently of successful prose/result promotion. Collectors and CI consumers then receive JSON instead of the expected output while accounting says the run succeeded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-cli-envelope-output.txt: Address the concern above.


### FINDING_15: final-report corrupt-zero guard ignores non-zero `claude_sub`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-cost-pipeline-output.txt, dyn-schema-compat-output.txt
- **Severity**: important
- **Concern**: `TOKEN_REPORT_CORRUPT_ZERO` only considers the legacy `claude`, `codex`, and `cursor` lanes. A subprocess-only run with non-zero `claude_sub` can be misclassified as corrupt, causing final summaries to emit `Cost: N/A` despite valid subprocess token/cost data.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-cost-pipeline-output.txt: Address the concern above.
  - From dyn-schema-compat-output.txt: Address the concern above.


### FINDING_16: CI `.token-record` fallback can produce misleading or inconsistent provenance
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-cli-envelope-output.txt
- **Severity**: important
- **Concern**: The CI launcher fallback `.token-record` path can word-count a JSON envelope when `.result` extraction fails, and its fallback raw label differs from the ledger raw label (`claude_ci_fix` vs `claude_ci`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-cli-envelope-output.txt: Address the concern above.


### FINDING_22: summary-format harness does not require `Claude (subprocess)`
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-schema-compat-output.txt
- **Severity**: latent
- **Concern**: The `--summary` format harness still checks only the legacy lane labels and does not require the new `Claude (subprocess):` segment, so the display contract can regress unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-schema-compat-output.txt: Address the concern above.


### FINDING_23: refresh-run-logs lacks a post-CI-fix `claude_sub` regression
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: No integration test verifies that post-flush CI-fixer `claude_sub` ledger rows are picked up when token reports are refreshed for committed run logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_25: baseline full-JSON shape test does not pin `BUCKETS_claude_sub`
- **Reviewer(s)**: dyn-schema-compat-output.txt
- **Severity**: latent
- **Concern**: Full JSON now emits `BUCKETS_claude_sub`, but the baseline shape test still pins only the three legacy bucket keys. Dropping the fourth bucket from persisted token reports would not fail that harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-schema-compat-output.txt: Address the concern above.


### FINDING_9: Claude subprocess summary lane omits cache-creation tokens
- **Reviewer(s)**: codex-specialist-security-output.txt, cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-cost-pipeline-output.txt, dyn-schema-compat-output.txt
- **Severity**: important
- **Concern**: `scripts/token-report.sh --summary` builds and displays the `claude_sub` lane from input/cache-read/output fields but omits cache-creation/cache-write tokens. Grand totals can remain correct while the operator-facing `Claude (subprocess)` lane is understated or rounded to `0k`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.
  - From dyn-cost-pipeline-output.txt: Address the concern above.
  - From dyn-schema-compat-output.txt: Address the concern above.


