# scripts/session-setup.sh — contract

Shared setup wrapper for larch skills. It creates a fresh session tmpdir, optionally runs preflight, Slack and repo discovery, reviewer health probes, and can write a session-env file plus a `.health` sidecar.

## Reviewer probe contract

- `--check-reviewers` probes the legacy Codex+Cursor set.
- `--check-gemini-reviewer` is opt-in and only meaningful with `--check-reviewers`; it passes `--include-gemini` to `check-reviewers.sh`.
- Caller-env `CODEX_HEALTHY=false`, `CURSOR_HEALTHY=false`, or `GEMINI_HEALTHY=false` auto-skips the corresponding probe.
- Gemini health failures use skip-style wording: Gemini is omitted for the session rather than replaced by Claude.
- When Gemini probing is enabled, `session-setup.sh` passes `--artifact-dir "$SESSION_TMPDIR"` to `check-reviewers.sh` so `gemini-tool-drift.txt` persists for the session lifetime instead of disappearing with the probe tmpdir.
- `GEMINI_TOOL_DRIFT_WARNING=` keys are re-emitted on stdout and summarized as a stderr banner. `GEMINI_TOOL_DRIFT_ARTIFACT=` is passed through when present.
- On `WAIT_INFRA_ERROR=`, the stderr banner says: `Probe could not classify tool health; available tools marked unhealthy for fail-closed gating.` This matches `check-reviewers.sh` emitting `*_HEALTHY=false` for every available tool on the wait/preflight/infra-error path while preserving `WAIT_INFRA_ERROR` as the cause diagnostic.

## Session-env contract

Recognized caller-env keys are `SLACK_OK`, `SLACK_MISSING`, `REPO`, `REPO_UNAVAILABLE`, `CODEX_HEALTHY`, `CURSOR_HEALTHY`, and `GEMINI_HEALTHY`. The file is parsed line-by-line and never sourced.

When `--write-health` is provided, the health sidecar contains Codex and Cursor health, plus Gemini health when Gemini probing is requested or inherited from caller-env.

## Edit-in-sync

Update `scripts/check-reviewers.sh`, `scripts/write-session-env.sh`, `skills/shared/subskill-invocation.md`, and `skills/shared/external-reviewers.md` when changing session-env keys or reviewer health semantics. Update `scripts/lib-gemini-tool-drift.sh` and `scripts/check-reviewers.md` when changing Gemini drift warning or artifact keys.
