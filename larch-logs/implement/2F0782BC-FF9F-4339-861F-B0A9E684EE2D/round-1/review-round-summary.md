# Review Round 1

- Mode: `diff`
- 10 accepted, 4 rejected (4 neutral)

## Accepted Findings

### FINDING_1: _refresh_gate_probe silently ignores check-reviewers failures
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-env-contract-output.txt
- **Severity**: important
- **Concern**: When `agent check-reviewers` refresh fails (`returncode != 0`), `_refresh_gate_probe()` returns without updating presence or surfacing an error. The absorbed continue tail then calls `degraded-tools-gate` with empty `--codex-present` / `--cursor-present`, which fail-safe to down and can hard-fail with `DEGRADED_HARD_FAIL` on transient probe or infra errors even when vendors are healthy. This is worse now that durable `session-env.sh` no longer carries presence keys and resume depends on this refresh path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: On probe failure, retry once, surface a distinct setup failure, or do not run the both-down gate until a successful refresh completes.
  - From cursor-specialist-edge-cases-output.txt: Surface probe failure loudly; retry or abort resume instead of passing empty presence into degraded-tools-gate.
  - From dyn-env-contract-output.txt: Treat refresh failure as a contract failure (log + `step_failed` such as `absorbed-gate-probe-refresh-failed`) or retry once; do not fall through to the gate with empty presence.


### FINDING_12: oos_filer honors stale LARCH_OOS_CODEX_AVAILABLE=false
- **Reviewer(s)**: dyn-routing-fidelity-output.txt
- **Severity**: important
- **Concern**: `_codex_available()` in `oos_filer.py` still honors `LARCH_OOS_CODEX_AVAILABLE=false` as a hard off switch before falling through to `CODEX_BINARY_FOUND` or `which()`. That env var historically encoded Step 0 probe health, not binary presence, so a stale `false` can skip Codex OOS combine even when the binary exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-routing-fidelity-output.txt: Drop `LARCH_OOS_CODEX_AVAILABLE` from the routing chain (or map it to binary-present semantics only), and treat explicit `false` there the same as other binary helpers: re-check `which()` before skipping.


### FINDING_15: dispatch-panel pre-filters manifest unlike voter dispatch pattern
- **Reviewer(s)**: dyn-shell-legacy-output.txt
- **Severity**: important
- **Concern**: Reviewer panel dispatch in `dispatch-panel.sh` still builds a smaller manifest when `CODEX_BINARY_FOUND` / `CURSOR_BINARY_FOUND` are `false`, omitting Codex/Cursor rows before `dispatch-with-waterfall.sh` runs. Code-voter dispatch always emits both external slots and lets `present_for_tool` drop them at launch. A stale `false` flag suppresses reviewer slots with no launch attempt and no skip status, while voters record `VOTER_*_STATUS=skipped`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-legacy-output.txt: Align `dispatch-panel.sh` with the voter pattern: always queue configured external rows in the manifest, pass binary-found only to `dispatch-with-waterfall.sh`, and let launcher failure or `tool-absent` drops surface degradation instead of pre-filtering rows at manifest build time.


### FINDING_16: tally-code-votes expected-voter predicate diverges from dispatch-code-voters
- **Reviewer(s)**: dyn-shell-legacy-output.txt
- **Severity**: important
- **Concern**: After the rename to `CODEX_BINARY_FOUND` / `CURSOR_BINARY_FOUND`, `expected_voters_for_round()` counts any value other than explicit `false` toward the expected panel (`!= "false"`), while `dispatch-code-voters.sh` only increments `expected_judges` when the flag is exactly `true`. Direct tally invocations (harnesses, partial argv) can compute `expected=3` while dispatch computed `expected_judges=1`, producing spurious or missing `DEGRADED_PANEL_WARNING` output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-legacy-output.txt: Make tally use the same `== "true"` predicate as `dispatch-code-voters.sh`, or require and validate `true|false` at tally entry the way `review-core.sh` does.


### FINDING_2: run_external_agent does not handle PermissionError from non-executable binaries
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: After removing the pre-launch health gate, `run_external_agent` only handles `FileNotFoundError`. A non-executable `codex` or `cursor` on PATH raises `PermissionError` from `subprocess.Popen` and produces a traceback instead of a structured non-transient fast-fail result.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Catch PermissionError and relevant OSError cases, write diagnostics, return a non-transient exit like 126, and keep the done sentinel consistent.


