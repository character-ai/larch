## Decision 1: Scope — all three sub-tasks
- **Question**: Address all three OOS sub-tasks (extract Python dedup to helper, document fence divergence, add run_loop integration test), or a subset?
- **Resolution**: All three sub-tasks are in scope.
- **Source**: user

## Decision 2: Fence-boundary semantics — document, not unify
- **Question**: Document the divergent fence-boundary models between parse-plan-commands.awk and the Python dedup, or unify them?
- **Resolution**: Document the intentional divergence only. Do NOT unify; the two parsers serve different concerns and unification carries regression risk across two well-tested paths.
- **Source**: user

## Decision 3: Behavior preservation (hard constraint)
- **Question**: Must the Python-extraction sub-task preserve dedup behavior exactly?
- **Resolution**: Yes — pure refactor. The extracted helper must produce byte-identical dedup output. All existing dedup tests in test-plan-review-loop.sh must continue to pass unchanged (section-aware 4-dup removal, Constraints protection, unclosed-fence non-collapse, nested/fenced/tagged-fenced cases, python-failure backup restore, non-numeric-output backup restore).
- **Source**: codebase

## Decision 4: New helper wiring + sibling doc (hard constraint)
- **Question**: How must a new standalone script be integrated to satisfy repo invariants?
- **Resolution**: New .py helper requires a sibling .md (script-md-siblings rule), PLUGIN_ROOT-relative path resolution with a test-overridable env var mirroring the existing DESIGN_DRIVER_SH / INVOKE_PLAN_VALIDATOR_SH / CHECK_PLAN_SIZE_SH pattern, and the eval-extraction tests must export that var so the extracted _run_post_apply_pipeline can locate the script.
- **Source**: codebase

## Decision 5: Bash 3.2 portability + lint (hard constraint)
- **Question**: What portability/lint invariants constrain the .sh edits?
- **Resolution**: Any plan-review-loop.sh edits stay Bash 3.2-compatible (BASH_AUTHORING.md §3); run `bash scripts/relevant-checks.sh` after edits. No behavior change to the loop caller beyond removing the inline heredoc.
- **Source**: codebase
