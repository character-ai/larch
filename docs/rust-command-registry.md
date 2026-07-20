# Rust Command Registry

`crates/larch-lint/data/command-registry.toml` is the migration source of
truth for larch commands and production callers. Each command pair appears
once. Its row records the current owner, machine-stdout contract, responsible
migration issue, implementation parity, consumer cutover, Python removal, and
an optional `clean_install_test` fixture ID.

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

5. For issue-registry parity audits, build schema-v1 JSON with
   `migration_governance.build_command_audit_issue` and
   `render_command_audit_input`, then run:

   ```bash
   cargo run --quiet --locked --package larch-lint -- command-registry audit --input INPUT.json
   ```

The caller ledger inventories `skill`, `hook`, `script`, `ci`, `agent`, and
`python-runtime` paths. Python modules that build a command with the shared
`larch.core.repo_roots.larch_entrypoint` resolver are Rust callers because the
resolver returns the verified `scripts/larch.sh` bootstrap. Syntax-aware
inspection recognizes resolver and module aliases while ignoring comments and
unexecuted string literals.

The rule fails for missing or duplicate command rows, stale Python target or
machine-stdout metadata, invalid status combinations, caller drift, unknown
caller selectors, incomplete Python retirement evidence, and missing
clean-install coverage. Every Rust-owned command with a production caller must
name one unique fixture from `CLEAN_INSTALL_CASES` in
`crates/larch-cli/tests/parity.rs`. The shared matrix starts without
`bin/larch`, validates the local binary version and target through
`scripts/larch.sh`, and reaches the named Rust selector.

The clean-install diagnostic is
`clean-install-coverage-missing <domain> <verb>`. The issue audit reports
`migration-issue-command-drift issue=#N command=<domain> <verb>` when a
canonical issue `COMMAND` row, its plan mention, or the registry's
`migration_issue` disagrees. Registry-to-issue checks apply only to open
executable leaves after the audit input enables rollout.

## Final release and upgrade boundary

`larch-lint rule release-python-free` pins the final #7674 command set. It
requires every `release` and `upgrade-larch` row, plus `plugin read-version`,
to keep Rust ownership, complete parity, complete caller cutover, complete
Python removal, and its owning leaf. It also pins each applicable clean-install
fixture.

The rule rejects a restored Python registration or command entrypoint, a
Python or direct-binary caller, and a release implementation that starts `gh`
instead of using the typed GitHub service. `scripts/larch.sh` remains the sole
direct executable owner and the no-binary bootstrap exception from #7670. The
release asset workflow may run its newly built `target/release/larch` because
that workflow constructs and verifies the release executable.

`/release` Step 7 builds the candidate executable, passes it to
`scripts/larch.sh` through the validated `LARCH_BINARY` override, and supplies
the separately validated installed cache root to `upgrade-larch run`. This
keeps executable identity bound to the released working tree without treating
the active old-session root as the executable owner.

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
