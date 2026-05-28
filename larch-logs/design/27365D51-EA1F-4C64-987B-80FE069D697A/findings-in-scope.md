### FINDING_1: design-log-publish must preserve PUBLISH_OK failure contract
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Edge, Codex-Edge, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-dyn-error-contract, Codex-dyn-error-contract
- **Severity**: important
- **Concern**: Validator failures in `scripts/design-log-publish.sh` must not use the validator's raw nonzero exit, because callers parse structured `PUBLISH_OK=false` stdout for expected publish failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Use `larch_design_tmpdir_validate "$DESIGN_TMPDIR" || { emit_publish_result false; exit 0; }` (validator already prints to stderr); place immediately after the lines 65-68 required-arg block, before the lines 84-88 `-d` check
  - From Codex-Arch: Use script-local failure paths: design-log-publish should emit_publish_result false and exit 0; design-pause-save should emit_fail "tmpdir-invalid" or equivalent after validation
  - From Cursor-Edge, Codex-Edge: Preserve structured output: on validator failure emit PUBLISH_OK=false PR_NUMBER= PR_URL= and exit 0
  - From Cursor-Innovation, Codex-Innovation: Wrap validation in existing emit helpers: design-log-publish should emit_publish_result false and exit 0; design-pause-save should emit_fail tmpdir-invalid
  - From Cursor-Pragmatic, Codex-Pragmatic: Replace the planned || exit $? with if ! larch_design_tmpdir_validate "$DESIGN_TMPDIR"; then emit_publish_result false; exit 0; fi
  - From Cursor-dyn-error-contract, Codex-dyn-error-contract: Use larch_design_tmpdir_validate "$DESIGN_TMPDIR" || { emit_publish_result false; exit 0; } after emit_publish_result is defined

### FINDING_2: design-pause-save must preserve PAUSE_OK failure contract
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Edge, Codex-Edge, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-dyn-error-contract, Codex-dyn-error-contract
- **Severity**: important
- **Concern**: Validator failures in `scripts/design-pause-save.sh` must route through `emit_fail` so pause callers receive `PAUSE_OK=false` and `ERROR=tmpdir-invalid` instead of a raw exit 2 with only stderr.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Use `larch_design_tmpdir_validate "$DESIGN_TMPDIR" || emit_fail "tmpdir-invalid"` immediately after the lines 62-63 unset/missing checks (mirror `design-pause-load.sh` adaptation)
  - From Codex-Arch: Use script-local failure paths: design-log-publish should emit_publish_result false and exit 0; design-pause-save should emit_fail "tmpdir-invalid" or equivalent after validation
  - From Cursor-Edge, Codex-Edge, Cursor-Pragmatic, Codex-Pragmatic: Use larch_design_tmpdir_validate "$DESIGN_TMPDIR" || emit_fail "tmpdir-invalid" after the existing unset/directory checks
  - From Cursor-Innovation, Codex-Innovation: Wrap validation in existing emit helpers: design-log-publish should emit_publish_result false and exit 0; design-pause-save should emit_fail tmpdir-invalid
  - From Cursor-dyn-error-contract, Codex-dyn-error-contract: Use larch_design_tmpdir_validate "$DESIGN_TMPDIR" || emit_fail "tmpdir-invalid" after the existing required-arg and directory checks

### FINDING_3: write-design-current-env must validate after absolute-path checks and map failure to argv rc
- **Reviewer(s)**: Codex-Arch, Cursor-Edge, Codex-Edge, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: important
- **Concern**: Placing allowlist validation before the existing absolute-path check changes the relative-path diagnostic and exit code contract for `scripts/write-design-current-env.sh`; validator failures should occur after absolute-path validation and map to the script's invalid-argv exit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Place larch_design_tmpdir_validate after the absolute-path check and map failure to exit 1 for this script
  - From Cursor-Edge, Codex-Edge: Keep the existing absolute-path check before larch_design_tmpdir_validate, then validate the absolute DESIGN_TMPDIR_ARG before writing outputs
  - From Cursor-Innovation, Codex-Innovation: Place validation after the existing absolute --design-tmpdir check and map validation failure to exit 1 while preserving the validator stderr
  - From Cursor-Pragmatic, Codex-Pragmatic: Leave the existing absolute-path check first, then call larch_design_tmpdir_validate "$DESIGN_TMPDIR_ARG" || exit 1 before writing exports

### FINDING_4: emit-design-plan-preview must keep warning-and-exit-0 degradation
- **Reviewer(s)**: Codex-Arch, Cursor-Edge, Codex-Edge, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-dyn-error-contract, Codex-dyn-error-contract
- **Severity**: important
- **Concern**: Top-level validator use in `skills/design/scripts/emit-design-plan-preview.sh` would turn existing Step 3 and Gate C display-only warning paths into hard exit 2 failures, breaking empty, missing, or invalid tmpdir behavior and pinned tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Move validation inside step3 and gatec after the existing -z or ! -d friendly branch and before any plan.txt read or marker touch
  - From Cursor-Edge, Codex-Edge: Render the existing step3/gatec invalid DESIGN_TMPDIR warning and exit 0 on validator failure, before reading plan.txt
  - From Cursor-Innovation, Codex-Innovation: Keep validation inside the existing variant-specific missing or invalid branch, printing the current warning and exiting 0 instead of using || exit $?
  - From Cursor-Pragmatic, Codex-Pragmatic: Keep validation inside the variant branches: treat empty, missing, or validator-failed tmpdir as the existing warning-and-exit-0 path, and only read plan.txt after validation succeeds
  - From Cursor-dyn-error-contract, Codex-dyn-error-contract: Move validation into each variant after the existing -d check and route validator failure to the same variant warning plus exit 0

### FINDING_5: check-plan-size must not reuse rc 2 for allowlist failures
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Pragmatic, Cursor-dyn-error-contract, Codex-dyn-error-contract
- **Severity**: important
- **Concern**: `skills/design/scripts/check-plan-size.sh` reserves rc 2 for missing or malformed plan artifacts with `PLAN_SIZE_STATUS`; validator allowlist failures should remain argv errors rather than producing rc 2 without status.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic, Codex-Pragmatic: Map validator failure to exit 3 for this helper, preserving the existing argv-error contract and avoiding new PLAN_SIZE_STATUS semantics
  - From Cursor-dyn-error-contract, Codex-dyn-error-contract: Use larch_design_tmpdir_validate "$DESIGN_TMPDIR" || exit 3 so validation remains a stderr-only argv error

### FINDING_6: SECURITY.md must document expanded tmpdir validation coverage
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The hardening plan changes security-relevant `--design-tmpdir` validation coverage but omits the required `SECURITY.md` update, leaving documented coverage stale and contradictory.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements, Codex-Requirements: Include SECURITY.md in the plan and update the /design --design-tmpdir allowlist paragraph to describe the expanded production caller coverage while preserving the existing validator behavior notes.

### FINDING_7: finalize-plan must preserve FINALIZE_PLAN_STATUS on invalid tmpdirs
- **Reviewer(s)**: Cursor-dyn-error-contract, Codex-dyn-error-contract
- **Severity**: latent
- **Concern**: A bare validator exit in `skills/design/scripts/finalize-plan.sh` would bypass the helper's `FINALIZE_PLAN_STATUS` reporting contract for design tmpdir and artifact failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-error-contract, Codex-dyn-error-contract: Use larch_design_tmpdir_validate "$DESIGN_TMPDIR" || { emit_kv FINALIZE_PLAN_STATUS missing-design-tmpdir; exit 1; } or document and test a new invalid-design-tmpdir status
