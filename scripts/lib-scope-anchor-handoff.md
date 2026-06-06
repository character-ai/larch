# lib-scope-anchor-handoff.sh

Sourced-only helper library (no shebang) for `SCOPE_ANCHOR_FILE` relay
gating and path validation in the plan-review pipeline.

- **API**: `larch_scope_anchor_relay_allowed` (terminal-status gate:
  `ok` / `main-agent-vote-required` only), shape/containment validators
  (CR/LF rejection, tmpdir containment under `DESIGN_TMPDIR` /
  `IMPLEMENT_TMPDIR`).
- **Primary callers**: `skills/design/scripts/plan-review-loop.sh`,
  `skills/design/scripts/run-step3-review.sh`,
  `skills/shared/scripts/render-assessor-prompt.sh`,
  `skills/shared/scripts/render-voter-prompt.sh`,
  `skills/review/scripts/aggregate-findings.sh`.
- **Invariants**: path-only handoff — the relay never inlines anchor bytes;
  the key is omitted on `tally-error`, `panel-failed`, and other
  non-terminal statuses (see `SECURITY.md` "Plan-review scope-anchor
  pipeline" — path-only handoff surface). Idempotent load guard
  (`LARCH_LIB_SCOPE_ANCHOR_HANDOFF_LOADED`).
- **Harness**: `scripts/test-lib-scope-anchor-handoff.sh` (Makefile target
  `test-lib-scope-anchor-handoff`).
