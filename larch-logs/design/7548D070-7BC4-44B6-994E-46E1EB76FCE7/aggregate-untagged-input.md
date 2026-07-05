### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/design/references/approval-gates.md:161-173
- **Concern**: Gate C and Step 1d.7 use bare $REPO_ROOT without a per-fence bind step. Scenario: /design documents that Bash does not preserve shell state; Gate C and 1d.7 run guideline helpers in fresh subshells. Persisting REPO_ROOT in source-env.sh does not populate $REPO_ROOT there, so --repo-root is omitted, read_guidelines falls back to plugin-cache cwd, and the silent-miss bug can persist despite writer recovery
- **Proposed resolution**: In each Presentation/persist helper Bash fence, read REPO_ROOT from $DESIGN_TMPDIR/source-env.sh (or source current-design-env-$PPID.sh) before the first present-note/persist call; keep the planned empty-root repair stop

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/state/session_env.py:774-787
- **Concern**: REPO_ROOT recovery must parse shlex-quoted exports, not mirror the bool regex. Scenario: _export_line writes export REPO_ROOT via shlex.quote; a bool-style ^export REPO_ROOT=...$ regex will not recover quoted paths, so init_runparams refresh can still drop REPO_ROOT and re-open the clobber path
- **Proposed resolution**: Implement _recover_prior_path using parse_allowlisted_env_line (or equivalent shlex split) and wire it into write-design-env when --repo-root is absent

### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/core/test_architectural_guidelines.py (planned from plan.txt:89-99)
- **Concern**: The planned Gate C regression is helper-level, not the `skip_approve_requested=true` Gate C contract. Scenario: The acceptance regression could pass while the skip-approve Gate C instructions stop invoking persistence, omit the bounded `Warnings` append on a non-zero persist, or still advance to auto-approval and Step 5 after failure.
- **Proposed resolution**: Revise the planned regression to pin the Gate C branch itself. Exercise an available Gate C harness, or add a narrow markdown contract test if no executable harness exists, that verifies the skip-approve branch runs `present-note --repo-root "$REPO_ROOT"` and `persist-design-assessment --repo-root "$REPO_ROOT"`, writes the assessment artifact, and stops with the bounded warning on forced persist failure.

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/design/references/approval-gates.md:161-173
- **Concern**: Gate C and Step 1d.7 use `$REPO_ROOT` without a load step. Scenario: The plan adds `--repo-root "$REPO_ROOT"` to `approval-gates.md` and `design-outline.md`, but `/design` Gate C and Step 1d.7 run those helpers from prompt-side Bash fences. Bash state does not persist across fences, and Step 0 stdout does not emit `REPO_ROOT`. `$REPO_ROOT` stays empty, so `present-note` / `persist-design-assessment` still fall back to plugin-cache cwd and can treat consumer guidelines as absent on `--skip-approve`.
- **Proposed resolution**: Before the first guideline helper in each gate, load the Step 0 capture: source `$DESIGN_TMPDIR/source-env.sh` in the same Bash fence, or emit `REPO_ROOT=` from `step0_session_main` stdout and require a repair stop when it is empty before any helper call. Do not rely on `session read-key` against `source-env.sh` as written today; lines use an `export` prefix.

### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/design/references/approval-gates.md:161-173
- **Concern**: Gate C and Step 1d.7 pass --repo-root "$REPO_ROOT" but never bind it from source-env.sh. Scenario: The plan updates presentation commands to use --repo-root "$REPO_ROOT", yet Gate C and Step 1d.7 run as orchestrator-side direct CLI calls in fresh Bash subshells that do not source $DESIGN_TMPDIR/source-env.sh or current-design-env. REPO_ROOT stays empty, helpers still fall back to plugin-cache cwd, and the assessment can be skipped despite persistence in source-env.sh.
- **Proposed resolution**: Add a binding step before every guideline helper call: read REPO_ROOT from $DESIGN_TMPDIR/source-env.sh via session read-key (or source that file once), then apply the existing repair-stop when empty; mirror the same pattern in design-outline.md.

### FINDING_13:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/approval-gates.md:161-173
- **Concern**: Gate C guideline commands assume $REPO_ROOT is set in fresh Bash fences. Scenario: Gate C and Step 1d.7 run direct python/cli.py helper fences; Bash does not keep shell state. Updating docs to pass --repo-root "$REPO_ROOT" without sourcing $DESIGN_TMPDIR/source-env.sh in the same fence leaves REPO_ROOT empty, so helpers still resolve guidelines from plugin-cache cwd and can treat a present repo as absent (the original silent-skip bug).
- **Proposed resolution**: Require each guideline helper fence to source $DESIGN_TMPDIR/source-env.sh first (or inline-read REPO_ROOT from that file) before present-note / persist-design-assessment; keep the empty-REPO_ROOT repair stop after binding.

### FINDING_15:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:99
- **Concern**: Accepted fail-closed regression is only testing the helper rc, not the Gate C warning and stop contract. Scenario: The plan can still ship with `persist_design_assessment_main` returning non-zero while Gate C forgets to append the bounded `Warnings` line or advances to Step 5, and the planned test stays green
- **Proposed resolution**: Add a focused regression or validation step that exercises the Gate C non-zero persistence branch and asserts the bounded warning is recorded and the flow does not prompt, auto-approve, or transition to Step 5
