# `scripts/test-harness-shards-coverage.sh`

## Purpose

Structural regression harness for the `test-harnesses-N` Makefile partition. It prevents silent harness coverage loss when a new `test-*` recipe target is added but not assigned to a shard, when a stale shard prerequisite points at no recipe, or when a harness appears in multiple shards.

This sibling contract exists because `AGENTS.md` requires every script and test harness under `scripts/` to carry a neighboring `<basename>.md` contract.

## Invariants

- **Set equality**: every lowercase-hyphenated `test-*` recipe target in `Makefile`, except documented standalone carve-outs, must appear in exactly one `test-harnesses-N:` prerequisite list.
- **Self-reference**: `test-harness-shards-coverage` is excluded from the individual-harness set comparison, but must appear as the first prerequisite of the last `test-harnesses-N:` shard so partition bugs surface before other harnesses on that shard run. The script discovers the highest declared `N` from the Makefile rather than hardcoding it, so the invariant tracks any reshard automatically.
- **Single physical line**: each `test-harnesses-N:` rule must stay on one physical line with no `\` continuation. The parser reads those rules literally instead of folding Make continuations.
- **Naming convention**: `test`-prefixed recipe targets use lowercase hyphenated names (`test-foo-bar:`). Targets like `test_foo:`, `testFoo:`, or `test-foo_bar:` (underscore after the first hyphen) fail loudly so they cannot escape the `test-*` inventory. The parser walks every `^test[^[:space:]:]*:` recipe line and validates each name against `^test-[a-z0-9-]+$`, so any deviation anywhere in the suffix is caught.
- **`.PHONY` membership**: every shard-bound `test-*` recipe target — including `test-harness-shards-coverage` itself — must appear in some `.PHONY:` declaration. The script unions all `.PHONY:` lines (folding backslash continuations), reports any individual-list target missing from that union, and adds an explicit assertion for `test-harness-shards-coverage` (which is excluded from the inventory by the carve-out filter but still requires `.PHONY` membership — without it, a same-named file or directory could shadow the guard target on the last shard and silently skip the partition check). This catches the "added a recipe and shard membership but forgot `.PHONY`" failure mode.

## Carve-Outs

The Makefile documents opt-in evaluation targets that are intentionally not part of `test-harnesses`: `test-eval-set-structure` and `test-eval-research-baseline-flag`. The script carries the same carve-out list as a single source of truth in the `CARVE_OUTS` shell variable near the top of `scripts/test-harness-shards-coverage.sh`; both the inventory parser and the naming-violation scan consume that variable via the shared `is_carve_out()` awk function (`CARVE_OUT_FN`). When adding another standalone carve-out, update both the Makefile comments near that target and the `CARVE_OUTS` variable in the same change — there is no second list to keep in sync inside the script.

## Makefile Wiring

`Makefile` defines:

- `test-harness-shards-coverage:` running `bash scripts/test-harness-shards-coverage.sh` and `bash scripts/test-harness-shards-coverage.sh --self-test`.
- The last `test-harnesses-N:` rule with `test-harness-shards-coverage` as the first prerequisite (currently `test-harnesses-6:`; the partition guard discovers the highest-N rule, so the invariant tracks any reshard automatically).
- `test-harnesses:` as an umbrella over every declared `test-harnesses-N` (currently `test-harnesses-1` through `test-harnesses-6`).

When adding a new harness target, add it to `.PHONY`, add its recipe, and assign it to exactly one `test-harnesses-N:` shard prerequisite list. Rebalance shard lists when timing drift makes a shard materially slower than the `test-validate-citations` floor documented in `docs/linting.md`.

## Self-Test Mode

`--self-test` runs embedded synthetic Makefile fixtures without reading the real `Makefile`. It covers:

- Happy path.
- Missing target: a recipe exists but no shard names it.
- Orphan in shards: a shard names a non-existent recipe.
- Duplicate across shards.
- Backslash-continuation violation.
- Naming-convention violation (`test_foo:` — bad first suffix character).
- Underscore naming violation (`test-foo_bar:` — bad mid-suffix character; widened parser case).
- Self-reference not first: `test-harness-shards-coverage` placed second on the last shard.
- Umbrella missing shard: `test-harnesses:` drops one of the declared `test-harnesses-N` shards.
- Umbrella extra shard: `test-harnesses:` lists an unexpected prerequisite.
- Missing `.PHONY`: a shard-bound `test-*` target absent from every `.PHONY:` declaration.

Negative cases assert both non-zero exit and a stable stderr substring.

## Edit-In-Sync

Changes to the parser, invariant set, standalone carve-outs, self-test cases, or Makefile shard layout must update this contract and `docs/linting.md` together. Changes that rename a harness must update the recipe target, `.PHONY`, exactly one `test-harnesses-N:` shard prerequisite list, and any sibling contract that cites the old target.
