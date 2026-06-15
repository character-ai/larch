## Decision 1: Probe retry counts are preserved
- **Question**: Do the existing retry counts in `check_reviewers()` satisfy the issue's "there should be retries" requirement?
- **Resolution**: Yes. `check_reviewers()` already retries via `_run_codex_probes`/`_run_cursor_probes` with `LARCH_EXTERNAL_AUTH_RETRIES` (default 5 for auth errors) and `LARCH_PROBE_TIMEOUT_SECONDS` (default 30). Binary-missing already short-circuits on the first attempt (no retry) because `shutil.which()` returns `None` before any probe runs.
- **Source**: codebase

## Decision 2: Both-down → true hard fail (no option to continue)
- **Question**: When both Codex and Cursor probe-fail after retries, should Step 0 hard-fail with no AskUserQuestion?
- **Resolution**: Yes. Print the error/explanation and exit non-zero immediately. No prompt, no option to continue. The user must fix the tooling before re-running. This changes the current `needs-degraded-decision` path for both-down.
- **Source**: user

## Decision 3: One-down → big warning + confirm (keep existing gate)
- **Question**: When only one vendor fails, keep the existing "warn + confirm" AskUserQuestion gate?
- **Resolution**: Yes. Print the degraded-tool explanation block and fire AskUserQuestion with Continue/Abort. No change to one-down behavior except the messaging should be prominent ("big warning").
- **Source**: user + issue text

## Decision 4: Global health state fully removed from session-env
- **Question**: Remove CODEX_AVAILABLE/CURSOR_AVAILABLE and also CODEX_PRESENT/CURSOR_PRESENT from session-env (WRITE_ENV_KEYS, WRITE_DESIGN_ENV_KEYS)?
- **Resolution**: Yes. Remove all four from `WRITE_ENV_KEYS` and `WRITE_DESIGN_ENV_KEYS` in session_env.py. Keep only CODEX_BINARY_FOUND/CURSOR_BINARY_FOUND (binary-on-PATH state). Callers that gated on CODEX_AVAILABLE or CODEX_PRESENT now gate on CODEX_BINARY_FOUND.
- **Source**: user (full removal everywhere)

## Decision 5: _external_health_gate removed entirely
- **Question**: Remove `_external_health_gate` from `agents.py` and its call in `run_external_agent`?
- **Resolution**: Yes. Remove the function and the call site. The pre-launch per-call health gate is eliminated. Calling sites rely on the waterfall/retry on failure.
- **Source**: user

## Decision 6: All caller sites switch to binary-found
- **Question**: What replaces CODEX_AVAILABLE/CURSOR_PRESENT at calling sites (dispatch-panel.sh, dispatch-code-voters.sh, dispatch-with-waterfall.sh, bootstrap.py, review_and_fix.py, oos_filer.py)?
- **Resolution**: Replace with CODEX_BINARY_FOUND/CURSOR_BINARY_FOUND. If binary is on PATH, attempt the slot; let the waterfall handle failures. If binary is not on PATH, skip the slot.
- **Source**: user + codebase (dispatch-with-waterfall.sh already has the --codex-present/--cursor-present flags that callers will now pass binary-found values to)

## Decision 7: scope — non-goals
- **Question**: What is explicitly out of scope?
- **Resolution**: We do NOT change the waterfall retry behavior (already handles failures). We do NOT change the probe command itself (same probe logic, just results are no longer written as durable globals). We do NOT add new retry mechanisms at caller sites.
- **Source**: issue text
