### FINDING_1: **Important** `security` `SECURITY.md:46`: The branch adds SessionStart tmpdir resolution and boundary advisory behavior in `scripts/sessionstart-health.sh:116-149`, but `SECURITY.md` still documents only the PostToolUse/Stop hook trust model around this resolver. Concrete breakage: a consumer auditing shipped hooks before upgrade will not see that `SessionStart` now reads `cwd`/`session_id`, scans session roots through `lib-resolve-implement-tmpdir.sh`, and emits resolved tmpdir basenames into session context. Update `SECURITY.md:46-48` to cover the new SessionStart path, including fail-open behavior, session-id binding/TTL reuse, no file writes, and basename-only disclosure.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `security` `SECURITY.md:46`: The branch adds SessionStart tmpdir resolution and boundary advisory behavior in `scripts/sessionstart-health.sh:116-149`, but `SECURITY.md` still documents only the PostToolUse/Stop hook trust model around this resolver. Concrete breakage: a consumer auditing shipped hooks before upgrade will not see that `SessionStart` now reads `cwd`/`session_id`, scans session roots through `lib-resolve-implement-tmpdir.sh`, and emits resolved tmpdir basenames into session context. Update `SECURITY.md:46-48` to cover the new SessionStart path, including fail-open behavior, session-id binding/TTL reuse, no file writes, and basename-only disclosure.
- **Suggested revision**: Address the concern above.


### FINDING_10: risk-integration: scripts/merge-pr.sh:166-180
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Flush-only OID recovery gates on commit subjects only, not on changed paths. A commit in PR_HEAD_OID..HEAD can carry arbitrary code while its %s subject still matches ^chore(larch-logs): flush ; merge-base can still pass, so merge-pr may force-push and continue as if the divergence were log-only. Add path-scoped verification (e.g. diffstat limited to larch-logs/) and/or a stricter subject template tied to larch-log-flush.sh.
- **Suggested revision**: Address the concern above.


### FINDING_11: risk-integration: scripts/sessionstart-health.md:25 / scripts/test-sessionstart-health.sh:375-460
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Doc claims malformed SessionStart JSON fails open; no harness asserts that. Future jq/stdin parsing changes could violate the fail-open contract without CI signal. Add stdin case with invalid JSON expecting exit 0 and empty stdout.
- **Suggested revision**: Address the concern above.


