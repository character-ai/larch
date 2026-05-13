## Goal

Stop /implement runs from cross-contaminating each other's timing data and from inheriting stale test-harness fixtures. Cleanup stale shared TSVs already on disk.

## Goal

Stop `/implement` runs from cross-contaminating each other's timing data and from inheriting stale test-harness fixtures, so the committed `timing-report.md` for a PR reflects only that PR's actual work. Also clean the stale ledgers already on disk.

## Background (verified during investigation)

1. `scripts/timing-ledger.sh` `resolve_ledger_path` priority is:
   (a) `--ledger` arg → (b) `$LARCH_TIMING_LEDGER` env (must validate under allowed roots) → (c) `$IMPLEMENT_TMPDIR/timing-ledger.tsv` (if `$IMPLEMENT_TMPDIR` env set + dir exists) → (d) `dirname($SESSION_ENV_PATH)/timing-ledger.tsv` → (e) `$DESIGN_TMPDIR/...` → (f) `$REVIEW_TMPDIR/...` → (g) default `$TMPDIR/larch-timing-<sha256(pwd)>.tsv`.
2. `skills/implement/SKILL.md:205` exports `LARCH_TIMING_LEDGER` only in Step 0's Bash block. Subsequent Bash blocks (21 sites: 247, 381, 671, 919, 1063, 1083, 1114, 1278, 1316, 1347, 1432, 1501, 1517, 1543, 1560, 1576, 1627) rehydrate ONLY `LARCH_TOKEN_SESSION_ID` and `LARCH_CLAUDE_SOURCE_FILE`. Each Bash invocation is a fresh process, so `LARCH_TIMING_LEDGER` is unset, AND `IMPLEMENT_TMPDIR` is unset in env (the orchestrator substitutes `$IMPLEMENT_TMPDIR` in command argv at compose time but does not export it).
3. Resolver therefore falls through to (g) — the cwd-hashed shared TSV — and every `/implement` run from a given clone writes its post-Step-0 telemetry to the same physical file. `scripts/timing-report.sh` aggregates the whole TSV with no session/timestamp filter (`timing-report.sh:240-258`), so every report includes every prior run plus any pre-`fbd84e7` test-harness fixtures still sitting there.
4. Test harnesses (`skills/implement/scripts/test-{codex,cursor,gemini}-implementer.sh`) export their own per-test `LARCH_TIMING_LEDGER` since commit `fbd84e7` (2026-05-12) — they no longer leak. Stale rows from before that fix are still in the default-cwd TSVs.

## Implementation Plan

### Change 1 — `skills/implement/SKILL.md` rehydration template

In every post-Step-0 rehydration block (17 sites grep-counted), add a third key alongside the existing two. Replace each occurrence of the literal sequence:

```bash
LARCH_TOKEN_SESSION_ID=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TOKEN_SESSION_ID --default "")
LARCH_CLAUDE_SOURCE_FILE=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_CLAUDE_SOURCE_FILE --default "")
export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE
```

with:

```bash
LARCH_TOKEN_SESSION_ID=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TOKEN_SESSION_ID --default "")
LARCH_CLAUDE_SOURCE_FILE=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_CLAUDE_SOURCE_FILE --default "")
LARCH_TIMING_LEDGER=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TIMING_LEDGER --default "")
export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE LARCH_TIMING_LEDGER
```

Use a single `Edit` with `replace_all=true` so all 17 sites change in one operation. The rehydration value comes from `session-env.sh`, which Step 0 already writes via `write-session-env.sh --timing-ledger "$IMPLEMENT_TMPDIR/timing-ledger.tsv"`.

Also update the prose at SKILL.md:242 from:

> Every Bash block after Step 0 that touches `token-ledger.sh` or `token-report.sh` MUST rehydrate `LARCH_TOKEN_SESSION_ID` and `LARCH_CLAUDE_SOURCE_FILE` …

to:

> Every Bash block after Step 0 that touches `token-ledger.sh` / `token-report.sh` / `timing-ledger.sh` / `timing-report.sh` MUST rehydrate `LARCH_TOKEN_SESSION_ID`, `LARCH_CLAUDE_SOURCE_FILE`, AND `LARCH_TIMING_LEDGER` …

