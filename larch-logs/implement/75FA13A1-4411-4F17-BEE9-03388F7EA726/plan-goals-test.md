## Goal
Implement issue #5175: [IMPLEMENTING] [py-code-quality] Packaging 9/9 CAPSTONE: move cli.py and _REGISTRY into larch.cli, consumer path unchanged.

## Implementation Plan
**Problem.** `cli.py` is the single dispatcher (~756 LOC, `_REGISTRY` of ~70 domains) and imports every domain module by top-level name. It must move last, after every domain package lands, and it owns the consumer-facing `python3 python/cli.py <domain> <verb>` contract that must not change.

**Proposed change.** Finalize the package move: repoint every `_REGISTRY` target to its package path (`agents` to `larch.agents.agents`, etc.), move the dispatcher into `larch.cli`, and keep `python3 python/cli.py ...` working as the documented entry point (the entry-point shape, thin shim vs. console entry, is decided in this child's `/design`). Sweep up any runtime modules not claimed by children 2 through 8 (for example `rendering`, `version_bump`, `release_*`, `promote_release`, `verify_*`, `alias_skill`, `upgrade_larch`, `research*`, `architectural_guidelines`, the `lint_*` surfaces, `design_log_ship`, run-log maintenance modules) into coherent packages so nothing is left flat. Update `python/README.md`, `docs/topology.md`, and `skills/shared/topology.tsv`. Re-enable strict per-package complexity rules where the move unlocks them.

**Out of scope / don't-touch.** No behavior change. The consumer invocation `python3 python/cli.py ...` MUST be unchanged from the caller's perspective. All wire formats preserved. Pure restructuring plus import rewrites.

**Acceptance.** All runtime modules live under coherent packages; `cli.py` dispatch unchanged from the caller's perspective; `make py-lint` / `make py-test` green; consumer invocations unchanged; topology docs regenerated.

**Effort / risk.** Medium-high / medium-high. Final integration; verify the full `/design` and `/implement` paths.

**Dependencies.** Blocked by every domain packaging child (2/9 through 8/9). Tracked under umbrella #4982. Wired via `/block-issue`.

## Test plan
(no test plan section in plan-file)
