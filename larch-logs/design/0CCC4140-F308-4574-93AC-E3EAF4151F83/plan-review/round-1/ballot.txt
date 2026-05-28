### FINDING_1: lib-quiet tests still call removed breadcrumb helpers
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Pragmatic, Codex-Innovation, Cursor-dyn-callsite-census, Codex-dyn-callsite-census, Cursor-dyn-substitution-fidelity, Codex-dyn-substitution-fidelity
- **Severity**: important
- **Concern**: The plan removes `emit_breadcrumb` but leaves earlier `scripts/test-lib-quiet.sh` cases, especially #4, #5, and #5b, that still generate helpers calling it. After `scripts/lib-quiet.sh` drops the function, `bash scripts/test-lib-quiet.sh` fails with `emit_breadcrumb: command not found`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add these cases to the migration (switch helpers to larch_err / larch_errf and revise assertions) or delete/replace them in the same commit as the API removal
  - From Codex-Arch: Delete or rewrite the #4/#5/#5b breadcrumb tests and update scripts/test-lib-quiet.md summary before renumbering the remaining cases
  - From Codex-Pragmatic: Delete or rewrite the #4/#5/#5b breadcrumb tests and update scripts/test-lib-quiet.md summary before renumbering the remaining cases
  - From Codex-Innovation: Delete or retarget those tests in the same pass; for SIMPLE scope, remove breadcrumb API-specific cases and update ci-wait assertions to the proposed stderr/quiet-log behavior
  - From Cursor-dyn-callsite-census: Update or delete the breadcrumb quiet/visible/alternate-fd tests at lines 71-91 in the same minimal pass, and sync scripts/test-lib-quiet.md if those contracts are removed.
  - From Codex-dyn-callsite-census: Update or delete the breadcrumb quiet/visible/alternate-fd tests at lines 71-91 in the same minimal pass, and sync scripts/test-lib-quiet.md if those contracts are removed.
  - From Cursor-dyn-substitution-fidelity: Delete or rewrite the breadcrumb quiet/surfacing tests at lines 71-91, and update `scripts/test-lib-quiet.md` to remove the remaining `emit_breadcrumb` public-contract references.
  - From Codex-dyn-substitution-fidelity: Delete or rewrite the breadcrumb quiet/surfacing tests at lines 71-91, and update `scripts/test-lib-quiet.md` to remove the remaining `emit_breadcrumb` public-contract references.

### FINDING_2: ci-wait stream tests still expect breadcrumb NDJSON
- **Reviewer(s)**: Cursor-Arch, Codex-Innovation
- **Severity**: important
- **Concern**: The plan migrates `ci-wait.sh` from `emit_breadcrumb_stderr` to `larch_errf`, but leaves `scripts/test-ci-wait.sh` stream cases that assert `LARCH_BREADCRUMB_STREAM` / NDJSON records. Those tests will fail once the script writes stderr instead of breadcrumb stream records.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Update test-ci-wait.sh (and test-ci-wait.md if needed) in the same PR—drop or rewrite stream cases to match quiet-log / stderr semantics, or defer ci-wait migration until Piece 3
  - From Codex-Innovation: Delete or retarget those tests in the same pass; for SIMPLE scope, remove breadcrumb API-specific cases and update ci-wait assertions to the proposed stderr/quiet-log behavior

### FINDING_3: breadcrumb publish tests still expect NDJSON artifacts
- **Reviewer(s)**: Cursor-Arch, Codex-Arch
- **Severity**: important
- **Concern**: The plan removes NDJSON breadcrumb publication but leaves harnesses that assert committed `*.ndjson` breadcrumb artifacts, including `scripts/test-larch-log.sh` and `scripts/test-design-log-publish.sh`. Quiet-log-only publishing will make those stated validation paths fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend Files to modify: adjust ndjson-centric commit assertions (e.g. lines 257–260) for quiet-log-only staging; keep redaction/hardlink cases that still apply
  - From Codex-Arch: Update the affected breadcrumb publish tests to assert quiet-log-only staging, and remove or retarget ndjson-only publish expectations

