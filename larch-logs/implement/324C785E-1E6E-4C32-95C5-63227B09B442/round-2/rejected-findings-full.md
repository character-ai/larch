### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: Codex-exec retry replays add-dir without path containment validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `collect-agent-results.sh` replays `OUTER_LAUNCHER_ADD_DIRS_JSON` as `--add-dir` without path containment validation. A same-UID process tampering session `.meta` before empty-output retry could add full-auto write grants outside the repo workdir.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Validate each replayed add-dir against canonical OUTER_LAUNCHER_WORKDIR/session root; reject .. and non-directory paths; fail closed like launch-review.sh --codex-add-dir.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: Linter misses run-external-agent.sh codex exec dispatch
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `lint-codex-exec-auth.sh` only matches literal `codex exec` tokens, not `run-external-agent.sh -- codex exec` dispatch. New scripts could pass lint while launching unwired Codex without `OPENAI_API_KEY` handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Also flag codex exec after -- or require auth helper / launch-codex-exec.sh on run-external-agent Codex dispatch lines.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: launch-codex-exec --add-dir paths not bounded to workdir at launch
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `launch-codex-exec.sh` accepts `--add-dir` paths without bounding them to workdir/session root at launch time. Misconfigured or future call sites could grant full-auto Codex write access to sensitive directories.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Add containment checks for --add-dir mirroring launch-review.sh session-root validation.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: launch-codex-exec duplicates launch-codex-ci mechanics
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: The new `launch-codex-exec.sh` largely duplicates `launch-codex-ci` mechanics, increasing long-term drift surface; future auth/retry fixes may require parallel edits across launchers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Track follow-up extraction of shared Codex prepare/retry/record helpers after stabilization.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

