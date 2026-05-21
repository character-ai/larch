### FINDING_10: [OUT_OF_SCOPE] Cursor auth tokens visible in process argv during probe subprocess
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Cursor authentication tokens injected into `CURSOR_AUTH_ARGS` appear in the process argv (`cursor agent … --api-key $TOKEN`) for the probe subprocess duration, making them visible in `/proc/$pid/cmdline` and `ps aux` output to co-users on shared hosts. Pre-existing pattern shared with all Cursor launchers; not introduced by this diff.
- **Suggested revision**: Consider passing tokens via environment variable rather than CLI args in a follow-up hardening pass.

---


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0 Result=exonerated


### FINDING_5: [OUT_OF_SCOPE] EXIT trap kills PROBE_PIDS but does not `wait` after kill
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: `larch_probe_exit_cleanup` (`scripts/check-reviewers.sh:62-70`) calls `kill` on each PID in `PROBE_PIDS` but does not `wait` afterward, leaving short-lived zombie entries for any in-flight probe when the trap fires. In practice the parent shell exits immediately so init reaps them; functionally harmless. Pre-existing limitation not introduced by this diff.
- **Suggested revision**: Add `wait "$pid" 2>/dev/null || true` after each `kill` in the cleanup loop if zombie avoidance is desired in future hardening.

---


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


