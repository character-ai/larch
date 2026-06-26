## Goal
Implement issue #5518: [IMPLEMENTING] [BUG] Cursor plan-review slots return fake-clean no_issues_found: two root causes (plan file outside workspace + silent auth-preflight token-read drop).

## Implementation Plan
## Summary

During a `/design` plan review, all five Cursor plan-review slots returned `{"no_issues_found": true}` with 25–123 byte canned responses (one-line preamble + sentinel, no tool calls), were recorded as `STATUS=OK, EXIT_CODE=0`, and the panel resolved `LOOP_STATUS=zero-findings-degraded-panel` → `NEXT_ACTION=step3b`. A completely un-reviewed plan looked clean and proceeded to Gate C.

This issue combines two **distinct root causes** for that same failure. Either one alone produces a fake-clean Cursor slot; both were observed together in the same run. Fixing one does not fix the other, so both are tracked here as separate work items, plus a shared collector-side safety net that backstops both.

Combined from #5507 (plan file outside Cursor workspace) and #5508 (split-step auth preflight silently drops token read).

## Shared observed symptom

- Five Cursor slots (`arch`, `innovation`, `pragmatic`, `requirements`, `dyn-wire-format-regression`) each returned `{"no_issues_found": true}` with minimal output. Response sizes: arch=101 bytes, innovation=102, pragmatic=25 (sentinel only), requirements=123, dyn-wire-format-regression=128.
- `launch-stderr` pattern: `❌ cursor agent: FAILED (exit code 1, output 0 bytes)` → `⏳ still running (1m elapsed)` → `✓ cursor agent: completed (exit code 0, output ~420 bytes)`.
- Sidecar history for failing slots shows two error patterns: `Error: Password not found for account 'cursor-user' and service 'cursor-access-token'` and `Error: Security command failed: Security process exited with code: 45`.
- All Cursor slots recorded `STATUS=OK, EXIT_CODE=0` in `collector-results.env` despite first-attempt failures.
- No `.sidecar.history` tool-call evidence for any Cursor slot that reached exit 0. By contrast, `codex-primary-plan-arch-output.txt.events.jsonl` shows 84 events including explicit `sed` reads of `plan.txt` — Codex read the plan; Cursor did not.

---

## Work item 1: Plan file lives outside the Cursor workspace (from #5507)

### Root cause

The review prompt instructs Cursor to review the plan file at `$DESIGN_TMPDIR/plan.txt`, where `$DESIGN_TMPDIR` is under `~/.cache/larch/sessions/`. Cursor is launched with `--workspace /path/to/repo`, which does **not** include the cache directory. Cursor cannot read the plan file and returns a canned sentinel without flagging the failure.

### Evidence

- Cursor `CMD_JSON` in `.meta`: `--workspace /Users/<user>/larch3` — the cache directory is not in scope.
- Cursor JSON `.result` for arch: `Reviewing the plan and tracing the cited code paths for contract alignment.\n{"no_issues_found": true}` (101 chars).
- `codex-primary-plan-arch-output.txt.events.jsonl`: 84 events with explicit `sed` reads of `plan.txt`, `stall_recovery.py`, `test_stall_recovery.py` — Codex DID read the plan; Cursor did not.

### Affected files

- Prompt rendering for plan-review (in `python/` or `skills/design/references/`): plan file path is referenced as an absolute path that may be outside the Cursor workspace.
- `python/agents.py`: `launch_review` (around line 4882) — Cursor review-slot launch arguments.

### Suggested fix(es)

1. Include `--add-dir "$DESIGN_TMPDIR"` in the Cursor plan-review launch (analogous to how Codex uses `--add-dir` for the round subdirectory). **Assess** the parity rule in `.claude/rules/external-tool-launcher-parity.md`, which documents Codex/Cursor intentional asymmetry here — any change must reconcile with that rule.
2. Alternatively, inline the plan content into the Cursor prompt instead of referencing a file path, avoiding the workspace-scope issue entirely.

### Open questions

- Is the Codex `--add-dir "$SESSION_TMPDIR/plan-review/round-N"` intentionally limited to the round subdirectory (excluding the parent `$DESIGN_TMPDIR`)? If so, why not add the parent?
- Does the parity rule in `.claude/rules/external-tool-launcher-parity.md` intentionally forbid `--add-dir` for Cursor? If so, option 2 (inline plan content) is the only path.

