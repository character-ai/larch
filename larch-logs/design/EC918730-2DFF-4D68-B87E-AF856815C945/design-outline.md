## Proposed Design Outline

### Goals
- Make `dyn-*-codex-output.txt` inclusion in implement run logs **explicit** (not incidental fallthrough) and regression-proof.
- Make the design-log Codex exclusion explicit: fix the dead `codex-plan-*` pattern and document dyn-Codex handling.
- Lock both with fixtures: phased + unphased dyn-Codex in implement logs; static + dynamic Codex in design logs.

### Non-goals
- Do not exclude phased static Cursor/Codex fallback outputs from implement logs (intentional forensics; existing test asserts it).
- Do not start including raw dynamic reviewer outputs in design logs (policy stays EXCLUDE).
- Do not touch allow/deny patterns outside the Codex static/dynamic boundary.

### Approach sketch
- `larch-log.sh round_artifact_included()`: add an explicit allow clause for `dyn-*-codex-output.txt` / `dyn-*-codex-output-*.txt` with a comment, placed so inclusion no longer depends only on the broad `*-output.txt` fallthrough.
- `lib-design-round-artifacts.sh design_round_artifact_included()`: replace dead `codex-plan-*-output.txt` with `codex-primary-plan-*-output.txt` (covers static + dynamic) and add a clarifying comment.
- Extend the two regression harnesses with the missing phased/dynamic assertions.

### Surfaces in scope
- `scripts/larch-log.sh` + `scripts/test-larch-log-write-round.sh`
- `scripts/lib-design-round-artifacts.sh` + `scripts/test-lib-design-round-artifacts.sh`
- Doc siblings: `scripts/larch-log.md`, `scripts/lib-design-round-artifacts.md`

### Open questions
- Verify no producer emits a bare `codex-plan-*-output.txt` (without `primary`) before removing that pattern; the plan confirms via grep.
