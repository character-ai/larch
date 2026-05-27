## Goal
Implement issue #2868: [IMPLEMENTING] Guarded aggregator containment relaxation\n\nPartition piece 2 of 5 split from #2677..

## Implementation Plan
## Plan

# Implementation Plan: Guarded aggregator containment relaxation (#2868)

## Files to modify/create

### UPDATED: `skills/review/scripts/aggregate-findings.sh`

Add a default-off `--allow-findings-outside-tmpdir true|false` flag that gates only the input-containment rejection branch. All other validation, dispatch, and output paths remain unchanged. The new flag is validated **before** any path-containment check fires so invalid values such as `maybe` produce the proper `must be true or false` diagnostic rather than a misleading containment error (resolves FINDING_2 and FINDING_8: the Approach below and the edit step list both use the same order — boolean validation before `REVIEW_TMPDIR_CANON` resolution).

Concrete edits, in implementation order:

1. **Variable initialization**: add `ALLOW_FINDINGS_OUTSIDE_TMPDIR="false"` next to the existing `INPUT_MODE="code"` initialization. Default `false` preserves byte-equivalent behavior for every current caller.
2. **`usage()` string**: append `[--allow-findings-outside-tmpdir true|false]` to the existing usage string after `[--input-mode plan|code]`. Keep the rest of the usage line identical.
3. **Argv parse `case`**: insert `--allow-findings-outside-tmpdir) ALLOW_FINDINGS_OUTSIDE_TMPDIR="${2:?}"; shift 2 ;;` alongside the other boolean cases (`--codex-present`, `--cursor-present`). The split argv form (`--allow-findings-outside-tmpdir true`) is the only accepted form; no `=*` arm. **Do not** add a separate `--allow-findings-outside-tmpdir=*` parser case — the hint, docs, and tests all use the split form.
4. **Early boolean validation**: validate the new flag immediately after the required-arg check for `--findings-file` / `--review-tmpdir`, **before** `REVIEW_TMPDIR_CANON` resolution and **before** the symlink/canonicalize/containment block. Add `[[ "$ALLOW_FINDINGS_OUTSIDE_TMPDIR" == "true" || "$ALLOW_FINDINGS_OUTSIDE_TMPDIR" == "false" ]] || { larch_err "aggregate-findings.sh: --allow-findings-outside-tmpdir must be true or false"; exit 2; }`. Same exit code and grammar as the sibling flags. Place the existing `--codex-present` / `--cursor-present` / `--mode` / `--input-mode` boolean validation block alongside this early validation so the entire boolean validation pass runs in one place before any filesystem check.
5. **Containment `case` gating**: leave the symlink rejection (`! -L "$FINDINGS_FILE"`) and the `_findings_canon` canonicalization unconditional. Wrap **only** the rejection branch of the `case "$_findings_canon"` block in `if [[ "$ALLOW_FINDINGS_OUTSIDE_TMPDIR" != "true" ]]; then ... fi`. The `"$REVIEW_TMPDIR_CANON"/* | "$REVIEW_TMPDIR_CANON"` accept branch stays as-is so its empty body remains the no-op fast path.
6. **Hint on the containment error**: change the containment `larch_err` to read `aggregate-findings.sh: --findings-file must resolve under --review-tmpdir ($REVIEW_TMPDIR_CANON): $FINDINGS_FILE (use --allow-findings-outside-tmpdir true to bypass)`. Note the **split argv form** in the hint (no `=`); copying the hint must produce a working command (resolves FINDING_1). **Do not** modify the symlink-rejection, `--findings-file is required`, missing-file, or unresolvable-tmpdir errors — the hint belongs only to the containment rejection.
7. **Post-dispatch output containment unchanged**: the `_cand_canon` / candidate-resolves-under-tmpdir check that emits `append_warning "- **findings aggregator**: aggregator output path resolves outside --review-tmpdir; ..."` stays strict. The new flag relaxes input only.
8. **Outside-input `mv -f` guard for non-fatal contract**: when `ALLOW_FINDINGS_OUTSIDE_TMPDIR == "true"`, wrap the final `mv -f "$merged_tmp" "$FINDINGS_FILE"` in a guarded form that does not let a non-zero `mv` exit cascade under `set -euo pipefail`. Use the existing `MERGE_PIPELINE_RC` / warning conventions: on `mv -f` failure set `MERGE_PIPELINE_RC=2`, append a Warning under `External Reviewer Issues` (matching the rest of the non-fatal aggregator path), leave the original outside `$FINDINGS_FILE` untouched, and emit `REASON=dispatch-failed` so the script exits 0 (resolves FINDING_13). For default-off (`false`) callers the `mv -f` path is byte-equivalent to today.

