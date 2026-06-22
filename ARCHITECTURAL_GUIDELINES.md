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
