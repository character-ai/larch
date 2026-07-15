## Proposed Design Outline

### Goals
- Add a `RUNTIME` evidence tier to `analyze-bugs` by running pytest tests and mapped make harnesses from fix commits.
- Downgrade verdicts to `SUSPECT` when runtime tests fail; annotate unmapped zones as `UNVERIFIED_RUNTIME`.
- Cap runtime verification to `--runtime-max M` (default 10) newest fixes without blocking existing MECH/TRIAGE/DEEP pipeline.

### Non-goals
- No live GitHub or vendor-CLI calls (coordinator-side only, offline).
- No authoring new harnesses (close-criteria sibling handles that).
- No changes to triage/deep agent stages or read-only agent contracts.

### Approach sketch
- Add new `RuntimeResult` frozen dataclass and `HARNESS_MAP` constant in `analyze_bugs.py`.
- Add a new `runtime_verify` function: discover test files from `git show --name-only` filtered to `python/tests/`, run pytest with timeout; check zone coverage via `HARNESS_MAP`, run `make <target>` with timeout.
- Add new `runtime_main` CLI subcommand in `analyze_bugs.py`; SKILL.md calls it after Stage 3 report when `--runtime-max > 0`.
- Update `_final_verdict_with_tier` to return tier `RUNTIME` when runtime results are present for a fix.
- Store per-fix runtime results in `$RUN_DIR/runtime-results.jsonl`.

### Surfaces in scope
- `python/larch/issue/analyze_bugs.py`: new constants, dataclass, functions, CLI subcommand.
- `.claude/skills/analyze-bugs/SKILL.md`: document `--runtime-max`, new stage, tier semantics.
- `python/tests/issue/` (new file): harness-map resolution, test-file discovery, timeout/failure-downgrade, tier rendering, budget cap.

### Open questions
- None.
