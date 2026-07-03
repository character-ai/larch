# test-pause-skill.sh contract

Offline regression harness for the `/larch:pause` skill Bash block. It extracts
the fenced command from `skills/pause/SKILL.md`, stubs the repo-resolution,
KV extraction, and pause-save helpers, and covers:

- no live env file
- incomplete live env
- successful `PAUSE_OK=true` parsing through `kv get`
- failing `PAUSE_OK=false` parsing through `kv get`
