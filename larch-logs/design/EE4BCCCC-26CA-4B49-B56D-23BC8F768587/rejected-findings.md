### [Plan Review] FINDING_1

### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-rebase-macro.sh:12-53
- **Concern**: Plan omits Makefile lint structural harnesses that still pin deleted script paths. Scenario: After deleting the 16 helpers, test-implement-rebase-macro.sh still reads scripts/rebase-checkpoint-probe.sh (line 12), test-implement-structure.sh still requires that file and bootstrap rebase-checkpoint-probe.sh strings (lines 221-222, 313), test-implement-fence-shape.sh still fakes create-branch.sh --check (line 356), and test-implement-step8-exit3-first-fixer.sh still requires scripts/gh-run-logs.sh in ship-pr-exit-matrix (line 19); make lint fails on harness shards 4, 14, and 16
- **Proposed resolution**: Add ### UPDATED entries for all four harnesses retargeting pins to python/cli.py push checkpoint-probe, pr create-branch, and gh run-logs (and drop probes of deleted .sh/.md files)




### [Plan Review] FINDING_2

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/push.py:274-304; scripts/rebase-checkpoint-probe.sh:79-337; scripts/test-rebase-checkpoint-probe.sh:559-735
- **Concern**: Checkpoint-probe parity omits the larch-log conflict pre-pass. Scenario: The deleted Bash probe resolves larch-logs/* conflicts, continues the rebase, filters mixed conflicts, and handles empty/already-applied continue failures. The planned Python update only adds ROUTE and fork defaults, so /implement checkpoints can regress to ROUTE=conflict on larch-log-only conflicts.
- **Proposed resolution**: Add the existing trivial-conflict pre-pass semantics to python/cli.py push checkpoint-probe and cover the larch-log-only, consecutive, mixed, continue-conflict, and continue-failure cases in python/test_push.py before deleting the Bash probe.




### [Plan Review] FINDING_3

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: blocking
- **Focus area**: risk-integration
- **Location**: scripts/lib-phantom-probe.md:3; scripts/test-implement-rebase-macro.sh:12-53; scripts/test-implement-step8-exit3-first-fixer.sh:19-21; scripts/test-implement-structure.sh:221-222
- **Concern**: The plan omits live harness and doc files that contain retired full-path references. Scenario: After manifest rows are added for scripts/rebase-checkpoint-probe.sh and scripts/gh-run-logs.sh, lint-retired-scripts will still find these references. make lint can also fail because test-implement-rebase-macro reads scripts/rebase-checkpoint-probe.sh after the plan deletes it.
- **Proposed resolution**: Add these files to Files to modify/create and retarget their assertions/prose to python/cli.py push checkpoint-probe and python/cli.py gh run-logs, or remove obsolete assertions tied only to the deleted Bash file.




### [Plan Review] FINDING_4

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation Phase2
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/push.py:274-292; scripts/rebase-checkpoint-probe.sh:242-358; scripts/test-rebase-checkpoint-probe.sh:559-815
- **Concern**: push checkpoint-probe cutover omits the Bash probe's larch-log conflict pre-pass and empty-continue skip loop. Scenario: Bash resolves larch-logs-only rebase conflicts, loops through consecutive trivial conflicts, and skips empty already-applied commits before ROUTE=continue. The proposed Python path only calls rebase.rebase_push once, so the same checkpoint returns ROUTE=conflict or ROUTE=bail after the helper is deleted.
- **Proposed resolution**: Add minimum parity to python/push.py before deletion: resolve larch-logs/* conflicts, continue/skip empty commits, re-derive CONFLICT_FILES after partial resolution, and port focused cases from scripts/test-rebase-checkpoint-probe.sh.




### [Plan Review] FINDING_5

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation Phase2
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: Makefile:120,140,144,580-630; scripts/test-implement-rebase-macro.sh:12-31; scripts/test-implement-structure.sh:221-222,313; scripts/test-implement-step8-exit3-first-fixer.sh:19; scripts/test-implement-fence-shape.sh:354-357
- **Concern**: Plan omits live /implement harness updates for deleted helper paths. Scenario: make lint still runs these harnesses. After deletion, test-implement-rebase-macro reads scripts/rebase-checkpoint-probe.sh, test-implement-structure requires the deleted script and md contract, step8 still expects scripts/gh-run-logs.sh, and fence-shape stubs the old create-branch.sh branch check.
- **Proposed resolution**: Add these harnesses to the plan and update assertions to the CLI targets and Python files, or remove only assertions made obsolete by the cutover.




### [Plan Review] FINDING_6

### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/push.py:274-304; scripts/rebase-checkpoint-probe.sh:255-337
- **Concern**: Checkpoint-probe cutover omits larch-log trivial-conflict pre-pass. Scenario: The plan deletes scripts/rebase-checkpoint-probe.sh but only adds ROUTE and fork defaults to push checkpoint-probe. When a checkpoint rebase conflicts only on larch-logs/*, the Bash wrapper auto-resolves and continues, while the proposed Python path would return conflict and skip phantom, regressing the parity gate.
- **Proposed resolution**: Port the existing larch-logs-only conflict loop into the Python checkpoint path with a focused test before deleting the wrapper. Do not broaden the rebase domain beyond that parity behavior.




### [Plan Review] FINDING_7

### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-rebase-macro.sh:10-28; scripts/test-implement-fence-shape.sh:36-37; scripts/test-implement-step8-exit3-first-fixer.sh:19-21; scripts/test-implement-structure.sh:221-222
- **Concern**: Files-to-modify list misses live /implement harnesses pinned to deleted helpers. Scenario: Following the plan deletes scripts/rebase-checkpoint-probe.sh and rewrites ship-pr-exit-matrix and implement fences, but make lint still runs these harnesses. They read the deleted script, assert old fence counts, or require scripts/gh-run-logs.sh, so verification fails after the cutover.
- **Proposed resolution**: Add these harnesses to the plan and update only their pinned expectations to the cli.py verbs and new fence counts. Keep the deleted helper-specific parity harnesses removed.




### [Plan Review] FINDING_8

### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/push.py:274-304
- **Concern**: Plan adds ROUTE and --forked-target but omits the bash probe trivial larch-logs/* conflict pre-pass. Scenario: After cutover, /implement checkpoints 1.r/4.r/7.r/7a.r stall on larch-logs rebase conflicts that scripts/rebase-checkpoint-probe.sh auto-resolves today; retargeted scripts/test-rebase-checkpoint-probe.sh cases 18-22 fail or behavior is deleted with the bash probe
- **Proposed resolution**: Add the larch-logs trivial-conflict loop (and empty-continue handling) from scripts/rebase-checkpoint-probe.sh into checkpoint_probe_main before Step 3 consumer repoint; port harness cases 18-22 into python/test_push.py




### [Plan Review] FINDING_9

### FINDING_9:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/extract-closes-issue-from-pr.sh:17
- **Concern**: Missed live bash consumer of deleted resolve-repo.sh. Scenario: After resolve-repo.sh is deleted, PR-body issue recovery silently resolves REPO empty and exits 0, so an existing PR with Closes #N is no longer adopted.
- **Proposed resolution**: Add scripts/extract-closes-issue-from-pr.sh to the plan and replace the resolver call with python3 "$SCRIPT_DIR/../python/cli.py" gh resolve-repo while preserving the empty-on-failure contract.




### [Plan Review] FINDING_10

### FINDING_10:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/push.py:274-294; scripts/rebase-checkpoint-probe.sh:79-337
- **Concern**: Checkpoint CLI parity omits existing larch-log conflict recovery. Scenario: Deleting rebase-checkpoint-probe.sh removes the current auto-resolution loop for larch-logs conflicts, stale CONFLICT_FILES re-derivation, and empty-continue skip recovery, so routine checkpoint rebases can route to conflict or bail instead of continue.
- **Proposed resolution**: Port only the existing Bash recovery cases into the Python checkpoint path, with focused tests mirroring the current harness cases 19-25, or defer deleting the Bash probe until parity exists.




### [Plan Review] FINDING_11

### FINDING_11:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: blocking
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-rebase-macro.sh:12-49; scripts/test-implement-structure.sh:221-222; scripts/test-implement-fence-shape.sh:36-37,354-357; scripts/test-implement-step8-exit3-first-fixer.sh:19-21
- **Concern**: Plan changes implement checkpoint and gh-run-log references but omits live structural harness updates. Scenario: make lint still runs these harnesses, and they currently require scripts/rebase-checkpoint-probe.sh, old fence counts, create-branch.sh bootstrap mocks, and scripts/gh-run-logs.sh text.
- **Proposed resolution**: Add these harnesses to the plan and update their assertions/mocks to the new cli.py targets and fence counts.




### [Plan Review] FINDING_12

### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: blocking
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-structure.sh:221-222
- **Concern**: Structural harness still requires retired rebase-checkpoint-probe.sh paths. Scenario: After deleting scripts/rebase-checkpoint-probe.sh and repointing bootstrap.py, require() lines 221-222 and 313 still grep for the .sh path; make test-implement-structure (make lint via test-harnesses-16) fails even when runtime cutover is correct
- **Proposed resolution**: Add ### UPDATED: scripts/test-implement-structure.sh: repoint require() rows to python/cli.py push checkpoint-probe and pr create-branch; drop retired-path literals per migration rules




### [Plan Review] FINDING_13

### FINDING_13:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-fence-shape.sh:36-37
- **Concern**: /implement fence-shape harness not listed for SKILL checkpoint fence edits. Scenario: Changing skills/implement/SKILL.md fences from scripts/rebase-checkpoint-probe.sh to python/cli.py push checkpoint-probe changes old/new fence counts; fake_run still keys on create-branch.sh --check (line 356) while bootstrap will call pr create-branch --check; make test-implement-fence-shape fails
- **Proposed resolution**: Add ### UPDATED: scripts/test-implement-fence-shape.sh (and .md if present): refresh EXPECTED_OLD/EXPECTED_NEW and resume-bootstrap stubs for CLI argv shapes




### [Plan Review] FINDING_14

### FINDING_14:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-step-7a.sh:493-744
- **Concern**: Step 7a harness assertions still name rebase-checkpoint-probe.sh. Scenario: Plan updates stubs to intercept python/cli.py push checkpoint-probe but says preserve existing assertions; call-order and assert_contains strings still require rebase-checkpoint-probe.sh, so the harness fails after cutover even when step_7a.py is correct
- **Proposed resolution**: Update test-step-7a.sh (and skills/implement/scripts/step-7a.md contract prose) to expect python/cli.py push checkpoint-probe in calls.log and ordering checks




### [Plan Review] FINDING_15

### FINDING_15:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/shared/skill-design-principles.md:78
- **Concern**: Retired-path literal outside planned reference sweep. Scenario: Line 78 embeds rebase-push.sh; after manifest rows for scripts/rebase-push.sh, make lint-retired-scripts flags this file though it is not in the plan file list
- **Proposed resolution**: Add skills/shared/skill-design-principles.md to reference cleanup (use push rebase / cli.py verb in the example) or extend step 6 prose to include skills/shared/*




### [Plan Review] FINDING_16

### FINDING_16:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/extract-closes-issue-from-pr.sh:13-18
- **Concern**: Plan omits a live resolve-repo.sh consumer. Scenario: The PR-body recovery helper still calls $SCRIPT_DIR/resolve-repo.sh, so deleting that helper leaves a live caller uncut and can fail make lint-retired-scripts once the manifest row is added
- **Proposed resolution**: Add UPDATED: scripts/extract-closes-issue-from-pr.sh and replace the resolver call with python3 cli.py gh resolve-repo while preserving the empty-output fallback




### [Plan Review] FINDING_17

### FINDING_17:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/rebase-checkpoint-probe.md:28-45, python/push.py:274-304
- **Concern**: Checkpoint-probe parity list omits larch-log conflict auto-resolution. Scenario: After deleting rebase-checkpoint-probe.sh, larch-log-only rebase conflicts can route as ROUTE=conflict instead of being auto-resolved and continued, regressing the existing /implement checkpoint contract
- **Proposed resolution**: Extend the python/push.py checkpoint-probe work to include the larch-logs/* trivial-conflict pre-pass and focused Python coverage for larch-log-only and mixed conflict cases




### [Plan Review] FINDING_18

### FINDING_18:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: code-quality
- **Location**: scripts/test-implement-rebase-macro.sh:12-53, scripts/test-implement-structure.sh:221-223, scripts/test-implement-fence-shape.sh:354-357, scripts/test-implement-step8-exit3-first-fixer.sh:19-21
- **Concern**: Plan omits live make lint harnesses tied to the deleted helper surfaces. Scenario: make lint runs these harnesses; after the proposed SKILL.md, checkpoint-probe, and ship-pr reference changes, they still read deleted scripts or assert retired script names
- **Proposed resolution**: Add UPDATED entries for these existing harnesses and revise their assertions to the new cli.py verbs and python/push.py checkpoint surface




