### FINDING_1: Read daemon result before lane artifacts
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-dyn-Ci Recovery Integrity
- **Severity**: major
- **Concern**: Finalization must inspect the daemon-owned `.result.env` and branch on `BGJOB_RC` before requiring merge or status artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In `--finalize`, validate `$BGJOB_DIR/$STEP.result.env` first for `BGJOB_RC` / `STEP`. Branch on non-zero before requiring merge env or status. Keep `BGJOB_RC=0` plus missing or mismatched lane artifacts on the existing `operator-bail` / `missing-result` path.
  - From Cursor-Innovation: Read BGJOB_RC from $BGJOB_DIR/$STEP.result.env first; require merge env and fixer-status.env only on the BGJOB_RC=0 path
  - From Cursor-dyn-Ci Recovery Integrity: Today --finalize requires $BGJOB_DIR/$STEP.merge.env and fixer-status.env before any routing; on BGJOB_RC!=0 the daemon writes only $STEP.result.env (BGJOB_RC timeout orphaned or numeric) while merge.env is absent, so the wrapper never reaches crash accounting Read and validate $IMPLEMENT_TMPDIR/bgjob/$STEP.result.env first; treat BGJOB_RC equal to 0 as the success path requiring merge.env and status agreement; treat any other BGJOB_RC token as the crash helper path


### FINDING_7: Account for salvage commits before retrying
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: Crash finalization must not retry another tier when the crashed lane already advanced `HEAD` with a salvage commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Before crashed-tier accounting compare live HEAD to launch STARTING_HEAD and emit RESULT=reship when advanced; document precedence in ship-pr-ci-fix.md and test it


### FINDING_10: Validate repository safety before advancing tiers
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Concern**: Crash recovery must fail closed on uncommitted drift or unverified changes before launching the next fixer tier.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Before returning retry-next-tool, validate live HEAD and working-tree state against the launch state. Fail closed on uncommitted drift or an unprovable HEAD change. Permit any advanced HEAD only through a narrowly validated lane-owned commit condition.


### FINDING_11: Enforce a global diagnostic size cap
- **Reviewer(s)**: Cursor-dyn-Ci Recovery Integrity, Codex-dyn-Ci Recovery Integrity
- **Severity**: minor
- **Concern**: Launch context plus stdout and stderr tails must be composed, redacted, and truncated as one bounded payload.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Ci Recovery Integrity: Plan requires a single payload near BGJOB_LOG_TAIL_BYTES; bgjob wait already tail-reads up to 4096 bytes per log file, so naively concatenating launch envelope plus stdout and stderr tails can exceed the committed-log cap and leak oversized diagnostics before append-failure Compose launch context plus both tails into one buffer then apply _safe_evidence_text-style redaction and one final truncate to config.BGJOB_LOG_TAIL_BYTES before run-log append-failure; add a unit test with oversized stdout and stderr fixtures proving total output stays bounded


