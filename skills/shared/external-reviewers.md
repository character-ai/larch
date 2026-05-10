# External Reviewer Procedures (Codex + Cursor; Gemini probe removed)

Shared mechanical procedures for running Codex and Cursor as external reviewers. The Gemini reviewer call sites and health probe have been removed (#1720 Part 1) — the probe ran with workspace-write access and modified the working tree. The launcher (`scripts/launch-gemini-review.sh`) and `--coder=gemini` implementer dispatch path are retained for future re-enablement with a proper read-only sandbox. `GEMINI_HEALTHY` is always `false`; `session-setup.sh` hard-codes this unconditionally. Each skill provides its own reviewer invocation commands (prompts, output paths, tmpdir variables) — this file covers the common scaffolding.

## Binary Check and Health Probe (Step 0)

The binary check, health probe, and health status file write are now handled by `session-setup.sh` with the `--check-reviewers` flag. Skills call a single script in Step 0:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/session-setup.sh --prefix <name> [--skip-preflight] [--skip-branch-check] \
  [--skip-codex-probe] [--skip-cursor-probe] [--write-health <path>]
```

The `--check-reviewers` flag runs `check-reviewers.sh --probe` internally and emits `CODEX_AVAILABLE`, `CURSOR_AVAILABLE`, `CODEX_HEALTHY`, `CURSOR_HEALTHY` on stdout. `GEMINI_HEALTHY=false` and `GEMINI_AVAILABLE=false` are always emitted unconditionally; no `--check-gemini-reviewer` flag is needed or accepted.

**Session-env override**: If `--caller-env` provides a non-empty `CODEX_HEALTHY` or `CURSOR_HEALTHY` value (either `true` or `false`), the script auto-sets the corresponding `--skip-codex-probe` / `--skip-cursor-probe` flag internally and propagates the caller value — you do not need to pass these explicitly when using `--caller-env`.

Set mental flags `codex_available` and `cursor_available` based on the output:
- If `CODEX_AVAILABLE=false`: `codex_available=false`. Print: `**⚠ Codex not available (binary not found). Proceeding without Codex reviewer.**`
- Else if `CODEX_HEALTHY=false`: `codex_available=false`. Print: `**⚠ Codex installed but not responding (health check failed: <CODEX_PROBE_ERROR>). Using Claude replacement.**` where `<CODEX_PROBE_ERROR>` is the `CODEX_PROBE_ERROR` value from `session-setup.sh` output (if available; omit the parenthetical detail if not present).
- Else: `codex_available=true`
- Same logic for Cursor (using `CURSOR_PROBE_ERROR`).
- For Gemini, `gemini_available` is always `false` — `GEMINI_HEALTHY=false` is hard-coded by `session-setup.sh`. `--coder=gemini` falls back to the main-agent code-edit path via `STATUS=claude_fallback`.

**Note**: `*_AVAILABLE` is a pure install-state signal (binary exists on PATH). `*_HEALTHY` indicates whether the tool actually responded to a trivial prompt within the 60-second probe timeout. Callers must combine both to determine runtime usability.

If `session-setup.sh` emits `WAIT_INFRA_ERROR=<reason>` alongside `*_AVAILABLE=true` and `*_HEALTHY=false`, the wait infrastructure failed before tool health could be classified, and the health key is fail-closed. Check `WAIT_INFRA_ERROR` first to attribute the cause as probe-infra abort rather than per-tool probe failure, then apply the appropriate warning template. Availability remains monotonic for session-state purposes, but launch eligibility still requires `*_AVAILABLE=true AND *_HEALTHY=true`.

## Runtime Timeout Fallback

When processing reviewer results (after `wait-for-reviewers.sh` returns), check each reviewer's sentinel file exit code and output validity. If any of the following are true for a reviewer, set the corresponding `*_available` mental flag to `false` for **all subsequent steps in this session**:

- Sentinel exit code is `124` (timeout — the common case when `run-external-agent.sh` enforces its timeout)
- Sentinel exit code is non-zero (any other failure)
- Output is empty/invalid after the retry-once procedure (per "Validating External Reviewer Output" below)
- `collect-agent-results.sh` reports `STATUS=SENTINEL_TIMEOUT` for the reviewer. Internally this is derived from `wait-for-reviewers.sh`'s indexed `TIMEOUT <idx> <basename>` grammar, correlated against the output-file argv order; the basename is informational only and is not a stable key.
- `STATUS=NOT_SUBSTANTIVE` (output passed sentinel + non-empty + retry checks but failed substantive-content validation under `collect-agent-results.sh --substantive-validation` — same Claude-subagent-fallback behavior as a timeout, since the lane is unusable for synthesis; Phase 3 of umbrella #413, closes #416)

Use one of two warning templates:

- **Replacement-style reviewers** (Codex/Cursor lanes with Claude fallback): `**⚠ <Reviewer> failed — <FAILURE_REASON>. Using Claude replacement for remainder of session.**`
- **Skip-style additive reviewers** (Gemini): `**⚠ Gemini failed — <FAILURE_REASON>. Skipping Gemini for remainder of session.**`

Where `<FAILURE_REASON>` is the `FAILURE_REASON` value from `collect-agent-results.sh` output (or from the `.diag` file if collecting results manually). Always include the reason so the user can diagnose the root cause (e.g., timeout duration, exit code, last error output).

This is a mental flag flip within the current skill invocation. For cross-skill propagation within `/implement`, child skills write a structured health status file — see the `/implement` SKILL.md for details.

**Note**: Once a reviewer is marked unhealthy during a session, it stays unhealthy for the remainder of that session. This is intentional — it prevents oscillation and wasted time on flaky tools during extended outages.

## Collecting External Reviewer Results

After launching Codex, Cursor, and/or Gemini as background tasks (via `run-external-agent.sh` with `run_in_background: true`), continue working on other tasks (e.g., processing Claude subagent results) while external reviewers run.

After all other tasks are done, collect and validate external reviewer outputs using the shared collection script:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh --timeout <seconds> [--write-health <path>] <output-file> [<output-file> ...]
```

Only include output file paths for reviewers that were actually launched. For the Bash tool call, use `timeout: <seconds>000` (milliseconds) and **do NOT** set `run_in_background: true` — this call must block. The script internally calls `wait-for-reviewers.sh` to poll for `.done` sentinel files, validates each output, and retries once on empty output (using `.meta` files written by `run-external-agent.sh`). Wait records are correlated by 1-based argv index, so callers should pass output files in the same order they want result blocks interpreted.

**Output**: The script emits structured `KEY=value` blocks on stdout (one block per reviewer, separated by blank lines):
```
REVIEWER_FILE=<output-path>
TOOL=<codex|cursor|gemini|unknown>
STATUS=<OK|TIMED_OUT|FAILED|EMPTY_OUTPUT|SENTINEL_TIMEOUT|NOT_SUBSTANTIVE>
EXIT_CODE=<N>
HEALTHY=<true|false>
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
