# show.sh contract

`skills/show-skill/scripts/show.sh` resolves a skill name to its `SKILL.md` path.

## Usage

```
show.sh <skill-name>
```

`<skill-name>` may be bare (`implement`), `larch:`-prefixed (`larch:review`), or `/`-prefixed (`/implement`). Both prefixes are stripped before lookup.

## Output (stdout)

```
STATUS=found
SKILL_PATH=<absolute-path>
```

or, when no match:

```
STATUS=not-found
```

Always exits 0. Callers parse `STATUS` without `eval`/`source`.

## Search order

1. `${CLAUDE_PLUGIN_ROOT}/skills/<name>/SKILL.md`
2. `$(git rev-parse --show-toplevel)/.claude/skills/<name>/SKILL.md`
3. `${CLAUDE_PLUGIN_ROOT}/.claude/skills/<name>/SKILL.md`

First match wins. When `CLAUDE_PLUGIN_ROOT` is unset, the script derives the plugin root from its own path: `skills/show-skill/scripts/` + `../../..` = repo root (three levels up).

## Safety

Names containing `/` or `..` are rejected with `STATUS=not-found` — no path traversal is possible.

## Callers

- `skills/show-skill/SKILL.md` Step 1

## Test harness

`skills/show-skill/scripts/test-show-skill.sh` — regression harness covering bare name resolution, prefix stripping, path-traversal rejection, and `STATUS=not-found` on missing skills. Wired into `make lint` via the `test-show-skill` target.
