# Review Round 1

- Mode: `diff`
- 8 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_1: 1.r probe runs in plugin cwd instead of consumer repo
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `_run_1r_probe` uses `cwd=_REPO_ROOT` (plugin tree), not the consumer git repo. Because `rebase-push.sh` runs git in the subprocess cwd, `/implement` in a consumer repo may rebase the wrong repository or fail while the feature branch in the target repo stays stale.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_2: `NON_INTERACTIVE_ARG` unbound under `set -u` when Step 0 omits flag
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `step-0-bootstrap.sh` reads `NON_INTERACTIVE_ARG` under `set -u` without a default, while the active Step 0 fence in `skills/implement/SKILL.md` omits `--non-interactive`. Normal `/implement` Step 0 invocation reaches `case "$NON_INTERACTIVE_ARG"` and exits with an unbound variable before bootstrap runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Initialize `NON_INTERACTIVE_ARG=""` and add a wrapper test for calls without the optional flag.
  - From codex-specialist-edge-cases-output.txt: Initialize `NON_INTERACTIVE_ARG=""` with the other argument defaults and add a no-flag wrapper test.


### FINDING_3: Probe stdout KV parsing truncates values at whitespace
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `_parse_probe_stdout` splits KV lines on whitespace and truncates values containing spaces. Spaced values such as `REBASE_ERROR=fetch failed on upstream main`, `CONFLICT_FILES=docs/user guide.md`, or `PHANTOM_*` advisory values are stored incorrectly, losing routed failure detail from absorbed Step 1.r.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Parse one `KEY=value` per line, preserving everything after the first equals sign.
  - From codex-specialist-edge-cases-output.txt: Parse each `KEY=value` line by splitting once at `=` and preserve the full value; reserve token scanning only for known multi-KV lines.
  - From codex-specialist-testing-output.txt: Parse whole-line `KEY=value` records for known probe and `PHANTOM_*` keys before token scanning, and add a spaced `REBASE_ERROR` test.


### FINDING_4: Non-interactive predicate incomplete vs `external-reviewers.md`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-apply-interface-backward-compat-output.txt
- **Severity**: important
- **Concern**: The absorbed degraded gate can block `/implement` on `DEGRADED_PROMPT_REQUIRED=true` when both external tools are down, but the non-interactive predicate in `step-0-bootstrap.sh` and `_resolve_non_interactive()` does not match `skills/shared/external-reviewers.md`. `LARCH_*` env vars are read but never set by drivers; `claude -p`, cron, and `<<autonomous-loop>>` signals are omitted. Those contexts can be classified as interactive, emit `DEGRADED_PROMPT_REQUIRED=true`, skip 1.r, and stall on `AskUserQuestion` instead of logging and proceeding.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Mirror the full `external-reviewers.md` predicate or set a canonical env from every non-interactive entrypoint; add tests.
  - From cursor-specialist-edge-cases-output.txt: Detect all canonical non-interactive entrypoints in `step-0-bootstrap.sh`; export flags from loop/eval drivers; add prompt-side non-interactive guard in `SKILL.md` as fallback.
  - From dyn-apply-interface-backward-compat-output.txt: Mirror the full `external-reviewers` predicate in one shared helper used by `step-0-bootstrap.sh` and `_resolve_non_interactive()` (including whatever env or TTY signals `claude -p` and cron already set, or set `LARCH_SKILL_NON_INTERACTIVE=true` at every non-interactive `/implement` entrypoint), and add a regression test that both-down non-interactive runs never emit `DEGRADED_PROMPT_REQUIRED=true`.


