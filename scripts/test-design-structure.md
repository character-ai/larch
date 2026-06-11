# test-design-structure.sh

## Purpose

Checks the `/design` skill's wrapper-only Bash fence contract.

## Primary callers

- `make test-design-structure`
- `scripts/relevant-checks.sh` when `skills/design/SKILL.md`, design references, or this harness change.

## Invariants

- Every Bash fence in `skills/design/SKILL.md` is one direct call to a repo wrapper under `skills/design/scripts/`.
- Direct wrappers are executable, have sibling `.md` files, and do not derive the root Claude PID from `$PPID` internally.
- Step-specific wrapper contracts retain parser, route, init, postplan, Step 3 review, Step 3b, Step 5c, and Step 6 handoffs.

## Edit in sync

Update this harness when `/design` moves another prompt-side Bash contract into a wrapper or renames a direct-called wrapper.
