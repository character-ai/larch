## Decision 1: Overall scope — full P1 issue
- **Question**: How much of the linter-suite migration is in scope for #3687?
- **Resolution**: Full issue. Port the leaf linters to Python, relocate the already-Python `scripts/lint-skill-invocations.py` into the `python/` runtime, AND complete the relevant-checks / lint-fix-loop orchestration cutover (delete the 4 bash orchestration scripts, repoint all consumers). Large diff accepted; the Step 2b.5 plan-size gate may later offer to split.
- **Source**: user (Step 1c)

## Decision 2: lint-skill-invocations.py handling
- **Question**: `scripts/lint-skill-invocations.py` is already Python but outside `python/` and not in `cli.py`. Relocate or leave?
- **Resolution**: Relocate into the `python/` flat layout, register a `lint` cli.py verb, add colocated pytest, repoint its pre-commit hook (`entry: python scripts/lint-skill-invocations.py`), and delete `scripts/test-lint-skill-invocations.sh`.
- **Source**: user (Step 1c)

## Decision 3: Behavior-preservation contract
- **Question**: How faithful must each port be?
- **Resolution**: Behavior-preserving. Per playbook step 5, run each retargeted `test-*.sh` harness once as a parity gate against the new CLI surface, then delete it and replace with colocated `python/test_<module>.py`. Preserve exit codes and the violation set each linter catches.
- **Source**: codebase (docs/python-migration.md)

## Decision 4: Cutover discipline
- **Question**: Shims, dual paths, or hard cutover?
- **Resolution**: Hard cutover, no `.sh` shims, no `LARCH_*_IMPL` selectors. All consumers repointed in the same change to `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" lint <verb> [args...]`.
- **Source**: codebase (playbook decision log + sh-to-py tracker)

## Decision 5: Non-goals — bash-staying linters
- **Question**: Which linters must NOT be touched?
- **Resolution**: Out of scope and untouched: `lint-bash32.sh`, `lint-bare-grep-probe.sh`, `lint-awk-multibyte-regex.sh`, `lint-renderer-substitution-safety.sh`, `pre-commit-shellcheck.sh`. They lint the remaining bash surface and are scoped down/retired later at E3 (#3691). Hooks stay bash.
- **Source**: issue #3687 + tracker

## Decision 6: Hard constraints — must stay green / behavior preserved
- **Question**: What existing behavior must be preserved?
- **Resolution**: `make lint`, `make py-lint`, `make py-test` stay green. Each linter must keep firing from its three invocation seams — Makefile `lint-*` targets, `.pre-commit-config.yaml` hooks, and the relevant-checks dispatcher. The relevant-checks dispatcher's byte-budget, validation, and helper-failure behaviors must be preserved (asserted by `test-relevant-checks-byte-budget`, `test-relevant-checks-validation`, `test-relevant-checks-helper-failure`). `lint-fix-loop`'s external-agent (codex/cursor) dispatch semantics preserved (already ported in `checks.py`).
- **Source**: codebase (DoD + existing harnesses)

## Decision 7: cli.py registration must be merge-order-agnostic
- **Question**: Does cli.py registration collide with in-flight work?
- **Resolution**: In-flight `[DESIGNING]` #3668 (F2, session/state) also registers verbs in `python/cli.py`. The `_REGISTRY` edit here must be additive and merge-order-agnostic (append `lint` verbs; do not assume #3668's verbs are present or absent). Secondary-surface overlap only; no blocked-by edge required between #3687 and #3668.
- **Source**: pre-design overlap survey

## Note: downstream — CI harness shard balance
Deleting ~12 `test-*.sh` linter harnesses removes them from the 20-way `test-harnesses-N` shards in the Makefile / `.github/workflows/ci.yaml`. Replacement coverage moves to `make py-test` (pytest). Re-balancing the 20 bash shards after removal is a downstream concern (the `rebalance-test-harnesses` skill owns it) — flag as a possible OOS / fast-follow, not a blocker for this issue.
