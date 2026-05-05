# scripts/write-session-env.sh — contract

## Purpose

Writes a shell-sourceable session-env file atomically for child skills and dispatcher scripts.

## Invariants

- Required flags: `--output`, `--slack-ok`, `--repo-unavailable`.
- `--slack-missing`, `--repo`, `--codex-healthy`, `--cursor-healthy`, and `--gemini-healthy` are append-if-set optional flags.
- Health keys are emitted only when their flag value is non-empty.
- `/dev/null` is accepted as a discard destination.

## Edit-in-sync

- `scripts/session-setup.sh`
- `skills/shared/subskill-invocation.md`
- `skills/implement/SKILL.md`
