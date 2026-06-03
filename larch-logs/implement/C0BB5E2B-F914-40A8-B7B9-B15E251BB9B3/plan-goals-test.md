## Goal
Implement issue #3402: [IMPLEMENTING] [BUG] /design review panel: weak Codex probe + false 'empty reviewer rows' warning\n\n## Summary.

## Implementation Plan
## Plan

Fix two misleading `/design` plan-review-panel diagnostics from issue #3402: **(a)** a Codex Step 0 probe that passes while every real review call fails (silent 2-judge degradation), and **(b)** a false "empty reviewer rows" warning on a valid `{"no_issues_found": true}` reviewer response. SIMPLE tier: smallest change that fixes both, plus tests. No circuit-breaker, no execution-issues noise aggregation, no Cursor-probe change.

### UPDATED: `scripts/check-reviewers.sh`
Strengthen `larch_run_one_codex_probe` (currently lines ~188-218) so the probe exercises the **same model** as real Codex reviewer calls. Today the probe runs `codex exec ... -- "Respond with OK"` with **no model args**, while real reviewer launches use `agent-model-args.sh --tool codex --with-effort` (`launch-review.sh:489,555-557`) → `--model gpt-5.5`. A per-model quota / `exit 7` on gpt-5.5 never trips the trivial probe (which runs Codex's default model) — the root cause behind "probe passes but every real call fails."
- Mirror the existing **Cursor** probe pattern (`check-reviewers.sh:152-158`): build a `_probe_model_args` array from `"$SCRIPT_DIR/agent-model-args.sh" --tool codex --with-effort`. On `agent-model-args.sh` failure, leave the array empty and continue (do not abort the probe).
- Pass `${_probe_model_args[@]+"${_probe_model_args[@]}"}` into the `codex exec` invocation, before the `--` separator (same position as `launch-review.sh:555-557`).
- Keep the prompt (`"Respond with OK"`), `--sandbox read-only`, `--output-last-message`, the serial-lock spawn guard, the poll, and the `0`/`2`/`1` return-code contract unchanged.
Result: when gpt-5.5 is quota/exit-7-degraded, the probe's `codex exec` exits non-zero → `probe_rc != 0` → non-auth → `return 1` (unhealthy) → `CODEX_PRESENT=false`. The run then starts already knowing Codex is down (degraded-tools-gate notice + Codex omitted from the panel manifest) instead of degrading silently mid-run.

### UPDATED: `scripts/check-reviewers.md`
Update the Codex bullet in **Probe behavior (summary)** (currently line 28): the probe now passes production model args via `agent-model-args.sh --tool codex --with-effort`, mirroring the Cursor probe, so it surfaces model-specific quota/auth errors. Record the intentional asymmetry per `.claude/rules/external-tool-launcher-parity.md`: Codex passes `--with-effort` (effort is meaningful for Codex) while the Cursor probe omits it (Cursor ignores effort).

### UPDATED: `scripts/test-check-reviewers.sh`
Add a probe-model-args propagation case: a PATH-stubbed `codex` that appends its argv to a log file and exits 0; run `check-reviewers.sh` with `LARCH_CODEX_MODEL=<sentinel-model>`; assert (1) `CODEX_PRESENT=true` and (2) the logged codex argv contains `<sentinel-model>`. Existing exit-0 codex stubs stay green because they ignore the extra argv.

### UPDATED: `skills/design/scripts/plan-review-loop.sh`
Fix the false empty-rows warning (currently lines ~1043-1046). Before emitting `WARN plan-review-tsv: empty or missing structured reviewer rows for ${_rf}`, check the reviewer output file `$_rf` for the zero-findings sentinel using the canonical pattern already used in `dispatch-plan-review-panel.sh` (`^[[:space:]]*\{"no_issues_found`). When the sentinel is present, treat the slot as a healthy zero-findings slot and emit **no** warning. Keep the warning only when output is genuinely empty/unparseable (no TSV finding rows **and** no sentinel). The slot already carries `STATUS=OK`, so coverage/quorum is unchanged.

### UPDATED: `skills/design/scripts/plan-review-loop.md`
Note in the WARN documentation that `plan-review-tsv: empty or missing structured reviewer rows` is suppressed for reviewers returning the `{"no_issues_found": true}` sentinel (counted as a healthy zero-findings slot).

### UPDATED: `skills/design/scripts/test-plan-review-loop.sh`
Add a `{"no_issues_found": true}` scenario: a new `write_collect` mode that writes the sentinel literal to the reviewer output file `$p` (the `_rf`) plus a header-only `.tsv`, emitting `STATUS=OK`. Assert the loop output does **not** contain `WARN=plan-review-tsv:` for that reviewer and the slot is still successful (`TALLY_PLAN_REVIEW_STATUS=skipped-empty-findings`). Leave the existing "zero findings (empty TSV)" test (lines ~943-958) unchanged — its `_rf` has no sentinel, so it must still emit the WARN (no-false-negative guard).

### Approach, edge cases, failure modes
- (a) is a parity + root-cause fix (align the probe's model with real reviewer calls), not a bigger prompt — lowest-risk realization of "stronger probe," reusing the tested Cursor-probe pattern.
- (b) is a single guard branch reusing the repo's canonical sentinel regex.
- Edge: healthy Codex on a high-effort trivial prompt still exits 0 → no false negative. `agent-model-args.sh` failure → empty args, probe still runs. A TSV header with zero rows and no sentinel still warns.
- Failure modes: concurrency-only quota may still slip a single probe (deferred circuit-breaker, out of scope); probe/launcher arg drift (keep both on `agent-model-args.sh --tool codex --with-effort` per the parity rule); sentinel false-suppression is low risk (line-anchored exact token).

## Acceptance

- [ ] `larch_run_one_codex_probe` in `scripts/check-reviewers.sh` builds `_probe_model_args` via `agent-model-args.sh --tool codex --with-effort` and passes them to `codex exec` before `--`; prompt, `--sandbox read-only`, `--output-last-message`, serial-lock, and the 0/2/1 return contract are unchanged.
- [ ] `scripts/check-reviewers.md` documents the new Codex probe model args and the Codex-only `--with-effort` asymmetry per the parity rule.
- [ ] `scripts/test-check-reviewers.sh` asserts the probe forwards the configured model (e.g. `LARCH_CODEX_MODEL=<sentinel>` appears in the codex argv) with `CODEX_PRESENT=true`; the existing matrix still passes.
- [ ] `skills/design/scripts/plan-review-loop.sh` suppresses the empty-rows WARN when `$_rf` contains the `{"no_issues_found": true}` sentinel and still warns on genuinely empty/unparseable output.
- [ ] `skills/design/scripts/plan-review-loop.md` documents the sentinel suppression.
- [ ] `skills/design/scripts/test-plan-review-loop.sh` adds the sentinel scenario (no WARN + successful slot); the existing empty-TSV WARN test still passes.
- [ ] `make test-check-reviewers` and `make test-plan-review-loop` pass; `bash scripts/relevant-checks.sh` is clean (shellcheck, bash32, sibling-`.md`, bare-grep-probe lint).
- [ ] Per `.claude/rules/verify-external-tool-invocations.md`, the new `codex exec ... --model … --with-effort … -- "Respond with OK"` invocation is run against a healthy Codex (exit 0 + non-empty last message), or flagged in the PR for manual CI verification when Codex is unavailable locally.

diff_lines: 95

## Test plan
(no test plan section in plan-file)
