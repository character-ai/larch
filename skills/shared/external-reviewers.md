## Binary Presence Check (Step 0)

The binary check, presence check, and presence status write are now handled by `session-setup.sh` with the `--check-reviewers` flag. Skills call a single script in Step 0:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/session-setup.sh --prefix <name> [--skip-preflight] [--skip-branch-check] \
  [--skip-codex-probe] [--skip-cursor-probe]
```

**Session-env override**: If `--caller-env` provides a non-empty `CODEX_PRESENT` or `CURSOR_PRESENT` value (either `true` or `false`), the script auto-sets the corresponding `--skip-codex-probe` / `--skip-cursor-probe` flag internally and propagates the caller value — you do not need to pass these explicitly when using `--caller-env`.

Set mental flags `codex_available` and `cursor_available` from session-env / `session-setup.sh` stdout. Treat `codex_available` as `true` only when **both** `CODEX_BINARY_FOUND=true` **and** `CODEX_PRESENT=true`; if **either** `CODEX_BINARY_FOUND=false` **or** `CODEX_PRESENT=false`, set `codex_available=false` (aliases `CODEX_AVAILABLE` / `CURSOR_AVAILABLE` mirror the same booleans). Use `CODEX_BINARY_FOUND` / `CURSOR_BINARY_FOUND` when you need to split the cases:

- If `CODEX_BINARY_FOUND=false`: `codex_available=false` — the Codex CLI is not on `PATH`. Print: `**⚠ Codex not available (binary not found). Proceeding without Codex reviewer.**`
- Else if `CODEX_PRESENT=false`: `codex_available=false` — the binary exists but the Step 0 runtime probe reported unhealthy (skipped probe, non-auth failure, auth failure after retries, or timeout). Print: `**⚠ Codex not healthy for this session (runtime probe failed). Using Claude replacement.**`
- Else: `codex_available=true`

Mirror the same two-tier pattern for Cursor (`CURSOR_BINARY_FOUND` / `CURSOR_PRESENT`): `cursor_available=false` when **either** `CURSOR_BINARY_FOUND=false` **or** `CURSOR_PRESENT=false`; `cursor_available=true` only when both are `true`.

**Note**: `*_AVAILABLE` remains a backward-compatible alias for `*_PRESENT`; it does **not** mean "binary on `PATH`" by itself.

Launch eligibility requires `*_PRESENT=true`. Runtime failures do not mutate `session-env.sh`; multi-slot dispatchers handle them through per-slot waterfall fallback.

## Degraded-tools gate (Step 0)

Issue #3207: when an external tool is unhealthy at session start, the skill MUST **tell the operator and let them choose** rather than silently proceeding degraded. Immediately after presence detection, run the gate detector with **all four** `--check-reviewers` keys on every invocation (contract: `scripts/degraded-tools-gate.md`). Do not rely on exported env from an earlier skill in the same shell — re-parse `session-setup.sh` stdout in the current Step 0 block and pass explicit `--codex-binary-found` / `--codex-present` / `--cursor-binary-found` / `--cursor-present` flags:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/degraded-tools-gate.sh \
  --codex-binary-found "$CODEX_BINARY_FOUND" --codex-present "$CODEX_PRESENT" \
  --cursor-binary-found "$CURSOR_BINARY_FOUND" --cursor-present "$CURSOR_PRESENT" \
  --skill <design|implement|review|research>
```

Parse `DEGRADED`, `CODEX_STATE`, `CURSOR_STATE`:

- **`DEGRADED=false`** — both tools healthy; proceed silently (the per-tool warning prints above are unaffected).
- **`DEGRADED=true`** — lift the explanation block between `DEGRADED_EXPLANATION_BEGIN` / `DEGRADED_EXPLANATION_END`, then:
  - **Interactive run** — present the explanation block and fire `AskUserQuestion` with two options: **Continue (reduced panel — unavailable tools dropped, no cross-tool or Claude padding)** and **Abort**. On **Continue**, proceed with availability-gated `--no-fallback` dispatch (drop slots whose tool is absent; no per-slot cross-tool or Claude padding). On **Abort**, print `**⚠ /<skill>: aborted by operator — external tool unhealthy; re-run once it recovers.**`, clean up the session tmpdir, and stop the skill (run no further steps).
  - **`/design` and `/implement`** use the reduced-panel contract above. **`/review` and `/research`** that still run the legacy multi-phase waterfall use **Continue (degraded waterfall)** when that skill's Step 0 documents the backup waterfall — see each skill's degraded-tools gate bullet.
  - **Non-interactive / autonomous run** (cron, `claude -p`, `<<autonomous-loop>>`, eval) — do **NOT** block. Print the explanation block once as a notice and, when a session tmpdir exists, log it to `execution-issues.md` under `Warnings`; then proceed degraded — the waterfall guarantees completion. This mirrors the autonomous carve-outs that already bracket `AskUserQuestion` in `/implement`.

Fire the gate **once per run**: guard it with a `.degraded-tools-gate-prompted` sentinel under the session tmpdir so Step 0 re-entry (e.g. `/implement` dirty-tree / resume-plan-tail) does not re-prompt. The gate is advisory about availability only — it does **not** flip `codex_available` / `cursor_available`, which continue to drive per-slot launch eligibility and the runtime waterfall below.

## Runtime Waterfall Fallback

When processing reviewer results, failed external slots should fall through the waterfall dispatcher rather than flipping session-wide availability:

- Phase 1 launches the slot's assigned external tool when present.
- Phase 2 retries the slot with the other present external tool.
- Phase 3 launches a Claude reviewer subprocess via `scripts/launch-claude-review.sh`.

Use this warning template when a slot reaches Phase 3:

- `**⚠ <Reviewer> failed — <FAILURE_REASON>. Using Claude replacement for this slot.**`

