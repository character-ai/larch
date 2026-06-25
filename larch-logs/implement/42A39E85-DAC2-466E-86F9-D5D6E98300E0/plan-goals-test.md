## Goal
Implement issue #5338: [IMPLEMENTING] architectural-guidelines-II Add new judgment-only architectural guidelines to ARCHITECTURAL_GUIDELINES.md.

## Implementation Plan
## Plan

Docs-only change. Add 7 judgment-only guidelines to `ARCHITECTURAL_GUIDELINES.md`.

Constraints:
- Preserve the preamble and all 9 existing entries byte-for-byte. Touch no code.
- Use the existing entry shape only: `### G-...:` heading, then `- Why:`, then `- Deviate when:`. No `- Evidence:` bullet.
- Keep reserved ID gaps `G-Py-9` and `G-Cfg-2` (they are the sibling lint issue's IDs).
- Add no mechanically-validatable guidelines (subprocess-via-`Runner`, env-via-config-constant).

### UPDATED: ARCHITECTURAL_GUIDELINES.md

Add three entries after `G-Py-6`, inside the existing `## Python coding practices` section, in this order:

`### G-Py-7: Wrap external CLIs (git/gh) as typed functions over the injected Runner; read helpers raise the ShipError hierarchy, mutating helpers return CommandResult`
- Why: call sites get refactor-safe typed results and one uniform failure mode instead of ad-hoc returncode checks per caller.
- Deviate when: a one-shot internal probe with nothing to type, or a parser that needs the raw `CommandResult` (use the `*_read` variant).

`### G-Py-8: After a security-or-integrity-critical mutation, re-verify the postcondition and raise if the invariant did not hold`
- Why: a redaction or cleanup that silently leaves the bad state is worse than a loud failure; re-checking turns "probably scrubbed" into a proven invariant.
- Deviate when: the operation is cheap-to-retry and non-security-bearing.

`### G-Py-10: Make loop totality explicit when a bounded loop must always return, instead of relying on fall-through`
- Why: an impossible loop exit should be loud; otherwise a future edit that changes the bound returns `None` or `""` silently.
- Deviate when: the function legitimately returns a default after the loop and that default is intended.

Add four new `##` sections after `## Python coding practices` and before `## Skill authoring and context economy`, in this order, each holding one entry:

`## Configuration and protocol literals`
`### G-Cfg-1: Define every exit code, env-var name, tunable, and wire-literal once in config.py as a Final; aggregate token sets from prior sets rather than re-listing`
- Why: a single edit point for protocol literals; aggregated sets cannot drift out of sync with their members.
- Deviate when: a module-private constant used at one call site with no cross-module contract.

`## Wire-file I/O`
`### G-IO-1: Route reads/writes of larch wire files through larch_io helpers with explicit caller-selected policy flags, instead of re-implementing KEY=value parsing or bare tmp+replace`
- Why: one audited implementation of the on-disk grammar (duplicate-key, CR, symlink, atomicity) keeps every envelope byte-compatible and centralizes fail-closed temp cleanup.
- Deviate when: a throwaway internal file with no wire contract, or stdin/stdout streaming.

`## CLI surface`
`### G-CLI-1: Expose each runtime entry as a module-level main(argv)->int returning a typed exit code, registered by (domain, verb) in the cli.py table; no per-script shim`
- Why: uniform process contract for prompt-side callers, one dispatcher to audit, exit codes mapped to the `Outcome` enum.
- Deviate when: pure library helpers with no CLI surface.

`## Security`
`### G-Sec-1: Validate untrusted strings (git refs/remotes/refspecs) against an allowlist regex before they enter a subprocess argv`
- Why: validating at the boundary prevents a bad label reaching `git` argv; the intent already exists but is applied unevenly.
- Deviate when: the value is a known constant or already validated upstream at the single trust boundary (note it and skip the redundant re-check).

### Edge cases
- Use exactly `###` for guideline headings. `_HEADING_RE` in `python/architectural_guidelines.py` requires that depth, and markdownlint MD001 forbids an h2 to h4 jump.
- Match bullet labels exactly: `- Why:` and `- Deviate when:` (case and spacing). `parse_guideline_entries` silently drops variants such as `- Deviate:` while the heading still parses.
- Keep `G-Py-10` numbered 10; do not collapse it to `G-Py-9`.
- Add no `- Evidence:` bullets; the parser keeps only Why and Deviate when, so any third bullet is inert.

### Failure modes
- A malformed `### G-*` heading (missing colon, wrong ID token, or `####` depth) leaves the entry in the raw file but absent from `architectural-guidelines read` parsed output, so `/design` and `/implement` would silently miss a claimed entry.
- A mistyped `- Why:` or `- Deviate when:` bullet on a valid heading produces the same silent loss: an ID-only grep passes while the parsed block lacks the body text.
- Restyling or reordering existing entries creates needless churn and review noise.

### Testing strategy
- Run `make lint`.
- Run `python3 python/cli.py architectural-guidelines read`; require `ARCHITECTURAL_GUIDELINES_STATUS=present`.
- From the parsed `architectural_guidelines` content block (normalized output, not the raw file), confirm 16 parsed entries (9 existing + 7 new) and verify each new ID's block (`G-Py-7`, `G-Py-8`, `G-Py-10`, `G-Cfg-1`, `G-IO-1`, `G-CLI-1`, `G-Sec-1`) includes both a `- Why:` line and a `- Deviate when:` line. ID-only matches are insufficient.
- No Python unit tests are required; this is docs-only and parser behavior does not change.

## Acceptance
- All 7 entries (G-Py-7, G-Py-8, G-Py-10, G-Cfg-1, G-IO-1, G-CLI-1, G-Sec-1) appear in the existing format: `### G-...:` heading, `- Why:`, `- Deviate when:`; no `- Evidence:` bullet.
- The preamble, all 9 existing entries, and all code are unchanged.
- The 4 new `##` sections sit after `## Python coding practices` and before `## Skill authoring and context economy`; G-Py-7/8/10 sit inside `## Python coding practices` after G-Py-6.
- `make lint` passes.
- `python3 python/cli.py architectural-guidelines read` reports `ARCHITECTURAL_GUIDELINES_STATUS=present`, and each new ID's parsed block includes both a `- Why:` and a `- Deviate when:` line.
- The file still contains only judgment-only guidelines; no mechanically-linter-validated entries are added.

diff_lines: 36

## Test plan
(no test plan section in plan-file)