### FINDING_4: apply-bump tests still assert stdout breadcrumbs
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The plan cites only one `apply-bump` assertion change, but `scripts/test-apply-bump.sh` has many stdout breadcrumb checks. Since `apply-bump` runs with `LARCH_QUIET_DISABLE=1`, replacing `emit_breadcrumb` with `larch_err` moves output from stdout to stderr and breaks retry / breadcrumb shape cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: List test-apply-bump.sh explicitly and move assertions to stderr.log (or merge streams in run_case) for all ^apply-bump: retry patterns

### FINDING_5: stdout breadcrumb harnesses are not retargeted to stderr
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Codex-Edge
- **Severity**: important
- **Concern**: The plan migrates breadcrumb output to `larch_err` / `larch_errf`, which writes stderr under `LARCH_QUIET_DISABLE=1`, but several harnesses still grep stdout-only captures. This affects `skills/implement/scripts/test-implement-bootstrap.sh` and adjacent review / dispatch / ship-pr tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add skills/implement/scripts/test-implement-bootstrap.sh to Files to modify: capture stderr for breadcrumb assertions (tests using LARCH_QUIET_BREADCRUMB_FD=1 must follow the implement-bootstrap.md larch_err contract)
  - From Cursor-Edge: Update the listed tests and sibling docs to capture/assert stderr for migrated larch_err lines, or remove breadcrumb-specific stdout assertions where they no longer express the contract
  - From Codex-Edge: Update the listed tests and sibling docs to capture/assert stderr for migrated larch_err lines, or remove breadcrumb-specific stdout assertions where they no longer express the contract

### FINDING_6: breadcrumb-monitor still depends on removed category validator
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Pragmatic, Cursor-Edge, Codex-Edge, Cursor-Innovation, Cursor-Requirements, Codex-Requirements, Cursor-dyn-piece-boundary, Codex-dyn-piece-boundary
- **Severity**: important
- **Concern**: The plan removes `larch_quiet_bc_valid_category` from `scripts/lib-quiet.sh` while `scripts/breadcrumb-monitor.sh` still calls it and monitor migration is deferred to Piece 3. Any monitored `larch:bc` line can hit `command not found` under `set -e`, causing monitor failure and breaking `test-breadcrumb-monitor`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Keep larch_quiet_bc_valid_category until Piece 3, or move the category validator into breadcrumb-monitor.sh in this PR
  - From Codex-Innovation: Keep larch_quiet_bc_valid_category until Piece 3, or move the category validator into breadcrumb-monitor.sh in this PR
  - From Codex-Pragmatic: Keep larch_quiet_bc_valid_category until Piece 3, or move the category validator into breadcrumb-monitor.sh in this PR
  - From Cursor-Edge: Keep larch_quiet_bc_valid_category until breadcrumb-monitor.sh is migrated, or inline the category case statement in breadcrumb-monitor.sh in this PR
  - From Codex-Edge: Keep larch_quiet_bc_valid_category until breadcrumb-monitor.sh is migrated, or inline the category case statement in breadcrumb-monitor.sh in this PR
  - From Cursor-Innovation: Keep larch_quiet_bc_valid_category in lib-quiet.sh until Piece 3 removes breadcrumb-monitor.sh, or move the case statement into the monitor in the same PR
  - From Cursor-Requirements: Update the plan to either keep larch_quiet_bc_valid_category until breadcrumb-monitor.sh is retired or move the validator into breadcrumb-monitor.sh before removing the lib helper, and include bash scripts/test-breadcrumb-monitor.sh in validation
  - From Codex-Requirements: Update the plan to either keep larch_quiet_bc_valid_category until breadcrumb-monitor.sh is retired or move the validator into breadcrumb-monitor.sh before removing the lib helper, and include bash scripts/test-breadcrumb-monitor.sh in validation
  - From Cursor-dyn-piece-boundary: Keep larch_quiet_bc_valid_category until Piece 3 removes or rewrites breadcrumb-monitor.sh, or inline the same category case check in breadcrumb-monitor.sh as part of this plan.
  - From Codex-dyn-piece-boundary: Keep larch_quiet_bc_valid_category until Piece 3 removes or rewrites breadcrumb-monitor.sh, or inline the same category case check in breadcrumb-monitor.sh as part of this plan.

