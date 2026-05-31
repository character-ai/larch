### [rejected] FINDING_11

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_11: **Argv hardening**: `--issue`, `--claude-pid`, `--repo`, `--issue-title`, and `--issue-body-file` are validated (`validate_repo`, `validate_plain_scalar`, numeric checks, regular-file + no-symlink on the body file) in `design-route.sh` / `design-init-runparams.sh`.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Argv hardening**: `--issue`, `--claude-pid`, `--repo`, `--issue-title`, and `--issue-body-file` are validated (`validate_repo`, `validate_plain_scalar`, numeric checks, regular-file + no-symlink on the body file) in `design-route.sh` / `design-init-runparams.sh`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_12: **Symlink refusal** on `.design-route-result.env` / `.design-init-runparams-result.env` in both `phase_driver_write_result_env` and the orchestrator fences matches the Step 3 precedent.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Symlink refusal** on `.design-route-result.env` / `.design-init-runparams-result.env` in both `phase_driver_write_result_env` and the orchestrator fences matches the Step 3 precedent.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_13: **Resume safety**: `step_is_registered` plus `ROUTE=cancel-pause-load` for `LOAD_OK=true` with missing/unregistered `STEP` closes a class of bad pause payloads before the orchestrator jumps steps (`design-route.sh` ~195–241, `SKILL.md` ~272–274).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Resume safety**: `step_is_registered` plus `ROUTE=cancel-pause-load` for `LOAD_OK=true` with missing/unregistered `STEP` closes a class of bad pause payloads before the orchestrator jumps steps (`design-route.sh` ~195–241, `SKILL.md` ~272–274).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_14: **Orchestrator KV merge** uses an allowlisted `case` before `printf -v` — unknown keys cannot become dynamic variable names (`SKILL.md` ~247–263).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Orchestrator KV merge** uses an allowlisted `case` before `printf -v` — unknown keys cannot become dynamic variable names (`SKILL.md` ~247–263).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_15: **REPO forwarding** after a single `resolve-repo.sh` / `gh repo view` resolve reduces wrong-remote `gh` operations on fork/multi-remote checkouts (planned FINDING_1 R4).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **REPO forwarding** after a single `resolve-repo.sh` / `gh repo view` resolve reduces wrong-remote `gh` operations on fork/multi-remote checkouts (planned FINDING_1 R4).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_16: **Pause-load trust chain** remains intact: `design-pause-load.sh` still validates slugs, steps, repos, and emits fixed-token `ERROR=` values; drivers only relay stdout KVs.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Pause-load trust chain** remains intact: `design-pause-load.sh` still validates slugs, steps, repos, and emits fixed-token `ERROR=` values; drivers only relay stdout KVs. No new secret material, `eval` on untrusted input, or unsafe deserializers appear in the diff. Router-flag `jq` merge uses `--argjson` booleans and a fixed filter over a path under `$DESIGN_TMPDIR`. Residual risk (result-env TOCTOU / last-key-wins parsing, collaborator-driven issue content in banners) is **pre-existing or local-user** in scope and not materially worse than Step 3’s file-first handoff; not elevated to Important/Latent under your scope rules.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_22: correctness: skills/design/scripts/design-init-runparams.sh:238-241
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] jq router-flag merge failure logs only to execution-issues.md. Operator sees INIT_STATUS=ok; partition/brainstorm/manual argv flags may not persist across subshells. add_warn on jq failure with operator-visible text in addition to append-tool-failure.sh.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_28

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_28: architecture: skills/design/scripts/design-init-runparams.sh:178-184; skills/design/scripts/design-init-runparams.md:31; skills/design/SKILL.md:398-400
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] INIT_STATUS env-refresh-failed outside plan allowlist ok contract-drift Consumers of documented INIT_STATUS set miss env-refresh-failed handling Extend plan and design-init-runparams.md allowlist or collapse into documented statuses
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_29

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_29: code-quality: skills/design/SKILL.md:265-266
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] No-op loops over _route_warn_lines and _route_error_lines after route merge Dead code suggests incomplete Round 2 pre-branch re-emit step Remove no-op loops or add explicit WARN ERROR re-emit if required
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: code-quality: skills/design/scripts/design-route.sh:38-58
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] plan_block_present duplicates plan-block-read.sh pairing rules. Next marker-rule fix updated only in plan-block-read.sh could leave design-route.sh routing already-planned incorrectly. Extract shared presence helper or single source of truth for marker pairing.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: code-quality: skills/design/scripts/design-route.sh:23-36
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Duplicated validate_plain_scalar/validate_repo in both drivers. Argv validation fixes must be applied twice; risk of skew between route and init drivers. Centralize in lib-phase-driver.sh or lib-design-driver-argv.sh.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

