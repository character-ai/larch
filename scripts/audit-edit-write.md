# scripts/audit-edit-write.sh — contract

`scripts/audit-edit-write.sh` is a dev-only PostToolUse audit hook for `Edit`/`Write` tool use. It is shipped in the plugin install tree but is **not registered by default** in `hooks/hooks.json` or `.claude/settings.json`; contributors opt in locally by adding a `PostToolUse` entry to `.claude/settings.local.json` (gitignored). Appends one JSONL record per invocation to `.claude/hook-audit.log` (also gitignored). `scripts/test-audit-edit-write.sh` is its regression harness, wired into `make lint` via the `test-audit-edit-write` target. See `docs/dev-hook-audit.md` for enable/rotate/privacy details and `docs/security/workflow-trust-and-mutations.md` for the security posture.

This hook has no contract stdout. It appends audit JSONL directly and ignores write failures so PostToolUse completion is never blocked.
