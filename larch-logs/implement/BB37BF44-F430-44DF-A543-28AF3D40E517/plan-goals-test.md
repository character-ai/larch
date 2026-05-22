## Goal
Speed up test-harnesses CI job by caching site-packages, splitting requirements, and rebalancing shards by CI timing

## Implementation Plan

### Feature
Speed up `test-harnesses` CI job: (1) cache installed site-packages, (2) split requirements to drop pre-commit, (3) rebalance 20 shards by CI timing.

### Files to modify
- `.github/workflows/ci.yaml` — add site-packages cache step, change install to new requirements file
- `.github/workflows/requirements-test-harnesses.txt` — new file, only pyyaml==6.0.2
- `Makefile` — rebalanced test-harnesses-1 through test-harnesses-20

### Approach

#### Change 1: requirements-test-harnesses.txt (new file)
Create `.github/workflows/requirements-test-harnesses.txt`:
```
# PyYAML is the only dependency needed for test-harnesses.
# pre-commit is not needed here; it is installed via requirements-lint.txt
# for the lint/shellcheck/agent-sync jobs only.
pyyaml==6.0.2
```

#### Change 2: ci.yaml — test-harnesses job
Replace `cache-dependency-path: .github/workflows/requirements-lint.txt` with
`cache-dependency-path: .github/workflows/requirements-test-harnesses.txt`.

Add a site-packages cache step AFTER `actions/setup-python` but BEFORE the
`pip install` step:
```yaml
- name: Cache installed Python packages
  id: cache-site-packages
  uses: actions/cache@v5
  with:
    path: ~/.local/lib/python${{ steps.setup-python.outputs.python-version }}/site-packages
    key: ${{ runner.os }}-pip-site-${{ steps.setup-python.outputs.python-version }}-${{ hashFiles('.github/workflows/requirements-test-harnesses.txt') }}
- name: Install lint dependencies
  if: steps.cache-site-packages.outputs.cache-hit != 'true'
  run: pip install -r .github/workflows/requirements-test-harnesses.txt
```

Note: change the install step to use `requirements-test-harnesses.txt`, and add
`if: steps.cache-site-packages.outputs.cache-hit != 'true'` condition.

The `setup-python` `cache: pip` + `cache-dependency-path` line also needs updating
to reference `requirements-test-harnesses.txt`.

#### Change 3: Makefile shard rebalancing (LPT from CI timing data)
Based on CI timing from run 26263091066 (2026-05-22, "Bump version to 34.0.24"),
scraped LARCH_HARNESS_TIMING from all 20 shards.

New shard assignments (LPT greedy, sorted by descending CI time):
- Shard 1: test-check-reviewers (43.97s)
- Shard 2: test-launch-cursor-ci (36.02s)
- Shard 3: test-dispatch-code-voters-happy (31.97s)
- Shard 4: test-dispatch-code-voters-edge-and-r3-claude (31.90s)
- Shards 5-20: ~30.3s each (14-17 tests each)

Max shard: 43.97s, Min shard: 30.32s


## Test plan
After implementing:
1. `scripts/test-harness-shards-coverage.sh` — verifies all tests are present, no gaps/typos
2. CI green on the PR
