# Review Round 1

- Mode: `diff`
- 3 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: research Step 0a missing executable session setup invocation
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-skill-contracts
- **Severity**: important
- **Concern**: Step 0a in `skills/research/SKILL.md` removed the required executable `session setup` Bash fence; only a shared-doc citation and `--prefix claude-research` delta remain while parse/abort prose still assumes script stdout. An orchestrator following Step 0a literally may never run session setup (or may omit the shared reviewer flag tail), so `SESSION_TMPDIR`, reviewer presence keys, and related bindings are never established; Step 0b and lane launch can fail on unset `RESEARCH_TMPDIR`, and the explicit degraded-tools gate on the following lines can see missing or default reviewer keys.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Restore a bash fence after the shared cite that invokes session setup with --prefix claude-research and the shared reviewer flag tail from session-setup-output.md; keep the explicit parse/bind enumeration.
  - From cursor-specialist-edge-cases: Restore a Step 0a Bash fence using the shared stem plus reviewer tail from session-setup-output.md, with only --prefix claude-research as the local inline delta, or add a mandatory read of the shared file before execution.
  - From cursor-specialist-testing: Restore a shortened bash fence with only --prefix claude-research as the local delta, cite skills/shared/session-setup-output.md for the shared stem and flag tail, and keep the explicit parse/bind line.
  - From dyn-dyn-skill-contracts: Restore a Bash fence after the shared cite, e.g. `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" session setup --prefix claude-research` plus a one-line note that the shared reviewer tail from `session-setup-output.md` is appended in the same invocation; keep the existing parse/bind list unchanged.


### FINDING_2: `/review` Step 0 parses `LARCH_TIMING_LEDGER` from session-setup stdout incorrectly
- **Reviewer(s)**: codex-specialist-correctness, codex-generalist
- **Severity**: important
- **Concern**: `skills/shared/session-setup-output.md` lists `LARCH_TIMING_LEDGER` under session setup “Output keys,” and `skills/review/SKILL.md` Step 0 tells `/review` to parse it from that setup stdout. The implementation only emits `LARCH_TOKEN_SESSION_ID` and `LARCH_CLAUDE_SOURCE_FILE` on stdout; `LARCH_TIMING_LEDGER` is forwarded into a written session env path only when `--write-session-env` is used (`python/larch/state/session_env.py`). A `/review` run with a valid timing ledger already in session-env can still leave the ledger empty if Step 0 follows the doc literally, breaking downstream review-and-fix timing propagation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Remove LARCH_TIMING_LEDGER from the stdout parse list and rehydrate it from SESSION_ENV_PATH/session-env.sh before exporting it.
  - From codex-generalist: Split stdout-emitted keys from session-env-only telemetry in `skills/shared/session-setup-output.md`, and update `/review` Step 0 to bind `LARCH_TIMING_LEDGER` from `$SESSION_ENV_PATH` or the persisted `session-env.sh`, not from session setup stdout.


### FINDING_3: review Step 0 missing executable session setup invocation
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-skill-contracts
- **Severity**: important
- **Concern**: Step 0 in `skills/review/SKILL.md` replaced the prior inline `session setup` command with citation-only prose and delta lists, with no runnable Bash fence. Standalone `/review` may not run session setup mechanically; without the canonical stem plus shared reviewer tail (`--check-reviewers`, probe skips), `SESSION_TMPDIR`, reviewer keys, and telemetry fields may never bind before later steps, breaking token/timing propagation and the explicit degraded-tools gate contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Restore a Bash fence with the canonical stem, shared reviewer tail, and review-only deltas (--prefix claude-review, optional --caller-env, probe skips).
  - From cursor-specialist-testing: Add back a shortened bash fence using the shared stem and reviewer tail from session-setup-output.md plus local deltas only; retain the seven-key parse enumeration.
  - From dyn-dyn-skill-contracts: Reinsert a shortened runnable invocation in Step 0 prose or a Bash fence: canonical stem from `session-setup-output.md`, `--prefix claude-review`, and the optional `[--caller-env …]` / probe-skip deltas; keep the expanded explicit parse enumeration.


