### Deviation: G-Cfg-1 (centralize wire-literals in config.py)
- **Where**: `python/larch/release/release_prepare.py`, new companion-issue regex (`^Fixes #([0-9]+):`).
- **What**: plan describes this as a module-private constant rather than a `config.py` Final.
- **Rationale**: `ship_pr.py` independently produces the matching `Fixes #{issue}: ` prefix elsewhere in the codebase, so this is an informal cross-module contract; G-Cfg-1's own carve-out ("module-private constant... with no cross-module contract") plausibly applies since neither side imports a shared constant today. Low-severity, non-blocking; /implement may centralize it in `config.py` for tighter consistency without changing behavior.
