## Goal
Harden SKIP_REASON awk extractor in generate-code-flow-diagram.sh and sanitize untrusted ci-failed-jobs.sh stderr passthrough

## Implementation Plan
## Plan


This plan resolves issue #2854, a combined OOS follow-up that bundles two latent-severity shell sanitization fixes:

- **Item A**: `generate-code-flow-diagram.sh` `SKIP_REASON` capture currently uses `awk -F=` which drops content past the second `=` on a `REASON_TOKEN=` line, breaking on hypothetical tokens containing embedded `=`.
- **Item B**: `ci-failed-jobs.sh` forwards `gh run view` stderr lines verbatim via `larch_err "$line"`; a crafted job name or matrix label containing control bytes (BEL, ESC, ANSI escapes, etc.) is echoed without sanitization.

Both items ship in a single PR per Step 1c clarification.

## Scope contract (set by plan-review findings)

- **Item A — SKIP_REASON output contract is preserved unchanged for production-shape sanitizer lines**. The real sanitizer at `scripts/sanitize-mermaid-fragment.sh:201,224,227,238` emits lines of the form `REASON_TOKEN=<token> fence=<N> line=<M>` where `<token>` is a single space-bounded identifier. Today's `awk -F=` returns the substring up to the first space (e.g., `pipe-in-node-label fence` — note the trailing word `fence` from the `=` split, not the intended `pipe-in-node-label`). The fix MUST emit only the token (`pipe-in-node-label`), matching the same-script consumer at `sanitize-mermaid-fragment.sh:283-285` which uses `awk -F'[ =]'` to extract `$2`. The fix also preserves embedded `=` within the token (the issue's hypothetical `pipe-in-node-label=foo` case).
- **Item B — per-input-line control-byte stripping only**. The new helper sanitizes individual diagnostic lines after the `while IFS= read -r line` loop has already split `gh run view` stderr on `\n`. Newline-driven log-line splitting from upstream stderr is **explicitly out of scope** for this fix: the line-oriented loop is the correct boundary for gh-trusted diagnostic output. Items concerning raw job-name sanitization in TSV/KV emit paths (lines 125-128) are filed as **OOS_3** for separate triage. The plan documents this scope explicitly in `ci-failed-jobs.md` so future operators understand the boundary.

## Files to modify/create

### UPDATED: `skills/implement/scripts/generate-code-flow-diagram.sh`

