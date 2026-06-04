## Proposed Design Outline

### Goals
- Flip `LARCH_SHIP_PR_IMPL` so unset/empty selects `python3 python/ship.py` at `/implement` Step 8+.
- Make legacy bash `scripts/ship-pr.sh` opt-in via `LARCH_SHIP_PR_IMPL=bash`.
- Add a regression pin asserting the python-default selector wording.

### Non-goals
- Removing `scripts/ship-pr.sh` or its bash contract (deferred to a later cutover step).
- Gating the flip on open soak blockers #3446 / #3404 / #3405 / #3449 (flip unconditionally, per Round 1).
- Changing `python/ship.py` behavior, argv, or the JSON stdout contract.

### Approach sketch
- The default lives prompt-side in the `skills/implement/SKILL.md` "Python driver selector" block — rewrite so python is default and `=bash` is the explicit opt-in.
- Update the doc/prose surfaces that state the bash default: `AGENTS.md`, `docs/configuration-and-permissions.md`, `python/README.md`.
- Add one offline selector-default pin test asserting SKILL.md reads python-default + bash-opt-in; wire it into Makefile / CI shards.
- Keep the bash invocation contract byte-stable; only the default selection flips.

### Surfaces in scope
- `skills/implement/SKILL.md` (selector block, ~L955)
- `AGENTS.md` (`python/` section), `docs/configuration-and-permissions.md` (`LARCH_SHIP_PR_IMPL`), `python/README.md` (Phase 7 line)
- New selector-default pin test under `scripts/` + Makefile/CI wiring
- `SECURITY.md` (light touch only if the env-var framing becomes misleading)

### Open questions
- None.