---

## Work item 2: Split-step auth preflight passes existence check but silently drops the token read (from #5508)

### Root cause

The preflight and the token-read are split into two separate `security` invocations:

1. `cursor_auth_preflight` (line 644): `security find-generic-password -a cursor-user -s cursor-access-token` — checks entry **existence** only. On macOS, access-controlled entries may report existence but deny the `-w` read without UI interaction.
2. `cursor_preread_service_token` (line 684): `security find-generic-password ... -w` — reads the **actual** token. On failure (`returncode != 0`), `token = ""` silently and `CURSOR_API_KEY` is not set.

So the preflight passes the existence check → reports `ok=True` → Cursor launches without credentials → Cursor's own internal auth reads the same keychain entry directly → fails because of access-control restriction or non-interactive session (e.g. `errSecInteractionNotAllowed`, security exit code 45) → exit code 1, 0 bytes. The preflight reports green while the token is unreadable.

### Evidence

- `python/agents.py` line 644: preflight uses `find-generic-password` without `-w` — exits 0 if the entry exists, regardless of readability.
- `python/agents.py` line 684: `cursor_preread_service_token` uses `find-generic-password ... -w`; on non-zero exit, `token = ""` silently.
- `cursor_auth_preflight` returns `AuthVerdict(ok=True, rc=0)` while the `-w` read fails.
- `collector-results.env`: all Cursor slots record `STATUS=OK, EXIT_CODE=0` despite first-attempt auth failures.

### Affected files

- `python/agents.py`: `cursor_auth_preflight` (line 615) and `cursor_preread_service_token` (line 669) — split-step auth check where the existence pass and the token-read failure do not propagate.
- `python/test_agents.py`: auth preflight test coverage may not cover the split-step failure mode (existence passes, read fails).

### Suggested fix(es)

1. Merge the existence check and read in `cursor_auth_preflight`: attempt the `-w` read directly in the preflight. If the read fails (any non-zero exit), return `AuthVerdict(ok=False, rc=2)`. This makes the preflight fail closed when the token is unreadable.
2. Surface `cursor_preread_service_token` failures: log a warning and abort the Cursor slot when the token read fails. Do not silently proceed with an empty `CURSOR_API_KEY`.

### Open questions

- Is the split between `cursor_auth_preflight` and `cursor_preread_service_token` intentional? If so, what motivates keeping them separate, and should preread be folded into preflight entirely?
- Does macOS `errSecInteractionNotAllowed` (security code 45) consistently cause `find-generic-password` (without `-w`) to return 0 while `-w` returns non-zero? Which macOS version introduced this behavior?

---

## Work item 3: Collector treats canned, tool-call-free responses as clean (shared backstop, from #5507 and #5508)

Both root causes reach the same gap: a Cursor slot that auth-succeeds on retry but cannot do real review still returns a sub-200-byte preamble + sentinel, and the collector records `STATUS=OK` with zero findings. This is the safety net that makes either root cause silent.

### Root cause

The `_review_write_preflight_bundle` path correctly records a failure when `cursor_auth_preflight` fails **before** launch. But when auth/access fails **inside** the Cursor process (not in the Python preflight), the retry can produce a zero-finding OK result that bypasses degraded-panel detection. The collector does not validate response size or the presence of tool calls.

### Affected files

- `python/plan_review.py`: collector result parsing and degraded-panel detection — does not validate response size or presence of tool calls.
- `python/agents.py`: `launch_review` retry logic for Cursor review slots.

### Suggested fix(es)

1. Add a minimum-response-size check in the collector: if a Cursor slot returns fewer than N bytes (e.g. 200) and/or shows no tool-call evidence, treat it as a degraded slot rather than a clean no-findings result.
2. Detect in-process auth failure in the retry logic: when a Cursor first attempt exits with code 1 and 0 bytes, check the sidecar for auth-related error patterns before re-launching. If auth is the cause, mark the slot degraded instead of retrying into a canned response.

### Open questions

- What is the minimum response size below which a Cursor slot should be considered degraded?
- Should a tool-call-free Cursor response always be treated as degraded for plan review, independent of size?

---

*Combined from #5507 and #5508. Both source issues describe the same `/design` plan-review incident; this issue preserves both distinct root causes and both fix sets so they can be designed and implemented as one unit.*

## Test plan
(no test plan section in plan-file)
