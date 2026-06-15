## Proposed Design Outline

### Goals
- Replace three separate Bash calls (phantom probe, branch assertion, `git rev-parse`) with one wrapper call on the `STATUS=complete` path.
- Emit `BRANCH=`, `PHANTOM_*`, and `COMMIT_SHA=` from a single `step-2-post-dispatch.sh` call.
- Let Step 4 consume `$COMMIT_SHA` directly instead of calling `git rev-parse --short HEAD`.

### Non-goals
- No changes to bail semantics or the `claude_fallback` carve-out.
- No changes to the Python dispatcher (`python/cli.py implement step2-dispatch`).
- No changes to any other probe site (8-pre-ship, rebase checkpoints).

### Approach sketch
- Create `skills/implement/scripts/step-2-post-dispatch.sh`: sources `lib-quiet.sh` and `lib-phantom-probe.sh`, calls `phantom_probe_with_warn "2-post-dispatch"`, inlines branch assertion and SHA, emits `BRANCH=` and `COMMIT_SHA=`.
- Update `SKILL.md` `STATUS=complete` block: one call replaces two, parse `PHANTOM_*`, `BRANCH=`, and `COMMIT_SHA=`.
- Update `SKILL.md` Step 4: `sha=$COMMIT_SHA` replaces `sha=$(git rev-parse --short HEAD)`.
- Update `phantom-probe.md` registry and `test-implement-structure.sh` checks.

### Surfaces in scope
- `skills/implement/scripts/step-2-post-dispatch.sh` (new)
- `skills/implement/scripts/step-2-post-dispatch.md` (new sibling doc)
- `skills/implement/SKILL.md`
- `skills/implement/references/phantom-probe.md`
- `scripts/test-implement-structure.sh`

### Open questions
- None.
