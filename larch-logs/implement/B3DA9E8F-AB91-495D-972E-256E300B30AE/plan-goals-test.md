## Goal
Add repeatable --context-files flag to launch-claude-review.sh with strict validation, allow-root forwarding, and dedup

## Implementation Plan
## Plan

### Approach

Expose a public, repeatable `--context-files <path>` argv flag on `scripts/launch-claude-review.sh` that forwards verbatim to `scripts/launch-claude-subprocess.sh`'s existing `--context-files` interface. The launcher does only what the subprocess cannot — early hard-error on missing/empty/unreadable operator-supplied paths via explicit arity validation (NOT Bash `${parameter:?...}` expansion, whose exit-1 status would violate the documented exit-2 contract), and canonical-path dedup across all five context-flag sources (implicit `--diff-file/--scope-files/--plan-file/--feature-file` plus the new explicit flag) — while the subprocess retains authority over canonicalization, symlink rejection, allow-root containment, the 1 MB per-file size cap, and the 20-file global cap. The asymmetric validation (hard-error for explicit, silent-skip for implicit) is intentional: implicit-flag callers (`launch-review.sh`, `dispatch-code-voters.sh`) legitimately pass empty strings when a phase has no plan/feature/scope, but explicit operator-typed `--context-files` should fail fast on typos.

**Containment-test contract**: the launcher's `--allow-root` propagation for context-file dirnames is the intentional contract — operator-supplied `--context-files` paths are AUTHORIZED via widened allow-roots, matching the existing implicit-flag behavior. Tests verify this propagation positively and use an orthogonal rejection vector (symlink) for subprocess-stderr-propagation coverage. The subprocess remains authoritative for what counts as "inside" allowed roots; the launcher only widens the set.

No changes to the subprocess. No new callers added.

### Files to modify

#### UPDATED: `scripts/launch-claude-review.sh`

- Add `EXPLICIT_CONTEXT_FILES=()` initialization near the existing scalars (around line 28).
- Insert a new case-arm in the argv parser between `--feature-file` (line 43) and `--timeout` (line 44) using explicit arity validation (NOT `${2:?...}` which would exit 1):
  ```bash
  --context-files)
      [[ $# -ge 2 && -n "${2:-}" && "$2" != --* ]] || {
          larch_err "launch-claude-review.sh: --context-files requires a value"
          exit 2
      }
      EXPLICIT_CONTEXT_FILES+=("$2")
      shift 2
      ;;
  ```
- Update the `usage()` larch_err string (line 12) to include `[--context-files <file>...]`.
- Refactor `append_context_file()` (line 95) to accept a `strict` argument with `local strict="${2:-0}"` default for backward compat. Signature `<path> <strict>`. Compute canonical path with `cd "$(dirname "$path")" && pwd -P` + basename. When `strict=1`: hard-error with the fixed wording `launch-claude-review.sh: --context-files path missing or unreadable: $path` and exit 2 if path is empty, `! -f`, `! -r`, or canonical is empty. When `strict=0`: preserve current silent-skip (only `! -f`, NOT `-r`).
- Add canonical-path dedup via a new `:`-separated `seen_canonical_paths` parallel to existing `seen_allow_roots`. Forward `--context-files "$path"` (operator form, subprocess re-canonicalizes), append canonical to `seen_canonical_paths`, and add the canonical dirname to `allow_root_args` via the existing `seen_allow_roots` dedup logic.
- Update the four existing call sites (lines 105-108) to pass `0` as the second argument explicitly: `append_context_file "$DIFF_FILE" 0`, etc.
- Append a new loop after the four existing calls iterating `EXPLICIT_CONTEXT_FILES[@]` with `strict=1` using the `${array[@]+"${array[@]}"}` empty-array guard.
- Add a one-line WHY comment above the refactored helper: `# strict=1: --context-files hard-errors on missing/empty/unreadable; strict=0: implicit flags silent-skip (callers may pass empty).`
- Bash 3.2 compatibility: no associative arrays, no `mapfile`/`readarray`, no `${var,,}`.

#### UPDATED: `scripts/launch-claude-review.md`

