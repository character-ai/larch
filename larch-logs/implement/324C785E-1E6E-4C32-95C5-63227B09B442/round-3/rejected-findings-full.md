### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: Collector retry replays add-dir paths without path safety validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Codex-exec outer retry replays add-dir paths from `OUTER_LAUNCHER_ADD_DIRS_JSON` with only array-type validation. Same-UID tampering can append a malicious line to a session `.meta` file; on empty-output retry Codex full-auto may receive extra `--add-dir` grants outside the intended workspace.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Validate each JSON add-dir element (reject .. and symlinks, canonicalize paths, optionally constrain under OUTER_LAUNCHER_WORKDIR) before appending to _codex_exec_retry_args.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: launch-codex-exec.sh passes --add-dir without canonicalization
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `--add-dir` values are passed through to `codex exec` without symlink or `..` canonicalization checks present in `launch-review.sh`. An orchestrator-supplied symlinked add-dir could expand Codex full-auto write access beyond the intended directory on research/lint-fix/voter lanes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Apply launch-review-style _codex_canonical_existing_dir validation to every --add-dir before dispatch.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: run-negotiation-round.sh lacks auth-retry loop
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The negotiation Codex path has no auth-retry loop unlike `launch-codex-exec.sh`. Transient `OPENAI_API_KEY`/auth startup failures fail negotiation immediately without the retries other swept paths get.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Document intentional asymmetry or add shared auth-retry wrapper.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: voting-protocol.md direct-fence vs dispatch-script routing undocumented
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: The generic Codex voter fence implies `dispatch-plan-voters` mirrors it, but plan voters use `launch-review.sh`. Direct copies of the fence can diverge from automated `/design` and `/review` voter dispatch, which still use `launch-review` auth/retry semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Split documentation: direct fence vs dispatch-script routing.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: research lanes pass huge prompts via --prompt argv
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Research lanes pass large `RESEARCH_PROMPT_*` strings via `--prompt` argv instead of `--prompt-file`. Very large prompts can fail at shell/Codex argv limits while validation and negotiation paths succeed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Use --prompt-file for lane prompts like the validation lane does.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

