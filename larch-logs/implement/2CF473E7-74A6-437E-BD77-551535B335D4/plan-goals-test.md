## Goal
Create flush-execution-issues.sh helper with shared lib extraction, test harness, and SKILL.md Step 11 one-line reduction

## Implementation Plan
# Implementation Plan: flush-execution-issues.sh Helper

## Context

`implement-finalize.sh` currently contains `normalize_body_for_hash`,
`write_execution_issues_records`, `sha256_file`, `sha256_stream`, and
`json_escape_stream_python` as internal functions. Because `implement-finalize.sh`
ends with `main "$@"`, it cannot be sourced safely. To share these functions
without reimplementation, they must be extracted to a new shared library
`scripts/lib-execution-issues.sh`. Both `implement-finalize.sh` and the new
`flush-execution-issues.sh` will source this library.

**Post-CI trigger timing decision (Option 2):** Run flush BEFORE Step 7a's
pre-bump log-flush. Drop the `CI_PASSED=true` post-CI execution-issues
checkpoint entirely. Rationale: committing or appending log batches after green
CI either validates a different tree or creates an "audit log changed post-CI"
smell. Pre-bump keeps the NDJSON record settled inside the same PR commit that
CI tests, and the teardown safety-net in `implement-finalize.sh` teardown
continues to cover stalled/failed runs that never reach the bump.

---

## Step 1: Create `scripts/lib-execution-issues.sh`

Extract from `scripts/implement-finalize.sh` into `scripts/lib-execution-issues.sh`:
- `sha256_file()`
- `sha256_stream()`
- `normalize_body_for_hash()`
- `json_escape_stream_python()`
- `write_execution_issues_records()`

The library begins with `#!/usr/bin/env bash` shebang but is sourced-only
(no `main` or top-level invocation). Add `set -uo pipefail` but NOT `set -e`,
matching the best-effort error model inherited from `implement-finalize.sh`.

**warn_line shim:** The library must NOT assume `warn_line` is provided by the
caller (it is defined locally in `implement-finalize.sh`, not by `lib-quiet.sh`).
Add a library-local shim:
```bash
_lib_warn_line() { larch_err "lib-execution-issues: $*" || true; }
```
Replace all `warn_line` calls in `write_execution_issues_records` with
`_lib_warn_line`.

**set -e leakage fix:** In `write_execution_issues_records`, the python fallback
path currently runs `set +e` before the python call then `set -e` after it
unconditionally. Fix by saving and restoring the caller's errexit state:
```bash
local _old_opts
_old_opts=$(set +o)          # capture current shell options
set +e
if body_json=$(json_escape_stream_python < "$input_file"); then
  ...
fi
eval "$_old_opts"            # restore (may re-enable errexit if caller had it)
```
Alternatively, restructure with an `if` assignment to avoid option toggling
entirely.

**step/source parameterization:** Add two optional parameters to
`write_execution_issues_records`:
- `step_label` (default `"18"`)
- `source_label` (default `"execution-issues.md safety-net"`)

Callers that want pre-bump records should pass `step_label="7a"` and
`source_label="execution-issues.md pre-bump"`.

Add `# shellcheck source=scripts/lib-quiet.sh` annotation and source
`lib-quiet.sh` for the `larch_err`/`emit`/`emit_kv` functions used internally.

Add companion `scripts/lib-execution-issues.md` (stub pointing to the primary
`skills/implement/scripts/flush-execution-issues.md` which documents the shared
functions).

## Step 2: Update `scripts/implement-finalize.sh`

Replace the five internal function definitions with a single source line near
the top of the file (after `lib-quiet.sh`):

```bash
# shellcheck source=scripts/lib-execution-issues.sh
source "$SCRIPT_DIR/lib-execution-issues.sh"
```

Remove the now-duplicated function bodies for `sha256_file`, `sha256_stream`,
`normalize_body_for_hash`, `json_escape_stream_python`, and
`write_execution_issues_records`. All call sites within `implement-finalize.sh`
remain unchanged since the functions are now provided by the library.

The existing `flush_execution_issues_safety_net` in `implement-finalize.sh`
calls `write_execution_issues_records` and `larch-log.sh` directly as a teardown
safety net. It should be updated to pass the default `step_label="18"` and
`source_label="execution-issues.md safety-net"` explicitly (matching the current
hardcoded behavior), ensuring no behavioral change.

Update `scripts/implement-finalize.md` "Edit In Sync" section to reference
`scripts/lib-execution-issues.sh` and `skills/implement/scripts/flush-execution-issues.sh`.

