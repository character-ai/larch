# blocker-helpers.sh

**Consumer**: sourced by `scripts/implement-admission.sh` (and any future scripts that need the same native+prose blocker union). Provides the canonical implementation of `native_open_blockers`, `prose_open_blockers`, and `all_open_blockers`.

**Contract**: single normative source for the three blocker-resolution functions. Functions are sourced (never executed directly) and operate on `$REPO`, which the caller MUST set before sourcing or before calling any function defined here. Permissions are `0644` (matches the `lib-*.sh` sourced-only convention in `scripts/`).

## Functions

### `native_open_blockers <issue-number>`

Queries GitHub's native issue-dependencies API (`repos/<REPO>/issues/<N>/dependencies/blocked_by`) and prints a space-separated list of OPEN blocker issue numbers on stdout. Empty output means no native blockers known. Fail-open on any gh error (404 on repos without the dependencies feature, transient `gh` failures): prints nothing, returns 0.

### `prose_open_blockers <issue-number>`

Scans the issue body and every comment body separately (per-document iteration to prevent cross-document fabrication) for the conservative prose-dependency keyword set defined in `parse-prose-blockers.sh`, resolves each referenced same-repo issue's current state, and prints a space-separated list of OPEN refs on stdout. Self-references (the candidate's own number) are filtered out. The parser is invoked via `bash "$parser_script"` so it works regardless of the execute bit; if the file exists but is not executable, a warning is emitted on stderr. If the parser file is missing entirely (`! -f`), the function returns 0 silently (fail-open). Every boundary (body fetch, comments fetch, parser invocation, per-ref state lookup) is fail-open: any failure degrades to "no additional prose blockers known".

### `all_open_blockers <issue-number>`

Unions native and prose blocker sets, dedupes, and returns a space-separated list of OPEN blockers. Native-first short-circuit: if `native_open_blockers` returns a non-empty list, the prose path is skipped entirely (the issue is already ineligible). Documented tradeoff: skip/error messages may list only native blocker numbers when both sources apply — see `skills/implement/SKILL.md` Preflight section **Preflight — admission gate known limitation (D3)** and the admission-gate note immediately following it (same fail-open posture is intentional).

## Sourcing requirements

1. **`REPO` must be set first.** The functions read `$REPO` at call time; sourcing the library does not resolve it for you. `scripts/implement-admission.sh` resolves `REPO` via `gh repo view` (or `--repo` when passed) before sourcing.
2. **`set -euo pipefail`-safe.** The functions are written so empty-pipeline edges (no native blockers found, no prose refs found) produce empty output rather than triggering `pipefail`. The library can be sourced into a script running with `set -euo pipefail`.
3. **Source-failure guard required.** An unguarded `source` of a missing or unreadable file under `set -e` aborts the script before any stdout is emitted. Admission wraps `source` with explicit failure handling per `scripts/implement-admission.md`.

## Edit-in-sync pointers

| File | Relationship |
|---|---|
| `scripts/parse-prose-blockers.sh` | The regex parser invoked by `prose_open_blockers`. Resolved at function call time via `$(dirname "${BASH_SOURCE[0]}")/parse-prose-blockers.sh` so the path stays correct regardless of which script sources the library. |
| `scripts/parse-prose-blockers.md` | Sibling-doc contract for the parser. |
| `scripts/test-parse-prose-blockers.sh` | Offline regression harness; `make test-parse-prose-blockers`. |
| `scripts/implement-admission.md` | Admission orchestration contract (exit codes, sentinel, fork `--repo`). |
| `agent-lint.toml` | Both `blocker-helpers.sh` and `blocker-helpers.md` are excluded from agent-lint — the script is sourced-only (agent-lint does not follow `source`); the sibling `.md` mirrors the `parse-prose-blockers.md` exclusion pattern. |

## When edits to this file require updates elsewhere

- **Function signature change** (rename, argument order, return semantics) → update `scripts/implement-admission.sh` and this contract; update `parse-prose-blockers.md` if the parser-invocation contract shifts; update `scripts/test-parse-prose-blockers.sh` when parser behavior changes.
- **Fail-open posture change** → update `scripts/implement-admission.md` and Preflight prose in `skills/implement/SKILL.md` if operator-visible semantics change.
