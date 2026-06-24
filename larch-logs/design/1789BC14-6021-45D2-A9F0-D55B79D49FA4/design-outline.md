## Proposed Design Outline

### Goals
- `bootstrap invoke` emits `BOOTSTRAP_NEXT` directive so prompt-side routing is a lookup, not a multi-row table.
- `implement preflight` self-validates its output envelope and exits 2 on any malformed key.
- SKILL.md routing prose shrinks to 5 directive rows; preflight schema bullets are removed.

### Non-goals
- Do not fold §2.1.5 (adversarial dispatcher-envelope cross-check in Preflight; stays prose).
- Do not change any other bootstrap/preflight behavior or exit codes.
- Do not add new envelope keys beyond `BOOTSTRAP_NEXT`.

### Approach sketch
- Add `_compute_bootstrap_next(data)` in `python/bootstrap.py`; emit `BOOTSTRAP_NEXT` at end of `invoke_main` after final data assembly.
- Add `BOOTSTRAP_NEXT` to `ROUTING_KEYS` so it flows through envelope filtering and `bootstrap-routing.env`.
- Add `_validate_preflight_envelope(...)` in `python/preflight.py`; call it before printing the 7 keys; exit 2 on any violation.
- Collapse SKILL.md routing table (8 rows) to a 5-row `BOOTSTRAP_NEXT` directive table; collapse preflight schema bullets to "on exit 0, parse the 7 keys".

### Surfaces in scope
- `python/bootstrap.py` (new `_compute_bootstrap_next`, `ROUTING_KEYS` update, `invoke_main` emit)
- `python/preflight.py` (new `_validate_preflight_envelope`, called before exit-0 emit)
- `skills/implement/SKILL.md` (routing table lines ~287-298; preflight schema bullets ~215-232)
- `python/test_bootstrap.py` (new tests for `_compute_bootstrap_next`)
- `python/test_preflight.py` (new test for envelope self-validation exit 2)

### Open questions
- None.