Where `<FAILURE_REASON>` is the `FAILURE_REASON` value from `collect-agent-results.sh` output (or from the `.diag` file if collecting results manually). Always include the reason so the user can diagnose the root cause (e.g., timeout duration, exit code, last error output).

Do not write runtime failure status back to session env. `CODEX_PRESENT` and `CURSOR_PRESENT` are set once at session start via the runtime health probe; they are not updated mid-session by per-slot launch failures.

## Collecting External Reviewer Results

After all other tasks are done, collect and validate external reviewer outputs using the shared collection script:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh --timeout <seconds> <output-file> [<output-file> ...]
```

Only include output file paths for reviewers that were actually launched. For the Bash tool call, use `timeout: <seconds>000` (milliseconds) and use a foreground collector invocation The script internally calls `wait-for-reviewers.sh` to poll for `.done` sentinel files, validates each output, and retries once on empty output (using `.meta` files written by `run-external-agent.sh`). Wait records are correlated by 1-based argv index, so callers should pass output files in the same order they want result blocks interpreted.

**Output**: The script emits structured `KEY=value` blocks on stdout (one block per reviewer, separated by blank lines):
```
REVIEWER_FILE=<output-path>
STATUS=<OK|TIMED_OUT|FAILED|EMPTY_OUTPUT|SENTINEL_TIMEOUT|NOT_SUBSTANTIVE>
EXIT_CODE=<N>
FAILURE_REASON=<explanation>
```

Parse each reviewer's `STATUS`, `REVIEWER_FILE`, and `FAILURE_REASON`:
- `STATUS=OK`: Read the output file — it is non-empty and validated. `FAILURE_REASON` is empty.
- Any other status: The reviewer failed. `FAILURE_REASON` explains why (e.g., "Timed out after 1800s (limit: 1800s). Process was killed after exceeding the timeout." or "Failed with exit code 1 after 5s. Last output: error message here"). Follow the **Runtime Timeout Fallback** procedure above, including `FAILURE_REASON` in the message.
- Treat `STATUS=OK` with empty `FAILURE_REASON` as the success signal; do NOT use `EXIT_CODE` alone — see `scripts/collect-agent-results.md` for retry-row exit-code semantics.

**Important**: Do NOT read output files before calling `collect-agent-results.sh`. Cursor buffers all stdout until exit — its output file is empty until the process finishes. The collection script handles all sentinel polling and validation internally.

**Substantive-content validation is opt-in.** The default collector behavior described above is sentinel + non-empty + retry. Substantive-content classification (`STATUS=NOT_SUBSTANTIVE`) only runs when callers pass `--substantive-validation` (and optionally `--validation-mode` for short reviewer-style outputs). See the `--substantive-validation` / `--validation-mode` stanza of the `scripts/collect-agent-results.sh` header for the authoritative flag documentation and `docs/external-reviewers.md` Output Validation for the per-skill opt-in matrix.

## Negotiation Protocol

> **Note**: `/design` and `/review` now use the **Voting Protocol** in `voting-protocol.md` instead of this Negotiation Protocol. This section is retained for skills that still use negotiation: `/research`.

> **Variable substitution**: Replace `<skill-tmpdir>` in all paths below with the session tmpdir variable passed by the caller (e.g., `$DESIGN_TMPDIR` or `$REVIEW_TMPDIR`).

> **Parameters**: `max_rounds` (default: 3) — the maximum number of negotiation rounds.

Negotiate with each external reviewer (Codex, Cursor) for up to **`max_rounds` rounds** of back-and-forth:

1. Evaluate each finding. **Accept** it unless it is factually incorrect (references wrong file/line, misunderstands the code) or contradicts a project convention documented in CLAUDE.md.
2. For findings you disagree with, write a response to a negotiation prompt file explaining your reasoning. Use the Write tool if available; if the skill does not allow Write (e.g., `/research`), write the prompt file via the `run-negotiation-round.sh` script's `--prompt-file` argument (the caller must create the file through whatever means the skill permits). The prompt should include the original finding, your counter-argument, and ask the reviewer to either maintain its position with additional justification or withdraw the finding.
   - **Codex**: Write to `<skill-tmpdir>/codex-negotiation-prompt.txt`, then:
     ```bash
     ${CLAUDE_PLUGIN_ROOT}/scripts/run-negotiation-round.sh --tool codex --prompt-file "<skill-tmpdir>/codex-negotiation-prompt.txt" --output "<skill-tmpdir>/codex-negotiation-output.txt" --workspace "$PWD"
     ```
   - **Cursor**: Write to `<skill-tmpdir>/cursor-negotiation-prompt.txt`, then:
     ```bash
     ${CLAUDE_PLUGIN_ROOT}/scripts/run-negotiation-round.sh --tool cursor --prompt-file "<skill-tmpdir>/cursor-negotiation-prompt.txt" --output "<skill-tmpdir>/cursor-negotiation-output.txt" --workspace "$PWD"
     ```
   Use `timeout: 300000` on both Bash tool calls. `run-negotiation-round.sh` distinguishes failure modes by exit code: `0` success, `1` argv/usage or `agent-model-args.sh` propagation, `2` reviewer command (`cursor agent` / `codex exec`) failed, `3` Cursor `cursor_auth_preflight` failed before the reviewer ran. Wrappers that need to disambiguate auth-vs-tool failures should branch on these codes — see `${CLAUDE_PLUGIN_ROOT}/scripts/run-negotiation-round.md` for the full contract and the `RESPONSE_FILE=` stdout key.
3. Repeat up to 3 rounds total. After round 3 (or earlier if all disagreements are resolved), **Claude makes the final call** on any remaining disputes.
## External Reviewer Procedures