Add a paragraph documenting `--context-files`:
- Repeatable single-value flag (each occurrence appends one path).
- Operator-supplied paths hard-error with exit 2 on missing/empty/non-existent/unreadable (in contrast to implicit context flags' silent-skip).
- Role-orthogonal across `--role reviewer` and `--role voter`.
- Deduplicates by canonical path against the four implicit flags and against repeated `--context-files`.
- The launcher AUTHORIZES each forwarded context file's parent directory via `--allow-root`, matching implicit-flag behavior. Subprocess remains authoritative for symlink rejection, 1 MB per-file cap, and 20-file global cap.
- Markdownlint MD038 hygiene: `--context-files <path>` (no inner whitespace at code-span boundaries); "repeatable" qualifier in prose.

#### UPDATED: `scripts/test-launch-claude-review.sh`

Extend the existing stub `claude` to tee stdin to `$TMPROOT/claude-stdin.log` when `LARCH_TEST_CLAUDE_STDIN_LOG` is set. Export this env var once in harness setup.

Add 8 new test cases before the final `echo "PASS: ..."` line:
1. Two `--context-files` paths under `--role reviewer` — assert exit 0 + stub passthrough + both file contents appear in `claude-stdin.log`.
2. Same as (1) under `--role voter` — role-orthogonality.
3. Missing-value contract: trailing `--context-files` AND `--context-files --timeout 5` (flag-like next token) — both exit 2 with stderr `launch-claude-review.sh: --context-files requires a value`.
4. Non-existent path — exit 2 with stderr `launch-claude-review.sh: --context-files path missing or unreadable`.
5. Dedup observation via rendered prompt: `--diff-file foo --context-files foo` (same path) — grep `claude-stdin.log` for the rendered context marker, assert exactly ONE occurrence.
6. Positive allow-root propagation: context file in a separate mktemp dir outside `$TMPROOT` — assert exit 0 (launcher widens allow-roots).
7. Subprocess-stderr propagation via symlink: `ln -s "$prompt" "$TMPROOT/symlink-ctx.txt"`; invoke with `--context-files "$TMPROOT/symlink-ctx.txt"` — assert exit 2 + stderr `invalid context file`.
8. Unreadable file: `chmod 000 "$TMPROOT/unreadable.txt"`; skip case when `EUID == 0`; assert exit 2 + stderr `launch-claude-review.sh: --context-files path missing or unreadable`. Add `chmod 644` cleanup.

All existing test cases must continue to pass byte-for-byte.

#### UPDATED: `scripts/test-launch-claude-review.md`

Extend Covers line 5 to mention: repeatable `--context-files` reviewer + voter, missing-value (trailing + flag-like next token) exit-2, non-existent + unreadable exit-2, dedup via rendered prompt, allow-root propagation positive test, subprocess symlink-rejection propagation.

#### UPDATED: `skills/design/scripts/test-validate-plan-commands.sh`

Flip the regression at lines 104-107: replace the `grep -Fq "$launch_want"` positive assertion with an inverted assertion that the unknown-flag DEFECT for `--context-files` is NOT emitted after the launcher's `usage()` lists the new flag. If the validator's known-flag allowlist also needs updating, do so in the same PR.

#### UPDATED: `skills/design/scripts/fixtures/validate-plan-commands/launch-context-plan.md`

Content unchanged; the fixture now acts as a positive regression (plan using `--context-files` must NOT trigger unknown-flag DEFECT). Same-PR alignment with the launcher's `usage()` update.

#### UPDATED: `SECURITY.md`

Add 2-4 sentences in the existing "Claude voter subprocess (`launch-claude-review.sh`)" paragraph documenting:
- Public repeatable `--context-files <path>` operator surface.
- Strict hard-error on missing/empty/unreadable.
- Launcher widens `--allow-root` for each accepted path's parent directory (matches implicit-flag behavior).
- Subprocess mechanical guarantees retained: symlink rejection, control-character / `..` rejection, 1 MB per-file size cap, 20-file global cap.

### Edge cases

- Repeated identical paths — dedup collapses to one forwarded entry.
- Explicit duplicate of implicit path — first-seen wins (implicit four processed first); explicit duplicate dropped silently.
- Empty `EXPLICIT_CONTEXT_FILES` under `set -u` — guarded via `${array[@]+"${array[@]}"}`.
- Embedded spaces in paths — array expansion preserves them.
- Relative paths — canonicalized via `cd && pwd -P`; subprocess re-canonicalizes.
- Symlink path — launcher dedup uses target via `pwd -P`; subprocess rejects the symlink at validation.
- Path beyond 20-file cap — subprocess rejects with `--context-files is capped at 20 files`.
- Unreadable file — strict mode hard-errors before subprocess invocation.
- Trailing `--context-files` and `--context-files --timeout 5` — both rejected by explicit arity check with exit 2.
- Context file outside default PLUGIN_ROOT/SESSION_ROOT — launcher widens allow-roots; subprocess accepts.

### Failure modes

1. **Backward-compat regression on existing `append_context_file` call sites**: helper signature changes. Earliest warning: existing test cases fail. Mitigation: `local strict="${2:-0}"` default + explicit `0` at all 4 call sites in same PR.
2. **Canonicalization mismatch with subprocess**: launcher and subprocess may resolve symlinked parents differently. Earliest warning: dedup test fails under symlinked `$TMPROOT`. Mitigation: keep canonicalization shape identical (`cd && pwd -P`).
3. **`make lint` breakage from stale validator-harness expectations**: existing `test-validate-plan-commands.sh` lines 104-107 expects unknown-flag DEFECT. Earliest warning: first commit fails CI. Mitigation: flip assertion in same PR.
4. **Unreadable-file test under root EUID**: chmod 000 is bypassed by root. Mitigation: skip case when `EUID == 0`.
5. **`scripts/test-launch-claude-review.md` sibling drift**: `.claude/rules/script-md-siblings.md` enforcement. Mitigation: same-PR Covers-line extension.

### Testing strategy

- Extend `scripts/test-launch-claude-review.sh` with the 8 new cases. All existing cases pass byte-for-byte.
- Update `skills/design/scripts/test-validate-plan-commands.sh` for the assertion flip.
- Run `make lint-bash32`.
- Run `make lint` (or `bash scripts/relevant-checks.sh`).
- No new CI workflows; both extended harnesses are already wired into the lint chain.

## Acceptance

The implementation is complete and ready to land when ALL of the following hold:

1. `scripts/launch-claude-review.sh --context-files <path> --context-files <path2>` is accepted; both paths are forwarded to `launch-claude-subprocess.sh` via `--context-files` argv tokens.
2. `scripts/launch-claude-review.sh --context-files` (trailing, no value) and `scripts/launch-claude-review.sh --context-files --timeout 5` (flag-like next token) BOTH exit with code 2 and stderr line containing `launch-claude-review.sh: --context-files requires a value`.
3. `scripts/launch-claude-review.sh --context-files /nonexistent` exits with code 2 and stderr line containing `launch-claude-review.sh: --context-files path missing or unreadable`.
4. `scripts/launch-claude-review.sh --context-files <chmod-000-file>` exits with code 2 and the same `--context-files path missing or unreadable` stderr (skipped under `EUID == 0`).
5. `scripts/launch-claude-review.sh --diff-file <path> --context-files <same-path>` causes the rendered prompt sent to the claude subprocess to contain the file's content exactly ONCE (dedup observable via stdin-tee of the stub `claude`).
6. `scripts/launch-claude-review.sh --context-files <path-in-separate-mktemp-dir>` exits with code 0 (launcher's `--allow-root` propagation widens the subprocess's allowed roots).
7. `scripts/launch-claude-review.sh --context-files <symlink>` exits with code 2 and stderr line containing `invalid context file` (subprocess symlink rejection propagated via the existing tempfile-stderr capture).
8. The flag works identically under `--role reviewer` and `--role voter`.
9. `scripts/launch-claude-review.md` documents the new flag, role-orthogonality, dedup behavior, and the `--allow-root` propagation contract.
10. `scripts/test-launch-claude-review.sh` contains 8 new test cases (per the Plan section) AND all pre-existing test cases continue to pass byte-for-byte.
11. `scripts/test-launch-claude-review.md` Covers line 5 mentions the new test cases per `.claude/rules/script-md-siblings.md`.
12. `skills/design/scripts/test-validate-plan-commands.sh` no longer asserts `--context-files` as `unknown-flag`; the fixture `launch-context-plan.md` is a positive regression (no DEFECT emitted).
13. `SECURITY.md` documents the operator-facing `--context-files` surface, strict missing/unreadable behavior, and `--allow-root` widening.
14. `make lint-bash32` passes.
15. `make lint` (or `bash scripts/relevant-checks.sh`) passes — script-md-siblings + validator-harness flips both green.
16. No changes to `scripts/launch-claude-subprocess.sh`; the 20-file cap and 1 MB per-file cap remain authoritative there.

diff_lines: 250

## Test plan
(no test plan section in plan-file)
