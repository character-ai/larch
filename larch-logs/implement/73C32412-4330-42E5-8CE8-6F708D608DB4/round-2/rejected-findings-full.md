### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: Round-1 exports session token keys into child process env
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Round-1 exports LARCH_TOKEN_SESSION_ID and related keys into child process env. Same-UID local observers can read session identifiers from child /proc during long runs. Document intent in SECURITY.md or limit exports to helpers that cannot use read-session-env-key.sh.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Step 8 ship-pr exit routing before full invocation completes
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: After Stage 4 removed Family-B PID wait/monitor coupling, foreground `ship-pr` plus harness auto-background can return Bash early while `ship-pr.sh` is still running (including writes to `ship-pr-state.sh`). Step 8+ then parses exit code, applies the Exit 0–6 matrix, or re-invokes from partial state while anti-halt encourages immediate continuation—without an in-fence wait or script-level overlap guard. That can cause orphan or double `ship-pr`, wrong bail/stall paths, or overlapping git/gh work on one clone (2454-class / #2454-class risk).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

