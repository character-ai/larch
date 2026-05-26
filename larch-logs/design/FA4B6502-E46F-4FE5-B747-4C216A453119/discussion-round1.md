## Decision 1: Audit scope — include `generate-code-flow-diagram.sh` callsite

- **Question**: Should the fix be scoped strictly to `is_small_non_runtime_change` in `step-7a.sh`, or include a quick grep audit for similar `origin/main`-vs-`forked_target` callsites in the implement skill?
- **Resolution**: Quick grep audit too. Audit returned two real callsites:
  1. `skills/implement/scripts/step-7a.sh:81` — `is_small_non_runtime_change` (primary, named in issue #2844)
  2. `skills/implement/scripts/generate-code-flow-diagram.sh:58` — `git diff` against `origin/main` to enumerate changed files for the LLM prompt
  Both must honor `forked_target` and switch to `upstream/main` when true. The third hit (`oos-disposition-gate.md`) is documentation only — no fix.
- **Source**: user (scope confirmation) + codebase (audit grep)

## Decision 2: Backward compatibility (non-fork path)

- **Question**: When `forked_target` is unset/false, should both classifiers behave bit-for-bit identically to today?
- **Resolution**: Yes. The legacy non-fork path must keep using `origin/main` exactly as today; only the fork path (`forked_target=true`) switches to `upstream/main`. The existing `diagram-skip` test case (which currently passes on `origin/main`) must continue to pass unchanged.
- **Source**: codebase (issue body specifies "read `forked_target` argv (already plumbed)" — preserving the false branch is implicit)

## Decision 3: Test regression coverage

- **Question**: What is the minimum viable test coverage for the fix?
- **Resolution**: Add at least one new harness case to `skills/implement/scripts/test-step-7a.sh` that demonstrates the classifier skip path firing on a `forked_target=true` fixture with an `upstream/main` base and no `origin/main`. (Test fixture shape is implementation detail; scope here only mandates that the new case exists and is gated by `forked_target=true`.)
- **Source**: codebase (issue body: "add a harness regression case"; existing pattern is `diagram-skip`)
