# Rust Command Registry

`crates/larch-lint/data/command-registry.toml` is the migration source of
truth for larch commands and production callers. Each command pair appears
once. Its row records the current owner, machine-stdout contract, responsible
migration issue, implementation parity, consumer cutover, and Python removal.

## Update workflow

Use one workflow for registry or caller changes:

1. Edit the Python or Rust command implementation and every affected
   production caller.
2. Refresh imported command metadata and caller rows. Pass the issue that owns
   any newly added command:

   ```bash
   cargo run --quiet --locked --package larch-lint -- command-registry sync --migration-issue ISSUE
   ```

3. Edit only the affected command rows to advance `owner`,
   `implementation_parity`, `consumer_cutover`, or `python_removal`. Sync keeps
   these fields and existing `migration_issue` values unchanged.
4. Validate the ledger and render the Chief issue progress block:

   ```bash
   cargo run --quiet --locked --package larch-lint -- rule command-registry
   cargo run --quiet --locked --package larch-lint -- command-registry report
   ```

The caller ledger inventories `skill`, `hook`, `script`, `ci`, `agent`, and
`python-runtime` paths. Python modules that build a command with the shared
`larch.core.repo_roots.larch_entrypoint` resolver are Rust callers because the
resolver returns the verified `scripts/larch.sh` bootstrap. Syntax-aware
inspection recognizes resolver and module aliases while ignoring comments and
unexecuted string literals.

The rule fails for missing or duplicate command rows, stale Python target or
machine-stdout metadata, invalid status combinations, caller drift, unknown
caller selectors, and incomplete Python retirement evidence.

## State transitions

Keep `owner = "python"` and `consumer_cutover = "pending"` while Python owns
production behavior. A parity implementation may set
`implementation_parity = "complete"` without changing ownership.

Cut over one command atomically: complete parity, update all production callers,
remove the Python registry row and module-level entrypoint, remove every
production import and call of that symbol, set `owner = "rust"`, and mark both
completion fields `complete`. There is no Rust-owned pending-removal state.
`python_module` and `python_function` remain in the ledger after deletion so
the rule can continue proving that the retired entrypoint is absent.

A Rust owner becomes valid only in the PR that completes all of those changes.
Adapter parity alone does not transfer command ownership. For local Git, the
`git-ownership` rule also pins the complete #7675 command set and compares
[`docs/git-operation-inventory.md`](git-operation-inventory.md) with live
production surfaces. Commands assigned to a later domain stay Python-owned
until that domain's issue performs the same atomic transition.

The atomic-owner diagnostic is
`non-atomic-rust-owner <domain> <verb>: python removal is not complete`.
Retirement evidence uses `python-entrypoint-still-present` for a remaining
registration or module-level definition, `python-entrypoint-still-imported`
for an import or attribute reference, and `python-entrypoint-still-called` for
a direct or qualified call. Each diagnostic includes the selector and path.

For retirement, remove every caller and Python registry entry, set
`owner = "retired"`, `implementation_parity = "not-applicable"`, and mark both
completion fields `complete`.

Caller selectors may use `domain *` only when a production wrapper chooses the
verb dynamically. Such a selector conservatively blocks Rust ownership for
every command in that domain until the wrapper moves or becomes exact.