Replace the `awk -F=` extractor at line 102 with a two-step portable awk that strips the `REASON_TOKEN=` prefix then truncates at the first whitespace. This:
- preserves embedded `=` within the token (the issue's intent),
- discards trailing `fence=<N> line=<M>` metadata (preserves the existing token-only contract),
- returns non-zero when no `REASON_TOKEN=` line is present (keeps the `|| printf 'sanitizer-rejected'` fallback meaningful).

Current (line 102):

```sh
emit_kv SKIP_REASON "$(awk -F= '$1=="REASON_TOKEN"{print $2; exit}' "$sanitize_log" 2>/dev/null || printf 'sanitizer-rejected')"
```

Replacement:

```sh
emit_kv SKIP_REASON "$(awk '/^REASON_TOKEN=/{sub(/^REASON_TOKEN=/, ""); sub(/ .*$/, ""); print; found=1; exit} END{exit !found}' "$sanitize_log" 2>/dev/null || printf 'sanitizer-rejected')"
```

Behavior contract (post-fix):
- `REASON_TOKEN=pipe-in-node-label fence=1 line=7` → `SKIP_REASON=pipe-in-node-label` (matches today's intent; the existing buggy `awk -F=` returned `pipe-in-node-label fence` — the new form fixes this).
- `REASON_TOKEN=pipe-in-node-label=foo fence=1 line=7` → `SKIP_REASON=pipe-in-node-label=foo` (embedded `=` preserved; issue's reported case).
- `REASON_TOKEN=` (empty value, hypothetical) → `SKIP_REASON=` (empty captured; fallback does NOT fire). Unchanged from existing.
- Sanitizer log missing or no `REASON_TOKEN=` line → `SKIP_REASON=sanitizer-rejected` (fallback fires via `END{exit !found}`). Unchanged.
- Multiple `REASON_TOKEN=` lines → first one captured (early `exit`). Unchanged.

The chosen awk form uses only portable POSIX features (`sub`, `print`, `END{exit ...}` — no gawk-only `match(...,arr)` 3-arg form). Runs unchanged on macOS BSD awk, gawk, and mawk.

### UPDATED: `skills/implement/scripts/generate-code-flow-diagram.md`

Add a paragraph documenting the post-fix `SKIP_REASON` contract:

- `SKIP_REASON` carries the bare REASON_TOKEN identifier (everything between `REASON_TOKEN=` and the first whitespace, including any embedded `=`).
- It does NOT carry trailing `fence=` / `line=` metadata even when the sanitizer log includes it.
- It falls back to `sanitizer-rejected` only when no `REASON_TOKEN=` line is present in the sanitizer log.

Per `.claude/rules/script-md-siblings.md`, this `.md` update ships in the same PR as the `.sh` behavior change.

### UPDATED: `scripts/ci-failed-jobs.sh`

Add a new local shell function `sanitize_diagnostic_line()` defined immediately after the existing `sanitize_list()` (between current lines 27 and the `job_class()` definition). Apply it inline at the existing line-80 `larch_err "$line"` call inside the `while IFS= read -r line || [ -n "$line" ]; do ... done < "$tmp_stderr"` loop. Do not modify the loop structure; do not change the strict `sanitize_list` policy used at lines 145-147.

Implementation:

```sh
sanitize_diagnostic_line() {
    # Strip C0 control bytes (0x00-0x1F) and DEL (0x7F) from one diagnostic line.
    # Preserves printable ASCII (0x20-0x7E), spaces, punctuation, and pass-through UTF-8.
    # LC_ALL=C forces byte-wise tr behavior; BSD/macOS tr under UTF-8 locales can otherwise
    # report "illegal byte sequence" on malformed input from untrusted gh stderr.
    LC_ALL=C tr -d '[:cntrl:]'
}
```

At the existing line-80 site, change:

```sh
        larch_err "$line"
```

to:

```sh
        larch_err "$(printf '%s' "$line" | sanitize_diagnostic_line)"
```

The `printf '%s'` form prevents `printf` from interpreting `%`-like sequences in `$line` (defensive against `gh` diagnostics containing literal `%` characters).

Audit confirmation (from Step 1c scope, reinforced by plan-review):
- The line-80 site IS the only `larch_err` call in this file that takes external untrusted input from `gh run view` stderr.
- The other `larch_err` calls (`usage()` at line 16, `die()` at line 20) emit internal literal strings only and need no sanitization.
- The KV emits at lines 145-147 already pass through the strict `sanitize_list` and are unchanged.
- The TSV / KV emit paths at lines 125-128 carry job names from `gh run view` stdout JSON, which is a separate threat surface; auditing those is filed as **OOS_3** per voting.

### UPDATED: `scripts/ci-failed-jobs.md`

Document:
- The new `sanitize_diagnostic_line()` helper, its policy (strip C0+DEL, preserve printable ASCII), and its placement (inline at the stderr-passthrough loop).
- The explicit scope boundary: this helper protects against intra-line control-byte injection (BEL, ESC, ANSI escapes) in gh-stderr passthrough. It does NOT protect against newline-driven log-line splitting; the line-oriented `while IFS= read -r` loop is the correct boundary for gh-trusted diagnostic output. Operators concerned with newline-injection in gh stderr should escalate via a separate audit (OOS surface).
- The `LC_ALL=C` requirement and rationale (byte-wise tr on BSD/macOS UTF-8 locales).

### UPDATED: `skills/implement/scripts/test-generate-code-flow-diagram.sh`

Extend the existing harness using the actual harness API (`assert_contains`, inline `SANITIZE_REJECT=1` stub-driven flow). The harness currently has one sanitizer-stub `STUB` heredoc at lines 35-39:

```sh
cat > "$plugin/scripts/sanitize-mermaid-fragment.sh" <<'STUB'
#!/usr/bin/env bash
if [ "${SANITIZE_REJECT:-}" = 1 ]; then printf 'STATUS=rejected\nREASON_TOKEN=test-reject\n'; exit 1; fi
printf 'STATUS=ok\n'
STUB
```

Replace it with an env-driven variant that respects `SANITIZE_REASON_LINE` for the full REASON_TOKEN payload (defaults to today's `REASON_TOKEN=test-reject` for backward compat with the existing case at lines 50-53):

```sh
cat > "$plugin/scripts/sanitize-mermaid-fragment.sh" <<'STUB'
#!/usr/bin/env bash
if [ "${SANITIZE_REJECT:-}" = 1 ]; then
    printf 'STATUS=rejected\n'
    printf '%s\n' "${SANITIZE_REASON_LINE:-REASON_TOKEN=test-reject}"
    exit 1
fi
printf 'STATUS=ok\n'
STUB
```

Add three new test cases after the existing rejection case (lines 50-53):

```sh
# Item A regression: production-shape sanitizer line (issue #2854, FINDING_5, FINDING_20).
tmp3="$TMP_ROOT/session3"; mkdir -p "$tmp3"
out=$(cd "$repo" && CLAUDE_PLUGIN_ROOT="$plugin" SANITIZE_REJECT=1 \
    SANITIZE_REASON_LINE='REASON_TOKEN=pipe-in-node-label fence=1 line=7' \
    "$HELPER" --implement-tmpdir "$tmp3")
assert_contains 'SKIP_REASON=pipe-in-node-label' "$out" 'SKIP_REASON extracts token only from production-shape line'

# Item A regression: embedded = inside token (issue #2854 hypothetical, FINDING_25).
tmp4="$TMP_ROOT/session4"; mkdir -p "$tmp4"
out=$(cd "$repo" && CLAUDE_PLUGIN_ROOT="$plugin" SANITIZE_REJECT=1 \
    SANITIZE_REASON_LINE='REASON_TOKEN=pipe-in-node-label=foo fence=1 line=7' \
    "$HELPER" --implement-tmpdir "$tmp4")
assert_contains 'SKIP_REASON=pipe-in-node-label=foo' "$out" 'SKIP_REASON preserves embedded = within token'

# Item A regression: explicit no-token fallback (FINDING_10, FINDING_18).
tmp5="$TMP_ROOT/session5"; mkdir -p "$tmp5"
out=$(cd "$repo" && CLAUDE_PLUGIN_ROOT="$plugin" SANITIZE_REJECT=1 \
    SANITIZE_REASON_LINE='STATUS_DETAIL=other' \
    "$HELPER" --implement-tmpdir "$tmp5")
assert_contains 'SKIP_REASON=sanitizer-rejected' "$out" 'SKIP_REASON falls back when REASON_TOKEN absent'
```

Notes on harness API fidelity:
- Use existing `assert_contains "$needle" "$haystack" "$label"` signature (NOT the previously-cited `assert_file_contains` — that helper does not exist in this harness).
- Capture stdout into `out` via `out=$(cd "$repo" && ... "$HELPER" --implement-tmpdir "$tmp")` exactly mirroring the existing pattern at lines 47-49.
- The existing first rejection case at lines 50-53 (no env override) keeps the default `REASON_TOKEN=test-reject` payload and is unchanged — preserves backward compat for the existing `SKIP_REASON=test-reject` assertion.

### UPDATED: `skills/implement/scripts/test-generate-code-flow-diagram.md`

One-line note: harness now covers (1) production-shape sanitizer log line, (2) embedded-`=` token, (3) explicit no-token fallback, in addition to the original happy-path and default-rejection cases.

### UPDATED: `scripts/test-ci-failed-jobs.sh`

Extend the existing harness with a new test block (`T8`) that exercises the `sanitize_diagnostic_line` helper via the existing `GH_MODE=fail` path with a fixture stderr file. Two threading changes are required:

1. Update the existing `gh` stub `fail` mode (lines 44-47) to source stderr content from an optional fixture file when `GH_FAIL_STDERR_FILE` is set:

```sh
fail)
    if [ -n "${GH_FAIL_STDERR_FILE:-}" ] && [ -r "${GH_FAIL_STDERR_FILE}" ]; then
        cat "${GH_FAIL_STDERR_FILE}" >&2
    else
        printf '%s\n' 'HTTP 500' >&2
    fi
    exit 2
    ;;
```

2. Update `run_subject()` (lines 67-74) to thread `GH_FAIL_STDERR_FILE` into the subject's env so the copied gh stub sees it:

```sh
run_subject() {
    local root=$1 out=$2 err=$3 tsv=$4 rc=0
    PATH="$root/scripts:$PATH" LARCH_QUIET_DISABLE="${LARCH_QUIET_DISABLE:-1}" \
        GH_MODE="${GH_MODE:-lines}" GH_LINES_FILE="${GH_LINES_FILE:-}" \
        GH_FAIL_STDERR_FILE="${GH_FAIL_STDERR_FILE:-}" \
        "$root/scripts/ci-failed-jobs.sh" --run-id run123 --repo owner/repo --output-tsv "$tsv" \
        > "$out" 2> "$err" || rc=$?
    printf '%s\n' "$rc"
}
```

3. Add the `T8` block after the existing `T7` table-driven block:

```sh
# T8 — Item B regression: stderr passthrough strips control bytes but preserves printable prose.
T8="$TMPROOT/t8"
mkdir -p "$T8"
write_subject "$T8"
write_gh_lines "$T8"
# Fixture: single logical diagnostic line with BEL (0x07) and ESC (0x1b) embedded between printable text.
# No interior \n — we are testing intra-line control-byte stripping per the documented scope (FINDING_6,
# FINDING_21, FINDING_24: newline-injection prevention is OUT OF SCOPE for this fix).
printf '%b\n' 'HTTP 500\x07Bad Gateway\x1b[31mred\x1b[0m' > "$T8/stderr.txt"
GH_MODE=fail
GH_FAIL_STDERR_FILE="$T8/stderr.txt"
rc=$(run_subject "$T8" "$T8/out" "$T8/err" "$T8/jobs.tsv")
assert_rc "Item B: gh failure with control bytes in stderr exits 1" "$rc" 1
# Printable prose preserved.
assert_file_contains "T8: printable prose passes through" "$T8/err" "HTTP 500"
assert_file_contains "T8: trailing printable text preserved" "$T8/err" "Bad Gateway"
# Control bytes stripped: assert the literal BEL and ESC byte sequences are absent.
if grep -aF $'\x07' "$T8/err" >/dev/null; then
    fail "T8: BEL (0x07) was not stripped from stderr passthrough"
else
    ok "T8: BEL (0x07) stripped from stderr passthrough"
fi
if grep -aF $'\x1b' "$T8/err" >/dev/null; then
    fail "T8: ESC (0x1b) was not stripped from stderr passthrough"
else
    ok "T8: ESC (0x1b) stripped from stderr passthrough"
fi
unset GH_FAIL_STDERR_FILE
```

Notes on harness API fidelity:
- Use existing `assert_file_contains`, `assert_rc`, `ok`, `fail` helpers (already defined at lines 13-23).
- The negative byte assertion uses an inline `if grep -aF ... >/dev/null; then fail; else ok` block exactly like the T6 pattern at lines 138-142 — no new helper required (addresses FINDING_28).
- The `unset GH_FAIL_STDERR_FILE` at the end prevents leaking the fixture path into any subsequent tests.

Embedded-newline assertions are intentionally NOT added (per documented scope in `ci-failed-jobs.md` and FINDING_6/FINDING_21/FINDING_24 re-scope guidance).

### UPDATED: `scripts/test-ci-failed-jobs.md`

One-line note: harness now covers T8 stderr passthrough control-byte stripping via the new `GH_FAIL_STDERR_FILE` thread-through.

## Approach

The two fixes are independent shell hardening changes with bounded behavioral impact. Both follow the same pattern: identify the untrusted-input edge case, replace the existing parser/passthrough with a defensive form that preserves all existing behavior contracts, and add focused regression tests using each harness's existing API.

Item A's awk replacement uses two `sub()` calls: first to strip the `^REASON_TOKEN=` prefix, then to truncate at the first whitespace. Combined with `END{exit !found}`, the awk command returns non-zero when no token line is present, preserving the existing `|| printf 'sanitizer-rejected'` fallback semantics. The chosen idiom is portable POSIX awk; no gawk-only extensions. The matching block keeps `exit` so only the first `REASON_TOKEN=` line is captured.

Item B introduces a single small helper (`sanitize_diagnostic_line`) defined locally in `ci-failed-jobs.sh`. The function is intentionally NOT added to `scripts/lib-quiet.sh` even though `larch_err` lives there: broadening the helper's scope to every `larch_err` caller would expand the audit surface beyond the explicit Step 1c-clarified boundary (one file). A shared helper extraction is filed as **OOS_1** for separate triage.

The sanitizer uses `LC_ALL=C tr -d '[:cntrl:]'`. The `LC_ALL=C` environment override forces `tr` into byte-wise behavior, sidestepping BSD/macOS tr's tendency to report "illegal byte sequence" on malformed UTF-8 input from untrusted stderr. The `[:cntrl:]` class under C locale covers exactly C0 control bytes (0x00-0x1F) and DEL (0x7F); printable ASCII, multi-byte UTF-8 continuation bytes, and high-ASCII bytes are preserved.

The scope-boundary documentation in `ci-failed-jobs.md` is load-bearing: the helper protects against intra-line control-byte injection (the actual threat from job names with embedded ANSI escapes or BEL), but does NOT prevent newline-injection from upstream stderr — because the surrounding `while IFS= read -r line` loop has already split on `\n` at the input boundary. The line-oriented loop is the correct boundary for gh-trusted diagnostic output (gh CLI emits its own diagnostics as multi-line stderr; collapsing them into a single record would lose structural fidelity). Operators concerned with stronger newline-handling in gh stderr can escalate via a separate audit.

## Edge cases

- **Empty `$sanitize_log` or missing `REASON_TOKEN=` line (Item A)**: `END{exit !found}` fires, awk exits non-zero, `|| printf 'sanitizer-rejected'` runs. Unchanged from existing.
- **`REASON_TOKEN=` line with empty value (Item A)**: prefix strip leaves empty string; whitespace truncate leaves empty string; `print` emits empty; `found=1` so fallback does NOT fire. Result: `SKIP_REASON=`. Unchanged from existing.
- **`REASON_TOKEN=<token>` line with no trailing whitespace (Item A)**: prefix strip leaves `<token>`; whitespace-truncate `sub(/ .*$/, "")` has nothing to remove; `print` emits `<token>`. Result: `SKIP_REASON=<token>`.
- **Multiple `REASON_TOKEN=` lines (Item A)**: matching-block `exit` fires on the first. Unchanged.
- **`gh` stderr containing only control bytes (Item B)**: after sanitization, `sanitize_diagnostic_line` emits an empty string; `larch_err ""` runs once per input line. Per-line passthrough contract preserved (one log line per input line).
- **`gh` stderr containing valid UTF-8 multi-byte sequences (Item B)**: `LC_ALL=C` byte-wise behavior; multi-byte UTF-8 continuation bytes (0x80-0xBF) are not in `[:cntrl:]` and pass through unchanged.
- **`gh` stderr containing malformed non-UTF-8 high bytes (Item B)**: `LC_ALL=C tr` treats input as bytes; malformed sequences pass through control-byte-stripped without `tr` errors. Addresses FINDING_3/FINDING_14/FINDING_17.
- **`gh` stderr with embedded newlines (Item B)**: explicitly out of scope. The `while IFS= read -r line` loop splits on `\n` BEFORE the helper runs; each resulting line is independently sanitized for control bytes. Operators read multiple `larch_err` lines; the line-oriented gh stderr contract is preserved. Documented in `ci-failed-jobs.md`.
- **Sanitizer log path missing (Item A)**: existing `2>/dev/null` swallows the awk error; `||` fallback fires. Unchanged.
- **Non-ASCII high bytes in sanitizer log (Item A)**: awk handles bytes by default; `sub` operates on the byte sequence; `print` emits bytes unchanged. No change.

## Failure modes

The 3 most likely architectural/systemic failure paths, with earliest warning signals and simplest mitigations:

1. **Item A: portable awk silently requires gawk extensions** — A future maintainer could "improve" the extractor by using `match($0, /^REASON_TOKEN=(.*)$/, arr)` (gawk-only 3-arg `match`) or `gensub()` (gawk-only). Earliest warning signal: the new tests `SKIP_REASON extracts token only from production-shape line` and `SKIP_REASON preserves embedded = within token` fail on macOS BSD awk during local development or on a CI runner using BSD awk. Mitigation: the chosen `sub(/^REASON_TOKEN=/, ""); sub(/ .*$/, ""); print` form is portable POSIX awk; verified manually on macOS in Step 1d. The `.md` sibling documents the portability constraint.

2. **Item B: `LC_ALL=C` forgotten during refactor** — A future maintainer factoring `sanitize_diagnostic_line` into a shared helper (per OOS_1) could drop the `LC_ALL=C` prefix, reintroducing the BSD/macOS UTF-8 illegal-byte-sequence regression. Earliest warning signal: a CI run on macOS hits a `gh` failure whose stderr contains malformed bytes; `tr` emits its own diagnostic into the captured stderr; the test harness sees unexpected `larch_err` content. Mitigation: the helper definition includes an inline comment documenting the `LC_ALL=C` requirement; the `.md` sibling restates it; the OOS_1 follow-up issue will reference this constraint when designing the shared helper.

3. **Item B: scope-creep into newline handling** — A future reviewer or contributor could re-open the "newline injection" concern and propose a stream-level sanitization that collapses gh stderr into a single record. This would lose the per-line diagnostic structure that operators rely on. Earliest warning signal: a PR proposing to move the sanitizer outside the `while IFS= read -r` loop, or to add `tr -d '\n'` to the helper. Mitigation: the `ci-failed-jobs.md` scope documentation explicitly names this as out-of-scope and points to the operator audit path (OOS surface).

## Testing strategy

Both target scripts have co-located regression harnesses:

- `skills/implement/scripts/test-generate-code-flow-diagram.sh` (with `.md` sibling) — covers Item A.
- `scripts/test-ci-failed-jobs.sh` (with `.md` sibling) — covers Item B.

Per-harness extensions (see "UPDATED" sections above):
- **test-generate-code-flow-diagram.sh**: extend the sanitizer stub to accept `SANITIZE_REASON_LINE` env override; add three test cases (production-shape token-only extraction; embedded-`=` preservation; no-token fallback).
- **test-ci-failed-jobs.sh**: thread `GH_FAIL_STDERR_FILE` through `run_subject` and the `fail` mode of the gh stub; add a `T8` block exercising the helper with control-byte fixtures (BEL, ESC).

After implementation:
1. Run the two harnesses directly: `bash skills/implement/scripts/test-generate-code-flow-diagram.sh` and `bash scripts/test-ci-failed-jobs.sh`. Both must exit 0.
2. Run `bash scripts/relevant-checks.sh` to verify no other linter or harness regressed.
3. Manually verify on macOS (BSD awk) by running:
   ```sh
   printf '%s\n' 'REASON_TOKEN=pipe-in-node-label fence=1 line=7' | awk '/^REASON_TOKEN=/{sub(/^REASON_TOKEN=/, ""); sub(/ .*$/, ""); print; found=1; exit} END{exit !found}'
   ```
   and confirming the output is `pipe-in-node-label` and exit code is 0.
4. Manually verify on macOS the LC_ALL=C tr behavior:
   ```sh
   printf '%b' 'hello\x07world\x1b[31mred\x1b[0m\n' | LC_ALL=C tr -d '[:cntrl:]'
   ```
   confirming output is `helloworldredred` (or similar; control bytes stripped, printable text retained), and that a UTF-8 sequence passes through unmodified:
   ```sh
   printf '\xc3\xa9\xc3\xa8' | LC_ALL=C tr -d '[:cntrl:]'
   ```
   (output: `éè` or the equivalent two-byte sequence preserved).

No new integration tests, no new CI workflow changes, no changes to existing test infrastructure beyond the per-harness extensions described above.


## Acceptance

This design is done when an implementation PR satisfies all of the following:

### Item A — `SKIP_REASON` extraction (`skills/implement/scripts/generate-code-flow-diagram.sh`)

- [ ] Line 102 `emit_kv SKIP_REASON ...` uses the two-step portable awk form: `awk '/^REASON_TOKEN=/{sub(/^REASON_TOKEN=/, ""); sub(/ .*$/, ""); print; found=1; exit} END{exit !found}'`. No gawk-only extensions (no 3-arg `match`, no `gensub`).
- [ ] `skills/implement/scripts/generate-code-flow-diagram.md` documents the post-fix `SKIP_REASON` contract: token-only (everything between `REASON_TOKEN=` and the first whitespace, including embedded `=`); no trailing `fence=`/`line=` metadata; falls back to `sanitizer-rejected` when no `REASON_TOKEN=` line is present.
- [ ] `skills/implement/scripts/test-generate-code-flow-diagram.sh` is extended: the sanitizer stub accepts `SANITIZE_REASON_LINE` env override (defaults to today's `REASON_TOKEN=test-reject`); three new test cases pass — (1) production-shape line `REASON_TOKEN=pipe-in-node-label fence=1 line=7` → `SKIP_REASON=pipe-in-node-label`, (2) embedded-`=` `REASON_TOKEN=pipe-in-node-label=foo fence=1 line=7` → `SKIP_REASON=pipe-in-node-label=foo`, (3) no-token fallback `STATUS_DETAIL=other` (no `REASON_TOKEN=` line) → `SKIP_REASON=sanitizer-rejected`.
- [ ] `skills/implement/scripts/test-generate-code-flow-diagram.md` sibling carries a one-line note about the new coverage.
- [ ] The existing first rejection case (default `SKIP_REASON=test-reject`) is unchanged.

### Item B — stderr passthrough sanitization (`scripts/ci-failed-jobs.sh`)

- [ ] New local function `sanitize_diagnostic_line()` defined between the existing `sanitize_list()` (line ~27) and `job_class()`. Body: `LC_ALL=C tr -d '[:cntrl:]'`. Comment explains the `LC_ALL=C` requirement for BSD/macOS byte-wise behavior.
- [ ] The line-80 `larch_err "$line"` call is rewritten to `larch_err "$(printf '%s' "$line" | sanitize_diagnostic_line)"`.
- [ ] The existing `while IFS= read -r line || [ -n "$line" ]; do ... done < "$tmp_stderr"` loop structure is unchanged.
- [ ] The other `larch_err` calls in this file (lines 16, 20 in `usage()`/`die()`) are unchanged — they emit internal literal strings.
- [ ] The strict `sanitize_list` policy used at lines 145-147 is unchanged.
- [ ] `scripts/ci-failed-jobs.md` documents (1) the new helper and its policy, (2) the explicit scope boundary: intra-line control-byte stripping only — newline-driven log-line splitting from upstream stderr is OUT OF SCOPE; the line-oriented loop is the correct boundary for gh-trusted diagnostic output, (3) the `LC_ALL=C` rationale.
- [ ] `scripts/test-ci-failed-jobs.sh` is extended: (a) the `gh` stub `fail` mode reads stderr from optional `GH_FAIL_STDERR_FILE`; (b) `run_subject()` threads `GH_FAIL_STDERR_FILE` into the subject env; (c) a new `T8` block exercises a single-line fixture with BEL (0x07) and ESC (0x1b) bytes, asserts `rc=1`, asserts printable substrings `HTTP 500` and `Bad Gateway` survive in captured stderr, asserts neither BEL nor ESC bytes survive (inline `if grep -aF $'\x07' ... ; then fail; else ok` pattern matching the existing T6 negative-check style).
- [ ] `scripts/test-ci-failed-jobs.md` sibling carries a one-line note about the new T8 coverage.

### Cross-cutting acceptance

- [ ] `bash skills/implement/scripts/test-generate-code-flow-diagram.sh` exits 0.
- [ ] `bash scripts/test-ci-failed-jobs.sh` exits 0.
- [ ] `bash scripts/relevant-checks.sh` reports no new failures.
- [ ] Manual macOS verification: the new awk form produces `pipe-in-node-label` for the production-shape line and exits 0; `LC_ALL=C tr -d '[:cntrl:]'` strips BEL/ESC from a hand-crafted printf input while preserving UTF-8 multi-byte sequences (e.g., `é`, `è`).
- [ ] OOS follow-ups #2874, #2875, #2876 are filed and recorded as `blocked-by` this issue (already done by `/design`; implementation PR should NOT re-create or modify these OOS issues).
- [ ] The implementation PR title and body reference issue #2854 (e.g., `Fixes #2854: ...`).

diff_lines: 140

## Test plan
(no test plan section in plan-file)
