## Proposed Design Outline

### Goals
- Make the `_DESIGN_LIFECYCLE_STDOUT_KEYS` check in `scripts/test-design-structure.sh` robust so a transient truncation of the once-captured block never masquerades as a genuine `missing design <verb>` failure.
- Remove the observed spurious `main` CI failures by self-healing a transient capture, and — if it stays incomplete — failing with a distinct, auditable diagnostic instead.

### Non-goals
- No CI workflow / `test-harnesses` shard resource changes (trackable separately if pressure recurs).
- No refactor of unrelated blocks or broader harness cleanup beyond this check.
- No new meta-test framework for this shell harness.

### Approach sketch
- Replace the single inline `stdout_keys_block="$(awk …)"` capture (~line 320) with a small helper that re-extracts up to 3x, validating each capture against the frozenset's terminal sentinel `("plan", "step1-log")`.
- If every attempt is still incomplete, `fail` with a distinct `block extraction incomplete` message rather than the misleading per-verb "missing key".
- Helper assigns the existing global `stdout_keys_block`; the four reuse sites (~324, ~405, ~633, ~686) stay unchanged because they read the validated in-memory variable (no re-capture occurs).
- Tighten the awk stop pattern (`/^)/` → stop at the frozenset close `})`) so extraction ends exactly at the last entry, making the sentinel completeness check precise.

### Surfaces in scope
- `scripts/test-design-structure.sh` (single capture site + one new helper; reuse sites unchanged).

### Open questions
- None — guard behavior (retry then fail loud), scope (harness only), and awk tightening were resolved in Round 1.
