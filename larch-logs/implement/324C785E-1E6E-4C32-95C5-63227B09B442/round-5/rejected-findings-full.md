### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: Retry replays `OUTER_LAUNCHER_ADD_DIRS_JSON` without path containment validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Retry replays `OUTER_LAUNCHER_ADD_DIRS_JSON` into `--add-dir` without path containment validation. A same-UID actor tampering session `.meta` before empty-output retry could add paths like `$HOME/.ssh` while canonical launcher checks still pass, widening Codex full-auto filesystem access beyond the original launch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Validate each replayed add-dir: scalar path charset, no .., canonical directory under workdir/session root; reject symlinks used to widen grants.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: Retry accepts tamperable `OUTER_LAUNCHER_SANDBOX` without launch-time binding
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Retry accepts tamperable `OUTER_LAUNCHER_SANDBOX` without binding to original launch policy. Tampering `.meta` from read-only to full-auto between launch and retry could run a read-only voter lane with full-auto sandbox on retry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Bind sandbox to launch-time sidecar metadata or hash; fail closed when retry meta disagrees.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: `launch-codex-exec.sh` `--add-dir` has no containment checks
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `--add-dir` in `launch-codex-exec.sh` has no containment checks unlike `launch-review --codex-add-dir`. An orchestrator mistake or over-broad fence can grant Codex write access outside the intended repo/session tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Canonicalize and require add-dir paths under workdir or session root; reject symlink parents.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: `WORKDIR` embedded in trust config without control-character validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `WORKDIR` is embedded in `TRUST_CONFIG_ARG` without control-character validation. Pathological workdir values could break or inject extra `-c` TOML fragments passed to Codex.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Apply validate_meta_scalar_path to workdir/add-dir before building trust -c argv.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_23: Add-dir metadata serialization deferred until after Codex dispatch
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Add-dir metadata serialization is deferred until after `run-external-agent.sh` completes even though `ADD_DIRS` are known at launch. Long-running research lanes pay full Codex cost before a deterministic metadata error can fail the launcher.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Move add-dir JSON construction before auth setup and Codex dispatch; treat serialization failure as preflight-only.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_24: `launch-codex-exec.sh` serial lock may serialize parallel research lanes
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `launch-codex-exec.sh` blocks through `run-external-agent.sh` and acquires the Darwin serial lock, changing parallelism versus the old direct `run-external-agent` fence. Four background research lanes may serialize at Codex spawn and stretch Step 1.3 wall time on concurrent auth retries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Document as intentional, or restructure so only the inner agent dispatch blocks/backgrounds.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_27

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_27: `lint-fix-loop.sh` uses `--prompt-file` instead of plan-literal `--prompt`
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The plan specified `--prompt "$prompt_body"`; the implementation uses `--prompt-file`. This is a traceability gap versus the plan literal, though functionally OK for typical prompts already written to `prompt.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Document approved deviation in lint-fix-loop.md or switch to --prompt if ARG_MAX is not a concern.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Negotiation inlines Codex auth setup instead of shared helper
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `run-negotiation-round.sh` duplicates Codex auth setup already implemented in `launch-codex-exec.sh` and `check-reviewers.sh`. The next `OPENAI_API_KEY` or auth-contract change can land in the launcher but be missed in negotiation, leaving env-key mode inconsistent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract a shared ephemeral-CODEX_HOME prep helper used by launcher negotiation and health probe when auth changes next.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Dead `external_serial_lock_acquire` failure branch in negotiation
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: The `if ! external_serial_lock_acquire` branch in `run-negotiation-round.sh` appears dead because the helper always returns 0. Serial-lock exhaustion never triggers exit 2 from this check.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Remove dead branch or make acquire return non-zero when lock is not obtained.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

