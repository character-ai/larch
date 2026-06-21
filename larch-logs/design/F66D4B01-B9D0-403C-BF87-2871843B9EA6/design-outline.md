## Proposed Design Outline

### Goals
- Close the sh-to-py terminal sweep: retire only truly-orphaned shared bash libs, scope-down (never port) the 6 bash-targeting linters, prune verified-orphan utility scripts.
- Refresh authoring docs (BASH_AUTHORING.md, AGENTS.md Python section, python/README.md), regenerate the topology projection, update SECURITY.md for the reduced bash surface.
- Document the residual bash inventory (9 hooks, 6 linters, ~50 thin wrappers, sleep-seconds.sh, test harnesses) so the kept surface is explicit.

### Non-goals
- Do NOT repoint or edit the deliberately-kept bash surface to force more lib retirements.
- Do NOT hand-edit CI shard manifests; defer rebalance to the /rebalance-tests skill.
- Do NOT port the 6 linters to Python; narrow their globs only.
- No decomposition; one consolidated plan.

### Approach sketch
- Inventory pass: verify zero-consumption per lib and per candidate orphan across .sh/.md/.py/.tsv/.json/Makefile/CI (exclude larch-logs); only zero-consumer artifacts get deleted.
- Retire confirmed-orphan libs (lib-prune-decision.sh confirmed; re-verify the other 7) plus verified-orphan utility scripts; keep `make lint-retired-scripts` clean.
- Narrow the 6 linters' path globs to the residual bash surface without weakening coverage for files that still exist.
- Shrink/rewrite the three doc surfaces; regenerate skills/shared/topology.tsv via its generator; update SECURITY.md.

### Surfaces in scope
- scripts/lib-*.sh (retire only zero-consumer) and orphan utility scripts under scripts/ and skills/*/scripts/.
- The 6 linters: lint-bash32, lint-bare-grep-probe, lint-awk-multibyte-regex, lint-renderer-substitution-safety, pre-commit-shellcheck, pre-commit-bash-syntax.
- Docs: BASH_AUTHORING.md, AGENTS.md, python/README.md, SECURITY.md; plus the residual-inventory location and retired-scripts manifest.

### Open questions
- The exact zero-consumer lib/orphan set is finalized by the drafting-time inventory pass; only lib-prune-decision.sh is confirmed orphaned so far.