### UPDATED: `skills/review/scripts/aggregate-findings.md`

1. **CLI table**: add a new row at the bottom of the fenced CLI block: `--allow-findings-outside-tmpdir true|false  (optional, default false) — relaxes only the input containment check`. Keep all existing rows byte-identical.
2. **CLI table caveat on `--findings-file`**: refine the existing `--findings-file PATH      (required) ballot path under $REVIEW_TMPDIR` row to read `(required) ballot path under $REVIEW_TMPDIR (unless --allow-findings-outside-tmpdir=true)`. Single-line change.
3. **New `## Escape hatch` bullet** appended after the existing `LARCH_AGGREGATOR_DISABLED=1` paragraph: `--allow-findings-outside-tmpdir true — narrow opt-in that relaxes input-path containment only. Symlink rejection and the post-dispatch output containment check remain enforced; the rejection error message names this flag so callers can discover the opt-in from the failure.` Use the **split argv form** in the doc body since that is the only parser-accepted form.
4. **Asymmetric-relaxation paragraph**: append a short paragraph noting that opt-in callers can place `--findings-file` outside `--review-tmpdir`, but every dispatch artifact (`aggregator-prompt.md`, candidate output, etc.) still must resolve under `--review-tmpdir`; this asymmetry is intentional and is the trust boundary.
5. **`mv -f` blast-radius + non-fatal contract note**: append one sentence to the same paragraph: success rewrites `--findings-file` in place; opt-in callers that need rollback should snapshot or stage the ballot before invoking the aggregator, since validator failure preserves input but success always clobbers in place. Note that when the final `mv -f` itself fails for an outside path (read-only parent, lost permissions), the aggregator preserves the original input and reports `REASON=dispatch-failed` instead of exiting non-zero, matching the non-fatal aggregator contract.
6. **`LARCH_AGGREGATOR_DISABLED=1` interaction note**: add one sentence under the existing `LARCH_AGGREGATOR_DISABLED=1` paragraph noting that the disabled fast-path still runs the containment check before returning `REASON=disabled`; operators who want both disabled-mode and an outside-tmpdir input must also pass `--allow-findings-outside-tmpdir true` (resolves the in-scope doc-only portion of FINDING_10; the behavior change to move the disabled fast-path before containment is out of scope for #2868).

### UPDATED: `SECURITY.md`

Add a concise trust-model note for the aggregator's containment relaxation. One short paragraph (or one to two bullets in the existing Pre-vote findings aggregation section, whichever matches the file's style at edit time):

- Default `--allow-findings-outside-tmpdir` value is `false`; existing `/review` call sites are byte-equivalent.
- Opt-in (`true`) relaxes **input** path containment only; the symlink-rejection rule on `--findings-file` and the post-dispatch output containment check both remain enforced.
- When opt-in is active, success rewrites the outside `--findings-file` in place via `mv -f`; opt-in callers that need rollback must stage or snapshot the ballot. Validator failure preserves input; only successful merge clobbers in place.
- Residual same-UID TOCTOU window between canonicalize and `mv` is the same as today's in-tmpdir behavior — no new structural guarantee is offered by the flag.

(Resolves FINDING_3. The note is a doc-only update; no audit signal, breadcrumb, or `execution-issues.md` line — per the user-resolved Step 1c decision that the explicit flag is the audit signal.)

### UPDATED: `skills/review/scripts/test-aggregate-findings.sh`

Add the regression cases before the `=== stub merges 3 findings into 1 ===` block so the new tests run against early validation only (no LLM-stub dependency on the rejected case). Use the existing `mktemp` `$TMP` and `$AGG` bindings.