And widen the followup example block at SKILL.md:244-248 to include the third read+export.

### Change 2 — Regression test

Add `scripts/test-implement-timing-rehydration.sh` (+ sibling `.md` per `.claude/rules/script-md-siblings.md`) that asserts the rehydration template invariant on `skills/implement/SKILL.md`:

- `^export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE$` (old pattern) → expect 0 matches.
- `^export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE LARCH_TIMING_LEDGER$` (new pattern) → expect ≥ 17 matches.
- Plus a positive cross-check: count of `LARCH_TIMING_LEDGER=$(... read-session-env-key.sh ... --key LARCH_TIMING_LEDGER` lines equals the count of `LARCH_TOKEN_SESSION_ID=$(... --key LARCH_TOKEN_SESSION_ID` lines.

The test runs from the repo root, exits 0 on pass, exits 1 on fail with a clear diagnostic. Wired into CI via the existing `agent-lint` / pre-commit pathway (sibling tests in `scripts/test-implement-*.sh` already run as part of `make test-agent-lint`).

### Change 3 — Wipe the stale shared ledgers (manual, in-run)

`rm -f /var/folders/dw/.../T/larch-timing-*.tsv*` and `rm -f /var/folders/dw/.../T/larch-tokens-*.jsonl*` (token files share the same default-cwd-hash mechanism for the close-of-Step-18 capping mark; pre-`fbd84e7` leakage there is also stale). Print a count line for the audit trail.

This is a one-time housekeeping action performed inside the run, not a committed code change.

## Files to modify

- `skills/implement/SKILL.md` (17 rehydration sites + ~3 prose lines)
- `scripts/test-implement-timing-rehydration.sh` (new)
- `scripts/test-implement-timing-rehydration.md` (new, per sibling-doc rule)
- Optional touch: `docs/configuration-and-permissions.md` if it documents the rehydration contract — verify before edit.

## Edge cases

- **`design-only=true` / quick-mode** paths: rehydration sites cover both. No special-casing.
- **`/design` and `/review`** SKILL.md files already forward `SESSION_ENV_PATH` to the ledger calls (`SESSION_ENV_PATH="$SESSION_ENV_PATH" ... timing-ledger.sh mark ...`) and the resolver step (d) (`dirname(SESSION_ENV_PATH)/timing-ledger.tsv`) routes them to the same per-run TSV via the directory containing `session-env.sh`. No change needed there.
- **Token ledger** (`larch-tokens-<pwd-hash>.jsonl`): the closing Step-18 mark is intentionally written to the pwd-hash fallback per SKILL.md:1632 — keep that behavior; just stop the mid-run timing leakage, which is what the user complained about.
- **`validate_env_ledger`**: must accept `$IMPLEMENT_TMPDIR/timing-ledger.tsv` even when `IMPLEMENT_TMPDIR` env isn't set in the rehydrated Bash block. Since `LARCH_TIMING_LEDGER`'s value is the same canonical path Step 0 wrote, and `IMPLEMENT_TMPDIR` is included in `timing_allowed_roots()` iff env-set — to make validation always succeed, the rehydration block should ALSO export `IMPLEMENT_TMPDIR` when it isn't already in env. Approach: prepend `IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR:-<literal path>}"` is not needed because the orchestrator already substitutes `$IMPLEMENT_TMPDIR` at compose time. Simpler: change every rehydration block to also `export IMPLEMENT_TMPDIR`. Concretely, add the line `export IMPLEMENT_TMPDIR` to the rehydration template so the env var is re-exported into the child process at every step.

Adjusted rehydration template (final form):

```bash
export IMPLEMENT_TMPDIR
LARCH_TOKEN_SESSION_ID=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TOKEN_SESSION_ID --default "")
LARCH_CLAUDE_SOURCE_FILE=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_CLAUDE_SOURCE_FILE --default "")
LARCH_TIMING_LEDGER=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TIMING_LEDGER --default "")
export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE LARCH_TIMING_LEDGER
```

