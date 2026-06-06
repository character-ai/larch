### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: `launch-codex-exec.sh` lacks `--add-dir` path validation / containment checks
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `--add-dir` paths are passed to `codex exec` without directory validation or containment checks unlike `launch-review.sh` hardening. A buggy or malicious caller passing `--add-dir /tmp` or `$HOME/.ssh` in full-auto mode can grant Codex write access outside the intended workspace.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Mirror launch-review.sh add-dir validation: reject `..`, require canonical existing directories, and optionally require paths under `--workdir` or session root.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: Collector outer-retry replays `OUTER_LAUNCHER_ADD_DIRS_JSON` without per-path safety checks
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Outer-retry for `launch-codex-exec` replays `OUTER_LAUNCHER_ADD_DIRS_JSON` without per-path safety checks. Same-UID tampering with a session `.meta` sidecar could inject arbitrary add-dir paths on empty-output retry, widening Codex write grants in full-auto lanes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Validate each jq-decoded add-dir with `validate_meta_scalar_path`, reject `..`, require existing directories, and bind to `META_OUTER_LAUNCHER_WORKDIR` before retry launch.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: `launch-codex-exec.sh` pre-auth failures may exit without collector preflight bundle
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Pre-auth failures (prompt sidecar write, `mktemp`) exit under `set -e` without collector bundle. Background research/voter lanes may hang `wait-for-reviewers` or leave inconsistent sidecars.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Route early failures through `write_preflight_bundle`.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_22: Research lanes use `--prompt` not `--prompt-file` for large prompts
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Research lanes use `--prompt` not `--prompt-file` for large lane prompts. Long `RESEARCH_QUESTION` can exceed argv limits and fail lanes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Write per-lane prompt file and use `--prompt-file`.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

