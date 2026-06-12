# Rebase checkpoint routing

**Consumer**: `/implement` orchestrator.
**Contract**: exit-code and stdout-KV routing for `scripts/rebase-checkpoint-probe.sh` and the Step 7a wrapper relay.
**When to load**: **MANDATORY — READ ENTIRE FILE** before branching on any rebase checkpoint wrapper result.

**Absorbed Step 1.r.** For checkpoint `1.r`, the orchestrator receives the rebase result from the Step 0 bootstrap envelope (`ROUTE=`, `REBASE_RC=`, and related keys), not a standalone probe process. Load this reference for Step 1.r only when `ROUTE` is `conflict`, `bail`, missing, or malformed. Do **not** treat missing `ROUTE` as rebase failure when `DEGRADED_PROMPT_REQUIRED=true`. Steps `4.r`, `7.r`, and `7a.r` still use direct foreground probe fences per the call-site registry below.

**Orchestrator contract — parse the wrapper stdout** (token-aware KV scan; multiple `KEY=value` tokens per line allowed — mirror Step 5-style parsing):

1. Run the foreground `rebase-checkpoint-probe.sh` invocation and capture its stdout as the contract stream (stderr is normally empty; FINDING_1 combined-stream rules live in `scripts/rebase-checkpoint-probe.md`). For `7a.r`, the direct foreground call is `skills/implement/scripts/step-7a.sh`, which invokes the probe internally and re-emits the probe stdout before its final KV tail; the orchestrator must branch on the wrapper's process exit code plus the relayed `REBASE_*` keys, not on a separate probe fence.
2. Branch on the process exit code **and** `REBASE_OUTCOME=` / `REBASE_ERROR=` / `CONFLICT_FILES=` keys emitted on stdout:
   - **Exit 1 (`REBASE_OUTCOME=conflict`)** — print `🔃 <step-prefix>: <short-name> | rebase — conflict detected, invoking Conflict Resolution Procedure (caller_kind=early_rebase)`. Parse `CONFLICT_FILES=<comma-separated list>` from the captured stdout; `--keep-on-conflict` leaves the rebase in progress so this list is authoritative for Phase 1. (If the line is missing — defensive only — fall back to `git diff --name-only --diff-filter=U` to enumerate the in-progress rebase's unmerged paths.) **MANDATORY — READ ENTIRE FILE** before executing the Conflict Resolution Procedure: `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/conflict-resolution.md`. Invoke the Conflict Resolution Procedure with `caller_kind=early_rebase` and the parsed `CONFLICT_FILES`. On success, continue. On hard failure, the procedure runs `${CLAUDE_PLUGIN_ROOT}/scripts/git-rebase-abort.sh`, sets `STALL_TRACKING=true` (signals Step 18 teardown's title-prefix terminal transition to rename the tracking issue to `[STALLED]`), and skips to Step 18.
   - **Exit 3 (`REBASE_OUTCOME=failed`)** — read `REBASE_ERROR=...` from the same stdout capture. If the value begins with `unexpected-rc-` (FINDING_9 prefix — non-1/3 non-zero exits rewritten by the wrapper), print `**⚠ Rebase onto main failed unexpectedly (exit $rc). Bailing to cleanup.**` (derive the numeric exit token from the suffix after `unexpected-rc-` when present; otherwise use the process exit code), set `STALL_TRACKING=true`, and skip to Step 18. **Otherwise** (non-conflict rebase failure — fetch error, detached HEAD, etc.): print `**⚠ Rebase onto main failed (non-conflict): $REBASE_ERROR. Bailing to cleanup.**`, set `STALL_TRACKING=true`, and skip to Step 18.
   - **Other non-zero exit** — the wrapper emits `REBASE_OUTCOME=failed` + `REBASE_ERROR=unexpected-rc-<n>` then re-exits with the original code: print `**⚠ Rebase onto main failed unexpectedly (exit $rc). Bailing to cleanup.**`, set `STALL_TRACKING=true`, and skip to Step 18 (same bail copy as the `unexpected-rc-` branch — parse the suffix after `unexpected-rc-` from `REBASE_ERROR` when present).
   - **Exit 0 (`REBASE_OUTCOME=ok` or `skipped`)** — on the captured stdout, check `SKIPPED_ALREADY_PUSHED=true` **before** `SKIPPED_ALREADY_FRESH=true` (wrapper preserves `rebase-push.sh` precedence). If either skip marker is present, silently continue; otherwise continue. Phantom tail KVs (`PHANTOM_*`) may trail on the same stream — treat them as advisory per the **Phantom Untracked Probe** pointer (`PHANTOM_APPEND_WARN_ERROR` is already surfaced by the wrapper when warn-append fails).

**STALL_TRACKING**: the wrapper does **not** set `STALL_TRACKING`; the orchestrator sets it only on the bail branches above.

**Call-site registry** (the four authorized instantiations; `scripts/test-implement-rebase-macro.sh` pins these rows):

| Step | `<step-prefix>` | `<short-name>`   |
|------|-----------------|------------------|
| 1.r  | `1.r`           | `plan materialization` |
| 4.r  | `4.r`           | `commit (impl)`  |
| 7.r  | `7.r`           | `commit (review)`|
| 7a.r | `7a.r`          | `diagrams`       |

For `7a.r`, the registry row is reached via `step-7a.sh`, not a standalone probe fence. The orchestrator must branch on `step-7a.sh`'s process exit code plus the relayed `REBASE_*` keys, and the helper only runs the pre-ship log flush after wrapper-visible `REBASE_OUTCOME=ok|skipped`.
