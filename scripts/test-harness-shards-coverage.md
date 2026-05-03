# `scripts/test-harness-shards-coverage.sh`

## Purpose

Structural regression harness for the `test-harnesses-N` Makefile partition. It prevents silent harness coverage loss when a new `test-*` recipe target is added but not assigned to a shard, when a stale shard prerequisite points at no recipe, or when a harness appears in multiple shards.

This sibling contract exists because `AGENTS.md` requires every script and test harness under `scripts/` to carry a neighboring `<basename>.md` contract.

## Invariants

- **Set equality**: every lowercase-hyphenated `test-*` recipe target in `Makefile`, except documented standalone carve-outs, must appear in exactly one `test-harnesses-N:` prerequisite list.
- **Self-reference**: `test-harness-shards-coverage` is excluded from the individual-harness set comparison, but must appear as the first prerequisite of `test-harnesses-6:` so partition bugs surface before other shard-6 harnesses run.
- **Single physical line**: each `test-harnesses-N:` rule must stay on one physical line with no `\` continuation. The parser reads those rules literally instead of folding Make continuations.
- **Naming convention**: `test`-prefixed recipe targets use lowercase hyphenated names (`test-foo-bar:`). Targets like `test_foo:` or `testFoo:` fail loudly so they cannot escape the `test-*` inventory.

## Carve-Outs

The Makefile documents opt-in evaluation targets that are intentionally not part of `test-harnesses`: `test-eval-set-structure` and `test-eval-research-baseline-flag`. The script carries the same carve-out list explicitly. When adding another standalone carve-out, update both the Makefile comments near that target and this script's exclusion list in the same change.

## Makefile Wiring

`Makefile` defines:

- `test-harness-shards-coverage:` running `bash scripts/test-harness-shards-coverage.sh` and `bash scripts/test-harness-shards-coverage.sh --self-test`.
- `test-harnesses-6:` with `test-harness-shards-coverage` as the first prerequisite.
- `test-harnesses:` as an umbrella over `test-harnesses-1` through `test-harnesses-6`.

When adding a new harness target, add it to `.PHONY`, add its recipe, and assign it to exactly one `test-harnesses-N:` shard prerequisite list. Rebalance shard lists when timing drift makes a shard materially slower than the `test-validate-citations` floor documented in `docs/linting.md`.

## Self-Test Mode

`--self-test` runs embedded synthetic Makefile fixtures without reading the real `Makefile`. It covers:

- Happy path.
- Missing target: a recipe exists but no shard names it.
- Orphan in shards: a shard names a non-existent recipe.
- Duplicate across shards.
- Backslash-continuation violation.
- Naming-convention violation.
- Self-reference handling: the coverage harness is excluded from the individual set and present in shard 6.

Negative cases assert both non-zero exit and a stable stderr substring.

## Edit-In-Sync

Changes to the parser, invariant set, standalone carve-outs, self-test cases, or Makefile shard layout must update this contract and `docs/linting.md` together. Changes that rename a harness must update the recipe target, `.PHONY`, exactly one `test-harnesses-N:` shard prerequisite list, and any sibling contract that cites the old target.
