# auto-fix-plan-commands.sh

**Consumer**: `/design` shared **### Plan command validator failure (shared)** handler in `SKILL.md` (Step 2b, Gate B / Step 3.5, discussion-round2, Step 5c).

**Contract**: cross-vendor auto-repair loop for plan-command validator defects (#3628 Component D). On `VALIDATE_STATUS=defects-found`, the shared handler calls this helper **before** escalating to the operator. It spawns an external vendor (Codex/Cursor) to edit the target plan file in place, re-validates, and alternates vendors across bounded attempts. The operator `Fix-and-retry` / `Override` / `Cancel` prompt fires only when this helper returns `exhausted` or `unavailable`.

**When to load**: before wiring the shared validator handler's auto-repair step, or when editing the helper.

## Argv

| Flag | Required | Notes |
|------|----------|-------|
| `--design-tmpdir DIR` | yes | Validated via `larch_design_tmpdir_validate`; exported so the validator seam resolves the log path |
| `--plan-file PATH` | yes | Target file the validator flagged (`plan.txt` or `composed-plan.md`); must exist |
| `--codex-present true\|false` | yes | Step 0 Codex availability |
| `--cursor-present true\|false` | yes | Step 0 Cursor availability |
| `--repo-root DIR` | no | Defaults to the git toplevel of the plan file's directory, else `pwd` |
| `--max-attempts N` | no | Positive integer; default `2` (one fix attempt per vendor) |
| `--site STR` | no | Diagnostic label only |
| `--timeout SECS` | no | Per-vendor launcher timeout; default `1800` |

## Vendor attribution / alternation

"The vendor that introduced the defect" is not attributable — plan text is applied by the orchestrator from mixed-vendor findings — so the pragmatic default is **cross-vendor alternation**: attempt 1 = Codex (when present) else Cursor; attempt 2 = the other vendor. With `--max-attempts 2` and both vendors present, each vendor gets exactly one attempt. Unavailable vendors are dropped from the order; with neither present the helper returns `AUTOFIX_STATUS=unavailable` without dispatching.

## Dispatch reuse

Reuses the verified launcher primitives (same argv grammar as `scripts/lint-fix-loop.sh`):

- **Codex** → `scripts/launch-codex-exec.sh --workdir "$DESIGN_TMPDIR" --add-dir "$DESIGN_TMPDIR" --prompt-file … --usage-label codex_plan_autofix --timing-task-kind codex-plan-autofix` (parses `LAUNCHER_EXIT`).
- **Cursor** → `scripts/run-external-agent.sh --tool cursor --capture-stdout -- cursor agent -p --trust ${MODEL_ARGS} --workspace "$DESIGN_TMPDIR" "<wrapped-prompt>"` with `lib-cursor-launcher-common.sh` model/auth/serial-lock glue and `cursor-wrap-prompt.sh`.

The agent edits the plan file IN PLACE; `revalidate()` (re-running `validate-plan.sh`) is the authoritative success signal, not the launcher exit code. The fix prompt wraps the plan content and validator log as **untrusted data** (trust-boundary preserved) and instructs minimal, defect-only edits preserving plan prose, structure, and the trailing metadata block.

## Hermetic seams

- `LARCH_AUTOFIX_VALIDATE_PLAN_SH` — default `validate-plan.sh`; re-validation driver.
- `LARCH_AUTOFIX_LAUNCH_CODEX_EXEC_SH` — default `scripts/launch-codex-exec.sh`.
- `LARCH_AUTOFIX_RUN_EXTERNAL_AGENT_SH` — default `scripts/run-external-agent.sh`.
- `LARCH_AUTOFIX_DISPATCH_SH` — full per-vendor dispatch override (`--vendor`, `--run-dir`, `--prompt-file`, `--plan-file`, `--design-tmpdir`); replaces the real launcher path so the harness simulates a vendor edit deterministically.

## Machine output (FD 3 KVs)

- `AUTOFIX_STATUS` = `ok` (validator passed) | `exhausted` (attempts spent, still `defects-found`) | `unavailable` (no vendor present)
- `VENDOR_SEQUENCE` = comma-separated vendors attempted, in order
- `ATTEMPTS` = integer attempts made
- `FIXED_BY` = vendor that produced the passing plan, or empty
- `FINAL_VALIDATE_STATUS` = last `VALIDATE_STATUS` observed

Exit `0` on every loop outcome (status is in the KVs); exit `2` only on argv/setup errors.

## Orchestrator handoff

The shared handler runs this helper, parses `AUTOFIX_STATUS`. On `ok`, continue the success path (validation now passes) and append a `Warnings` entry recording the auto-correction (vendor + defect count). On `exhausted` / `unavailable`, fall through to the existing `Fix-and-retry` / `Override` / `Cancel` `AskUserQuestion`. **A `Warnings` entry is always logged whenever defects occurred**, even when auto-corrected (operator decision 6 on #3628).

## Edit in sync

Update together: `skills/design/SKILL.md` **### Plan command validator failure (shared)**, `skills/design/references/flags.md` (plan-command validator section), `skills/design/scripts/test-auto-fix-plan-commands.sh`, `Makefile` (`test-auto-fix-plan-commands` target), and `SECURITY.md` (the auto-fix agent reads the plan + validator log and edits the plan file; covered by the existing external-reviewer outbound-redaction posture — the fix prompt redacts the validator log via `redact-secrets.sh`).

## External-binary verification

The live Codex/Cursor dispatch reuses already-verified `launch-codex-exec.sh` / `run-external-agent.sh` argv shapes (per `.claude/rules/external-tool-launcher-parity.md`). The end-to-end live cross-vendor fix path is exercised only against real vendors; the offline harness covers loop/alternation/re-validation/KV logic through the dispatch seam. Live verification belongs to CI / manual runs.

## Harness

`skills/design/scripts/test-auto-fix-plan-commands.sh` (Makefile target: `test-auto-fix-plan-commands`).
