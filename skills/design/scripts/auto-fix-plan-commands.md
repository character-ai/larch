# auto-fix-plan-commands.sh

**Consumer**: `/design` shared **### Plan command validator failure (shared)** handler in `SKILL.md` (Step 2b, Gate B / Step 3.5, discussion-round2, Step 5c).

**Contract**: cross-vendor auto-repair loop for plan-command validator defects (#3628 Component D). On `VALIDATE_STATUS=defects-found`, the shared handler calls this helper **before** escalating to the operator. It spawns an external vendor (Codex/Cursor) to edit the target plan file in place, re-validates with durable diagnostics, and alternates vendors across bounded attempts capped to the number of available vendors. The operator `Fix-and-retry` / `Override` / `Cancel` prompt fires only when this helper returns `exhausted` or `unavailable`.

**When to load**: before wiring the shared validator handler's auto-repair step, or when editing the helper.

## Argv

| Flag | Required | Notes |
|------|----------|-------|
| `--design-tmpdir DIR` | yes | Validated via `larch_design_tmpdir_validate`; exported so the validator seam resolves the log path |
| `--plan-file PATH` | yes | Target file the validator flagged (`plan.txt` or `composed-plan.md`); must be an existing non-symlink file under `--design-tmpdir` |
| `--codex-present true\|false` | yes | Step 0 Codex presence/health probe result |
| `--cursor-present true\|false` | yes | Step 0 Cursor presence/health probe result |
| `--codex-available true\|false` | no | Degraded-tools availability flag. Defaults to `--codex-present` for backward-compatible harness callers |
| `--cursor-available true\|false` | no | Degraded-tools availability flag. Defaults to `--cursor-present` for backward-compatible harness callers |
| `--repo-root DIR` | no | Consumer repo root for Tier 3 validator command resolution and dirty-tree snapshots; callers should pass the same repo root used by the initial validation. Defaults to the current worktree root, then the plugin root |
| `--max-attempts N` | no | Positive integer; default `2` (one fix attempt per vendor) |
| `--site STR` | no | Diagnostic label only |
| `--timeout SECS` | no | Per-vendor launcher timeout; default `1800` |

## Vendor attribution / alternation

"The vendor that introduced the defect" is not attributable — plan text is applied by the orchestrator from mixed-vendor findings — so the pragmatic default is **cross-vendor alternation**: attempt 1 = Codex (when present and available) else Cursor; attempt 2 = the other vendor. With `--max-attempts 2` and both vendors available, each vendor gets exactly one attempt. Unavailable vendors are dropped from the order, and `--max-attempts` is clamped to the resulting vendor count so a single-vendor run cannot burn duplicate attempts on the same tool; with neither available the helper returns `AUTOFIX_STATUS=unavailable` without dispatching.

## Dispatch reuse

Reuses the verified launcher primitives (same argv grammar as `scripts/lint-fix-loop.sh`):

- **Codex** → `scripts/launch-codex-exec.sh --workdir "$DESIGN_TMPDIR" --add-dir "$DESIGN_TMPDIR" --prompt-file … --usage-label codex_plan_autofix --timing-task-kind codex-plan-autofix` (parses `LAUNCHER_EXIT`).
- **Cursor** → `scripts/run-external-agent.sh --tool cursor --capture-stdout -- cursor agent -p --trust ${MODEL_ARGS} --workspace "$DESIGN_TMPDIR" "<wrapped-prompt>"` with `lib-cursor-launcher-common.sh` model/auth/serial-lock glue and `cursor-wrap-prompt.sh`; the helper records a best-effort `cursor-plan-autofix` timing row around this dispatch.

The agent edits the plan file IN PLACE; `revalidate()` (re-running `validate-plan.sh`) is the authoritative success signal, not the launcher exit code. Nonzero launcher exits, repository dirty-tree deltas, failed non-target `$DESIGN_TMPDIR` restoration, and optional-trailer guard failures are treated as failed attempts and cannot be converted into success by a passing revalidation. Non-target tmpdir mutations that restore cleanly do not fail an otherwise valid target-file fix. The fix prompt wraps the plan content and validator log as **untrusted data** (trust-boundary preserved) and instructs minimal, defect-only edits preserving plan prose, structure, and the trailing metadata block. The helper copies the original validator log to a site/target-specific `plan-autofix/original-validate-plan-commands-*.log` before revalidation can overwrite the live log; if `redact secrets` fails while rendering the prompt, the raw validator log is withheld and a fixed placeholder is included instead. Each revalidation writes `attempt-*/revalidate.log`; validator infrastructure failures stop the loop immediately and emit that path as `REVALIDATE_LOG_FILE`.

## Mutation guards

Before each dispatch the helper snapshots the target file, all non-target regular files/directories except `plan-autofix/**`, and the repository dirty-tree status/content under `--repo-root`. Symlinks and special files in the guarded tmpdir surface fail closed. After dispatch it restores any non-target session changes, rejects repo dirty-tree status or content changes introduced by the vendor, then runs a fresh per-attempt optional-trailer snapshot/dedup cycle for `plan.txt` targets before revalidation. Failed attempts restore the target file to its pre-attempt bytes so later attempts and operator prompts never inherit unvalidated vendor edits. This makes auto-fix a target-file-only repair path; logs and prompts remain confined to `plan-autofix/**`.

## Hermetic seams

- `LARCH_AUTOFIX_VALIDATE_PLAN_SH` — default `validate-plan.sh`; re-validation driver.
- `LARCH_AUTOFIX_LAUNCH_CODEX_EXEC_SH` — default `scripts/launch-codex-exec.sh`.
- `LARCH_AUTOFIX_RUN_EXTERNAL_AGENT_SH` — default `scripts/run-external-agent.sh`.
- `LARCH_AUTOFIX_GATE_B_DEDUP_PLAN_SH` — default `gate-b-dedup-plan.sh`; optional-trailer snapshot/dedup guard for `plan.txt`.
- `LARCH_AUTOFIX_DISPATCH_SH` — full per-vendor dispatch override (`--vendor`, `--run-dir`, `--prompt-file`, `--plan-file`, `--design-tmpdir`); replaces the real launcher path so the harness simulates a vendor edit deterministically.

## Machine output (FD 3 KVs)

- `AUTOFIX_STATUS` = `ok` (validator passed) | `exhausted` (attempts spent or stopped on validator infrastructure failure) | `unavailable` (no vendor present)
- `VENDOR_SEQUENCE` = comma-separated vendors attempted, in order
- `ATTEMPTS` = integer attempts made
- `FIXED_BY` = vendor that produced the passing plan, or empty
- `FINAL_VALIDATE_STATUS` = last `VALIDATE_STATUS` observed
- `ORIGINAL_VALIDATE_LOG_FILE` = preserved original validator evidence copied before revalidation, when available
- `REVALIDATE_LOG_FILE` = durable revalidation stdout/stderr when validator infrastructure failed

Exit `0` on every loop outcome (status is in the KVs); exit `2` only on argv/setup errors.

## Orchestrator handoff

The shared handler runs this helper once per site/target/evidence cycle using a durable `.plan-command-autofix-*.attempted` sentinel, parses `AUTOFIX_STATUS`, and treats nonzero helper exits or missing/unknown status as `failed`. On `ok`, continue the success path (validation now passes) and append a `Warnings` entry recording the auto-correction (vendor + defect count) using `ORIGINAL_VALIDATE_LOG_FILE` where present. On `exhausted` / `unavailable` / `failed` / `skipped-cycle-cap`, fall through to the existing `Fix-and-retry` / `Override` / `Cancel` `AskUserQuestion`. **A `Warnings` entry is always logged whenever defects occurred**, even when auto-corrected (operator decision 6 on #3628).

## Edit in sync

Update together: `skills/design/SKILL.md` **### Plan command validator failure (shared)**, `skills/design/references/flags.md` (plan-command validator section), `skills/design/scripts/test-auto-fix-plan-commands.sh`, `Makefile` (`test-auto-fix-plan-commands` target), and `SECURITY.md` (the auto-fix agent reads the plan + validator log and edits the plan file; covered by the existing external-reviewer outbound-redaction posture — the fix prompt redacts the validator log via `redact secrets`).

## External-binary verification

The live Codex/Cursor dispatch reuses already-verified `launch-codex-exec.sh` / `run-external-agent.sh` argv shapes (per `.claude/rules/external-tool-launcher-parity.md`). The offline harness covers loop/alternation/re-validation/KV logic through the full dispatch seam (`LARCH_AUTOFIX_DISPATCH_SH`) and also exercises the per-vendor exit-parsing code paths via the narrower `LARCH_AUTOFIX_LAUNCH_CODEX_EXEC_SH` and `LARCH_AUTOFIX_RUN_EXTERNAL_AGENT_SH` seams (with stubbed cursor libs via `CLAUDE_PLUGIN_ROOT`). Full end-to-end live cross-vendor fix paths require real vendors; live verification belongs to CI / manual runs.

## Harness

`skills/design/scripts/test-auto-fix-plan-commands.sh` (Makefile target: `test-auto-fix-plan-commands`).
