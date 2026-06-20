### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:49-54
- **Concern**: In-flight guard omits non-empty DESIGN_TMPDIR conjunct. Scenario: Shell only fires in-flight when sidecar is missing, DESIGN_TMPDIR is non-empty, and .bg-wait-active exists (skills/design/scripts/design-step6-prelude.sh:96-98). Without the same conjunct, empty/unset tmpdir can hit exit 1 or probe a bogus path instead of the rc-0 missing-sidecar branch.
- **Proposed resolution**: Pin the exact predicate in step6_prelude_core and step6_cleanup_core: sidecar missing AND design_tmpdir_raw non-empty AND .bg-wait-active present. Add a pytest case with empty rehydrated DESIGN_TMPDIR plus .bg-wait-active and no sidecar asserting rc 0 skip/preserve, not rc 1.



### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/session_env.py:858-868
- **Concern**: [SCOPE-REDUCTION] SKILL Step 6 fence moves to bare `step6` but the plan never specifies a design-run launcher exec branch for bare `step6` / `step6-prelude` / `step6-cleanup`. Scenario: After deleting `design-step6.sh`, `"$HOME/.cache/larch/sessions/design-run-$PPID.sh" step6` hits the default `ERROR=unknown design wrapper verb` branch; Step 6 never runs despite pytest/cli registry work
- **Proposed resolution**: Add a `step6|step6-prelude|step6-cleanup)` case that `exec python3 "$PLUGIN_ROOT/python/cli.py" design "$script" --session-env-path ...` (mirror the step0 bare-verb case); pin that routing in `scripts/test-design-structure.sh`, not only retired `.sh` basename maps



### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/session_env.py:805-869
- **Concern**: SKILL Step 6 moves to bare `step6`, but the plan only documents `.sh` basename remaps and a loose bare-verb allowlist token grep; it never requires extending `_design_run_launcher_text` with a `step6|step6-prelude|step6-cleanup)` case arm that execs `python3 … design "$script"`.. Scenario: After SKILL changes the Step 6 fence to `"$HOME/.cache/larch/sessions/design-run-$PPID.sh" step6`, the launcher hits the final `*)` branch and returns `ERROR=unknown design wrapper verb`; cleanup never runs on the happy path.
- **Proposed resolution**: Add an explicit launcher case arm for `step6|step6-prelude|step6-cleanup)` (same exec pattern as step0 bare verbs) and pin it in `scripts/test-design-structure.sh` with a `contains` check for `design step6 --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID" "$@"` (mirror the Step 2 `.sh` mapping pins).



### FINDING_4:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/design_lifecycle.py:step6_prelude_core/step6_cleanup_core
- **Concern**: In-flight guard omits shell non-empty DESIGN_TMPDIR conjunct. Scenario: Shell only hard-fails when sidecar is missing, DESIGN_TMPDIR is non-empty, and .bg-wait-active exists (design-step6-prelude.sh:96-98, design-step6-cleanup.sh:96-98). Plan bullets mention .bg-wait-active plus missing sidecar but never require design_tmpdir_raw non-empty before the join. A naive Path("") / ".bg-wait-active" check uses cwd, not / like bash, and can exit 1 on preserve paths that shell exits 0.
- **Proposed resolution**: Document and implement in-flight as: sidecar missing AND design_tmpdir_raw non-empty AND (tmpdir / ".bg-wait-active").is_file(); otherwise fall through to missing-sidecar skip/preserve. Mirror in pytest (empty DESIGN_TMPDIR plus cwd .bg-wait-active must not trip in-flight).



### FINDING_5:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/design_lifecycle.py:3649
- **Concern**: Empty DESIGN_TMPDIR probes can resolve to the repo cwd. Scenario: The plan requires empty or unset DESIGN_TMPDIR to take rc-0 missing-sidecar skip/preserve branches, but it also tells the Step 6 helpers to use Path(design_tmpdir_raw) for marker and sidecar checks. In Python, Path("") is ".", unlike the shell path "$DESIGN_TMPDIR/.design-step5c-status.env", which checks "/.design-step5c-status.env" when empty. A stray .pause-requested, .design-step5c-status.env, or .pause-save-complete in the cwd can make prelude, cleanup, or combined step6 pause, validate, or skip cleanup instead of taking the required missing-sidecar branch.
- **Proposed resolution**: After rehydration, if design_tmpdir_raw is empty, do not construct Path("") for any Step 6 marker, sidecar, or pause-complete probe. Have prelude and cleanup emit the missing-sidecar skip/preserve rows, and have combined follow the same non-empty guards as the shell. Only construct Path after the raw value is non-empty, with validation still deferred to the deletion path.



