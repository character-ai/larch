## Decision 1: Audit scope / depth
- **Question**: How exhaustive should this design/PR be across the ~12 vendor-agent call sites the issue lists?
- **Resolution**: Centralize the fix. Route all vendor launches through the shared `lib-failed-agent-stderr-tail.sh` diagnostic-capture path plus the publish-inclusion change so every site benefits at once; fix the incident's 4 stacked layers; add regression coverage for the shared path and the incident surface; and record a full audit table enumerating every site. Residual per-site gaps the audit table surfaces are filed as OOS follow-ups rather than exhaustively hand-patched in this PR.
- **Source**: user

## Decision 2: What survives to git on a FAILED launch (publish policy, #3534 tension)
- **Question**: What diagnostics get committed on a failed vendor launch while respecting #3534 (no bulky raw transcripts for successful runs)?
- **Resolution**: Relax `design_artifact_excluded` (and add `larch-log-batches.sh` slugs for the implement side) to commit `*.diag` and a new `*.sidecar.history` artifact ONLY for failed launches, redacted via `redact-secrets.sh` at publish time. This preserves the full append-only multi-attempt failure record the root-cause analysis needed. Successful runs still exclude these (keeps #3534 intent intact).
- **Source**: user

## Decision 3: Audit-table deliverable location
- **Question**: Where should the audit table (call site × {saved, logged, flushed}) live?
- **Resolution**: A committed, versioned doc under `docs/` (e.g. `docs/vendor-agent-diagnostics-audit.md`), not just the PR description, so the inventory stays discoverable and current as new launch sites are added.
- **Source**: user

## Decision 4: Hard constraints (resolved from codebase + issue — must not break)
- **Question**: What existing behavior must be preserved?
- **Resolution**:
  - #3534 successful-run raw-transcript/diagnostic exclusion remains in force; only FAILED-launch diagnostics become eligible for the flush.
  - Every newly committed diagnostic is redacted via `redact-secrets.sh` at publish time.
  - Codex/Cursor launcher parity (`.claude/rules/external-tool-launcher-parity.md`): symmetric changes across the `launch-*.sh` family and shared collectors; `launch-claude-subprocess.sh` (claude-as-subprocess) included.
  - Sibling `.md` updated for every changed `.sh` (`.claude/rules/script-md-siblings.md`); regression coverage per `make lint` harness conventions.
  - Per-attempt sidecar truncation (`: > "$SIDECAR"`) must keep its current-attempt-only auth/quota classification semantics intact — any history archiving must NOT reintroduce stale-marker reads from prior attempts.
  - Both design-side (`design-log-publish.sh`) and implement-side (`larch-log-batches.sh`) publish paths are covered.
- **Source**: codebase + issue
