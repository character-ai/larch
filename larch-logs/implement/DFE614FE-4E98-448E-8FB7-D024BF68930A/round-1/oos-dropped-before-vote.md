### OOS_1: [OUT_OF_SCOPE] New `_warn` paths embed raw stderr without redaction
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: New `_warn` paths in `python/larch/git/pr_body.py` (e.g. `_plugin_version_from_completed` at 68–71) embed raw `completed.stderr` without `redact.redact()`, while `_diagram_failure_capture` in the same module redacts subprocess output before surfacing it. A failed `gh`/`plugin` call could put token fragments on stderr and into run logs. Marked OOS because upsert failures already returned stderr-derived text via `ERROR=` KV and the plan explicitly adds stderr diagnostics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Run stderr through `redact.redact()` (or a bounded redacted-tail helper) before `_warn`.

### OOS_2: [OUT_OF_SCOPE] Missing `LARCH_PLUGIN_VERSION=` on exit 0 yields silent `unknown`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-dyn-cli-path-output.txt
- **Severity**: latent
- **Concern**: When `plugin read-version` exits 0 but stdout lacks a `LARCH_PLUGIN_VERSION=` line, version falls back to `"unknown"` with no stderr warning. Pre-existing behavior; not introduced by this diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Emit a bounded stderr warning when `returncode == 0` and the KV line is missing.

### OOS_3: [OUT_OF_SCOPE] `_code_flow_launch_cmd` warns on missing CLI but still launches subprocess
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `_code_flow_launch_cmd()` warns when `_PY_CLI` is missing but still launches the subprocess (same ENOENT failure mode, now with an earlier stderr hint). Plan calls for warn-only degradation, not fail-fast; after the fix `_PY_CLI` exists in normal plugin layout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Optional early return with a synthetic failure tuple if you want to skip the redundant subprocess attempt on missing CLI.

### OOS_4: [OUT_OF_SCOPE] Metadata test does not assert plugin version is written
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `test_post_tracking_issue_writes_metadata` mocks successful `read-version` but does not assert version is written to `summary-metadata.md`. `_plugin_version_from_completed` could regress to always returning `unknown` while argv assertions still pass; metadata would show `Larch version: unknown` despite a successful CLI mock.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: After post_tracking_issue, assert summary-metadata.md contains Larch version: `99.0.0`; in the nonzero-warning sibling, assert `unknown`

### OOS_5: [OUT_OF_SCOPE] In-process Step 7a may not capture new `_warn` stderr
- **Reviewer(s)**: dyn-dyn-cli-path-output.txt
- **Severity**: latent
- **Concern**: Step 7a calls `pr_body.generate_code_flow_diagram()` in-process (`python/larch/implement/step_7a.py:242-246`), so new `_warn` stderr from `_code_flow_launch_cmd()` is not automatically copied into `execution-issues.md` (only the returned `reason` string is, via `_append_diagram_warning`). Failures remain visible through `generation-failed rc=...`; the extra stderr warning may be lost unless the parent captures stderr.
- **Suggested revisions (informational for voters; coder decides)**:
  - (dyn-dyn-cli-path-output.txt provided concern only; no distinct fix bullet beyond the concern text)

