## Goal
Implement issue #3074: [IMPLEMENTING] [OOS] Shared voter/tally infrastructure hardening — library reuse coupling, path validation, and emit_kv newline safety\n\n## Out-of-Scope Observation.

## Implementation Plan
## Plan

Address three hardening items from this OOS issue in one coherent change. The validator is wired into the two OOS-named consumers only; the broader `--design-tmpdir` sweep is deferred (FINDING_6).

### Item 1 — `lib-voter-coverage` plan-scope rename

Rename `scripts/lib-voter-coverage.sh` to `scripts/lib-plan-voter-coverage.sh` via `git mv`, and rename every public function from `voter_coverage_*` to `plan_voter_coverage_*` (full prefix replacement). Apply the same `git mv` + edit to `scripts/lib-voter-coverage.md`. A future code-review caller now hits a missing-symbol or missing-file error instead of silently breaking on plan-review-specific KV interleaving. The top comment in the renamed `.sh` and `.md` marks the library as plan-review-specific and names the interleaved KV order in `plan_voter_coverage_emit_status_block` as a binding contract. No backward-compat shim under the old name.

One production sourcer needs updating (`scripts/dispatch-plan-voters.sh:14-15`); three function-call sites in the same script rename to `plan_voter_coverage_*`. The regression harness `scripts/test-dispatch-plan-voters.sh` exercises the dispatcher stdout contract and remains structurally unchanged — it will validate that the rename did not regress KV byte-ordering.

### Item 2 — shared `--design-tmpdir` validator, narrowly wired

Add a new source-only library `scripts/lib-design-tmpdir.sh` exposing `larch_design_tmpdir_validate <dir>`. Wire it into `scripts/dispatch-plan-voters.sh` and `skills/design/scripts/tally-plan-review.sh` only.

The validator algorithm:

1. Reject empty input with `larch_err` + return 2.
2. Build the canonical allowlist once at first call from `${XDG_CACHE_HOME:-${HOME:-/tmp}/.cache}/larch/sessions/`, `${TMPDIR%/}` (when set), and `/tmp`. Canonicalize each prefix via `cd "$prefix" 2>/dev/null && pwd -P` when it exists (handles the macOS `/private` mapping); fall back to the literal string otherwise. Append a trailing `/` to each canonical prefix.
3. Walk up the candidate path component-by-component until the deepest existing ancestor is found (`/` floor).
4. Canonicalize that ancestor explicitly: `if ! resolved_ancestor=$(cd "$ancestor" 2>/dev/null && pwd -P); then larch_err "parent resolution failed"; return 2; fi`. This explicit guard is required (FINDING_10) so callers under `set -e` get the documented `larch_err` text.
5. Concatenate the unresolved tail onto `resolved_ancestor` to form `resolved_candidate`. No `mkdir` of untrusted parents (FINDING_3).
6. If the candidate exists, canonicalize the leaf too (`cd "$resolved_candidate" && pwd -P`) and use that. Reject a symlink-to-non-directory leaf (FINDING_4).
7. Compare via `case "$resolved" in "$prefix"*)` with the prefix literal quoted and only the trailing `*` unquoted (FINDING_9).
8. On no match, `larch_err` naming the resolved path and the allowlist; return 2.

The validator never modifies the filesystem. Callers `mkdir -p "$DESIGN_TMPDIR"` only after validation succeeds.

The validator is wired AFTER each script's existing argv validation block and BEFORE `mkdir -p "$DESIGN_TMPDIR"`. Both `dispatch-plan-voters.sh` and `tally-plan-review.sh` already use `larch_err` + `exit` for argv errors, so `exit $?` after validation is consistent with the existing failure contract (FINDING_5 does not apply to either wired script).

### Item 3 — `emit_kv` newline reject

Extend `emit_kv` in `scripts/lib-quiet.sh` to reject values containing `\n` or `\r` before printing. On match, call `larch_err` naming the offending key and return 2. Use `case "$value" in *$'\n'*|*$'\r'*)` to stay Bash 3.2-compatible. The reject runs in both the `LARCH_QUIET_ACTIVE` (FD-3) and stdout-fallback branches.

Pre-flight audit: `grep -rn 'emit_kv' scripts/ skills/` during implementation. Current call-sites pass single-line values; no regressions expected.

### File operations

