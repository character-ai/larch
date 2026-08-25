# Rust Command Registry

`crates/larch-lint/data/command-registry.toml` is the final source of truth for
larch commands and their production callers. Runtime dispatch does not read the
registry. Clap owns dispatch in the released executable, while `larch-lint`
uses the registry to detect ownership, caller, and clean-install drift.

## Schema

The schema-version 3 registry contains one `[[commands]]` row per command pair:

```toml
[[commands]]
domain = "agent"
verb = "model-args"
machine_stdout = false
owner = "rust"
planning_issue = 7678
migration_issue = 8107
clean_install_test = "clean-install-agent-model-args"
```

- `domain` and `verb` are the exact closed CLI selector.
- `machine_stdout` records whether callers parse standard output as a wire
  contract.
- `owner` is `rust` for a live command or `retired` for an intentionally
  removed command.
- `planning_issue` records the historical domain umbrella. It must not point
  at the chief migration issue.
- `migration_issue` records the exact non-umbrella leaf that implemented or
  retired the command. Every row requires one.
- `clean_install_test` optionally names the exact case in
  `crates/larch-cli/tests/clean_install.rs`. Every Rust-owned command with a
  production caller requires one unique matching case.

The registry also contains one `[[callers]]` row per production path:

```toml
[[callers]]
path = "agents/_implementer-base.md"
kind = "agent"
rust = ["checks run-relevant", "redact secrets"]
```

Caller kinds are `skill`, `hook`, `script`, `ci`, and `agent`. Selectors must be
sorted and unique. A `domain *` selector is allowed only when the caller chooses
the verb dynamically; it conservatively records every command in that domain.

## Update workflow

Use one workflow for a command or caller change:

1. Update the typed Clap command and every production caller in the same
   change. Public callers enter through `scripts/larch.sh`; they do not execute
   `bin/larch`, Cargo, or a target-directory binary.
2. Add or update the affected `[[commands]]` row. New live commands use
   `owner = "rust"`, a concrete planning issue, and an exact implementation
   leaf. Add a clean-install case when the command has a production caller.
3. Refresh the caller projection through the verified entrypoint:

   ```bash
   scripts/larch.sh lint command-registry sync
   ```

   Sync preserves command rows and rewrites only the discovered caller rows.
   Review the diff; a missing caller usually means the source shape is outside
   the supported static inventory and needs rule coverage before merge.
4. Validate the registry and render its summary:

   ```bash
   scripts/larch.sh lint rule command-registry
   scripts/larch.sh lint command-registry report
   ```

5. Run the focused integration tests when registry parsing, discovery, or
   validation changes:

   ```bash
   cargo test --locked --package larch-lint --test integration command_registry::
   cargo test --locked --package larch-cli --test integration clean_install::
   ```

## Validation contract

The `command-registry` rule fails on:

- unsupported schema fields or versions;
- missing, unsafe, duplicate, unsorted, or unknown command and caller data;
- a command without a concrete planning issue and exact implementation leaf;
- a retired command with any live production caller;
- caller projection drift;
- a missing, duplicate, unknown, or selector-mismatched clean-install fixture;
- a Rust-owned command with production callers but no matching clean-install
  case.

The shared clean-install matrix starts without `bin/larch`, validates the local
binary version and target through `scripts/larch.sh`, and reaches the named
selector. The missing-coverage diagnostic is
`clean-install-coverage-missing <domain> <verb>`.

Permanent closure rules such as `release-python-free`, `state-python-free`,
`agent-python-free`, `issue-python-free`, `reporting-python-free`, and
`review-python-free` retain their historical names. They are Rust rules that
prevent restoration of retired runtime packages, registrations, command
implementations, or callers in their completed domains. They do not describe a
second live runtime.

## Issue audit

`lint command-registry audit` compares registry `migration_issue` ownership
with schema-version 1 JSON produced from canonical issue and plan parsing:

```bash
scripts/larch.sh lint command-registry audit --input INPUT.json
```

The input enables rollout explicitly and supplies issue number, state,
executable-leaf status, the issue's command selector, and any plan selectors.
The audit reports
`migration-issue-command-drift issue=#N command=<domain> <verb>` when those
sources disagree. It is read-only and does not edit issues or the registry.

## Maintenance boundaries

The registry is an inventory, not a plugin runtime configuration file. Do not
use it to select implementations or weaken a typed command boundary. Add new
behavior inside the owning Rust crate, keep `larch-cli` as the composition
root, and update service or Git inventories when the command consumes those
boundaries.

Historical planning and implementation issue fields remain for traceability.
They are not evidence that a migration is still active. Command behavior is
held by Rust unit and integration tests, reviewed recorded contracts where
needed, and clean-install dispatch coverage.
