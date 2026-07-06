## Proposed Design Outline

### Goals
- Add three mechanical lints (A3 wire-artifact pairing, A4 unguarded empty-array, A5 gh-timeout enforcement).
- Append six guideline entries to `ARCHITECTURAL_GUIDELINES.md` (Part C) and create `.claude/rules/wrapper-sentinel-before-stdout.md` (B2).
- Thread a default timeout through `_retry_read` in `python/larch/git/gh.py` (A5 code change).

### Non-goals
- A1 (if/elif command-grep lint) and A2 (tempfile dir= lint): tracked in #6472 and #6473.
- Creating `ARCHITECTURAL_INVARIANTS.md` or deciding B3's home: tracked in #6471.
- Backfilling all possible wire-artifact basenames; initial manifest covers run-log and design/implement sidecar families only.

### Approach sketch
- A3: New Python lint module `lint_wire_artifact_pairing.py` + standalone manifest JSON + reason-bearing baseline JSON; registered in `cli.py` and `Makefile`.
- A4: Extend `scripts/lint-bash32.sh` with a per-file two-pass awk check: collect empty-array assignments, then flag unguarded expansions of those names.
- A5 code: Add `default_timeout` parameter to `_retry_read`; callers that omit `timeout=` inherit the default.
- A5 lint: Extend `lint_subprocess_via_runner.py` to also flag `runner.run(["gh", ...])` calls outside `python/larch/git/gh.py`.
- Part C + B2: Append six `ARCHITECTURAL_GUIDELINES.md` entries; create `.claude/rules/wrapper-sentinel-before-stdout.md` with the exact B2 body.

### Surfaces in scope
- `python/larch/lint/lint_wire_artifact_pairing.py` (new)
- `python/wire-artifact-manifest.json` (new)
- `python/wire-artifact-pairing-baseline.json` (new)
- `scripts/lint-bash32.sh`
- `python/larch/git/gh.py`
- `python/larch/lint/lint_subprocess_via_runner.py`
- `ARCHITECTURAL_GUIDELINES.md`
- `.claude/rules/wrapper-sentinel-before-stdout.md` (new)
- `Makefile` and `python/larch/cli.py` (wire lint + register verb)

### Open questions
- None.
