### FINDING_1: SECURITY.md missing subprocess JSON-envelope trust-boundary update
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: The launcher contract says security documentation must be synced when argv grammar or sidecar behavior changes. The new spawned-Claude JSON envelope path and `claude_sub` usage accounting are not reflected in `SECURITY.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] token-ledger still permits reserved `claude` vendor writes
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `record-vendor` still accepts arbitrary vendor names, including `claude`, which could collide with transcript-derived `claude` totals. The reviewer marked this as pre-existing; the new code uses `claude_sub`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] CI fixer prompt still inlines plan file without hardening
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `launch-claude-ci.sh` still inlines `$(cat "$PLAN_FILE")` into the CI-fixer prompt without symlink canonicalization or broader content redaction. The reviewer marked this prompt-injection surface as pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] report-tokens/topology docs still describe the old lane model
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-cost-pipeline-output.txt, dyn-schema-compat-output.txt
- **Severity**: nit
- **Concern**: Plan-listed documentation surfaces such as `skills/report-tokens/SKILL.md` and `skills/shared/topology.tsv` were not updated, leaving operator-facing docs with the old three-lane story.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-cost-pipeline-output.txt: Address the concern above.
  - From dyn-schema-compat-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] JSON parsing and numeric validation appear hardened
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: The reviewer observed that JSON parsing uses `jq --arg` and digit-only validation before ledger writes, avoiding shell interpolation of untrusted JSON fields.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] subprocess token capture is gated on exit 0 and stale sidecars are cleared
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: The reviewer observed that `launch-claude-subprocess.sh` gates token capture on subprocess exit `0` and clears stale JSON sidecars before copy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] `TOKEN_RAW` provenance is constrained by timing-kind case mapping
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: The reviewer observed that `TOKEN_RAW` provenance is derived from a fixed `case` on `--timing-task-kind`, not caller-supplied free text.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] `claude_sub` naming avoids transcript-`claude` collision in the reviewed diff
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-cli-envelope-output.txt, dyn-schema-compat-output.txt
- **Severity**: nit
- **Concern**: Multiple reviewers observed that the new subprocess lane uses `claude_sub`, preserving separation from transcript-derived `claude` accounting and avoiding the known merge collision in the reviewed path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From dyn-cli-envelope-output.txt: Address the concern above.
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

### FINDING_10: plan-voter subprocess spend is misattributed as review provenance
- **Reviewer(s)**: codex-specialist-security-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `claude-plan-voter` / voter retry timing kinds fall through to review-style raw provenance, so plan-voter subprocess spend is counted in `claude_sub` but labeled as review spend.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: subprocess launcher deletes or fails to preserve the raw Claude JSON envelope
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: After successful spawned Claude reviewer/scout runs, the ledger has `claude_sub` counts but the original `${OUTPUT}.json` envelope is removed, preventing audit of usage against the source envelope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.

### FINDING_12: CI launcher deletes or fails to preserve the raw Claude JSON envelope
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: CI-fixer runs can record `claude_sub` usage while deleting the raw `.usage` source envelope, preventing operators from cross-checking ledger totals.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.

### FINDING_13: terse token report uses raw `claude_sub` instead of display label
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: The terse report path still emits raw `claude_sub` labeling rather than the locked display label `Claude (subprocess)`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.

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

### FINDING_17: [OUT_OF_SCOPE] `launch-claude-ci.sh` exits 0 regardless of `LAUNCHER_EXIT`
- **Reviewer(s)**: dyn-cli-envelope-output.txt
- **Severity**: latent
- **Concern**: The CI launcher always exits `0`, requiring callers to parse `LAUNCHER_EXIT=` from stdout instead of relying on process exit status. The reviewer marked this as pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cli-envelope-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] cache 5m/1h collapse is an accepted v1 trade-off
- **Reviewer(s)**: dyn-cli-envelope-output.txt
- **Severity**: nit
- **Concern**: The reviewer observed that collapsing cache 5m/1h into a single `cache_create` bucket is documented as an accepted v1 trade-off, not a new regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cli-envelope-output.txt: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] append-token-record rewrites CI Claude token-records to unknown
- **Reviewer(s)**: dyn-cost-pipeline-output.txt
- **Severity**: latent
- **Concern**: The new CI launcher writes `TOOL=claude` into `.token-record`, but `append-token-record.sh` only accepts `codex|cursor` and rewrites other tools to `unknown`, weakening the NDJSON audit fallback path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cost-pipeline-output.txt: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] fourth-lane final-summary/Python/callsite integration tests are incomplete
- **Reviewer(s)**: cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-schema-compat-output.txt
- **Severity**: important
- **Concern**: Several integration test surfaces do not pin non-zero `claude_sub` behavior, including final-summary fixtures, render-run-summary callsite argv wiring, Python token-cost/KV parsing, scan parsing, and four-lane final cost-line shape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.
  - From dyn-schema-compat-output.txt: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] per-bucket `claude_sub` cost harness coverage is missing
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-cost-pipeline-output.txt
- **Severity**: important
- **Concern**: The dedicated per-bucket harness was not updated for `claude_sub`, leaving subprocess per-bucket rate arithmetic and environment-precedence behavior unpinned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-cost-pipeline-output.txt: Address the concern above.

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

### FINDING_24: ledger-vendor collision regression is reported missing
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: One reviewer reported that there is no regression fixture proving a ledger vendor named `claude` cannot overwrite transcript-derived `claude` totals in report JSON merge semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_25: baseline full-JSON shape test does not pin `BUCKETS_claude_sub`
- **Reviewer(s)**: dyn-schema-compat-output.txt
- **Severity**: latent
- **Concern**: Full JSON now emits `BUCKETS_claude_sub`, but the baseline shape test still pins only the three legacy bucket keys. Dropping the fourth bucket from persisted token reports would not fail that harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-schema-compat-output.txt: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] historical-log backward compatibility appears handled
- **Reviewer(s)**: dyn-schema-compat-output.txt
- **Severity**: nit
- **Concern**: The reviewer observed that historical logs without `BUCKETS_claude_sub` / `.claude_sub` are handled with `// 0` defaults and defaulted Python fields, so old runs should render zero subprocess spend instead of failing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-schema-compat-output.txt: Address the concern above.
