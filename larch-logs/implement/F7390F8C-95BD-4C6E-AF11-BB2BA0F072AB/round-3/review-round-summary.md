# Review Round 3

- Mode: `diff`
- 4 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: `_resolve_non_interactive` omits `claude -p` and cron from canonical predicate
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-absorbed-tail-robustness-output.txt
- **Severity**: important
- **Concern**: `_resolve_non_interactive` does not implement the full non-interactive predicate described in the plan, SKILL, and `skills/shared/external-reviewers.md`. It omits detection of `claude -p` and cron (and related entrypoints may not set `LARCH_SKILL_NON_INTERACTIVE`, `LARCH_AUTONOMOUS_LOOP`, or `LARCH_EVAL_RUN`). In those modes, a both-down degraded run can be classified interactive, emit `DEGRADED_PROMPT_REQUIRED=true`, and stall on `AskUserQuestion` instead of logging and continuing to 1.r.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Detect claude -p and cron in resolve-non-interactive (env from launchers or parent probe); add a test proving both-down never emits DEGRADED_PROMPT_REQUIRED in that mode.
  - From cursor-specialist-edge-cases-output.txt: Mirror every non-interactive entrypoint from external-reviewers.md in _resolve_non_interactive, or have launchers export a flag that step-0-bootstrap.sh always forwards as --non-interactive true.
  - From dyn-absorbed-tail-robustness-output.txt: Extend `resolve-non-interactive` (and `step-0-bootstrap.sh` if needed) to detect every non-interactive mode named in `skills/shared/external-reviewers.md`, including explicit env exports from eval/loop/`claude -p` drivers, and add harness cases that fail if those modes still resolve interactive.


### FINDING_13: Absorbed tail drops degraded-gate stderr diagnostics
- **Reviewer(s)**: dyn-absorbed-tail-robustness-output.txt
- **Severity**: latent
- **Concern**: `_run_absorbed_continue_tail` captures the degraded gate subprocess output but only relays `explanation_lines` to operator stderr. When `PRESENCE_INPUT_EMPTY=true`, it appends a `Warnings` entry but drops the gate’s own stderr diagnostics that the absorbed-tail contract and SKILL require to remain operator-visible. Absorption regresses behavior from the legacy `step-0-degraded-gate.sh` path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-absorbed-tail-robustness-output.txt: After a successful gate subprocess, forward sanitized non-KV stderr lines (or the full gate stderr when `PRESENCE_INPUT_EMPTY=true`) to `_err` before parsing, and add a unit test that asserts those diagnostics appear in captured stderr.

---

**Subsumed non-findings (omitted):** FINDING_16, FINDING_17, FINDING_20, and FINDING_21 were reviewer attestations of correct or intentional behavior, not actionable defects. Generic “Address the concern above” placeholders were omitted per aggregator rules where no distinct verbatim fix was provided.


### FINDING_2: Symlinked `bootstrap-routing.env` trusted before absorbed tail is blocked
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-generic-output.txt, dyn-architecture-output.txt
- **Severity**: important
- **Concern**: Resume routing restoration applies inconsistent symlink/non-regular policy. `_preserve_resume_routing` refuses symlinked caches, but `_restore_resume_coder` can still read a symlinked `bootstrap-routing.env`, and `invoke_main` can run `_run_absorbed_continue_tail` (degraded gate + 1.r rebase probe) before refusing an unsafe routing file. A continue-shaped run with an untrusted routing cache may therefore execute git-mutating absorbed-tail work despite the plan contract that symlinked or non-regular prior routing state is not trusted for tail execution.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Skip symlinked/non-regular routing files in _restore_resume_coder; use session-env/run-flags fallbacks only.
  - From codex-generic-output.txt: Check and handle `bootstrap-routing.env` symlink/non-regular status before `_restore_resume_coder` and `_run_absorbed_continue_tail`, or explicitly skip the absorbed tail whenever the routing cache is unsafe.
  - From dyn-architecture-output.txt: Apply one symlink/non-regular guard before any resume coder restoration and before `_run_absorbed_continue_tail` (mirror `_preserve_resume_routing`’s `is_symlink()` / `is_file()` checks in `_restore_resume_coder`, or centralize both paths through a shared “safe routing file” helper). If a symlink is detected, skip tail execution and restore `coder` only from `session-env.sh` / `run-flags.sh`; align or remove `test_restore_resume_coder_from_symlinked_routing_file` accordingly.


### FINDING_5: `test_invoke_resume_preserves_prior_coder_in_routing_file` invokes real gate/probe
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The test enables the continue predicate but does not mock the absorbed degraded-gate or 1.r probe. Local pytest or CI can invoke real `degraded-tools-gate` and `rebase-checkpoint-probe.sh` against the workspace git tree while only asserting coder preservation; failures or flakes depend on `GITHUB_ACTIONS` non-interactive mode and live git state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Mock _cli/_run in this test (gate_and_probe pattern) or limit it to coder restoration and add separate mocked invoke_main absorbed-tail tests