## Step 3: Update `scripts/test-implement-finalize.sh`

The sandbox in `scripts/test-implement-finalize.sh` currently copies only
`implement-finalize.sh` and `lib-quiet.sh`. After extraction, the sandboxed
`implement-finalize.sh` will `source "$SCRIPT_DIR/lib-execution-issues.sh"`.
Add the copy into the sandbox setup:

```bash
cp "$SCRIPT_DIR/lib-execution-issues.sh" "$SANDBOX/scripts/lib-execution-issues.sh"
```

This ensures all existing safety-net assertions run against the extracted
implementation without breakage.

## Step 4: Create `skills/implement/scripts/flush-execution-issues.sh`

New script with the following contract:

**Arguments:**
```
flush-execution-issues.sh \
  --log-root PATH \
  --run-id RUN_ID \
  --issue-log PATH \
  [--batch execution-issues]
```

Note: `--skill` is hardcoded to `implement` internally. `--log-file` is removed
from the contract (it had no defined behavior).

**Behavior:**
1. If `--issue-log` is empty or not a non-empty file, emit
   `FLUSH_STATUS=skip RECORDS=0` and exit 0.
2. Compute `sha=$(sha256_file "$issue_log")`. If empty, skip.
3. Check sentinel `$IMPLEMENT_TMPDIR/.execution-issues-flushed.sha`:
   if it exists and matches `$sha`, emit
   `FLUSH_STATUS=already-flushed RECORDS=0` and exit 0.
4. Derive `batch_path` from `--log-root/implement/<run-id>/execution-issues.ndjson`.
   Validate that `--run-id` matches the slug pattern (alphanumeric, hyphens only)
   before constructing the path to prevent path traversal. Require `--log-root`
   to be an absolute path. If the batch file exists and already contains
   `"source_sha256":"$sha"`, write sentinel and emit
   `FLUSH_STATUS=already-flushed RECORDS=0` and exit 0.
5. Call `write_execution_issues_records "$issue_log" "$record_file" "$sha"
   "$batch_path" "7a" "execution-issues.md pre-bump"`.
   If the record file is empty after composition, write sentinel and emit
   `FLUSH_STATUS=no-records RECORDS=0` and exit 0.
6. Capture stdout+stderr from `larch-log.sh append` to a temp log file:
   ```bash
   larch-log.sh append --log-root "$log_root" --skill implement \
     --run-id "$run_id" --batch execution-issues --record-file "$record_file" \
     >"$append_log_tmp" 2>&1
   ```
7. On success (exit 0): write `$sha` to sentinel file, emit
   `FLUSH_STATUS=ok RECORDS=<N> APPEND_LOG_FILE=<append_log_tmp>` and exit 0.
8. On failure: call `append-tool-failure.sh --output-file "$issue_log"
   --site flush-execution-issues --tool larch-log.sh --exit-code "$rc"
   --redact`. Emit
   `FLUSH_STATUS=failed RECORDS=0 APPEND_LOG_FILE=<append_log_tmp>` and exit 1.

The script sources `lib-execution-issues.sh` (which provides `sha256_file`,
`write_execution_issues_records`, etc.) and `lib-quiet.sh` for `emit`/`emit_kv`.

Record count `<N>` is the line count of the non-empty `record_file` (one NDJSON
record per line).

## Step 5: Create `skills/implement/scripts/flush-execution-issues.md`

Sibling contract covering:
- Purpose and primary callers (Step 7a pre-bump, SKILL.md)
- Arguments and output envelope (`FLUSH_STATUS`, `RECORDS`, `APPEND_LOG_FILE`)
- Invariants (idempotency via sentinel + batch SHA check, best-effort failure model)
- Makefile wiring (`test-flush-execution-issues`, shard assignment in
  `test-harnesses-3` alongside `test-implement-finalize`)
- Harness coverage description
- Edit In Sync: `scripts/lib-execution-issues.sh`,
  `scripts/implement-finalize.sh`, `skills/implement/SKILL.md`

## Step 6: Create `skills/implement/scripts/test-flush-execution-issues.sh`

Harness covering all five cases:
1. **Empty input** — empty or absent `execution-issues.md` → `FLUSH_STATUS=skip`
2. **Single-section** — one `### Tool Failures` section →
   `FLUSH_STATUS=ok RECORDS=1`; sentinel written; NDJSON line has correct fields
   including `"step":"7a"` and `"source":"execution-issues.md pre-bump"`