### FINDING_5: review SKILL.md Step 0 still documents presence-only parsing
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Step 0 parse prose still says reviewer presence only while Steps 2–3 require `CODEX_BINARY_FOUND` and `CURSOR_BINARY_FOUND`. Orchestrator binds only probe-health keys; `dispatch-panel` gets empty `--codex-available`/`--cursor-available` and `review-core.sh` exits 2 on validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Update Step 0 to explicitly parse and bind CODEX_BINARY_FOUND and CURSOR_BINARY_FOUND from session setup stdout before Step 2.


### FINDING_6: _refresh_gate_probe uses stale session state on resume instead of fresh probing
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-routing-fidelity-output.txt, dyn-env-contract-output.txt
- **Severity**: important
- **Concern**: `_refresh_gate_probe()` skips a fresh `check-reviewers` call when `st.codex_present` / `st.cursor_present` are already set, and passes `--skip-codex-probe` / `--skip-cursor-probe` from durable `CODEX_BINARY_FOUND` / `CURSOR_BINARY_FOUND=false` in session env. On `/implement` resume (dirty-tree or degraded-gate Continue), rehydrated snapshots are not re-probed even if the operator fixed PATH, auth, or installed CLIs mid-session. Refresh can then return `*_BINARY_FOUND=true` with `*_PRESENT=false`, and the degraded gate can emit `DEGRADED_PROMPT_REQUIRED` or `DEGRADED_HARD_FAIL` from stale Step 0 snapshots instead of current reality, including false both-down hard-fail despite installed binaries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Re-derive binary-found on resume before honoring skip-probe flags.
  - From codex-specialist-testing-output.txt: Ignore durable legacy health keys on resume or always refresh them with agent check-reviewers before degraded gate; add a legacy-session regression test.
  - From dyn-routing-fidelity-output.txt: Always rerun `check-reviewers` for the immediate gate on resume (or at least when sentinel/`DEGRADED_PROMPT_REQUIRED` recovery is in play), and base skip-probe only on a live `which`/`command -v` miss, not on persisted `false`.
  - From dyn-env-contract-output.txt: In `_refresh_gate_probe()`, always run a full `check-reviewers` probe (no skip flags from stale session env), or derive skip flags from fresh `shutil.which()` inside the probe, not from persisted `*_BINARY_FOUND`.


### FINDING_7: plan_review Step 3 still routes from CODEX_PRESENT / CURSOR_PRESENT
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The embedded `/design` Step 3 runner still feeds plan-review routing from `CODEX_PRESENT` / `CURSOR_PRESENT`; the decompressed `run-step3-review.sh` body passes `--codex-present "${CODEX_PRESENT:-false}" --cursor-present "${CURSOR_PRESENT:-false}"`, but `python/session_env.py` now intentionally persists only `CODEX_BINARY_FOUND` / `CURSOR_BINARY_FOUND`. In a normal design session with both binaries present, Step 3 defaults both externals to false and silently collapses the Codex/Cursor reviewer and voter lanes to the degraded Claude-only path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Regenerate the embedded plan-review assets so Step 3 derives those per-call flags from `CODEX_BINARY_FOUND` / `CURSOR_BINARY_FOUND` or fresh executable checks, and add a regression where both binary-found values are true while `*_PRESENT` is unset.


### FINDING_8: Missing test locking in launch-without-pre-probe behavior
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Health-gate removal deletes spawn-blocking tests without a replacement that locks in launch-without-pre-probe behavior. Reintroducing `_external_health_gate()` or an equivalent pre-launch block would pass CI while violating acceptance that `run_external_agent` attempts launch regardless of Step 0 probe health.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a test that forces unhealthy probe output and asserts run_external_agent still spawns (no rc 7/8 fast-fail).


### FINDING_9: Missing test for both-down hard-fail with existing sentinel
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No automated test for both-down hard-fail when `.degraded-tools-gate-prompted` already exists. A refactor that reorders Step 0 status routing could honor a stale sentinel and continue one-down after both vendors recover then fail again, violating the hard-fail contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add tests that pre-create the sentinel, mock both-down gate output, and assert hard-fail with no ROUTE=continue.


