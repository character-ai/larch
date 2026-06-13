# Review Round 1

- Mode: `diff`
- 1 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_4: Research Bash ingestion block can fail the collection step on token command errors
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, dyn-warning-surface-output.txt
- **Severity**: important
- **Concern**: Research sidecar ingestion is documented as best-effort, but the documented Bash command block can return a failing status because token commands are unguarded. A failed `append-record` or `record-vendor-sidecar` (e.g. exit 2 when the research ledger path is non-regular) can fail the research collection step instead of continuing with a visible warning. The documented commands also lack the explicit exit-code checks and operator-visible wrappers (`larch_err`, stderr relay on exit 0) used elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Guard both token commands with `if ! ...; then printf 'WARNING: ...' >&2; fi` so failures are visible and non-fatal.
  - From codex-specialist-correctness-output.txt: Guard both token commands with `if ! ...; then printf 'WARNING: ...' >&2; fi` so failures are visible and non-fatal.
  - From codex-specialist-edge-cases-output.txt: Wrap each token command in a non-fatal warning handler so failures are visible but do not change the enclosing step status.
  - From dyn-warning-surface-output.txt: Document concrete wrappers such as `if ! python3 … append-record …; then larch_err "…"; fi` and the same for `record-vendor-sidecar`, including relay of captured stderr on exit 0 when non-empty.


