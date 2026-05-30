### FINDING_10: [OUT_OF_SCOPE] Stale `.stderr-tail` sidecar on success path
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Success path in `scripts/run-external-agent.sh` (~325) does not remove stale `.stderr-tail` until next pre-launch rm; long-lived output basename could retain sidecar until relaunch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Optionally rm .stderr-tail on exit 0


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_16: [OUT_OF_SCOPE] Implement launchers lack stderr-tail surfacing
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/launch-codex-*.sh` / `scripts/launch-cursor-*.sh` implement launchers lack sidecar choke point per plan SIMPLE out-of-scope note; `/implement` codex/cursor failures may still lack chat tails despite #3202 for review/design paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Follow-up stderr-source hook for implement launchers (already planned out of scope).


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_17: [OUT_OF_SCOPE] design-log-publish `.stderr-tail` copy untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: stderr-tail publishability documented but not covered by `test-design-log-publish.sh`; regressions could drop `.stderr-tail` from larch-logs without a targeted test failing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Extend design-log-publish or larch-log write-round harness to assert .stderr-tail copies when present.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_24: [OUT_OF_SCOPE] Anti-read-poll hook scope vs #3202 stderr work
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Heuristic Bash/Read task-output poll detection on branch is unrelated to stderr tails; possible false positives/negatives on complex shell.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Separate hook-focused review if incidents appear.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_28: [OUT_OF_SCOPE] Generic Read poll state keyed by cwd only across sessions
- **Reviewer(s)**: dyn-hook-parser-fidelity-output.txt
- **Severity**: latent
- **Concern**: Pre-existing: generic Read polling keys state with `state-${cwd_hash}.tsv` only, while task-output polling adds `session_hash`; unrelated sessions sharing cwd can share counters and trigger reminders on the third read across sessions.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_29: [OUT_OF_SCOPE] Documented accepted hook parser false-negative shapes
- **Reviewer(s)**: dyn-hook-parser-fidelity-output.txt
- **Severity**: nit
- **Concern**: `hook-anti-read-poll.md` documents accepted gaps (`VAR=…/tasks/id.output` then `cat "$VAR"`, subshell/heredoc, unquoted `;` in strings)—by design, not regressions.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_30: [OUT_OF_SCOPE] Hook fail-open invariant holds
- **Reviewer(s)**: dyn-hook-parser-fidelity-output.txt
- **Severity**: nit
- **Concern**: Hook omits `set -e`, guards parse paths with `|| exit 0`, always ends `exit 0`; parse failures should not block tools.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_31: [OUT_OF_SCOPE] Branch context — intentional `--summary-only` skip and weaker digit dedup
- **Reviewer(s)**: dyn-hook-parser-fidelity-output.txt
- **Severity**: nit
- **Concern**: Reviewer notes #3202 collector dedup intentionally skipped under `--summary-only`; digit-run normalization not implemented by design in harness; not a hook issue.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_35: [OUT_OF_SCOPE] Primary chat path dual redaction implemented correctly
- **Reviewer(s)**: dyn-stderr-redaction-chain-output.txt
- **Severity**: nit
- **Concern**: Positive observation: `render_failed_agent_stderr_tail` applies tail → tmpdir redact → secrets redact → byte cap after redaction; sidecars and design-log publish align with `SECURITY.md:256`.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_36: [OUT_OF_SCOPE] `emit_failed_agent_stderr_tail_raw` inherits fail-open spool behavior
- **Reviewer(s)**: dyn-stderr-redaction-chain-output.txt
- **Severity**: nit
- **Concern**: `run-external-agent.sh` emits already-redacted sidecar with plain `cat` to FD 2; acceptable given sidecar write path but inherits fail-open spool behavior (see in-scope pipefail finding).
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_37: [OUT_OF_SCOPE] `larch_err` re-redacts secrets only; tmpdir scrub on first pass
- **Reviewer(s)**: dyn-stderr-redaction-chain-output.txt
- **Severity**: nit
- **Concern**: Collector tails fine on chat path; compose/append path for raw `.launch-stderr` is the gap (`lib-quiet.sh` secrets-only re-redact).
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_38: [OUT_OF_SCOPE] Gitleaks does not scan `larch-logs/`
- **Reviewer(s)**: dyn-stderr-redaction-chain-output.txt
- **Severity**: nit
- **Concern**: Documented in `SECURITY.md` / `.gitleaks.toml`; committed `*.stderr-tail` depends on redaction quality, not scanner backstop (overlaps in-scope FINDING_20 with different emphasis).
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_39: [OUT_OF_SCOPE] Pre-existing raw `.diag` in same compose redaction path
- **Reviewer(s)**: dyn-stderr-redaction-chain-output.txt
- **Severity**: nit
- **Concern**: `.diag` was already raw-`cat`'d into secrets-only `append-tool-failure.sh --redact`; branch amplifies exposure by adding `.launch-stderr` with same treatment.
- **Suggested revisions (informational for voters; coder decides)**:

Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_7: [OUT_OF_SCOPE] run-external-agent failure tails stdout before stderr sidecar
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: On failure with non-empty output file, `scripts/run-external-agent.sh` (~300–306) still tails OUTPUT_FILE (review stdout) before stderr sidecar path; misleading “output (last lines)” label when stderr is sidecar-only. Pre-existing shape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Pre-existing; only note if tightening failure diagnostics further


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

