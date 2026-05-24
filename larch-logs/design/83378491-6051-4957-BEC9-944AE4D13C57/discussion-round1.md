## Decision 1: 1.r phantom probe coverage
- **Question**: Should the new combined wrapper add a phantom probe at the 1.r (plan materialization) site that previously had no phantom probe?
- **Resolution**: Always run probe at all 4 sites — uniform wrapper invocation; 1.r gets a new sub-second phantom probe.
- **Source**: user

## Decision 2: Test harness organization
- **Question**: One combined test harness covering both wrappers, or two separate harnesses (`test-rebase-checkpoint-probe.sh` and `test-phantom-probe-with-warn.sh`)?
- **Resolution**: Two separate harnesses — clearer scope per file; two Makefile targets.
- **Source**: user

## Decision 3: Forked-target argv pass-through
- **Question**: How does the wrapper handle `--base-remote upstream --base-ref main` for `forked_target=true` (currently appended conditionally inside the macro's M1)?
- **Resolution**: Optional `--base-remote <r>` / `--base-ref <b>` argv pass-through; SKILL.md call sites pass them conditionally on `forked_target=true`. Wrapper does NOT detect forked state itself.
- **Source**: user

## Decision 4: Hard constraints (already pinned by issue body)
- **Question**: Any hard constraints to flag beyond the issue body's Constraints section?
- **Resolution**: No additions. Locked-in constraints (binding for sketches and plan):
  - lib-quiet.sh contract (source at top, larch_quiet_init, emit/emit_kv, one emit_breadcrumb per invocation: `→ rebase-probe: <step-prefix> <short-name>`)
  - Bash 3.2 portability (BASH_AUTHORING.md §3)
  - Foreground markers (BASH_AUTHORING.md §4): denylist entry, banner, per-anchor comments
  - script-md-siblings.md: sibling .md files required for every new .sh
  - Conflict path behavior unchanged: REBASE_OUTCOME=conflict + CONFLICT_FILES= populated
- **Source**: codebase (issue body Constraints section)

## Decision 5: Out-of-scope hard line
- **Question**: Any scope items in the issue body that need re-confirmation as out of scope?
- **Resolution**: Out-of-scope items stand: Step 0 / implement-bootstrap.sh (handled by #2732 / #2735–#2738), Step 7a body absorption (separate follow-up), ship-pr.sh argv changes (separate follow-up), Conflict Resolution Procedure changes (wrapper preserves existing signal).
- **Source**: codebase (issue body Out of scope section)
