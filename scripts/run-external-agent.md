# scripts/run-external-agent.sh — contract

## Purpose

Runs an external agent subprocess with timeout handling, transcript capture, and `.done` sentinel metadata for callers that need deterministic collection.

## Invariants

- `--tool <name>` is metadata for logs and sentinel files; current call sites include `codex`, `cursor`, and `gemini`.
- `--capture-stdout` captures stdout to the output file while wrapper progress goes to the caller's stdout/stderr unless redirected by the launcher.
- Callers that need KV-only stdout must redirect this wrapper's chatter to a sidecar log.

## Edit-in-sync

- `scripts/launch-codex-implement.sh`
- `scripts/launch-cursor-implement.sh`
- `scripts/launch-gemini-implement.sh`
- `scripts/check-reviewers.sh`
