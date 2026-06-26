## Plan

## Approach

- Keep `_RUN_EXTERNAL_TIMEOUT = 300`.
- Keep read-only Codex lanes unchanged.
- Keep Codex lint-fix on `--full-auto` / workspace-write with existing `run_dir` and repo-root `--add-dir` grants only.
- Fix the reported stall in two layers:
  - **Fast-fail safety net**: detect Codex `exec_command` policy rejection in the shared `agent launch-codex-exec` launcher, terminate the child within one poll interval, and short-circuit auth / unclassified-empty retries so deterministic policy denials do not replay a full launch budget.
  - **Task split for verification (Codex-only)**: stop asking Codex to self-verify via shell. Pass the machine `site` token from `run_lint_fix` into `_run_codex`, append Codex-only edit-only / orchestrator-verification language after shared `_compose_prompt`, and forbid `exec_command` / ad-hoc `/tmp` verification roots in that Codex appendix only.
- **Do not** broaden shared `_compose_prompt` with Codex-specific exec prohibitions; Claude and Cursor tiers keep the existing shared prompt unchanged and may still self-verify locally.
- **Do not** add a Codex `--add-dir` grant for `implement_tmpdir`, `allowed_root`, or any session-root scratch path. Post-dispatch verification stays on the orchestrator path already used by `review_and_fix.py` (`_run_relevant_checks_captured` after lint-fix returns).

## Files to modify/create

### UPDATED: python/agents.py

- Add a small Codex policy-rejection detector near the existing Codex event helpers.
- Match bounded text from the Codex `--json` events stream and `${output}.diag` / sidecar against required evidence families:
  - `exec_command failed`
  - `blocked by policy` or `Rejected(`
  - optionally `CreateProcess`
- Require both the `exec_command failed` family and the policy-rejection family to avoid false positives from unrelated model text.
- Add an optional early-failure hook to `run_external_agent` poll loop:
  - On each poll timeout, when `stdout_path` points at the Codex events file, scan new tail bytes line-by-line.
  - Tolerate malformed JSON and plain-text fragments.
  - If the detector matches, terminate the child process immediately.
  - Append a clear `policy-rejection` diagnostic to `${output}.diag` (include the matched excerpt, redacted as needed).
  - Return exit code `1`, not `124`, so callers see `dispatch-failed` rather than a timeout class.
- Extend `RunExternalAgentResult` or `${output}.diag` with an explicit non-retryable marker (for example `POLICY_REJECTION=true` or `FAILURE_CLASS=policy-rejection`) that auth-retry logic can read without re-parsing free text.
- Wire the hook only through `launch_codex_exec_main`:
  - Pass the existing `events` path as the watched stream.
  - Preserve auth retry behavior for genuine auth failures.
  - Preserve `.done`, `.failure-diag`, `.stderr-tail`, token-record, timing, and metadata sidecars.
- Update `_run_external_agent_with_auth_retries`:
  - After each `run_external_agent` return, if the policy-rejection marker is present in `${output}.diag` (or the dedicated result flag is set), return immediately.
  - Skip `_is_unclassified_empty_startup_failure` retry and `external_auth_verdict` auth-retry branches on that path.
  - Do not relaunch Codex for deterministic policy denials.
- Keep `--sandbox` choices unchanged.
- Do not change read-only call sites beyond benefiting from the shared fast-fail hook when an events stream is present.

### UPDATED: python/checks.py

- **Leave `_compose_prompt` signature and body unchanged** so Claude and Cursor lint-fix tiers keep the existing shared prompt (including any self-verify wording those tiers can honor locally).
- Add a small Codex-only helper (for example `_codex_lint_fix_prompt_appendix(site: str) -> str`) that encodes the task-split contract:
  - State that fixes target machine site `{site}` (for example `step5`, not an invented `step5-review-fixes` label unless that site is the actual `run_lint_fix` argument).
  - State that the parent orchestrator runs `python3 python/cli.py checks run-relevant --site {site} --tmpdir <canonical session tmpdir>` after Codex exits.
  - Instruct Codex to make file edits only; do **not** run `exec_command`, shell, or `checks run-relevant` inside the Codex sandbox.
  - Do not tell Codex to create ad-hoc `/tmp` verification roots.
  - Keep the final `FIXED:` / `UNFIXABLE:` line contract unchanged (still owned by shared `_compose_prompt`).
- Extend `_run_codex(...)` with a required `site: str` argument.
  - After `run_lint_fix` builds shared `prompt_body` via `_compose_prompt`, pass `site` into `_run_codex`.
  - Concatenate `prompt_body + _codex_lint_fix_prompt_appendix(site)` before writing `run_dir/prompt.md`.
  - Do not mutate the shared `prompt_body` used by `_run_claude` or `_run_cursor`.
- Leave `_build_codex_argv` unchanged: no additional `--add-dir` for `implement_tmpdir`, `allowed_root`, or verification scratch paths.
- Keep the total lint-fix budget, tier order, timeout `300`, and failure mapping (`dispatch-failed` when Codex exits non-zero and no later tier succeeds) unchanged.
- Do not broaden sandbox grants to plan auto-fix, review-and-fix, OOS combine, research, validation, voter, judge, or design drafter lanes.

