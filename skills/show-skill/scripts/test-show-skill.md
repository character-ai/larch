# test-show-skill.sh contract

Regression harness for `skills/show-skill/scripts/show.sh`. See `skills/show-skill/scripts/show.md` for the primary contract.

## Usage

```
bash skills/show-skill/scripts/test-show-skill.sh
```

Run from the repo root. Requires `CLAUDE_PLUGIN_ROOT` set or the script resolves it automatically from its own path.

## Coverage

- Bare name resolution (`show-skill` → found)
- `larch:` prefix stripping
- `/` prefix stripping
- Non-existent skill → `STATUS=not-found`
- Empty argument → `STATUS=not-found`
- Path-traversal rejection (`../`, `/` in name)