### FINDING_7: larch_err does not preserve durable breadcrumb logging or stream contracts
- **Reviewer(s)**: Codex-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: A blind `emit_breadcrumb` / `emit_breadcrumb_stderr` to `larch_err` / `larch_errf` migration changes core output contracts. `larch_err` writes stderr / FD4 and does not emit `larch:bc` stream records or write to the quiet log, so live `/implement` progress, breadcrumb-monitor feeds, and durable breadcrumb staging can regress before Piece 3.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Keep the ndjson path until writers target the quiet log, or use a minimal helper/path that writes intended breadcrumbs into the quiet log before making quiet logs the sole staging source
  - From Cursor-Pragmatic: Do not apply blind rename: keep a minimal stdout/stream helper for gated callsites until Piece 3, or explicitly drop both contracts and in the same PR retarget skills/implement/SKILL.md consumer expectations plus harnesses that grep stdout (test-ship-pr.sh:1107-1156, skills/implement/scripts/test-implement-bootstrap.sh:2489-2623)

### FINDING_8: security and run-log docs become stale after breadcrumb publication change
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Concern**: The plan changes breadcrumb publication semantics but leaves `SECURITY.md` and `docs/run-logs.md` describing regular `*.ndjson` stream publication and its security boundary. Operators would receive the wrong durable-log contract after NDJSON publication is removed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Update only the affected breadcrumb publication paragraphs to say quiet-log-only staging and remove obsolete ndjson fallback/security claims

### FINDING_9: ci-wait migration incorrectly adds newlines to inline progress
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements, Cursor-dyn-callsite-census, Codex-dyn-callsite-census, Cursor-dyn-substitution-fidelity, Codex-dyn-substitution-fidelity
- **Severity**: important
- **Concern**: The plan adds newline escapes to the two `ci-wait.sh` `emit_breadcrumb_stderr` callsites that currently omit them. Because `emit_breadcrumb_stderr` falls through to `larch_errf` printf semantics with no implicit newline, adding `\n` changes CI wait output from inline banner / dot progress to one line per dot and creates extra spacing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Convert those two callsites to larch_errf without adding newlines: larch_errf "⏳ CI: waiting" and larch_errf "."
  - From Codex-Requirements: Convert those two callsites to larch_errf without adding newlines: larch_errf "⏳ CI: waiting" and larch_errf "."
  - From Cursor-dyn-callsite-census: Convert line 184 to larch_errf "⏳ CI: waiting" and line 270 to larch_errf "." with no added newline; keep the existing newline-bearing formats unchanged.
  - From Codex-dyn-callsite-census: Convert line 184 to larch_errf "⏳ CI: waiting" and line 270 to larch_errf "." with no added newline; keep the existing newline-bearing formats unchanged.
  - From Cursor-dyn-substitution-fidelity: Convert those two calls to `larch_errf "⏳ CI: waiting"` and `larch_errf "."` without adding `\n`; keep the existing leading-newline formats unchanged.
  - From Codex-dyn-substitution-fidelity: Convert those two calls to `larch_errf "⏳ CI: waiting"` and `larch_errf "."` without adding `\n`; keep the existing leading-newline formats unchanged.

### FINDING_10: redirected breadcrumb callsites may change stderr destination
- **Reviewer(s)**: Cursor-dyn-substitution-fidelity, Codex-dyn-substitution-fidelity
- **Severity**: latent
- **Concern**: Some callsites currently use `emit_breadcrumb ... >&2`, which writes to current FD2 in initialized quiet sessions. Replacing those with `larch_err` writes to FD4 / original stderr instead, making messages operator-visible rather than quiet-log-only. That may be intended, but it is not a no-op substitution.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-substitution-fidelity: If visible stderr is intended, say so in the plan and adjust tests/docs around the visibility change. If strict destination preservation is required, replace these with `printf '%s\n' ... >&2` instead of `larch_err`.
  - From Codex-dyn-substitution-fidelity: If visible stderr is intended, say so in the plan and adjust tests/docs around the visibility change. If strict destination preservation is required, replace these with `printf '%s\n' ... >&2` instead of `larch_err`.