### UPDATED: scripts/test-prompt-template-invariants.sh

- Replace the lint-fix smoke block (~175–185) so it exercises **Codex prompt assembly** (shared `_compose_prompt` plus Codex appendix), not `_compose_prompt` alone. For example:
  - Render shared body with existing `_compose_prompt(..., site_label="Step 3", ...)`.
  - Append via the new Codex helper with `site="step3"`.
  - Write the combined result to the smoke artifact.
- Add `assert_contains` checks on the **combined Codex prompt** for:
  - the machine `site` token (for example `step3`) in the orchestrator-verification directive
  - `checks run-relevant --site step3` (or equivalent wording binding verification to the machine site)
  - edit-only / orchestrator-owned verification language (parent runs verification after Codex exits)
  - explicit prohibition of Codex-side `exec_command`, shell, or ad-hoc temporary verification roots
- Add a negative check that shared `_compose_prompt` output alone does **not** contain Codex-only exec prohibitions (guards against re-introducing tier-specific language into the shared helper).
- Keep existing lint-fix invariant asserts on the combined prompt (`FIXED:`, `UNFIXABLE:`, acceptable final-line shapes, submodule prohibition) unchanged.
- Run this harness under `make test-prompt-template-invariants` / `make lint` before relying on narrower pytest filters alone.

### UPDATED: scripts/test-prompt-template-invariants.md

- Extend the lint-fix row in the **Required markers** table to document Codex-combined-prompt markers: machine `site`, orchestrator-verification, edit-only, and no-`exec_command`, plus the negative shared-prompt guard.
- Keep the **Edit In Sync** note: lint-fix prompt composition changes must update this harness in the same PR.

### UPDATED: python/test_agents.py

- Add a unit test for `launch_codex_exec_main` fast-fail behavior.
- Stub `_run_external_agent_with_auth_retries` only if the early-fail logic lives above it; otherwise use a fake child process or a focused helper test.
- Cover a Codex events stream containing the policy rejection shape:
  - `CreateProcess`
  - `Rejected(...)`
  - `blocked by policy`
- Assert:
  - the launcher exits without waiting for the full configured timeout,
  - `${output}.diag` records `policy-rejection` (or equivalent marker),
  - `LAUNCHER_EXIT` is non-zero and not `124`,
  - `.done` is written,
  - `.failure-diag` or stderr tail still includes useful diagnostics where applicable.
- Add a negative test showing unrelated event text with only one token family does not trigger fast-fail.
- Add a test that when the policy-rejection marker is present, `_run_external_agent_with_auth_retries` does not perform an unclassified-empty or auth retry relaunch.
- If the early-fail hook is added to `run_external_agent`, add a focused test for that hook rather than relying only on end-to-end launcher tests.

### UPDATED: python/test_checks.py

- **Do not** change existing `_compose_prompt` unit tests; shared prompt behavior is unchanged.
- **Update every existing direct `_run_codex(...)` call site** before adding new tests: the signature change makes `site` required, so all four current invocations (token-ingest and warn paths around lines 1328–1433) must pass a representative `site=` argument (for example `site="step6"`) so `make py-test` / `make py-lint` do not fail at collection or first invocation.
- Add unit tests for `_codex_lint_fix_prompt_appendix` (or equivalent):
  - Assert the appendix includes the machine `site` token passed from `run_lint_fix` (for example `step5`).
  - Assert orchestrator-owned verification with `checks run-relevant --site <site>`.
  - Assert the appendix forbids Codex-side `exec_command` / shell verification and does not instruct creation of arbitrary temporary roots.
- Add or update a `_run_codex` test that the written `prompt.md` is `shared_compose + codex_appendix` when `site` is supplied.
- Assert `_compose_prompt` output alone lacks Codex-only exec prohibitions.
- Assert `_build_codex_argv` / `launch-codex-exec` argv still has only the existing `run_dir` and repo-root `--add-dir` grants (no `implement_tmpdir` / session-root grant).
- Preserve existing assertions for timeout `300`, workdir, run_dir grant, repo grant, usage label `codex_lint_fix`, and prompt-file use on the updated call sites.

### UPDATED: SECURITY.md

- Update the external delegation or `python/cli.py checks lint-fix` section (~325–331 neighborhood).
- Document that Codex lint-fix stays on workspace-write / `--full-auto` with repo and per-run `run_dir` grants only; no session-root / `implement_tmpdir` `--add-dir` is added.
- Document the shared `launch-codex-exec` fast-fail for Codex `exec_command` policy rejections and that policy rejections are non-retryable.
- Document the task-split verification model: orchestrator runs `checks run-relevant`; Codex lint-fix is edit-only (via Codex-specific prompt appendix) and must not receive write access to orchestrator-owned session files such as `session-env.sh`, `finalize-state.sh`, and timing ledgers.
- Note that Claude/Cursor lint-fix tiers keep the shared prompt and are not restricted by the Codex edit-only appendix.
- State that read-only Codex lanes remain unchanged.

