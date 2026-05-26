## Decision 1: Backward compatibility with existing callers
- **Question**: Must existing callers of `launch-claude-review.sh` (e.g., `dispatch-code-voters.sh`, `dispatch-plan-voters.sh`, plus design plan-review and review-and-fix code paths) continue to work without changes after adding `--context-files`?
- **Resolution**: Yes. Adding a new optional `--context-files` argv case is purely additive — no existing flag is renamed, removed, or has changed semantics. All existing call sites that don't pass `--context-files` must produce byte-identical subprocess invocations.
- **Source**: codebase

## Decision 2: Subprocess 20-file cap remains the authoritative limit
- **Question**: Should the new public `--context-files` flag enforce its own cap, or defer to the existing subprocess cap of 20 (`launch-claude-subprocess.sh` line 90)?
- **Resolution**: Defer to subprocess. The launcher MAY pre-check the total combined count (implicit + explicit, after dedup) and fail loudly with attribution before forking the subprocess, but the authoritative number remains 20. No new cap parameter.
- **Source**: codebase

## Decision 3: Test harness must be extended
- **Question**: Must `test-launch-claude-review.sh` (repo lint convention: every script ships a `test-*.sh` harness) be extended to cover the new flag?
- **Resolution**: Yes. New test cases must cover: (a) single `--context-files`, (b) repeated `--context-files`, (c) hard-error on missing/empty path, (d) dedup against an implicit `--scope-files`/`--plan-file` path, (e) both `--role reviewer` and `--role voter`, (f) total-count cap behavior. Harness must continue running under the existing stub `claude` binary so it stays hermetic.
- **Source**: codebase

## Decision 4: Documentation surface
- **Question**: Where do `--context-files` flag docs and the role-orthogonality note land?
- **Resolution**: Updates land in `scripts/launch-claude-review.md` (the explicit scope of this piece). The Usage line in `launch-claude-review.sh` is also updated to mention `--context-files <file>`. No other docs are touched in Piece 1.
- **Source**: codebase

## Decision 5: Out-of-scope items deferred to other pieces
- **Question**: What feature requests from the original Round-3 spec are explicitly NOT in this piece?
- **Resolution**: Voter 1 ballot-delivery code (separate piece of #2677); Cursor/Codex launcher symmetry (separate piece); `aggregate-findings.sh` input-root contract changes (R4/FINDING_2, separate piece); multi-round plan-review loop changes; per-round artifact discipline. This piece's scope ends at the `launch-claude-review.sh` surface plus its `.md` and tests.
- **Source**: codebase + issue body (`Dependencies (from panel): none`)
