# Architectural Guidelines

These guidelines are aspirational. Surface meaningful deviations in design or implementation reviews. Move deterministic requirements into lints, hooks, or tests instead of relying on this file.

## Python coding practices

### G-Py-1: Pass composite data as frozen dataclasses
- Why: immutability plus named, refactor-safe fields across boundaries.
- Deviate when: scalar returns; genuine builders; an external dict/JSON parsed into a frozen dataclass at the edge. Aspirational today (`frozen=True` in a minority of files).

### G-Py-2: Annotate types beyond signatures, including locals
- Why: documents intent and catches what inference will not demand.
- Deviate when: the type is obvious from the right-hand side (`count = 0`, loop targets). Note: ruff `ANN` is currently ignored, so annotation presence is unenforced; enabling `ANN001`/`ANN201` would mechanize signatures, leaving local-variable annotation as the judgment residue.

### G-Py-3: Prefer domain types over stringly-typed primitives
- Why: illegal states unrepresentable; self-documenting call sites.
- Deviate when: one-call-site private helper; signature fixed by an external API/protocol. Note: ruff `FBT001`/`FBT003` already flag this and are widely `# noqa`'d today.

### G-Py-4: Fail loudly and fail closed; never silently swallow
- Why: auditability and the codebase's fail-closed parity.
- Deviate when: a documented, narrow degraded path the caller explicitly handles.

### G-Py-5: Isolate side effects behind injectable seams
- Why: keeps logic unit-testable offline.
- Deviate when: thin CLI dispatch glue with nothing to test.

### G-Py-6: Pythonic judgment (PEP 20) is the scope; PEP 8 mechanics are not
- Why: the deterministic style layer is owned by ruff + pylint + pyright.
- Deviate when: n/a; this is what "adhere to official Python guidelines" reduces to once the linters take their half.

### G-Py-7: Wrap external CLIs (git/gh) as typed functions over the injected Runner; read helpers raise the ShipError hierarchy, mutating helpers return CommandResult
- Why: call sites get refactor-safe typed results and one uniform failure mode instead of ad-hoc returncode checks per caller.
- Deviate when: a one-shot internal probe with nothing to type, or a parser that needs the raw `CommandResult` (use the `*_read` variant).

### G-Py-8: After a security-or-integrity-critical mutation, re-verify the postcondition and raise if the invariant did not hold
- Why: a redaction or cleanup that silently leaves the bad state is worse than a loud failure; re-checking turns "probably scrubbed" into a proven invariant.
- Deviate when: the operation is cheap-to-retry and non-security-bearing.

### G-Py-9: Use the most-specific available type for every local variable annotation; never use `Any`
- Why: `Any` silently disables type-checking for every expression derived from it; a local annotation earns its keep only when it is more specific than what inference would produce.
- Deviate when: a union the type-checker cannot narrow even with a cast (document why); an interoperability boundary that forces `Any` (narrow to a protocol or typed alias at the first safe site).

### G-Py-10: Make loop totality explicit when a bounded loop must always return, instead of relying on fall-through
- Why: an impossible loop exit should be loud; otherwise a future edit that changes the bound returns `None` or `""` silently.
- Deviate when: the function legitimately returns a default after the loop and that default is intended.

## Configuration and protocol literals

### G-Cfg-1: Define every exit code, env-var name, tunable, and wire-literal once in config.py as a Final; aggregate token sets from prior sets rather than re-listing
- Why: a single edit point for protocol literals; aggregated sets cannot drift out of sync with their members.
- Deviate when: a module-private constant used at one call site with no cross-module contract.

## Wire-file I/O

### G-IO-1: Route reads/writes of larch wire files through larch.io helpers with explicit caller-selected policy flags, instead of re-implementing KEY=value parsing or bare tmp+replace
- Why: one audited implementation of the on-disk grammar (duplicate-key, CR, symlink, atomicity) keeps every envelope byte-compatible and centralizes fail-closed temp cleanup.
- Deviate when: a throwaway internal file with no wire contract, or stdin/stdout streaming.

## CLI surface

### G-CLI-1: Expose each runtime entry as a module-level main(argv)->int returning a typed exit code, registered by (domain, verb) in the cli.py table; no per-script shim
- Why: uniform process contract for prompt-side callers, one dispatcher to audit, exit codes mapped to the `Outcome` enum.
- Deviate when: pure library helpers with no CLI surface.

## Security

### G-Sec-1: Validate untrusted strings (git refs/remotes/refspecs) against an allowlist regex before they enter a subprocess argv
- Why: validating at the boundary prevents a bad label reaching `git` argv; the intent already exists but is applied unevenly.
- Deviate when: the value is a known constant or already validated upstream at the single trust boundary (note it and skip the redundant re-check).

## Skill authoring and context economy

### G-Skill-1: Load phase-local skill content lazily, at the point of need
- Why: lean active prompt; instructions adjacent to use.
- Deviate when: cross-cutting safety/NEVER constraints and Step-0-governing rules load eagerly; blocks too small to justify a separate Read.

### G-Skill-2: Logic lives in Python behind `cli.py`; SKILL.md and Bash stay thin
- Why: the judgment residue is "is this logic that belongs in Python?".
- Deviate when: n/a; mechanical parts (no consecutive Bash blocks; residual-bash allowlist) are lints, not this guideline.

## Enforcement philosophy

### G-Enf-1: Prefer mechanical enforcement
- Why: when a judgment call recurs, promote it to a lint, hook, or structural test. Governs this file too: entries graduate to lints over time.
- Deviate when: n/a.
