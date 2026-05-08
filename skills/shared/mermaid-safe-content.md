# Mermaid Safe Content

## Why This Matters

Anchor comments and PR bodies embed Mermaid diagrams that GitHub renders publicly. Unsafe diagram text can make the diagram block render as raw source or fail entirely, hiding the implementation context the anchor is meant to preserve. Issue #1404 is the pinned regression case.

## Forbidden Patterns

- Literal `|` inside flowchart node text delimited by `[...]`, `(...)`, `{...}`, or `((...))`. Use quoted node text such as `["foo|bar"]`, including escaped quotes when needed, or rephrase the label.
- `<br/>`, `<br />`, or `<br>` inside `sequenceDiagram` participant or actor aliases. Use a plain alias and put multiline detail in a `Note over` line.
- `$` inside `sequenceDiagram` participant or actor aliases. Use a plain alias and mention variables in notes or message text.

## Permitted Patterns

- Flowchart edge labels such as `A -->|text| B`.
- `<br/>` inside flowchart node labels.
- Quoted flowchart node text such as `A["foo \"x\" |bar"]`.

## Enforcement Layers

- Write-time sanitizer: `/design` Step 3b, `/implement` Step 7a, and `/implement` Step 9a validate diagram candidates with `scripts/sanitize-mermaid-fragment.sh`. Rejected diagrams are dropped and replaced with placeholders.
- Anchor assembly sanitizer: `scripts/assemble-anchor.sh` revalidates the `diagrams` slug as defense in depth and fails closed on sanitizer tooling errors.
- CI Mermaid lint: `scripts/lint-mermaid-fences.sh` runs Mermaid CLI over changed Markdown fences and catches syntax outside the narrow sanitizer policy.

## For Tool Authors

Any new Mermaid emitter must write a candidate file, run `scripts/sanitize-mermaid-fragment.sh --from-md` when the candidate includes fence delimiters, and only promote the candidate to the public artifact on `STATUS=ok`. On `STATUS=rejected` or exit 2, drop the candidate, log a public-safe `REASON_TOKEN`, and proceed with a placeholder.

## Node Toolchain Maintenance

This repo uses `@mermaid-js/mermaid-cli` for CI parsing. Keep the version pinned exactly in `package.json`; bump yearly or on critical CVE. Run `npm audit` opportunistically during bumps. There is no scheduled audit gate.

## Update Triggers

Update this file when sanitizer policy, Mermaid CLI pinning, diagram-emitter steps, or anchor/PR publication behavior changes.
