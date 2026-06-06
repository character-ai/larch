### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: `lint-codex-exec-auth.sh` misses variable-qualified `codex exec` spellings
- **Reviewer(s)**: dyn-linter-fidelity-output.txt
- **Severity**: important
- **Concern**: Detection is limited to the contiguous literal `codex[[:space:]]+exec`. Static lines that dispatch via a variable command word (`"$CODEX_BIN" exec …`, `"${CODEX_BIN:-codex}" exec` when `codex` is not immediately adjacent to `exec`, `exec "$codex_bin"`, etc.) never match, so unwired call sites can evade the guard while still running Codex. Path-qualified `/path/to/codex exec` is caught; variable-qualified forms are not.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-linter-fidelity-output.txt: Extend the matcher (or add a second rule) for common alternate spellings such as `"$…" exec` / `exec` immediately after a Codex-path variable when paired with Codex flags (`--full-auto`, `--sandbox`, `-C`, `--output-last-message`), and pin bypass cases in `scripts/test-lint-codex-exec-auth.sh`.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: `launch-codex-exec.sh` lacks workdir/add-dir path canonicalization
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `--workdir`/`--add-dir` inputs at `scripts/launch-codex-exec.sh:119-187` lack `validate_meta_scalar_path` symlink and `..` rejection before `codex exec` and metadata serialization. Full-auto lanes can be aimed at symlinked or out-of-scope directories, widening write grants beyond `launch-review` hardening.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Reuse launch-review add-dir canonicalization for all workdir/add-dir inputs before dispatch and meta write


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: `collect-agent-results.sh` replays outer-retry metadata without validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Outer-retry replays sandbox and add-dir JSON from `.meta` without path validation or `CMD_JSON` cross-check. Same-UID `.meta` tamper could escalate a read-only voter retry to full-auto or add arbitrary `--add-dir` paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Validate add-dir scalars and bind OUTER_LAUNCHER_* fields to CMD_JSON or signed metadata


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

