# scripts/sleep-seconds.sh — contract

`scripts/sleep-seconds.sh` is a thin wrapper around `sleep N` that exists so SKILL.md files can invoke a sleep via a documented script path rather than calling `sleep` from inline Bash. This keeps the AGENTS.md "anti-polling" rule legible and grep-able — every legitimate sleep is a call to this script, and any inline `sleep` in a SKILL.md is a violation. Used at the top of CI-transient-retry paths in `/implement` Step 10 / 12c and at the documented dialectic / negotiation pacing points. Always exits 0; rejects missing argument with exit 1.
