# Review Round 2

- Mode: `diff`
- 13 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Migrated Python CLI shell callsites use invalid command syntax
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Migrated shell callsites treat `python/cli.py` subcommands as invalid Bash assignments or one executable path with spaces. Step 2 completion, run-log append blocks, redaction, rejected-findings writing, materialize-manifest-oos, decompose, stall recovery, scope-anchor rendering, and Step 8 fallback logging can fail or skip required logging and scrubbing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_10: Router flag recovery harness uses dangling deleted-helper symlinks
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `scripts/test-step0b-router-flag-recovery.sh` symlinks deleted helper scripts, causing dangling symlinks and CI harness failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_11: lint-fix-loop fixture copies deleted redaction helpers
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `scripts/test-lint-fix-loop.sh` fixture setup copies deleted `redact-secrets.sh` and `redact-tmpdir-paths.sh`, so the test shard can abort before running.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_12: Ledger report rendering ignores failed subprocesses
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_render_ledger_reports` ignores non-zero exits from `token-report.sh` and `timing-report.sh`. Refreshed runs can miss token or timing JSON batches while later completeness checks report missing artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_17: Run-log init loses plugin version metadata
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `run-log init` hardcodes `larch_version` as `unknown`. New run manifests lose plugin version metadata needed by audit and version-window consumers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_18: run-log exists omits LOG_PATH for absent batches
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `run-log exists` emits an empty `LOG_PATH` when a validated batch is absent. Callers probing for a missing batch lose the expected computed path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_19: Commit refusal guards return the wrong legacy exit code
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Post-merge and default-branch commit refusal guards return exit code 3 instead of the legacy stderr-only exit code 1. Callers depending on the preserved guard contract can take the wrong failure path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_2: Run-log flush and refresh skip pre-commit staging
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Python run-log flush and refresh paths no longer stage execution issues, vendor failure diagnostics, transcript, or final report artifacts before commit. Teardown and pre-push refresh commits can publish incomplete run logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_4: Refresh status envelopes misreport commit outcomes
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Refresh output omits `ERROR=` details on commit failure and can report `REFRESH_COMMITTED=true` for the no-change result. Operators and callers lose the correct commit outcome.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_5: Manifest updates downgrade schema v2 data
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Internal manifest updates rewrite schema-v2 manifests through the legacy serializer. Updated manifests can lose `schema_version`, `skill`, `started_at`, `operator_cwd`, `operator_repo_root`, and related v2 fields.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_7: plan-goals sanitizer is a no-op
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The plan-goals sanitizer is registered but does not enforce the retired Bash checks. Pointer-only or structurally incomplete plan-goals payloads can pass instead of failing closed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_8: write-round stages raw artifacts without the old allowlist
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `write-round` copies broad raw review artifacts instead of applying the retired allowlist, denylist, trimming, caps, dedupe, and round-meta consolidation. Private transcripts, sidecars, diagnostics, and uncapped outputs can be committed into durable run logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_9: Commit scrubbing can leave unscrubbed files in the worktree
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_commit_run` copies logs into the consumer worktree before scrubbing and lets residual-secret scrub failures raise uncaught `RuntimeError`. A failed scrub can crash with a traceback and leave unscrubbed `larch-logs` files in the worktree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