- NEW: `scripts/lib-design-tmpdir.sh` + sibling `scripts/lib-design-tmpdir.md`.
- NEW: `scripts/test-lib-design-tmpdir.sh` + sibling `scripts/test-lib-design-tmpdir.md`.
- REWRITTEN via `git mv`: `scripts/lib-voter-coverage.sh` → `scripts/lib-plan-voter-coverage.sh` (function renames + plan-scope comment).
- REWRITTEN via `git mv`: `scripts/lib-voter-coverage.md` → `scripts/lib-plan-voter-coverage.md` (function signature updates + plan-scope warning).
- UPDATED: `scripts/lib-quiet.sh` (`emit_kv` newline reject).
- UPDATED: `scripts/lib-quiet.md` (newline contract note).
- UPDATED: `scripts/test-lib-quiet.sh` (reject coverage for LF, CR, both, literal backslash-n pass, long value pass).
- UPDATED: `scripts/dispatch-plan-voters.sh` (source-line rename, three function-call renames, validator guard).
- UPDATED: `scripts/dispatch-plan-voters.md` (function-call references + validator note).
- UPDATED: `skills/design/scripts/tally-plan-review.sh` (validator guard).
- UPDATED: `skills/design/scripts/tally-plan-review.md` (one-line note in Invariants).
- UPDATED: `SECURITY.md` (tmpdir allowlist + emit_kv single-line contract).

### Edge cases

- `--design-tmpdir` empty: validator returns 2; consumers' existing argv check already requires non-empty.
- `..` segments: nearest-existing-ancestor walk + canonicalize resolves them.
- Parent symlink redirection: `cd && pwd -P` exposes the true location.
- Leaf symlink escape: validator canonicalizes the leaf when it exists, or rejects a symlink-to-non-directory leaf.
- `$TMPDIR` unset: allowlist skips that prefix; `$HOME/.cache/larch/sessions/` and `/tmp` still accepted.
- `$XDG_CACHE_HOME` set: validator accepts paths under it.
- macOS `/tmp` paths: canonicalize to `/private/tmp`; allowlist prefix canonicalized the same way.
- Fully non-existent candidate: walk up, canonicalize ancestor, append tail; no `mkdir`.
- `emit_kv` literal `\n` text (backslash + n): allowed.
- `emit_kv` long single-line value: allowed.
- `emit_kv` value containing `=`: allowed (consumers split on first `=`).

### Failure modes

1. Trailing-slash mismatch in canonical prefix: normalize via `${tmpdir%/}/` at allowlist construction; harness covers trailing-slash variants.
2. `emit_kv` reject breaks a tolerant caller: pre-flight grep audit; fix any caller that constructs values from raw multi-line sources.
3. `git mv` rename misses a call-site or doc reference: post-rename `grep -rn 'voter_coverage_\|lib-voter-coverage'` audit across `scripts/`, `skills/`, `docs/`, `.github/`.

### Testing strategy

- New `scripts/test-lib-design-tmpdir.sh` covering allowed prefixes (HOME/.cache/larch/sessions, TMPDIR, /tmp, XDG_CACHE_HOME); macOS `/private/tmp` canonicalization; disallowed prefix; `..` traversal; parent-symlink redirection; **leaf symlink escape (FINDING_4 regression)**; fully non-existent path with existing parent; nearest-existing-ancestor multi-level walk; explicit `cd && pwd -P` failure path returning 2 (FINDING_10 regression); quoted-prefix `case` behavior with glob metacharacters in `$TMPDIR` (FINDING_9 regression); empty input.
- Extended `scripts/test-lib-quiet.sh` with `emit_kv` reject cases for LF, CR, both, literal backslash-n (pass), and long single-line value (pass).
- Existing `scripts/test-dispatch-plan-voters.sh` continues to validate the dispatcher stdout contract.
- `bash scripts/relevant-checks.sh` after each implementer commit.
- `make lint` for the broader hook set (bash32-portability, drift-prone-prose, script-md-siblings).

## Acceptance

- `scripts/lib-design-tmpdir.sh` exists with `larch_design_tmpdir_validate` implementing the 8-step algorithm.
- `scripts/lib-voter-coverage.sh` and `scripts/lib-voter-coverage.md` no longer exist; the renamed `scripts/lib-plan-voter-coverage.sh` and `scripts/lib-plan-voter-coverage.md` carry the renamed `plan_voter_coverage_*` symbols.
- `scripts/dispatch-plan-voters.sh` sources `lib-plan-voter-coverage.sh` and `lib-design-tmpdir.sh`, invokes the validator after argv parse, and uses the renamed function names. `skills/design/scripts/tally-plan-review.sh` sources `lib-design-tmpdir.sh` and invokes the validator after argv parse.
- `scripts/lib-quiet.sh` `emit_kv` returns 2 with a `larch_err` when the value contains `\n` or `\r`; existing single-line callers are unaffected.
- `SECURITY.md` documents the new tmpdir allowlist and the `emit_kv` single-line contract.
- `bash scripts/test-lib-design-tmpdir.sh` passes (new harness).
- `bash scripts/test-lib-quiet.sh` passes (extended harness).
- `bash scripts/test-dispatch-plan-voters.sh` passes (regression coverage for renamed symbols).
- `make lint` passes.
- No `voter_coverage_` or `lib-voter-coverage` references remain in `scripts/`, `skills/`, `docs/`, or `.github/`.

diff_lines: 365

## Test plan
(no test plan section in plan-file)