### FINDING_5: Non-interactive degraded handling mishandles logging and sentinel idempotency
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt, dyn-absorbed-tail-state-machine-output.txt
- **Severity**: important
- **Concern**: Non-interactive degraded branches in `python/bootstrap.py:1256-1266` are inconsistent with `skills/shared/external-reviewers.md` and the `.degraded-tools-gate-prompted` sentinel contract. The one-tool-down path (`both_down == "false"`) relays stderr but never calls `_log_degraded_explanation()`, leaving no durable `execution-issues.md` record. The both-down path always prints, logs, and rewrites the sentinel without checking `sentinel_exists`, duplicating stderr notices and warnings on resume or dirty-tree re-entry while interactive both-down correctly skips re-prompt when the sentinel exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Call `_log_degraded_explanation` for non_interactive degraded `BOTH_DOWN=false` after stderr relay.
  - From codex-specialist-correctness-output.txt: Log once for any non-interactive degraded state and honor the existing sentinel before printing/logging again.
  - From codex-specialist-testing-output.txt: Log non-interactive degraded explanations once only when the sentinel is absent, then write the sentinel and proceed.
  - From dyn-absorbed-tail-state-machine-output.txt: Wrap the non-interactive both-down notice/log/sentinel block in `if not sentinel_exists:` (mirror the one-down branch at lines 1256-1260), and always proceed to the 1.r probe when `run_probe` remains true.
  - From dyn-absorbed-tail-state-machine-output.txt: After relaying explanation lines to stderr in the one-down branch, also call `_log_degraded_explanation(st, explanation_text)` when `non_interactive` is true (still guarded by `if not sentinel_exists:` to avoid duplicate log entries on re-entry once finding 2 is fixed).


### FINDING_6: Interactive fail-closed `BOTH_DOWN` branches omit explanation relay before prompt
- **Reviewer(s)**: codex-specialist-testing-output.txt, dyn-absorbed-tail-state-machine-output.txt
- **Severity**: important
- **Concern**: Interactive degraded branches that set `DEGRADED_PROMPT_REQUIRED=true` (missing `BOTH_DOWN`, or `BOTH_DOWN` present but not exactly `true`/`false`) never relay the explanation block to stderr via `_err()`, unlike the `both_down == "true"` interactive path. `skills/implement/SKILL.md` requires that when `DEGRADED_PROMPT_REQUIRED=true`, the explanation was already relayed to operator-visible stderr during Step 0. On the missing/malformed `BOTH_DOWN` fail-closed path the operator gets a prompt with no prior notice.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Print the explanation lines before `prompt_required` in those branches and add the planned relays-explanation regression test.
  - From dyn-absorbed-tail-state-machine-output.txt: Before setting `prompt_required = True` and `run_probe = False` in the `not both_down_seen` and final `else` branches, emit every `explanation_lines` entry through `_err()` (same as the both-down interactive branch), so stderr is populated before the orchestrator reads `DEGRADED_PROMPT_REQUIRED=true`.


### FINDING_7: Missing presence keys coerced to false, hiding `PRESENCE_INPUT_EMPTY`
- **Reviewer(s)**: codex-specialist-testing-output.txt, dyn-dep-pipeline-input-integrity-output.txt
- **Severity**: important
- **Concern**: The absorbed continue tail coerces empty or missing `CODEX_PRESENT` / `CURSOR_PRESENT` envelope values to literal `"false"` before calling `agent degraded-tools-gate`. Partial presence rehydration never surfaces `PRESENCE_INPUT_EMPTY=true` and can be misread as a real tool outage (both-down prompt or one-down notice) instead of a caller contract failure, regressing the fail-closed rehydration signal the legacy `step-0-degraded-gate.sh` path and `skills/shared/external-reviewers.md` were written to preserve.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Pass raw envelope values through, including empty strings when absent, and add a missing-presence-key regression test.
  - From dyn-dep-pipeline-input-integrity-output.txt: Pass through empty strings unchanged (or a dedicated empty sentinel) so `python/agents.py` can emit `PRESENCE_INPUT_EMPTY=true`; only substitute `"false"` when bootstrap has positively confirmed absence, and add a regression test for missing envelope presence keys.


### FINDING_9: Plan-required `test_bootstrap.py` regression coverage absent or incomplete
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Absorbed-tail tests named in the plan are absent or incomplete. Wrong probe cwd, incomplete non-interactive predicate, degraded-gate failure modes, missing explanation relay, and malformed `ROUTE` handling lack regression coverage. A forked-target probe argv regression could make `--forked` runs rebase against the wrong remote while current absorbed tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add the plan-named tests including distinct consumer-repo cwd probe invocation.
  - From cursor-specialist-testing-output.txt: Add `test_invoke_absorbed_1r_passes_forked_target_without_base_remote_ref` capturing probe argv with `--forked-target true` and no base-remote flags.
  - From cursor-specialist-testing-output.txt: Add monkeypatch tests for absorbed-degraded-gate failure, explanation-missing contract failure, and malformed-ROUTE bail synthesis; include at least one `invoke_main` exit-2 integration case.
  - From cursor-specialist-testing-output.txt: Add capsys tests asserting explanation block lines appear on stderr for one-down and both-down interactive degraded paths.