1. **Sibling temp dir + cleanup**: at the top of the new test section, allocate `TMP_OUTSIDE="$(mktemp -d "${TMPDIR:-/tmp}/test-agg-outside.XXXXXX")"` so the directory is genuinely outside `$TMP` (and therefore outside `--review-tmpdir`). Extend the existing `EXIT` trap to include `${TMP_OUTSIDE:-}` (e.g. `trap 'rm -rf "$TMP" "${TMP_OUTSIDE:-}"' EXIT`) so the new fixture is cleaned up alongside `$TMP` (resolves FINDING_6).
2. **Test case 1 — outside-tmpdir rejected without flag**:
   - Write a 2-block `### FINDING_` ballot into `$TMP_OUTSIDE/outside.md` with two distinct reviewer slot names. Insufficient-input is therefore not the rejection path; containment is.
   - Snapshot for cmp: `cp "$TMP_OUTSIDE/outside.md" "$TMP_OUTSIDE/outside-orig.md"`.
   - Invoke under `set +e` so the negative exit does not abort the harness: `set +e; "$AGG" --findings-file "$TMP_OUTSIDE/outside.md" --review-tmpdir "$TMP" --codex-present true --cursor-present true --mode diff 2>"$TMP/out-outside-reject.err" >"$TMP/out-outside-reject.env"; _rc=$?; set -e` (resolves FINDING_14). Assert `[[ "$_rc" == "2" ]] || fail "outside without flag expected exit 2, got $_rc"`.
   - Assert stderr contains `must resolve under --review-tmpdir` and the new hint substring `--allow-findings-outside-tmpdir true` using `grep -Fq -- '...'` so the leading-dash pattern is not interpreted as a grep option (resolves FINDING_12).
   - Assert `outside.md` is byte-unchanged after the rejected call: `cmp -s "$TMP_OUTSIDE/outside-orig.md" "$TMP_OUTSIDE/outside.md" || fail "outside ballot changed on rejection"`.
3. **Test case 2 — outside-tmpdir allowed with flag**:
   - Build the allowed-outside fixture as a **3-block** `### FINDING_` file using the same reviewer slot names that the existing `write_stub_dispatch` merge stub emits (`cursor-a-output.txt`, `cursor-b-output.txt`, `cursor-c-output.txt`). The fixture intentionally mirrors `in3.md` so the merge stub's `cursor-a`/`cursor-b`/`cursor-c` outputs validate cleanly (resolves FINDING_5). A new 2-block fixture would either fail aggregator slot-validation or require a new dedicated stub kind; the 3-block fixture matches the existing pattern and adds no new stub.
   - Write to `$TMP_OUTSIDE/outside-work.md`; keep a `$TMP_OUTSIDE/outside-work-orig.md` copy for cmp.
   - Use the existing `write_stub_dispatch` helper + `AGGREGATE_DISPATCH_SH="$TMP/stub-dispatch.sh"` + `AGGREGATE_STUB_MODE=ok` + `AGGREGATE_STUB_MERGE_KIND=merge` pattern so the aggregator completes a real merge end-to-end without LLM dispatch.
   - Invoke `"$AGG" --findings-file "$TMP_OUTSIDE/outside-work.md" --review-tmpdir "$TMP" --codex-present true --cursor-present true --mode diff --allow-findings-outside-tmpdir true >"$TMP/out-outside-allow.env"`.
   - Assert `AGGREGATED=true` and `REASON=ok` in the env capture.
   - Strong persistence asserts (resolves FINDING_15): assert exactly one `^### FINDING_` heading in the rewritten file — `[[ "$(grep -c '^### FINDING_' "$TMP_OUTSIDE/outside-work.md" | tr -d '[:space:]')" == "1" ]] || fail "expected one FINDING after outside-allow merge"`. Also assert the file content changed: `! cmp -s "$TMP_OUTSIDE/outside-work-orig.md" "$TMP_OUTSIDE/outside-work.md" || fail "outside-work.md unchanged after merge"`.