3. **Multi-section** — two sections (`### Tool Failures` + `### Warnings`) →
   `FLUSH_STATUS=ok RECORDS=2`; both records in NDJSON
4. **Idempotent re-run** — run twice on same input → second run emits
   `FLUSH_STATUS=already-flushed RECORDS=0`; no duplicate appended
5. **larch-log.sh failure path** — stub `larch-log.sh` to exit 1 →
   `FLUSH_STATUS=failed`; `append-tool-failure.sh` called (verify via
   execution-issues.md containing the larch-log.sh failure entry)

Add companion `skills/implement/scripts/test-flush-execution-issues.md`.

## Step 7: Update `Makefile`

Add:
```makefile
test-flush-execution-issues:
	bash skills/implement/scripts/test-flush-execution-issues.sh
```

Add `test-flush-execution-issues` to `test-harnesses-3` (alongside
`test-implement-finalize`).

Add to `.PHONY`.

## Step 8: Update `skills/implement/SKILL.md`

### Step 7a pre-bump log-flush Bash block

Before the existing token/timing report writes, add a call to
`flush-execution-issues.sh`:

```bash
"${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/flush-execution-issues.sh" \
  --issue-log "$IMPLEMENT_TMPDIR/execution-issues.md" \
  --log-root "$IMPLEMENT_TMPDIR/larch-logs" \
  --run-id "$RUN_ID" \
  2>"$IMPLEMENT_TMPDIR/pre-bump-flush-execution-issues.log" || \
"${CLAUDE_PLUGIN_ROOT}/scripts/append-tool-failure.sh" \
  --output-file "$IMPLEMENT_TMPDIR/execution-issues.md" \
  --site step-7a \
  --tool flush-execution-issues.sh \
  --exit-code "$?" \
  --redact || true
```

The helper is best-effort: failure is non-fatal and logged back via
`append-tool-failure.sh`.

### Batch mapping table (Step 7a)

In the batch mapping table (line ~757), add an `execution-issues` row for Step
7a. The updated row should read that Step 7a tail writes:
`token-report`, `timing-report`, `execution-issues` (pre-bump), and a
log-flush commit.

### Step 11 / Execution-issues checkpoint

Replace the existing multi-paragraph Step 11 refresh contract (inline Python
pattern, manual SHA logic, etc.) with one line:

> Invoke `${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/flush-execution-issues.sh`
> per its contract (see `skills/implement/scripts/flush-execution-issues.md`).

### Exit 0 CI_PASSED=true bullet

Rewrite the `CI_PASSED=true` Exit 0 handling bullet (line ~1709) to remove the
execution-issues refresh instruction. The bullet currently reads:
> "refresh execution-issues summaries and larch-log batches using the Step 11 contract, then re-invoke ship-pr.sh --resume-phase ci-merge"

Replace with:
> "re-invoke ship-pr.sh --resume-phase ci-merge"

(Execution-issues were already flushed at Step 7a pre-bump; no post-CI refresh
is needed.)

## Step 9: Update `scripts/lib-execution-issues.md`

Document as a sourced-only library, list the five exported functions and the
`_lib_warn_line` private helper, note that primary callers are
`scripts/implement-finalize.sh` and
`skills/implement/scripts/flush-execution-issues.sh`. Reference
`skills/implement/scripts/flush-execution-issues.md` for the full flush contract.

---

## Files changed

| File | Change type |
|------|------------|
| `scripts/lib-execution-issues.sh` | **New** — shared library |
| `scripts/lib-execution-issues.md` | **New** — stub contract |
| `skills/implement/scripts/flush-execution-issues.sh` | **New** — helper |
| `skills/implement/scripts/flush-execution-issues.md` | **New** — contract |
| `skills/implement/scripts/test-flush-execution-issues.sh` | **New** — harness |
| `skills/implement/scripts/test-flush-execution-issues.md` | **New** — stub |
| `scripts/implement-finalize.sh` | **Edit** — source lib, remove 5 function bodies, update safety-net call args |
| `scripts/implement-finalize.md` | **Edit** — Edit In Sync update |
| `scripts/test-implement-finalize.sh` | **Edit** — copy lib-execution-issues.sh into sandbox |
| `skills/implement/SKILL.md` | **Edit** — Step 7a flush call, batch table, Step 11 collapse, Exit 0 bullet |
| `Makefile` | **Edit** — new target + shard assignment |

diff_lines: 330

## Test plan
(no test plan section in plan-file)
