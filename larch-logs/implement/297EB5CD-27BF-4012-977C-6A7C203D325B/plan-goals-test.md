## Goal
Implement issue #3629: [IMPLEMENTING] [BUG] (URGENT) Replace ALL requirements of Python >= 3.12 with 3.11 EVERYWHERE…\n\n## Bug.

## Implementation Plan
## Bug

Every Python runtime requirement and CI configuration in larch references **Python 3.12**, but the actual runtime floor is **3.11** (as evidenced by `python/test_ship.py` and `scripts/relevant-checks.sh`, both of which already correctly say 3.11). This discrepancy breaks `make py-test` / `make py-lint` for anyone running Python 3.11 and produces confusing mismatches across the repo.

Replace **every** occurrence of `3.12` (in Python context) with `3.11` uniformly.

## All occurrences (grep result, excluding .venv / node_modules / larch-logs / mermaid-lint JS packages)

| File | Line(s) | Current | Fix |
|------|---------|---------|-----|
| `python/pyproject.toml` | 4 | `requires-python = ">=3.12"` | `>=3.11` |
| `python/pyrightconfig.json` | 3 | `"pythonVersion": "3.12"` | `"3.11"` |
| `python/.pylintrc` | 90 | `py-version=3.12` | `py-version=3.11` |
| `.github/workflows/ci.yaml` | 51, 152, 184, 318, 426, 445 | `python-version: "3.12"` / `["3.12"]` | `"3.11"` / `["3.11"]` |
| `scripts/implement-bootstrap.sh` | 659 | `Python ship driver requires Python 3.12 or newer` | `3.11 or newer` |
| `docs/installation-and-setup.md` | 302 | `Python 3.12+` | `Python 3.11+` |
| `docs/linting.md` | 30, 31 | two inline references to `Python 3.12 jobs` and `version 3.12 or newer` | `3.11` |

Files already correct (no change needed):
- `scripts/relevant-checks.sh` — already checks `>= 3.11`
- `scripts/test-relevant-checks.sh` — fixture already says `3.11`
- `python/test_ship.py` — already says `Python >= 3.11`


## Test plan

After the fix, this should return zero results (excluding `.venv`):

```sh
command grep -rn "3\.12" python/ scripts/ docs/ .github/ \
  --include="*.toml" --include="*.json" --include="*.sh" \
  --include="*.md" --include="*.yaml" --include="*.cfg" \
  | command grep -v ".venv"
```

`make py-lint` and `make py-test` must pass on Python 3.11.
