# `scripts/test-harness-shards-coverage.sh`

## Purpose

Structural regression harness for the `test-harnesses-N` Makefile partition. It prevents silent harness coverage loss when a new `test-*` recipe target is added but not assigned to a shard, when a stale shard prerequisite points at no recipe, or when a harness appears in multiple shards.

This sibling contract exists because `.claude/rules/script-md-siblings.md` requires every script and test harness under `scripts/` to carry a neighboring `<basename>.md` contract.

## Invariants

- **Set equality**: every lowercase-hyphenated `test-*` recipe target in `Makefile` whose recipe does not invoke `pytest`, except documented standalone carve-outs, must appear in exactly one `test-harnesses-N:` prerequisite list. Targets that invoke `pytest` in their recipe are excluded from shard coverage: they duplicate the `python-tests` CI job (#5429).
- **Self-reference**: `test-harness-shards-coverage` is excluded from the individual-harness set comparison, but must appear as the first prerequisite of whichever `test-harnesses-N:` shard contains it so partition bugs surface before other harnesses on that shard run. The script discovers the guard-containing shard from the Makefile rather than hardcoding it, so later heavy-test-only shards can follow the guard shard.
- **Single physical line**: each `test-harnesses-N:` rule must stay on one physical line with no `\` continuation. The parser reads those rules literally instead of folding Make continuations.
- **Naming convention**: `test`-prefixed recipe targets use lowercase hyphenated names (`test-foo-bar:`). Targets like `test_foo:`, `testFoo:`, or `test-foo_bar:` (underscore after the first hyphen) fail loudly so they cannot escape the `test-*` inventory. The parser walks every `^test[^[:space:]:]*:` recipe line and validates each name against `^test-[a-z0-9-]+$`, so any deviation anywhere in the suffix is caught.
- **`.PHONY` membership**: every shard-bound `test-*` recipe target — including `test-harness-shards-coverage` itself — must appear in some `.PHONY:` declaration. The script unions all `.PHONY:` lines (folding backslash continuations), reports any individual-list target missing from that union, and adds an explicit assertion for `test-harness-shards-coverage` (which is excluded from the inventory by the carve-out filter but still requires `.PHONY` membership — without it, a same-named file or directory could shadow the guard target and silently skip the partition check). This catches the "added a recipe and shard membership but forgot `.PHONY`" failure mode.

## Carve-Outs

The Makefile documents opt-in evaluation targets and full-run convenience targets that are intentionally not part of `test-harnesses`: `test-eval-set-structure`, `test-eval-research-baseline-flag`, `test-review-and-fix` (a local-dev convenience wrapper that runs all review-and-fix sections sequentially; CI uses the section variants `test-review-and-fix-dispatch` and `test-review-and-fix-convergence` instead), `test-stall-recovery-report` (a local-dev convenience wrapper that delegates to `test-stall-recovery-report-1`, `test-stall-recovery-report-2`, and `test-stall-recovery-report-3`; CI shards use those three targets directly), and `test-lib-design-tmpdir` (retired stub kept for installed-plugin compatibility until the `_DIRECT_TARGET_RULES` entry ships without the lib-design-tmpdir mapping; the recipe is a no-op `@:`). The script carries the same carve-out list as a single source of truth in the `CARVE_OUTS` shell variable near the top of `scripts/test-harness-shards-coverage.sh`; both the inventory parser and the naming-violation scan consume that variable via the shared `is_carve_out()` awk function (`CARVE_OUT_FN`). When adding another standalone carve-out, update both the Makefile comments near that target and the `CARVE_OUTS` variable in the same change; there is no second list to keep in sync inside the script.

## Makefile Wiring

`Makefile` defines:

- `test-harness-shards-coverage:` running `bash scripts/test-harness-shards-coverage.sh` and `bash scripts/test-harness-shards-coverage.sh --self-test`.
- The guard-owning `test-harnesses-N:` rule with `test-harness-shards-coverage` as the first prerequisite (currently `test-harnesses-1:`; the harness discovers which shard that is — do not rely on a stale hardcoded id).
- `test-harnesses:` as an aggregate over every declared `test-harnesses-N` (currently `test-harnesses-1` through `test-harnesses-6`).

When adding a new harness target, add it to `.PHONY`, add its recipe, and assign it to exactly one `test-harnesses-N:` shard prerequisite list. Rebalance shard lists when timing drift makes a shard materially slower than the `test-render-findings-batch` floor documented in `docs/linting.md`. Review launcher coverage is now the shard-bound Python pytest target `test-launch-review`.

## Pytest Partition Guard (retired #5429)

`scripts/lint-harness-pytest-partition.py` is no longer invoked by this script.
After pruning all pytest-wrapper targets from the CI shards (#5429), none of the
`ENFORCED` files' targets exist in the shard lists, so the partition guard has
nothing to check and has been removed from the non-`--self-test` `main()` path.
See `scripts/lint-harness-pytest-partition.md`.

## Self-Test Mode

`--self-test` runs embedded synthetic Makefile fixtures without reading the real `Makefile`. It covers:

- Happy path.
- Missing target: a recipe exists but no shard names it.
- Orphan in shards: a shard names a non-existent recipe.
- Duplicate across shards.
- Backslash-continuation violation.
- Naming-convention violation (`test_foo:` — bad first suffix character).
- Underscore naming violation (`test-foo_bar:` — bad mid-suffix character; widened parser case).
- Self-reference not first: `test-harness-shards-coverage` placed second on its owning shard.
- Self-reference non-last: `test-harness-shards-coverage` remains first on its owning shard while a later shard exists.
- Aggregate missing shard: `test-harnesses:` drops one of the declared `test-harnesses-N` shards.
- Aggregate extra shard: `test-harnesses:` lists an unexpected prerequisite.
- Missing `.PHONY`: a shard-bound `test-*` target absent from every `.PHONY:` declaration.

Negative cases assert both non-zero exit and a stable stderr substring.

## Edit-In-Sync

Changes to the parser, invariant set, standalone carve-outs, self-test cases, or Makefile shard layout must update this contract and `docs/linting.md` together. Changes that rename a harness must update the recipe target, `.PHONY`, exactly one `test-harnesses-N:` shard prerequisite list, and any sibling contract that cites the old target.
