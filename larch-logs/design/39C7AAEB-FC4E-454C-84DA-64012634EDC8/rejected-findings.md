### [Plan Review] FINDING_1

### FINDING_1: Phase-A materialize-diff includes non-implementation noise after Step 7a flush
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Phase-A `materialize-diff` runs after Step 7a log flush but returns an unfiltered merge-base..HEAD diff. Step 7a pre-ship flush commits `larch-logs` (and related run-log batches) before Phase A, so orchestrator deviation judgment may see large non-implementation noise and emit false warnings or miss real code deviations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Make materialize-diff exclude mechanical non-implementation paths (at minimum larch-logs/**) or scope diff to manifest/plan-cited paths; document the filter in implement SKILL Phase A


### [Plan Review] FINDING_2

### FINDING_2: Bespoke repo-root resolver duplicates existing consumer-repo discovery
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: A bespoke repo-root resolver duplicates existing consumer-repo discovery. Parallel `CLAUDE_PROJECT_DIR`/cwd logic may drift from `repo_roots.consumer_repo_root` and `checks.py` patterns, yielding the wrong root when plugin cache cwd differs from the consumer repo.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend python/repo_roots.py (or reuse checks.py project-dir helper) for CLAUDE_PROJECT_DIR preference; call it from read_guidelines() with --repo-root test override only


### [Plan Review] FINDING_3

### FINDING_3: Architectural-guidelines CLI verbs pinned in wrong registry test harness
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: CLI registry tests target the design port harness for architectural-guidelines verbs. Architectural-guidelines is not a design lifecycle domain, so pinning it in `test_design_cli_ports.py` will not guard `_REGISTRY`/`_MACHINE_STDOUT_KEYS` for read/materialize-diff/write-staged-assessment/pin-note-from-staged.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add registry assertions in python/test_architectural_guidelines.py (or implement CLI port test) for all four verbs and machine-stdout keys


### [Plan Review] FINDING_9

### FINDING_9: Phase B pins staged assessment without verifying diff fingerprint
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: Phase B pins staged assessments to the current HEAD without verifying the stored diff fingerprint. On the fresh path, Step 8 can run postbump rebase after Phase A and before `compose_pr_body`. The plan then pins the old assessment to the new HEAD, so PR/final-summary output can surface stale deviation warnings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: In pin_note_from_staged, recompute the current materialized diff hash for the stored base and compare DIFF_FINGERPRINT before pinning. On mismatch, invalidate and return unconsumable, or route to prompt-side Phase A before compose. Keep semantic assessment out of Python.


### [Plan Review] FINDING_10

### FINDING_10:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:35-64
- **Concern**: [SCOPE-REDUCTION] Two-phase staged/durable HEAD pinning plus PR-body and final-summary surfacing exceeds issue acceptance. Scenario: Issue acceptance requires absent-file no-op, design gate notes, and implement warnings only; Phase B pin, diff_fingerprint, invalidate/reassess loops, ship.py hooks, and final_report append add substantial moving parts beyond chat-level warnings
- **Proposed resolution**: Defer Phase B durable surfacing to a follow-up: Phase A chat/execution-issues warning only for v1; drop pin_note_from_staged, note_consumable, and PR/final-summary append until durable surfacing is explicitly accepted


### [Plan Review] FINDING_11

### FINDING_11:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:225-235; skills/implement/SKILL.md:537-540,720-721; scripts/test-implement-fence-shape.sh:149-166
- **Concern**: [SCOPE-REDUCTION] New architectural-guidelines launcher scripts duplicate the existing direct cli.py launcher pattern. Scenario: The plan adds three runtime .sh files even though existing /implement fences already launch python/cli.py through larch-run and the fence harness accepts .py targets. The issue needs the new CLI verbs, not extra wrapper files.
- **Proposed resolution**: Remove the three step-architectural-guidelines-*.sh files. Use direct one-line fences such as bash "$IMPLEMENT_TMPDIR/larch-run.sh" python/cli.py architectural-guidelines read. Keep only the fence-count/test updates needed for those direct fences.


