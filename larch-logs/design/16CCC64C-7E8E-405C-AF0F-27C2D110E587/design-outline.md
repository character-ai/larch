## Proposed Design Outline

### Goals
- Add a rule note to `.claude/rules/skill-editing-trace.md` that `scripts/test-implement-fence-shape.sh` must be updated when adding Bash fences to `skills/implement/SKILL.md`.
- Add a new `.claude/rules/` file (triggered on `python/test_*.py` edits) documenting the `# type: ignore[arg-type]` pattern for `monkeypatch.setattr` lambda arguments.

### Non-goals
- Auto-detect or auto-fix stale `EXPECTED_NEW` values in the fence harness.
- Expand lint-fix-loop to auto-apply `# type: ignore` comments.
- Change how `scripts/test-implement-fence-shape.sh` itself works.

### Approach sketch
- Augment `.claude/rules/skill-editing-trace.md`: add a "Fence count harness" bullet naming `EXPECTED_NEW` in `scripts/test-implement-fence-shape.sh` as a required update target when new fences land in `skills/implement/SKILL.md`.
- Create `.claude/rules/python-test-monkeypatch-types.md` with `paths: ["python/test_*.py"]` frontmatter; document the established `# type: ignore[arg-type]` pattern for `monkeypatch.setattr` lambdas, citing `test_pr_body.py:218` as the canonical example.

### Surfaces in scope
- `.claude/rules/skill-editing-trace.md` (update)
- `.claude/rules/python-test-monkeypatch-types.md` (new file)

### Open questions
- None.
