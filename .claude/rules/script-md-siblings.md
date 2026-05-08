---
paths: ["scripts/**/*.{sh,py}", "skills/**/scripts/**/*.{sh,py}", ".claude/skills/**/scripts/**/*.{sh,py}", "skills/shared/*.md"]
---

# Script Documentation Siblings

Every `.sh` / `.py` script under `scripts/` and `skills/<name>/scripts/`
has a sibling `<basename>.md` beside it (e.g.
`scripts/redact-secrets.md` beside `scripts/redact-secrets.sh`) covering
purpose, primary callers, invariants, Makefile wiring, harness, and
edit-in-sync rules. Read it before editing a script; update it in the
same PR as any behavior change. Two co-location patterns are permitted,
neither is an exemption from the file-existence rule:

- **Primary owns the full contract.** When a primary script has a
  sourced-only library (`scripts/lib-*.sh` — no shebang) and/or a
  regression harness (`scripts/test-*.sh` for the primary), the primary
  `.md` owns the full contract and cites related paths. Library and
  harness still get sibling `.md` stubs so every `.sh` stays
  discoverable and auditable; stubs point to the primary `.md`.
- **Cross-tree harnesses.** A harness may live under `scripts/test-*.sh`
  while its primary lives at `skills/<name>/scripts/<primary>.sh` (e.g.
  `scripts/test-post-scaffold-hints.sh` testing
  `skills/create-skill/scripts/post-scaffold-hints.sh`). The primary
  `.md` owns the full contract; the harness in `scripts/` still gets a
  sibling `.md` stub naming its primary.

**Caller surface for shared scripts.** When changing a script under
`scripts/`, grep for callers across `skills/`, `hooks/`,
`.claude/settings.json`, `.github/workflows/`, and other scripts before
finalizing.

For canonical documentation files (`skills/shared/*.md`), update triggers
live at the file bottom.

This rule's `paths:` intentionally covers nested
`skills/**/scripts/**/*.{sh,py}` so future skill script layouts inherit
the same sibling-contract invariant.
