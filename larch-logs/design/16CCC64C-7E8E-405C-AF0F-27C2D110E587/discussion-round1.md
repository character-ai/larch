## Decision 1: Fence count convention location
- **Question**: Where should the convention to update test-implement-fence-shape.sh when adding fences to skills/implement/SKILL.md live?
- **Resolution**: .claude/rules/ file — augment skill-editing-trace.md (which already fires on skills/**/SKILL.md edits) with a note about the structural harness
- **Source**: user

## Decision 2: Pyright lambda pattern discoverability
- **Question**: How to make the `# type: ignore[arg-type]` suppression pattern for monkeypatch.setattr lambdas discoverable?
- **Resolution**: .claude/rules/ file — new rule triggered on python/test_*.py edits
- **Source**: user
