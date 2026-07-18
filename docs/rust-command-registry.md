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

The rule fails for missing or duplicate command rows, stale Python target or
machine-stdout metadata, invalid status combinations, caller drift, unknown
caller selectors, and Rust ownership while a known Python caller remains.

## State transitions

Keep `owner = "python"` and `consumer_cutover = "pending"` while Python owns
production behavior. A parity implementation may set
`implementation_parity = "complete"` without changing ownership.

Cut over one command atomically: update all production callers, set
`owner = "rust"`, and set `consumer_cutover = "complete"`. The rule rejects a
Rust owner if any inventoried Python caller remains. Remove the Python registry
entry later and then set `python_removal = "complete"`.

For retirement, remove every caller and Python registry entry, set
`owner = "retired"`, `implementation_parity = "not-applicable"`, and mark both
completion fields `complete`.

Caller selectors may use `domain *` only when a production wrapper chooses the
verb dynamically. Such a selector conservatively blocks Rust ownership for
every command in that domain until the wrapper moves or becomes exact.