## Edge cases

- **Partial event writes**: scan line-by-line on poll, but tolerate malformed JSON and plain text fragments.
- **Event stream absent**: do not crash. Fall back to the existing timeout path.
- **False positives**: require both the `exec_command failed` family and the policy-rejection family.
- **Auth failures**: do not classify auth failures as policy rejections; auth retry remains for genuine auth verdicts only.
- **Read-only callers**: keep `--sandbox read-only` callers unchanged. The fast-fail detector may still help if a future prompt asks for shell execution by mistake.
- **Retry behavior**: policy rejection is deterministic. The auth-retry wrapper must not relaunch on the policy-rejection marker.
- **Tier isolation**: Codex appendix must not leak into Claude/Cursor `prompt_body`; only `_run_codex` concatenates it.
- **Site mismatch**: bind Codex appendix scope to the `run_lint_fix` `site` argument so Codex does not invent a different `--site` label (for example `step5-review-fixes` when lint-fix was dispatched with `site="step5"`).
- **Harness drift**: Codex appendix or `_run_codex` signature changes must update `scripts/test-prompt-template-invariants.sh` in the same PR.
- **Existing test call sites**: every pre-existing `_run_codex` invocation in `python/test_checks.py` must receive `site=` when the signature changes; otherwise pytest fails before new appendix coverage runs.
- **Security posture**: do not broaden Codex write surface beyond existing repo / `run_dir` grants. Verification scratch and session integrity stay outside Codex.

## Failure modes

- If Codex still attempts unsanctioned shell verification, fast-fail stops the 300 s stall and lint-fix falls through to the next tier or `main-agent-required` quickly.
- If Codex event wording changes, fast-fail may miss the new wording until the detector is updated; the Codex-only task-split appendix should reduce how often Codex attempts shell verification at all.
- If Codex returns exit 0 without fixing lint, the existing orchestrator recheck in `review_and_fix.py` still fails closed and may re-enter the lint-fix loop; this plan does not widen Codex sandbox to make in-agent verification work.
- If task-split language is mistakenly added back into `_compose_prompt`, Claude/Cursor self-verify behavior narrows without fixing the Codex stall root cause.
- If existing `_run_codex` tests are not updated for the required `site` argument, CI fails immediately on signature mismatch rather than exercising the new behavior.

## Testing strategy

- Run targeted tests:
  - `python3 -m pytest python/test_agents.py -k 'launch_codex_exec or policy_rejection or run_external_agent'`
  - `python3 -m pytest python/test_checks.py -k 'codex or lint_fix or compose_prompt or codex_lint_fix_prompt'`
- Confirm all four legacy `_run_codex` call sites in `python/test_checks.py` (lines ~1328–1433) pass `site=` and still pass after the signature change.
- Run cross-cutting prompt harness (catches Codex combined-prompt drift before full lint):
  - `make test-prompt-template-invariants`
- Run Python checks:
  - `make py-lint`
  - `make py-test`
- Run full lint:
  - `make lint`
- Manually inspect generated failure diagnostics in the fast-fail test fixture to ensure the policy rejection reason is visible and redacted.

## Acceptance

- `launch_codex_exec_main` fast-fails on a Codex `exec_command` policy rejection: it detects both the `exec_command failed` family and the `blocked by policy` / `Rejected(` family in the events stream, terminates the child, writes a `policy-rejection` diagnostic to `${output}.diag`, returns `LAUNCHER_EXIT=1` (not `124`), and skips the auth / unclassified-empty retry branches.
- Unrelated event text matching only one token family does not trigger fast-fail.
- The Codex lint-fix tier (`_run_codex`) appends a Codex-only edit-only appendix bound to the `run_lint_fix` `site`: it tells Codex to make file edits only, forbids Codex-side `exec_command` / shell / ad-hoc `/tmp` verification, and leaves verification to the orchestrator. The shared `_compose_prompt` body and the Claude/Cursor tiers stay unchanged.
- `_build_codex_argv` adds no session-root / `implement_tmpdir` `--add-dir`; only the existing `run_dir` and repo-root grants remain.
- `_RUN_EXTERNAL_TIMEOUT` stays `300`. The lint-fix budget, tier order, and the `dispatch-failed` to `main-agent-required` mapping are unchanged.
- Read-only Codex lanes (research, validation, voter, judge, OOS-combine, design drafter) and the other workspace-write callers (plan auto-fix, review-and-fix) are unchanged except for benefiting from the shared launcher fast-fail when an events stream is present.
- `SECURITY.md` documents the non-retryable policy-rejection fast-fail, the task-split verification model, and that Codex lint-fix receives no session-root write grant.
- Regression coverage added or updated: `python/test_agents.py` (fast-fail plus no-retry), `python/test_checks.py` (Codex appendix, `_run_codex` `site` argument, all four existing call sites updated, no session-root add-dir), and `scripts/test-prompt-template-invariants.sh` (combined Codex prompt markers plus the negative shared-prompt guard).
- `make py-lint`, `make py-test`, and `make lint` pass.

review_status: complete
rounds_completed: 5
diff_lines: 218
