## Decision 1: Both issues in one PR or split

- **Question**: Address both the O(n²) heredoc rescanning perf issue AND the blanket suppression bypass issue in one design, or split into separate PRs?
- **Resolution**: Both in one PR — they touch the same file (`scripts/lint-foreground-markers.sh`) and are correlated under OOS rule 3 (multiple medium bugs ≥~30 LOC).
- **Source**: user

## Decision 2: Backward compatibility for existing bare suppressions

- **Question**: Should existing bare `# lint-foreground-markers: ok <reason>` comments (in `scripts/relevant-checks.sh`, `scripts/test-lint-foreground-markers.sh`, etc.) continue to suppress all checks, or be migrated to a scoped form?
- **Resolution**: Bare suppression keeps current 'suppress all checks' semantics. New scoped form (e.g. naming specific check tokens) is opt-in / additive. No migration of existing callsites in this PR.
- **Source**: user

## Decision 3: Documentation update scope

- **Question**: Do `scripts/lint-foreground-markers.md`, `BASH_AUTHORING.md` §4, and `scripts/test-lint-foreground-markers.md` need updates alongside the script?
- **Resolution**: Yes — `.claude/rules/script-md-siblings.md` is a hard repo invariant requiring sibling `.md` updates in the same PR as behavior changes; `BASH_AUTHORING.md` §4 documents the linter contract and must reflect the new opt-in scoped-suppression syntax.
- **Source**: codebase

## Decision 4: Harness coverage

- **Question**: Does `scripts/test-lint-foreground-markers.sh` need new assertions for the perf and suppression-scoping fixes?
- **Resolution**: Yes — the linter is enforcement infrastructure under `make lint-foreground` and the pre-commit hook; behavior changes require harness coverage. Perf fix is observable behavior (preserves all existing detections) and must keep all current `test-lint-foreground-markers.sh` assertions green; suppression-scoping adds new fixtures.
- **Source**: codebase
