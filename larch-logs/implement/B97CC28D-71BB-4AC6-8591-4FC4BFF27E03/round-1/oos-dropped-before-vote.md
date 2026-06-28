### OOS_1: [OUT_OF_SCOPE] Stale `.stderr` sidecar mislabels non-auth launcher failures as health/auth
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: Stale `.stderr` sidecar is not cleared at launcher start but is now read for auth classification. Reusing the same `--output-file` after an auth failure, then failing with empty stderr, can mislabel a non-auth failure as `health/auth` in Step 7a warnings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add .stderr to the pre-run stale sidecar unlink list or overwrite/truncate it when result.stderr is empty.

### OOS_2: [OUT_OF_SCOPE] Missing direct regression test for non-auth `other/timeout` launcher classification
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-launcher-kv
- **Severity**: nit
- **Concern**: No unit/integration test asserts `generation-failed other/timeout` (or equivalent `LAUNCHER_FAILURE_CLASS=other` / `LAUNCHER_FAILURE_REASON=timeout`) for a true non-auth timeout hang. Ordering in `classify_launch_failure` and shared `health/auth` parser tests may indirectly cover the split, but a dedicated `other/timeout` pr_body or fake-launcher test would lock in the `124` vs `health/auth` boundary called out in the plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add a fake-launcher test with LAUNCHER_FAILURE_CLASS=other and LAUNCHER_FAILURE_REASON=timeout in stdout.

### OOS_3: [OUT_OF_SCOPE] `_launcher_stdout_kv` duplicates KV parsing instead of shared `larch.io` helpers
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: `_launcher_stdout_kv` in `python/larch/git/pr_body.py` duplicates KV parsing instead of using `larch.io` helpers. Future wire-grammar changes could drift between parsers if more launcher consumers add ad-hoc parsers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Reuse larch.io KV parsing at the stdout envelope edge if a suitable helper exists.

### OOS_4: [OUT_OF_SCOPE] Legacy Bash code-flow generator diverges from Python Step 7a path
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The legacy Bash generator (`skills/implement/scripts/generate-code-flow-diagram.sh`) still passes `--timeout 600` and does not emit or parse `LAUNCHER_FAILURE_*` fields. Active Step 7a uses `python/larch/implement/step_7a.py` → `pr_body.generate_code_flow_diagram`, so `/implement` gets the fix; manual or harness invocations of the Bash script would not.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: **Suggested fix:** Either retire the Bash entrypoint or align its timeout and failure surfacing with the Python path when that dual-entrypoint debt is tackled.

### OOS_5: [OUT_OF_SCOPE] New launcher-failure tests not pinned in shard map
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: `test_launch_claude_subprocess_fast_fails_on_degraded_auth` and `test_generate_code_flow_diagram_labels_launcher_failure_class` are not pinned in `python/shard-assignments.json`. Unassigned nodeids still run via round-robin in CI, so this is shard-balancing hygiene, not a coverage gap for this change.
- **Suggested revisions (informational for voters; coder decides)**:

