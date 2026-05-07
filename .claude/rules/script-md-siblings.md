---
paths: ["scripts/**/*.{sh,py}", "skills/**/scripts/**/*.{sh,py}", "skills/shared/*.md"]
---

# Script Documentation Siblings

Every `.sh` / `.py` script under `scripts/` and `skills/<name>/scripts/` has a sibling `<basename>.md` next to it (e.g., `scripts/redact-secrets.md` beside `scripts/redact-secrets.sh`) documenting the script's purpose, primary callers, invariants, Makefile wiring, test harness, and edit-in-sync rules. When editing a script, read its sibling `.md` first; update it in the same PR as any behavioral change. Two co-location patterns are permitted, neither is an exemption from the file-existence rule:

- **Primary owns the full contract.** Where a primary script has a sourced-only library (`scripts/lib-*.sh` — no shebang) and/or a regression test harness (`scripts/test-*.sh` for the primary), the primary's `.md` owns the full contract and cites the related files by path. The library and harness still get their own sibling `.md` (typically a one-paragraph stub) so every `.sh` has a sibling for discoverability and audit; the stub points readers to the primary's `.md` rather than restating the contract.
- **Cross-tree harnesses.** A test harness may live under `scripts/test-*.sh` while its primary lives at `skills/<name>/scripts/<primary>.sh` (e.g. `scripts/test-post-scaffold-hints.sh` testing `skills/create-skill/scripts/post-scaffold-hints.sh`). The primary's `.md` (in its own tree) owns the full contract; the harness in `scripts/` still gets a sibling `.md` stub naming its primary.

For canonical documentation files (`skills/shared/*.md`), update triggers live inside the file itself at the bottom.

This rule's `paths:` intentionally covers nested `skills/**/scripts/**/*.{sh,py}` so future skill script layouts inherit the same sibling-contract invariant.