`export IMPLEMENT_TMPDIR` is safe: if the var is already exported, it's a no-op; if it's unset, the export creates a null-valued env var which the orchestrator then assigns the literal path in subsequent argv expansion (this is how it works today — the next `read-session-env-key.sh --file "$IMPLEMENT_TMPDIR/..."` invocation has its `$IMPLEMENT_TMPDIR` substituted by the orchestrator, so the script receives the literal path even though env is empty). What `export IMPLEMENT_TMPDIR` does is mark the (orchestrator-set, when applicable) variable as exportable so child processes like `timing-ledger.sh` see it.

Actually simpler: pass the literal path via orchestrator substitution to a `IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR"; export IMPLEMENT_TMPDIR` line, OR rely on the fact that `LARCH_TIMING_LEDGER` rehydration alone is sufficient because `validate_env_ledger` consults `timing_allowed_roots`, which includes the canonical TMPDIR root. `$IMPLEMENT_TMPDIR/timing-ledger.tsv` is at `~/.cache/larch/sessions/...`, NOT under TMPDIR. So the path will not validate against the TMPDIR root, and IMPLEMENT_TMPDIR must be in env for validation. Conclusion: BOTH `LARCH_TIMING_LEDGER` AND `IMPLEMENT_TMPDIR` need to be in env.

The orchestrator already substitutes `$IMPLEMENT_TMPDIR` to the literal path at compose time, so the rehydration block writes literal-path commands. To export the env var, the block needs an explicit `IMPLEMENT_TMPDIR=<literal>; export IMPLEMENT_TMPDIR` line OR `export IMPLEMENT_TMPDIR=<literal>`. The literal path comes from the orchestrator's substitution of `$IMPLEMENT_TMPDIR` — so the SKILL.md template can just say `export IMPLEMENT_TMPDIR` and let the orchestrator's earlier `$IMPLEMENT_TMPDIR` substitution provide the value. But that only works if `IMPLEMENT_TMPDIR` was assigned in this same Bash invocation… it wasn't.

**Simpler concrete fix**: use `IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR"; export IMPLEMENT_TMPDIR` in the template. The orchestrator substitutes `$IMPLEMENT_TMPDIR` to the literal path before sending, so Bash receives `IMPLEMENT_TMPDIR="/Users/.../claude-implement-larch3-XYZ"; export IMPLEMENT_TMPDIR` — that works.

Final template:

```bash
IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR"
export IMPLEMENT_TMPDIR
LARCH_TOKEN_SESSION_ID=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TOKEN_SESSION_ID --default "")
LARCH_CLAUDE_SOURCE_FILE=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_CLAUDE_SOURCE_FILE --default "")
LARCH_TIMING_LEDGER=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TIMING_LEDGER --default "")
export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE LARCH_TIMING_LEDGER
```

## Test plan

- After Change 1, run `bash scripts/test-implement-timing-rehydration.sh` → assertion passes.
- Run `bash skills/implement/scripts/test-step2-dispatch.sh` (existing) → still passes.
- Run `bash skills/implement/scripts/test-{codex,cursor,gemini}-implementer.sh` → no `cursor-implement` / `gemini-implement` rows leak into the default-cwd TSV (verifiable by checking byte count before/after).
- Run `make test-agent-lint` (or `bash scripts/agent-lint.sh`) → still clean.
- Run `/relevant-checks` per AGENTS.md → clean.

## Verification (manual checks during this run)

- Before code change, count `cursor-implement`/`gemini-implement` rows in the current larch3 default TSV → record.
- After cleanup, the file is gone.
- After Step 4 commit, run `bash scripts/test-implement-timing-rehydration.sh` from the working tree → exits 0.

## Out of scope

- Per-run isolation of the TOKEN ledger (`larch-tokens-<pwd-hash>.jsonl`): SKILL.md:1632 documents the deliberate pwd-hash landing site for the closing mark; redesigning the token ledger is its own change.
- Adding a session-id filter to `timing-report.sh`: not needed once writes are isolated per run.

## Test plan

- New harness `scripts/test-implement-timing-rehydration.sh` asserts SKILL.md rehydration blocks include LARCH_TIMING_LEDGER.
- Existing implementer test harnesses still pass and do not leak into default-cwd TSV.
- /relevant-checks passes on the diff.
