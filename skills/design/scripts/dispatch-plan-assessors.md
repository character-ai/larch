# dispatch-plan-assessors.sh

Launches Claude + Codex/Cursor waterfall assessor panel. Emits `DISPATCH_OK` and per-slot paths/statuses on stdout for the caller's dedicated KV capture. Uses `--require-result-pattern` for `ASSESSMENT:` lines (Cursor narration backstop).
