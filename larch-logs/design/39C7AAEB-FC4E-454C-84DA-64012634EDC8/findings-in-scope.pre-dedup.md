### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/architectural_guidelines.py:107-108
- **Concern**: Phase-A materialize-diff runs after Step 7a log flush but returns unfiltered merge-base..HEAD diff. Scenario: Step 7a pre-ship flush commits larch-logs (and related run-log batches) before Phase A; orchestrator deviation judgment then sees large non-implementation noise and may emit false warnings or miss real code deviations
- **Proposed resolution**: Make materialize-diff exclude mechanical non-implementation paths (at minimum larch-logs/**) or scope diff to manifest/plan-cited paths; document the filter in implement SKILL Phase A



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/architectural_guidelines.py:100-103
- **Concern**: Bespoke repo-root resolver duplicates existing consumer-repo discovery. Scenario: Parallel CLAUDE_PROJECT_DIR/cwd logic will drift from repo_roots.consumer_repo_root and checks.py patterns; wrong root when plugin cache cwd differs from consumer repo
- **Proposed resolution**: Extend python/repo_roots.py (or reuse checks.py project-dir helper) for CLAUDE_PROJECT_DIR preference; call it from read_guidelines() with --repo-root test override only



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_design_cli_ports.py:157-159
- **Concern**: CLI registry tests target the design port harness for architectural-guidelines verbs. Scenario: architectural-guidelines is not a design lifecycle domain; pinning it in test_design_cli_ports.py will not guard _REGISTRY/_MACHINE_STDOUT_KEYS for read/materialize-diff/write-staged-assessment/pin-note-from-staged
- **Proposed resolution**: Add registry assertions in python/test_architectural_guidelines.py (or implement CLI port test) for all four verbs and machine-stdout keys



### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:35-64
- **Concern**: [SCOPE-REDUCTION] Two-phase staged/durable HEAD pinning plus PR-body and final-summary surfacing exceeds issue acceptance. Scenario: Issue acceptance requires absent-file no-op, design gate notes, and implement warnings only; Phase B pin, diff_fingerprint, invalidate/reassess loops, ship.py hooks, and final_report append add substantial moving parts beyond chat-level warnings
- **Proposed resolution**: Defer Phase B durable surfacing to a follow-up: Phase A chat/execution-issues warning only for v1; drop pin_note_from_staged, note_consumable, and PR/final-summary append until durable surfacing is explicitly accepted



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/design-outline.md:78-81
- **Concern**: Planned design-outline.md edits omit rewriting the `--skip-approve` Approval prompt block that still short-circuits before guideline consultation. Scenario: SKILL.md narrows the carve-out to run Output, guideline consultation, and gate presentation before auto-approve, but design-outline.md still tells the orchestrator to write `.outline-approved` immediately, skip `AskUserQuestion`, and avoid printing the outline on the auto-approve path; implementers can follow the stale reference and skip deviation surfacing at Step 1d.7 under `-s`
- **Proposed resolution**: Rewrite the Approval prompt section explicitly: on `skip_approve_requested=true`, still run Output, call `architectural-guidelines read`, print the clean/deviation/invalid note per the new presentation rules, then write `.outline-approved` and emit the auto-approve breadcrumb



### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/residual-bash-paths.txt
- **Concern**: Plan adds four new Bash scripts but does not list them in the residual-Bash manifest. Scenario: The four new paths (step-architectural-guidelines-read.sh, step-architectural-guidelines-materialize.sh, step-architectural-guidelines-write-staged.sh, test-architectural-guidelines-step.sh) are outside scripts/residual-bash-paths.txt, so pre-commit shellcheck/bash-syntax and lint-bash32 may skip or mis-handle them and make lint can fail after merge
- **Proposed resolution**: Add ### UPDATED: scripts/residual-bash-paths.txt registering all four new script paths alongside existing skills/implement/scripts/*.sh rows



### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/ship-pr-exit-matrix.md:239-241
- **Concern**: Proposed reassessment block calls invalidate_implement_note via CLI but cli.py plan registers no invalidate verb. Scenario: ship-pr-exit-matrix.md tells the orchestrator to call invalidate via CLI when reassessing after CI-fix/conflict commits, yet ### UPDATED: python/cli.py only adds read, materialize-diff, write-staged-assessment, and pin-note-from-staged; implementers will improvise artifact deletion or skip invalidation
- **Proposed resolution**: Either add python/cli.py architectural-guidelines invalidate (thin wrapper around invalidate_implement_note) to the CLI allowlist and tests, or rewrite the ship-pr-exit-matrix/conflict-resolution reassessment bullets to rely solely on the Phase A entry artifact-clear list already specified in skills/implement/SKILL.md



### FINDING_8:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:771-773
- **Concern**: Gate C `--skip-approve` carve-out still jumps to Step 5 without guideline consultation. Scenario: The plan fixes Step 1d.7 `--skip-approve` explicitly (execute outline output + guideline note, then auto-approve), but Step 4b still says `proceed directly to Step 5 without calling AskUserQuestion` when `skip_approve_requested=true`. That bypasses the acceptance requirement to surface guideline deviations at final-plan approval, including under `--skip-approve`.
- **Proposed resolution**: Mirror the Step 1d.7 pattern in Step 4b: always run Gate C preview + `architectural-guidelines read` deviation note (clean/deviation/invalid branches) before writing `.outline-approved` equivalent or printing `⏩ 4b`; only then auto-approve to Step 5. Reconcile or delete the conflicting skip paragraph so it cannot short-circuit `approval-gates.md`.



### FINDING_9:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:225-235; skills/implement/SKILL.md:537-540,720-721; scripts/test-implement-fence-shape.sh:149-166
- **Concern**: [SCOPE-REDUCTION] New architectural-guidelines launcher scripts duplicate the existing direct cli.py launcher pattern. Scenario: The plan adds three runtime .sh files even though existing /implement fences already launch python/cli.py through larch-run and the fence harness accepts .py targets. The issue needs the new CLI verbs, not extra wrapper files.
- **Proposed resolution**: Remove the three step-architectural-guidelines-*.sh files. Use direct one-line fences such as bash "$IMPLEMENT_TMPDIR/larch-run.sh" python/cli.py architectural-guidelines read. Keep only the fence-count/test updates needed for those direct fences.



### FINDING_10:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:39-46,109-114,128-133
- **Concern**: Phase A has no explicit staged body contract for the orchestrator-authored assessment text. Scenario: write-staged-assessment receives assessment text, but the plan only specifies a staged env sidecar and diff snapshot. Phase B is forbidden to reassess, so pin_note_from_staged has no specified staged warning body to copy into the durable note.
- **Proposed resolution**: Specify a staged assessment body file, for example architectural-guideline-staged-assessment.md. Have write-staged-assessment write that body plus sidecar KVs, and have pin_note_from_staged copy only that staged body into the durable note.



### FINDING_11:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:48-56,257-263,341-344; python/ship.py:1365-1447
- **Concern**: Phase B pins staged assessments to the current HEAD without verifying the stored diff fingerprint. Scenario: On the fresh path, Step 8 can run postbump rebase after Phase A and before compose_pr_body. The plan then pins the old assessment to the new HEAD, so PR/final-summary output can surface stale deviation warnings.
- **Proposed resolution**: In pin_note_from_staged, recompute the current materialized diff hash for the stored base and compare DIFF_FINGERPRINT before pinning. On mismatch, invalidate and return unconsumable, or route to prompt-side Phase A before compose. Keep semantic assessment out of Python.



### FINDING_12:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:114,128-133,237-242
- **Concern**: Reference docs call invalidate_implement_note via CLI, but the plan registers no invalidate CLI verb. Scenario: The planned ship-pr-exit-matrix update can instruct the orchestrator to call a nonexistent CLI command on CI-fix reassessment paths. That breaks the recovery path instead of preserving warning behavior.
- **Proposed resolution**: For minimum change, remove the prompt-side CLI invalidation instruction and rely on Phase A entry clearing stale artifacts. If a prompt-side invalidation call remains required, add and test an architectural-guidelines invalidate CLI verb.



