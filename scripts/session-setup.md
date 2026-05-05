# scripts/session-setup.sh — contract

## Purpose

Shared Step 0 setup helper for skills. It creates a fresh session tmpdir, runs optional preflight/repo/Slack checks, optionally probes external tools through `check-reviewers.sh`, and can write `session-env.sh` plus a health sidecar.

## Probe Invariants

- `--check-reviewers` runs `check-reviewers.sh --probe`.
- `--include-gemini` is opt-in and forwards to `check-reviewers.sh`; callers that do not pass it retain Codex/Cursor-only output.
- `--caller-env` values for `CODEX_HEALTHY=false`, `CURSOR_HEALTHY=false`, and `GEMINI_HEALTHY=false` auto-set the matching `--skip-*-probe` flag. Seeing `GEMINI_HEALTHY=*` in caller-env also opts into Gemini handling.
- `CLAUDE_PLUGIN_OPTION_GEMINI_MODEL` is bridged to `LARCH_GEMINI_MODEL` when the env var is unset.

## Health Sidecar

`--write-health <path>` writes `CODEX_HEALTHY`, `CURSOR_HEALTHY`, and, only when Gemini is opted in, `GEMINI_HEALTHY`.

## Edit-in-sync

- `scripts/check-reviewers.sh`
- `scripts/write-session-env.sh`
- `skills/shared/external-reviewers.md`
- `skills/implement/SKILL.md`
