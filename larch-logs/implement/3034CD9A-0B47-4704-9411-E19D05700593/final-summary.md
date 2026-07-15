## Review Phase Detail

No review rounds completed.

## Architectural invariants

The diff adds a new `module-manifest` lint (`python/larch/lint/lint_module_manifest.py`), its committed `python/lint-module-manifest.json`, a `cli.py` registry entry, a Makefile target plus aggregate wiring, a `docs/linting.md` row, and a pytest module. None of this changed code weakens a hard gate using metadata that the gated entity controls, reuses a persisted step result without revalidating the inputs that produced it, alters run-log flush completeness, embeds a session-tmpdir pointer in a committed log field, commits a terminal outcome label for an in-flight run, drops a panel slot without a per-slot record, machine-ingests an agent verdict, or routes a merged or closed PR through a pre-merge mutation. The new lint is itself fail-closed, and its sole exemption path (`legacy`) is validated against a frozen in-code seed the gated module cannot author, so a new module cannot self-declare its way past the requirement. This changed code holds the architectural invariants.

## Architectural guidelines

The diff mechanizes a recurring review judgment (host-or-justify for lint modules) as a new lint built on the shared lint engine, and it lands the fail-closed gate together with the committed manifest that already satisfies it for every existing module and the docs entry that describes it, so nothing ships ahead of its producer or its author guidance. The new module exposes a typed `main(argv) -> int` registered in the CLI dispatch table with distinct, documented exit codes for clean, findings, and malformed or unsafe input; models each record as a frozen dataclass; isolates process calls behind an injectable runner seam that the tests drive offline; fails loudly on malformed JSON, bad field types, and duplicate or path-unsafe module names; and rejects symlinked or non-regular manifest and inventory entries. The manifest self-record names the module's host and its commissioning issue, and the grandfather seed is a shrink-only in-code constant covering pre-existing modules. The changed code is consistent with the applicable aspirational guidance, and I found no meaningful deviation to surface.

## /implement run 3034CD9A-0B47-4704-9411-E19D05700593: shipping

- **Outcome**: shipping
- Force: true
- **Duration**: 00:57:43
- **Cost**: 💰 TOTAL ~$18.75: Claude $18.57, Codex-5.6 $0.00, Codex-mini $0.00, Cursor $0.00, Claude (subprocess) $0.18  |  Tokens: 17841k
- **Issue**: #7210: https://github.com/character-ai/larch/issues/7210
- **Plan review**: N/A
- **Plan coverage**: 6/6 firm headings; band: advisory; disposition: none; todos_left: 0
- **Difficulty**: predicted HARD; applied HARD
- **Dynamic archetypes**: N/A
- **Code review**: 1/2 accepted
- **Lines (PR diff)**: N/A
- **OOS filed**: 0
- **Exec issues**: 0
- **Warnings**: 0
- **Run logs**: `larch-logs/implement/3034CD9A-0B47-4704-9411-E19D05700593/`
- **Main agent model**: claude-opus-4-8
- **Effort**: max
- **Larch version**: 53.1.5

<!-- larch:run-summary v=1 -->
