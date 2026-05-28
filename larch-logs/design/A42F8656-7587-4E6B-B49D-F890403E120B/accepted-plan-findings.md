### FINDING_1: Quiet-log publish skips sessions without breadcrumbs directory
- **Reviewer(s)**: Cursor-Edge, Codex-Edge, Cursor-dyn-path-derivation, Codex-dyn-path-derivation, Codex-Pragmatic
- **Severity**: important
- **Concern**: Quiet-log staging still depends on the legacy `breadcrumbs/` source directory existing. Sessions can produce root-level `larch-quiet-*-*.log` files without creating `breadcrumbs/`, so the new forensic logs can be silently omitted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Keep the ndjson no-source short-circuit, but compute `session_root=$(dirname "$source_dir")` first and run the quiet-log loop when `session_root` passes `larch_log_breadcrumbs_under_session_tmp`; only skip the ndjson loop when `source_dir` is absent. Add a harness case with quiet logs at tmpdir root and no `breadcrumbs/` directory.
  - From Codex-Edge, Cursor-dyn-path-derivation, Codex-dyn-path-derivation: Compute session_root first and let missing/empty breadcrumbs only skip the ndjson loop; return only after both ndjson and root quiet-log scans find nothing
  - From Codex-Pragmatic: Revise the plan so absent source_dir skips only the legacy ndjson loop. Still compute session_root from dirname source_dir, scan session_root/larch-quiet-*-*.log, and return no-op only when neither ndjson nor quiet logs were accepted.


### FINDING_2: Security and operator docs omit new quiet-log artifact boundary
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The plan adds committed `larch-quiet-*-*.log` artifacts but leaves security/operator documentation describing breadcrumb publication as ndjson-only and sidecars as session-local, obscuring the expanded durable log surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Update SECURITY.md alongside scripts/larch-log.md to describe accepted larch-quiet-*-*.log files, root-source resolution, redaction pipeline, symlink/hardlink rejection, and which .quiet monitor sidecars still remain session-local
  - From Cursor-Innovation, Codex-Innovation: Add a scoped SECURITY.md update and align docs/run-logs.md to document larch-quiet-*-*.log staging, redaction, guards, and that monitor .quiet sidecars remain excluded
  - From Cursor-Pragmatic: Add minimal SECURITY.md and docs/run-logs.md updates: session-root larch-quiet-*-*.log files are redacted and committed alongside legacy *.ndjson
  - From Codex-Requirements: Add a small SECURITY.md update to the breadcrumb redaction section: document accepted root-level larch-quiet-*-*.log files, the same containment/symlink/hardlink/redaction rules, and that legacy inside-breadcrumbs sidecars remain skipped.


### FINDING_3: /design publish callsites still assume post-push failures exit zero
- **Reviewer(s)**: Codex-Edge, Codex-Pragmatic, Cursor-Innovation, Codex-Innovation, Codex-Requirements, Cursor-dyn-caller-contract, Codex-dyn-caller-contract
- **Severity**: important
- **Concern**: The inline `/design` prompt callsites are not updated for `design-log-publish.sh` returning exit 1 with `PUBLISH_OK=false`, so Bash flow can abort before parsing stdout and running the documented warning, preservation, rename-skip, and recovery handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge, Codex-Pragmatic: Revise both publish instructions to capture stdout, stderr, and rc under set +e semantics, then parse PUBLISH_OK regardless of rc, matching design-pause-save.sh
  - From Cursor-Innovation, Codex-Innovation: Update these prompt callsites to capture stdout stderr and rc under set +e, then parse PUBLISH_OK regardless of rc and keep the existing PUBLISH_OK=false handling
  - From Codex-Requirements: Add a minimal UPDATED entry for skills/design/SKILL.md at both design-log-publish callsites: capture stdout/stderr and rc with set +e or equivalent, parse PUBLISH_OK even when rc is 1, and keep non-contract shell failures distinct.
  - From Cursor-dyn-caller-contract, Codex-dyn-caller-contract: Add a minimal plan step updating both /design callsites to capture stdout, stderr, and rc with set +e or || true, then parse PUBLISH_OK even when rc=1. Treat only non-zero with no PUBLISH_OK as unexpected. No design-pause-save.sh change is needed for this contract because scripts/design-pause-save.sh:156-169 already disables set -e around the helper, captures rc, and parses PUBLISH_OK.


### FINDING_4: Finalize harness cannot assert committed quiet logs through stubbed logger
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: `scripts/test-implement-finalize.sh` stubs `larch-log.sh` by recording argv only, so assertions about committed `breadcrumbs/` quiet-log artifacts would be vacuous or fail because the real commit path never runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Limit scripts/test-implement-finalize.sh to the planned one-line comments, or add a small real larch-log commit fixture like scripts/test-refresh-run-logs.sh; rely on scripts/test-larch-log.sh for publish behavior


### FINDING_5: Quiet logs may be duplicated as top-level design artifacts
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: latent
- **Concern**: Once the shared breadcrumbs helper publishes quiet logs, `design-log-publish.sh` may still stage the same top-level `DESIGN_TMPDIR` files as design artifacts, producing duplicates at both the run root and `breadcrumbs/`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Add larch-quiet-*-*.log to design_artifact_excluded once breadcrumbs owns quiet-log publication, and assert the top-level copy is absent.


### FINDING_6: Post-push tests mask the new nonzero exit-code contract
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The post-push failure harness cases use `|| true`, so new assertions that `design-log-publish.sh` exits 1 on push or merge failure would not actually validate the intended contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Capture exit code explicitly (e.g. `rc=0; out=$(...); rc=$?` without trailing `|| true`) for push-fail and merge-fail cases; assert `rc=1` alongside existing `PUBLISH_OK=false` / `RECOVERY_BRANCH` stdout checks