4. **Test case 3 — strict output containment preserved when input is outside-allowed**:
   - Reuse the same 3-block outside fixture in a fresh `$TMP_OUTSIDE/outside-output-test.md`.
   - Use `write_stub_dispatch` with a stub variant or env override that makes the dispatcher resolve `ALL_OUTPUT_FILES_PATH` (or `ALL_OUTPUT_FILES`) to a candidate path **outside `$TMP`** (e.g. `$TMP_OUTSIDE/outside-candidate.txt`). If the existing stub does not parameterize the candidate path, add a small `AGGREGATE_STUB_CANDIDATE_OUTSIDE_PATH=...` knob to the stub script written by `write_stub_dispatch`; do not change the live `aggregate-findings.sh` candidate-resolution logic.
   - Invoke `"$AGG" --findings-file "$TMP_OUTSIDE/outside-output-test.md" --review-tmpdir "$TMP" --codex-present true --cursor-present true --mode diff --allow-findings-outside-tmpdir true >"$TMP/out-outside-output.env"`.
   - Assert `AGGREGATED=false` and `REASON=dispatch-failed` in the env capture.
   - Assert that the existing `aggregator output path resolves outside --review-tmpdir` warning text was appended to `execution-issues.md` (use the harness's existing helper if available; otherwise grep `$TMP/execution-issues.md`).
   - Assert the outside input file is byte-unchanged: `cmp -s "$TMP_OUTSIDE/outside-output-test-orig.md" "$TMP_OUTSIDE/outside-output-test.md" || fail "outside input clobbered on dispatch-fail"` (resolves FINDING_4).
5. **Wiring**: no Makefile change needed — `make test-aggregate-findings` continues to run the file end-to-end. The new tests reuse the existing `$TMP` `--review-tmpdir`, the existing `write_stub_dispatch` helper (with one new stub knob for case 3), and the existing trap — so the shard assignment under `test-harnesses-8` is unaffected.

## Approach

The relaxation is a narrow trust-boundary knob in a single script, not a wider path-policy abstraction. The new flag is opt-in, default-off, and uses the same split-argv `true|false` grammar that the script already uses for `--codex-present` and `--cursor-present` so reviewers can pattern-match without learning a new convention. The new boolean is validated **immediately after argv parsing and before any filesystem check** so an invalid value like `maybe` produces the right diagnostic before the containment or symlink rules ever run.

Gating happens at exactly one location — the rejection branch of the containment `case` — because the surrounding canonicalization and symlink-rejection logic is load-bearing for other reasons (consistent absolute paths for downstream `mv`/`cat`; no surprise-indirection security guarantee). The error-message hint is the audit signal: anyone hitting the rejection now sees the exact split-form flag they can opt into, so the surface is self-documenting without requiring an extra stderr warning, breadcrumb, or `execution-issues.md` entry when the flag is in effect. The hint uses the parser-accepted **split** form (`--allow-findings-outside-tmpdir true`), not the equals form, so an operator copying the hint produces a working command.

The relaxation is deliberately **asymmetric**: input (`--findings-file`) becomes flag-controlled; output (the post-dispatch `_cand_canon` resolves-under-tmpdir check) stays unconditionally strict. This means a caller can place a ballot outside `--review-tmpdir` but every aggregator-produced artifact (prompt, LLM candidate, validate-py output) still lives inside `--review-tmpdir`. That is what the future R4/FINDING_2-style multi-round-loop wants: per-round ballots at `round-N/findings-in-scope.md`, with `round-N/agg-in-scope/` as the aggregator scratch dir. The flag is **not** wired into `review-core.sh` or `plan-review-loop.sh` in this partition; future multi-round callers opt in when their partition lands.

A `SECURITY.md` paragraph documents the trust-model change (input-only relaxation; symlink and output rules unchanged; in-place rewrite blast radius; residual same-UID TOCTOU). The aggregator's non-fatal contract — failures return `REASON=...` and exit 0 — is preserved by guarding the final outside-input `mv -f` against `set -e` cascade: if `mv` fails, emit a warning and `REASON=dispatch-failed`, leaving the original input untouched.

## Edge cases

- **Invalid flag value** (`--allow-findings-outside-tmpdir maybe`): the early boolean validation rejects with exit 2 and a clear `must be true or false` error **before** any filesystem check. Matches the sibling-flag behavior exactly.
- **Equals-form invocation** (`--allow-findings-outside-tmpdir=true`): the parser does not accept this form; the existing `unknown option` catch-all fires. The hint, docs, and tests all use the split form so operators discover the right grammar.
- **Flag missing entirely**: default `false` preserves byte-equivalent behavior for every current caller. All existing tests pass without modification.
- **Symlink + flag=true**: the unconditional symlink rejection still fires before the flag-gated containment case. Symlinks remain rejected with the existing `must name an existing regular file (not a symlink)` error — no hint suffix, because the hint applies only to containment violations.
- **Flag=true with input under tmpdir**: the containment `case`'s accept branch matches first; the rejection branch (now flag-gated) is unreached. No semantic change vs. today.
- **Flag=true with a non-existent file**: the pre-canonicalization `[[ -f "$FINDINGS_FILE" && ! -L "$FINDINGS_FILE" ]]` check rejects before canonicalization runs. The flag does not weaken the existence requirement.
- **Flag=true with a directory passed as `--findings-file`**: same regular-file check rejects with exit 2.
- **Flag=true with outside input but read-only outside destination**: the final `mv -f` may fail. The guarded `mv -f` path catches this, emits a warning, sets `REASON=dispatch-failed`, and exits 0 — non-fatal contract preserved. Test case 3 covers this with a stubbed candidate path outside `--review-tmpdir` (the same behavior is exercised: `REASON=dispatch-failed`, input byte-unchanged); a dedicated read-only-destination `mv` test is the natural extension but is not required by Step 1c's "minimal pair" scope.
- **Concurrent in-place rewrite of an outside-tmpdir ballot**: same TOCTOU window the script has always had between canonicalize and `cat`/`mv`. The flag does not materially worsen it; symlink rejection remains the main structural filesystem guard.
- **`LARCH_AGGREGATOR_DISABLED=1` + outside input + flag missing**: containment still runs in disabled mode (current behavior), so the call rejects with exit 2. Operators who want disabled+outside must pass both `LARCH_AGGREGATOR_DISABLED=1` and `--allow-findings-outside-tmpdir true`. Documented in `aggregate-findings.md`.

## Failure modes

The three most likely architectural failure paths, with earliest warning signals and mitigations:

1. **Accidental opt-in spreads via copy-paste**: an operator copies a `--allow-findings-outside-tmpdir true` snippet into a `/review` call site, silently relaxing input policy in a context that does not need it.
   - Earliest warning signal: `git grep --line-number 'allow-findings-outside-tmpdir' -- skills/ scripts/` returns hits outside the script + test + doc.
   - Mitigation: scope is documented in `aggregate-findings.md` as "future multi-round-loop callers only"; no in-tree wiring lands in this partition; the regression harness exercises only the script under test. A follow-up partition that wires the flag should land with explicit reviewer scrutiny of the call-site change. `SECURITY.md` records the trust-model change so future reviewers see the boundary.
2. **In-place rewrite corrupts a shared-state ballot when flag is on**: success path runs `mv -f "$merged_tmp" "$FINDINGS_FILE"` on the outside-tmpdir input. A bad LLM merge destroys the canonical ballot that other steps (next round, retries, manual inspection) expect.
   - Earliest warning signal: the `aggregate-findings.md` doc + `SECURITY.md` paragraph warning callers to snapshot or stage if rollback is needed; the validator's fail-closed contract still preserves the input on validation failure (only success clobbers).
   - Mitigation: opt-in callers should stage findings to a per-round `agg-*/` dir or snapshot before invocation. The validator already protects against partial / malformed merges; only an LLM that produces a structurally valid but semantically wrong merge can cause silent damage, which is the existing aggregator failure mode for in-tmpdir ballots too.
3. **Asymmetric model misunderstood — caller expects output to live outside tmpdir**: a future caller passes the flag and expects the LLM candidate output or the prompt file to also resolve outside `--review-tmpdir`. The post-dispatch `_cand_canon` check then fails with `REASON=dispatch-failed` and the `aggregator output path resolves outside --review-tmpdir` warning, which looks like "the flag didn't work."
   - Earliest warning signal: that warning is already explicit; the doc note in `aggregate-findings.md` calling out the asymmetry adds a second signal; Test case 3 locks the behavior as a regression so the asymmetric contract cannot silently drift.
   - Mitigation: `aggregate-findings.md` documents the input-only relaxation explicitly and names the post-dispatch check that remains strict. `SECURITY.md` records the same boundary in trust-model language.

## Testing strategy

- **Hermetic regression coverage**: three new cases in `test-aggregate-findings.sh`:
  - Outside ballot + flag absent → exit 2 with hint in stderr; ballot byte-unchanged.
  - Outside ballot + flag=true + stub merge → `AGGREGATED=true`, `REASON=ok`, exactly one `### FINDING_` block after rewrite, file content changed vs. snapshot.
  - Outside ballot + flag=true + stub candidate path outside `--review-tmpdir` → `AGGREGATED=false`, `REASON=dispatch-failed`, output-containment warning present, outside input byte-unchanged.
- **Test invariants**: every new invocation that expects a non-zero exit runs under `set +e ... set -e` so the harness's `set -euo pipefail` does not abort. Every `grep` against a flag-shaped pattern uses `--` to escape the leading dashes.
- **Cleanup hygiene**: `TMP_OUTSIDE` is created via `mktemp -d` and removed alongside `$TMP` by the extended `EXIT` trap.
- **No existing test changes required**: every existing test passes the flag implicitly as `false` (default), so none of the harness's other assertions move. `cmp -s` snapshots in the existing tests still match.
- **Verification commands** before commit:
  - `bash skills/review/scripts/test-aggregate-findings.sh` — direct harness run.
  - `make test-aggregate-findings` — Makefile-driven run including timer wrapper.
  - `bash scripts/relevant-checks.sh` — repo-wide pre-commit (shellcheck, markdownlint, lint-bash32, agent-lint, etc.).
  - Manual smoke: invoke the script with the flag against an inside-tmpdir ballot to confirm CLI parsing works (no need to combine with `LARCH_AGGREGATOR_DISABLED=1` since disabled mode still enforces containment; per FINDING_10 the doc note covers that interaction).
- **CI**: the existing `test-harnesses-8` shard already includes `test-aggregate-findings`; no Makefile shard reassignment.

diff_lines: 100

## Acceptance

- All edits to `skills/review/scripts/aggregate-findings.sh`, `skills/review/scripts/aggregate-findings.md`, `SECURITY.md`, and `skills/review/scripts/test-aggregate-findings.sh` land as specified in the plan.
- New `--allow-findings-outside-tmpdir true|false` flag parses (split form only), defaults to `false`, validates booleans before any path check, and rejects invalid values with `must be true or false` and exit 2.
- Default-off behavior is byte-equivalent to today for every current `/review` and `/design` call site: containment rejection still fires; symlink rejection still fires; error message wording changes only on the containment rejection (adds the split-form hint).
- Symlink rejection at the regular-file/symlink check stays unconditional; post-dispatch `_cand_canon` output containment check stays strict regardless of the flag.
- When the flag is `true` and the final `mv -f` fails for the outside destination, the script preserves the original input, emits a Warning under `External Reviewer Issues` in `execution-issues.md`, sets `REASON=dispatch-failed`, and exits 0 (non-fatal aggregator contract).
- `SECURITY.md` carries a concise trust-model note covering: default-off, input-only relaxation, symlink-still-rejected, output-containment-still-strict, in-place `mv -f` blast radius, residual same-UID TOCTOU.
- `aggregate-findings.md` carries a new CLI row, a `--findings-file` caveat parenthetical, an Escape hatch bullet using split-form, an asymmetric-relaxation paragraph including the `mv -f` non-fatal note, and a one-sentence note that `LARCH_AGGREGATOR_DISABLED=1` still runs containment.
- Three regression tests in `test-aggregate-findings.sh` cover: outside+no-flag → exit 2 with hint substring (under `set +e`); outside+flag=true with 3-block stub-compatible fixture → `REASON=ok` and exactly one `### FINDING_` block in rewritten file; outside+flag=true with stub candidate path outside `--review-tmpdir` → `REASON=dispatch-failed` with input byte-unchanged.
- `TMP_OUTSIDE` sibling tmpdir is created via `mktemp -d` outside `$TMP` and cleaned up by the extended `EXIT` trap. All grep assertions on flag-shaped patterns use `-Fq -- '...'`.
- `bash skills/review/scripts/test-aggregate-findings.sh` passes locally; `make test-aggregate-findings` passes; `bash scripts/relevant-checks.sh` passes.
- No changes to `review-core.sh`, `plan-review-loop.sh`, or any other caller. `Makefile` shard registration of `test-aggregate-findings` is unchanged.

diff_lines: 100

## Test plan
(no test plan section in plan-file)
