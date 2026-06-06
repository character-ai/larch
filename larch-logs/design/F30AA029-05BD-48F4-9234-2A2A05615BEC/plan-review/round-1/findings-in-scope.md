### FINDING_1: Add agent-lint exclusions for the new Makefile-only append-execution harness
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Codex-Innovation, Codex-Requirements
- **Severity**: important
- **Concern**: The plan adds `scripts/test-append-execution-issue.sh` and its sibling `.md` as a Makefile-only harness, but does not update `agent-lint.toml` dead-script exclusions. Because agent-lint does not treat Makefile targets as reachability edges, `bash scripts/relevant-checks.sh` can fail on the new harness despite correct Makefile/shard wiring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add agent-lint.toml to the plan with exclude entries and a short Makefile-only rationale for scripts/test-append-execution-issue.sh and scripts/test-append-execution-issue.md, mirroring scripts/test-append-tool-failure.sh/.md
  - From Codex-Edge: Add agent-lint.toml exclude entries for scripts/test-append-execution-issue.sh and scripts/test-append-execution-issue.md beside the analogous test-append-tool-failure exclusions
  - From Codex-Innovation: Add scripts/test-append-execution-issue.sh and scripts/test-append-execution-issue.md to the exclude list near test-append-tool-failure, or add an agent-lint-visible structured registration if preferred
  - From Codex-Requirements: Add `scripts/test-append-execution-issue.sh` and `scripts/test-append-execution-issue.md` to `agent-lint.toml` near the analogous append-tool-failure harness exclusion, or explicitly justify why agent-lint will see this harness through a runtime reference

### FINDING_2: Step 5 round-cap CLI must be captured in guarded Bash before banner math
- **Reviewer(s)**: Cursor-Innovation, Cursor-dyn-harness-wiring, Cursor-Pragmatic, Cursor-dyn-scope-control, Cursor-dyn-contract-surface, Codex-dyn-harness-wiring
- **Severity**: important
- **Concern**: The Step 5 SKILL change replaces the degraded-round glob/loop prose with a CLI directive, but does not reliably show a fenced Bash invocation that rehydrates `CLAUDE_PLUGIN_ROOT`, runs the new CLI, and captures stdout into `prior_degraded_rounds` before `effective_round_cap` is computed. That leaves the orchestrator free to ad-lib invalid or environment-dependent shell, or to leave the variable empty so the banner ignores degraded history.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Replace the glob/loop clause with prior_degraded_rounds=$("${CLAUDE_PLUGIN_ROOT}/scripts/lib-implement-round-cap.sh" --count-prior-degraded "$IMPLEMENT_TMPDIR" 1) (or equivalent) before the round_cap/effective_round_cap lines; match Round 1 design discussion wording
  - From Cursor-dyn-harness-wiring: Replace the glob/loop clause with prior_degraded_rounds=$("${CLAUDE_PLUGIN_ROOT}/scripts/lib-implement-round-cap.sh" --count-prior-degraded "$IMPLEMENT_TMPDIR" 1) (or equivalent) before the round_cap/effective_round_cap lines; match Round 1 design discussion wording
  - From Cursor-Pragmatic: Add a small fenced bash block before the banner line: standard rehydration prelude, export IMPLEMENT_TMPDIR, then prior_degraded_rounds=$("${CLAUDE_PLUGIN_ROOT}/scripts/lib-implement-round-cap.sh" --count-prior-degraded "$IMPLEMENT_TMPDIR" 1); keep round_cap/effective_round_cap and the existing run-step5-review fence unchanged
  - From Cursor-dyn-scope-control: Fold `lib-implement-round-cap.sh --count-prior-degraded "$IMPLEMENT_TMPDIR" 1` into the `770-775` bash fence after `plugin-root.env` sourcing; keep prose limited to parsing stdout into `prior_degraded_rounds` before the banner line
  - From Cursor-dyn-contract-surface: Add a Step 5 Bash fence (with IMPLEMENT_TMPDIR export + plugin-root.env rehydration) that runs lib-implement-round-cap.sh --count-prior-degraded and captures stdout; state orchestrator must parse that output into prior_degraded_rounds before printing the banner
  - From Codex-dyn-harness-wiring: Make the banner-count command a guarded Bash snippet: source $IMPLEMENT_TMPDIR/plugin-root.env with the canonical guard, then assign and validate prior_degraded_rounds from the new CLI before printing, or run it inside the existing guarded Step 5 block before invoking run-step5-review

### FINDING_3: Step 0 initial caller may still require CLAUDE_PLUGIN_ROOT before wrapper self-derivation can run
- **Reviewer(s)**: Codex-dyn-contract-surface
- **Severity**: important
- **Concern**: The planned self-derivation lives inside `implement-bootstrap-invoke.sh`, but the documented initial Step 0 caller may still use `${CLAUDE_PLUGIN_ROOT}` to locate that wrapper. In a fresh initial entry where `IMPLEMENT_TMPDIR`, `plugin-root.env`, and exported `CLAUDE_PLUGIN_ROOT` are absent, the shell can fail while expanding the wrapper path before the new in-wrapper fallback executes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-contract-surface: Update the Step 0 initial caller to make the wrapper path independent of CLAUDE_PLUGIN_ROOT in the no-tmpdir case, or render/export a plugin-root fallback before any ${CLAUDE_PLUGIN_ROOT}/... command; add a caller-level test for the unset initial path
