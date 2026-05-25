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

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

```bash
mkdir -p "$DESIGN_TMPDIR/breadcrumbs"
_launch_id="collect-agent-results.$$"
export LARCH_BREADCRUMB_STREAM="$DESIGN_TMPDIR/breadcrumbs/collect-agent-results.${_launch_id}.ndjson"
: > "$LARCH_BREADCRUMB_STREAM"
export LARCH_DONE_SENTINEL="$(mktemp "$DESIGN_TMPDIR/breadcrumbs/collect-agent-results.${_launch_id}.done.XXXXXX")"
export LARCH_STATUS_FILE="$(mktemp "$DESIGN_TMPDIR/breadcrumbs/collect-agent-results.${_launch_id}.status.XXXXXX")"
export LARCH_QUIET_LOG_FILE="$(mktemp "$DESIGN_TMPDIR/breadcrumbs/collect-agent-results.${_launch_id}.quiet.XXXXXX")"
export LARCH_BREADCRUMBS_SURFACED_FILE="$(mktemp "$DESIGN_TMPDIR/breadcrumbs/collect-agent-results.${_launch_id}.surfaced.XXXXXX")"
touch "$LARCH_DONE_SENTINEL" "$LARCH_BREADCRUMBS_SURFACED_FILE"
# Tool JSON: run_in_background: true
# Background pair required: see BASH_AUTHORING.md §4
${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh --timeout <seconds> <output-file> [<output-file> ...]

"${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh" \
  --stream "$LARCH_BREADCRUMB_STREAM" \
  --done-sentinel "$LARCH_DONE_SENTINEL" \
  --status-file "$LARCH_STATUS_FILE" \
  --quiet-log "$LARCH_QUIET_LOG_FILE" \
  --surfaced-sentinel "$LARCH_BREADCRUMBS_SURFACED_FILE"
```

Only include output file paths for reviewers that were actually launched. For the Bash tool call, use `timeout: <seconds>000` (milliseconds) and set `run_in_background: true` on the collector launch, paired with foreground `breadcrumb-monitor.sh` in the same Bash message. The script internally calls `wait-for-reviewers.sh` to poll for `.done` sentinel files, validates each output, and retries once on empty output (using `.meta` files written by `run-external-agent.sh`). Wait records are correlated by 1-based argv index, so callers should pass output files in the same order they want result blocks interpreted.

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
