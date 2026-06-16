# Review Round 2

- Mode: `diff`
- 4 accepted, 12 rejected (2 neutral)

## Accepted Findings

### FINDING_14: launcher guard checks presence only, not execute permission
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: New `command -v` fast-fail guard in `scripts/lib-external-launcher-common.sh` checks presence via `command -v` only, not execute permission, so non-executable PATH entries still enter probe retries. A chmod-broken codex/cursor on PATH triggers retry sleeps instead of immediate unhealthy fast-fail required by the plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Require -x on the resolved binary before the retry loop; add a harness case with a non-executable stub in case_dir/bin.


### FINDING_7: `oos_filer.py` ignores explicit false binary-state overrides
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: `_codex_available()` ignores explicit false binary-state overrides. If `CODEX_BINARY_FOUND=false` or `LARCH_OOS_CODEX_BINARY_FOUND=false` is supplied but `codex` is still on `PATH`, OOS filing will launch Codex anyway. This violates the new binary-found routing contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Return `False` for explicit false-like values before falling back to `shutil.which("codex")`, and add a test for `CODEX_BINARY_FOUND=false` with `codex` present on `PATH`.


### FINDING_8: design drafter drops Codex default when binary is present
- **Reviewer(s)**: dyn-routing-fidelity-output.txt
- **Severity**: important
- **Concern**: `skills/design/scripts/design-step2b-drafter.sh` removes the old `CODEX_PRESENT=true` Codex default but does not replace it with the plan's binary-based rule. When `LARCH_DESIGN_DRAFTER` is unset, the script always picks Claude, even if `CODEX_BINARY_FOUND=true` (or `command -v codex` would succeed). That drops Codex drafting whenever the operator does not set `LARCH_DESIGN_DRAFTER=codex`, which conflicts with the plan requirement to prefer Codex when the binary is present.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-routing-fidelity-output.txt: When `LARCH_DESIGN_DRAFTER` is unset, select Codex if `CODEX_BINARY_FOUND=true` or a fresh `command -v codex` check passes; otherwise use Claude. Update `skills/design/scripts/test-design-step2b-drafter.sh` so the default-route case expects Codex when the binary is present.


### FINDING_9: legacy `step-0-degraded-gate.sh` rehydrates unpersisted presence keys
- **Reviewer(s)**: dyn-routing-fidelity-output.txt, dyn-env-contract-output.txt
- **Severity**: important
- **Concern**: `skills/implement/scripts/step-0-degraded-gate.sh` still loads `CODEX_PRESENT` and `CURSOR_PRESENT` from durable `session-env.sh`, but `python/session_env.py` no longer writes those keys. On a normal post-refactor session, both presence args are empty, `degraded_tools_gate_main` treats that as fail-safe down, and the gate can report both vendors unavailable (including `PRESENCE_INPUT_EMPTY=true` and false both-down hard-fail) even when `CODEX_BINARY_FOUND` / `CURSOR_BINARY_FOUND` are `true`. This breaks offline harnesses and any caller still using this script instead of bootstrap's fresh `check-reviewers` refresh. `scripts/test-implement-structure.sh` still pins this stale rehydration contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-routing-fidelity-output.txt: Stop reading probe-health keys from session env in this script. Either rerun `python/cli.py agent check-reviewers` (as `python/bootstrap.py:1325-1340` does) or accept explicit `--codex-present` / `--cursor-present` argv from the caller, while still passing binary-found keys for `_tool_state`.
  - From dyn-env-contract-output.txt: Update the legacy script to run a fresh `agent check-reviewers` probe (or accept explicit presence argv) before calling the gate, and align the structural test pin with the non-persisted presence contract.


