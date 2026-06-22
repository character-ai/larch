## Goal
Implement issue #4969: [IMPLEMENTING] bash-to-py-mop-up: Migrate materialize-manifest-oos.sh to Python (security-sensitive).

## Implementation Plan
## Plan

## Approach

- Treat the Python port in `python/file_oos.py` as the source of truth.
- Do not re-port manifest parsing, redaction, title normalization, deduping, or security routing beyond the parity gaps called out below.
- Replace only the remaining `implement_dispatch.py` materialize subprocess calls with direct in-process calls.
- Close the original six accepted review gaps before retiring the shell helper: mandatory `TypeError` handling at CLI and dispatch boundaries, IPv6 internal-URL redaction parity, exact security-audit heading dedup, fail-closed non-object observation items on full materialization, dual-pass dispatch exception mapping, and fail-closed primary redactor errors.
- Close four additional accepted gaps from plan review: `TypeError` in Step 9a.1 `oos_filer` warn-and-continue wrapper, count-only item-shape parity (no per-item validation on count-only), explicit `count_str` string binding after in-process cutover, and post-pass-two bail evaluation decoupled from subprocess return codes.
- Fix the merged bail-regression finding: after in-process cutover, `_oos_materialize_should_bail()` must not treat a successful dual-pass run with positive `count_str` as a bail condition. Gate the `count_str > 0` branch behind `materialize_failed` (or equivalent helper/call-site gating) so the external-implementer happy path returns `""`.
- Initialize dual-pass bail state before any per-pass try/except so post-pass-two evaluation never hits `NameError` when a pass raises before assignment.
- Retire the orphaned shell helper, shell harness, and companion docs.
- Remove all tracked references to retired basenames before adding them to `python/migrated-scripts.tsv`.

## Files to modify/create

### UPDATED: python/file_oos.py

- Change the security breadcrumb label from `materialize-manifest-oos.sh` to `cli.py oos materialize-manifest`.
- **Mandatory `TypeError` handling (CLI):** add `TypeError` to `materialize_manifest_main()`'s handled exception tuple alongside `ValueError`, `RuntimeError`, and `OSError`. Print the message to stderr and return exit code `1`. Do not gate this on pytest discovery.
- **IPv6 internal-URL parity:** extend `_INTERNAL_URL_RE` with the retired shell `sed` alternatives for ULA and link-local hosts inside URL context: `fc[0-9a-f]{2}:`, `fd[0-9a-f]{2}:`, and `fe80:` (case-insensitive). Keep existing IPv4, localhost, and private-hostname coverage unchanged.
- **Exact security-audit dedup:** change `_security_audit_has_title()` to scan line-by-line and return true only when a line equals exactly `### Security OOS: {title}` (matching retired `grep -Fqx` behavior). Do not use substring `in` on the full file body.
- **Split observation loading for count-only parity (FINDING_2):** refactor `_load_manifest_observations()` (or equivalent) so top-level manifest JSON parsing and `oos_observations` array-type validation remain shared, but **per-item dict-shape validation runs only when `count_only=False`**. On count-only, return `len(observations)` after top-level array validation, counting all array elements including non-objects (matching retired `jq` length semantics). Do not coerce non-dict entries to `{}` on the full-materialization path; raise `TypeError` when any `oos_observations` item is not a JSON object during full materialization only.
- **Fail-closed redactor:** remove `contextlib.suppress(Exception)` around `redact(text)` in `_sanitize_public_text()`. Let redactor failures propagate so materialization logs and bails like the retired `set -euo pipefail` shell path instead of continuing with only local PII regexes.
- Keep `materialize_manifest_main()` as the CLI entrypoint.

### UPDATED: python/implement_dispatch.py

- Import `file_oos`.
- In `_materialize_oos`, **initialize bail state before the dual-pass blocks:** at function entry (after `log` binding), set `count_rc = 0`, `count_str = ""`, and `materialize_failed = False` so post-pass-two `_oos_materialize_should_bail(...)` always receives defined values even when a per-pass `try`/`except` catches an exception before inner assignment.
- Replace both `_invoke_cli(["oos", "materialize-manifest", ...])` calls with direct calls to `file_oos.materialize_manifest_oos()`.
- Preserve the two-pass behavior and **always run pass two after pass one:**
  - first call with `count_only=True`;
  - second call with `count_only=False`, even when the count-only pass fails.
- **Per-pass exception mapping:** wrap each direct call in `try`/`except` catching `TypeError`, `ValueError`, `RuntimeError`, and `OSError`. On failure, write the exception text to `materialize-manifest-oos.log`, set `count_rc=1` for the count-only pass or `materialize_failed=True` for the full pass, and continue to the next pass instead of letting exceptions escape Step 2 dispatch.
- **In-process count binding (FINDING_3):** on the count-only pass success path, bind explicitly: `count_result = file_oos.materialize_manifest_oos(..., count_only=True)`; `count_str = str(count_result)`; `count_rc = 0`. Do not assign the raw `int` return value directly to `count_str`.
- **Post-pass-two bail gate (FINDING_4 + merged bail-regression fix):** after both passes complete, evaluate bail from failure-state variables, not subprocess `returncode`. When `materialize_failed`, call `_append_materialize_oos_failure` before bail evaluation. Then call `_oos_materialize_should_bail(count_rc=count_rc, count_str=count_str, oos_nonempty=oos_observations_nonempty, materialize_failed=materialize_failed)` once. Return `manifest-oos-materialization-failed` when the bail gate fires; otherwise return `""`.
- **Bail helper semantics (merged FINDING_1 fix):** update `_oos_materialize_should_bail()` so `count_str.isdigit() and int(count_str) > 0` bails **only when `materialize_failed` is true**. Keep `count_rc != 0` as an independent bail signal (still bails even when the full pass succeeds). Preserve the existing `materialize_failed and oos_nonempty` tail branch. This restores retired subprocess-era behavior where the positive-count branch was reachable only after a failed full pass, while allowing unconditional post-pass-two evaluation without false-bailing successful dual-pass runs with non-empty manifest observations.
- Preserve `count_str`, `count_rc`, `materialize-manifest-oos.log`, `_append_materialize_oos_failure`, and overall bail-reason semantics.
- Change the Tool Failures label from `materialize-manifest-oos.sh` to `cli.py oos materialize-manifest`.

### UPDATED: python/oos_filer.py

- **Step 9a.1 warn-and-continue `TypeError` parity (FINDING_1):** at the `file_oos.materialize_manifest_oos(manifest_path, tmpdir)` call in `_file`, add `TypeError` to the existing `except (OSError, RuntimeError, ValueError)` tuple so item-shape and other `TypeError` failures warn-and-continue like today instead of aborting `python3 python/cli.py oos file` with an uncaught traceback.

### UPDATED: python/test_file_oos.py

- Port the legacy shell harness coverage into pytest.
- Cover these cases from `skills/implement/scripts/test-materialize-manifest-oos.sh`:
  - empty array no-op;
  - non-empty append with external implementer attribution;
  - duplicate-title rerun idempotency;
  - `--count-only` count behavior;
  - invalid top-level `oos_observations` type fail-closed via `materialize_manifest_main()` returning `1`;
  - **scalar/non-object observation item fail-closed on full materialization:** assert full materialization raises or CLI returns `1` and does not write a public `oos-accepted-main-agent.md` block such as `Untitled external implementer OOS`;
  - **count-only with mixed array including non-object:** assert `materialize_manifest_oos(..., count_only=True)` returns array length (e.g. `[{"title":"x"},"bad"]` → `2`) without raising;
  - structured security routing to `security-oos-observations.md`;
  - prose `focus-area = security` retained as public;
  - security title alone does not security-route;
  - structured `focus_area` beginning with security does route;
  - **security-audit prefix-collision dedup:** prior heading `### Security OOS: Token leak followup` must not suppress a distinct later observation titled `Token leak`;
  - missing redactor/plugin root failure behavior;
  - monotonic `OOS_N` allocation;
  - title newline injection prevention;
  - PII redaction for internal URL (IPv4 and one IPv6 ULA/link-local URL), email, phone, account-style IDs, and SSN;
  - **redactor failure fail-closed:** monkeypatch `redact` to raise and assert no public OOS file contains the raw secret text.
- Prefer direct calls for core behavior.
- Use `materialize_manifest_main()` where CLI return-code parity matters.

### UPDATED: python/test_implement_dispatch.py

- Update `_materialize_oos` failure tests to monkeypatch `implement_dispatch.file_oos.materialize_manifest_oos` instead of faking `_invoke_cli(["oos", "materialize-manifest", ...])`.
- Add coverage that a `TypeError` on the count-only pass still runs the full pass and maps to `manifest-oos-materialization-failed` when bail conditions are met.
- Add coverage that `count_rc != 0` on the count-only pass reaches `_oos_materialize_should_bail` and returns `manifest-oos-materialization-failed` even when the full pass succeeds (FINDING_4).
- **Add regression coverage for successful dual-pass materialization (merged FINDING_1 fix):** monkeypatch both in-process passes to succeed with `count_only=True` returning `1` (or higher) and full materialization succeeding; assert `_materialize_oos(...)` returns `""` and does not emit `manifest-oos-materialization-failed`.
- Add unit coverage on `_oos_materialize_should_bail()` itself: `(count_rc=0, count_str="1", materialize_failed=False)` returns `False`; `(count_rc=0, count_str="1", materialize_failed=True)` returns `True`; `(count_rc=1, count_str="0", materialize_failed=False)` returns `True`.
- **Add regression coverage for pre-assignment failure (FINDING_1):** monkeypatch the count-only pass to raise before any success-path assignment (e.g. `TypeError` on entry); assert `_materialize_oos(...)` returns `manifest-oos-materialization-failed` (or the configured bail reason) without raising `NameError`, and that the full pass still runs.
- Assert `count_str` remains a string after in-process count-only success (no `AttributeError` on `.isdigit()`).
- Assert the log file is still written on both-pass failures.
- Assert the bail reason remains `manifest-oos-materialization-failed`.
- Keep coverage for non-materialize `_invoke_cli` paths unchanged.

### UPDATED: python/test_oos_filer.py

- Add or extend coverage that a `TypeError` from `materialize_manifest_oos` during Step 9a.1 pre-file materialization is caught, emits a warning, and does not abort `_file` with an uncaught traceback (FINDING_1).

### UPDATED: python/migrated-scripts.tsv

- Add retired entries for:
  - `skills/implement/scripts/materialize-manifest-oos.sh`
  - `skills/implement/scripts/test-materialize-manifest-oos.sh`
- Also add the two companion `.md` entries per existing manifest convention:
  - `skills/implement/scripts/materialize-manifest-oos.md`
  - `skills/implement/scripts/test-materialize-manifest-oos.md`

### UPDATED: scripts/residual-bash-paths.txt

- Remove `skills/implement/scripts/test-materialize-manifest-oos.sh`.

### UPDATED: Makefile

- Remove the `test-materialize-manifest-oos` target (and its `.PHONY` entry) that invokes the deleted `skills/implement/scripts/test-materialize-manifest-oos.sh`. Update the testing strategy below to drop that target accordingly; pytest in `python/test_file_oos.py` is the replacement coverage.

### UPDATED: skills/implement/SKILL.md

- Remove machine-reachability bullets for the retired helper, harness, and docs.
- Keep the existing Python CLI and `python/test_file_oos.py` bullets.

### UPDATED: skills/implement/references/execution-issues-tracking.md

- Replace the stale helper contract and shell harness references with the live surfaces:
  - `python/cli.py oos materialize-manifest`
  - `python/file_oos.py`
  - `python/test_file_oos.py`
- Preserve the Step 9a.1 behavior statement.

### UPDATED: scripts/test-references-headers.sh

- Remove the explicit `skills/implement/scripts/materialize-manifest-oos.md` contract-file pin, since that file is retired.
- Keep the flat `skills/*/references/*.md` triplet check unchanged.

### UPDATED: skills/implement/scripts/materialize-manifest-oos.sh

- Delete this retired helper.

### UPDATED: skills/implement/scripts/materialize-manifest-oos.md

- Delete this retired companion contract.

### UPDATED: skills/implement/scripts/test-materialize-manifest-oos.sh

- Delete this retired shell harness after pytest parity exists.

### UPDATED: skills/implement/scripts/test-materialize-manifest-oos.md

- Delete this retired harness doc.

### MAY_UPDATE: SECURITY.md

- Do not edit for the intended parity-only change.
- Update only if implementation review shows an intentional redaction-family change rather than shell parity restoration.

## Edge cases

- Manifest `oos_observations` missing or `null` still counts as zero.
- Non-array `oos_observations` still fails closed with exit code `1` at CLI and mapped dispatch failure.
- Non-object items inside a valid `oos_observations` array fail closed on full materialization only; count-only still returns array length without per-item shape checks.
- A failed count-only pass (`count_rc != 0`) still triggers bail via post-pass-two evaluation even if the full pass succeeds.
- A failed count-only pass plus a failed full pass still bails when manifest OOS may be lost; the full pass always runs.
- Successful dual-pass materialization with positive `count_str` and `materialize_failed=false` must not bail; this is the common external-implementer `STATUS=complete` happy path.
- Pre-initialized `count_rc`, `count_str`, and `materialize_failed` ensure bail evaluation never references unbound locals when a pass raises before inner assignment.
- Security-routed observations still never enter public accepted-OOS files.
- Security-audit dedup matches exact heading lines only; title prefix overlap does not suppress distinct observations.
- IPv6 ULA/link-local URLs in manifest text are redacted to `<INTERNAL-URL>` before public write.
- Primary `redact secrets` failure stops materialization; local regex sanitizers are not a fallback.
- Step 9a.1 `oos file` warn-and-continue survives `TypeError` from manifest materialization the same as other materialization failures.
- Duplicate public titles still skip on rerun.
- Existing `OOS_N` headings still force max-plus-one allocation.
- Newlines in titles still cannot inject headings.

## Failure modes

- If direct materialization or sanitization raises (including `TypeError`, redactor failure, or invalid observation shape on full materialization), Step 2 must still write `materialize-manifest-oos.log`, append a Tool Failures entry when the full pass fails, and bail when `_oos_materialize_should_bail()` says to bail after both passes complete.
- If `_oos_materialize_should_bail()` still bails on `count_str > 0` without requiring `materialize_failed`, successful dual-pass runs with manifest observations will abort Step 2 incorrectly.
- If bail evaluation remains gated on subprocess return codes after in-process cutover, count-only failures may skip bail and lose manifest OOS silently.
- If `count_str` is bound to a raw `int`, `_oos_materialize_should_bail()` can raise `AttributeError` and abort Step 2 dispatch.
- If `count_rc`, `count_str`, or `materialize_failed` are not initialized before per-pass try/except blocks, an exception before inner assignment can leave unbound locals and cause `NameError` during post-pass-two bail evaluation instead of returning `manifest-oos-materialization-failed`.
- If item-shape validation runs in the shared loader on count-only calls, mixed arrays break count-only parity and can change bail semantics incorrectly.
- If `oos_filer._file` does not catch `TypeError`, Step 9a.1 can abort with a traceback instead of warn-and-continue.
- If retired paths remain referenced after manifest update, `make lint-retired-scripts` should fail.
- If the deleted `.md` pin stays in `scripts/test-references-headers.sh`, the header harness can fail on a missing file.
- If `_security_audit_has_title` regresses to substring matching, distinct security observations with overlapping title prefixes can be silently dropped from both public and audit artifacts.

## Testing strategy

- Run targeted tests first:
  - `python3 -m pytest python/test_file_oos.py -q -k 'materialize_manifest_oos or sanitize_public'`
  - `python3 -m pytest python/test_implement_dispatch.py -q -k 'materialize_oos or oos_materialize'`
  - `python3 -m pytest python/test_oos_filer.py -q -k 'materialize'`
  - `make lint-retired-scripts`
- Then run required repo checks:
  - `make py-lint`
  - `make py-test`
  - `make lint`

## Acceptance

- `python/implement_dispatch.py:_materialize_oos` calls `file_oos.materialize_manifest_oos()` in-process; no `oos materialize-manifest` subprocess hop remains in the dispatch path.
- Redaction parity (or stronger) verified by pytest covering each PII family: internal-URL (IPv4 plus IPv6 ULA/link-local), email, SSN, phone, and account-style ID. `redact secrets` is reused in-process and fails closed.
- Security-routing parity: security-signalled observations route to `security-oos-observations.md` and never to public OOS; security-audit dedup matches exact heading lines only (no prefix-collision suppression).
- `--count-only` preserved, including count-only item-shape parity (mixed arrays counted without per-item validation).
- Bail semantics preserved after in-process cutover: a successful dual-pass run with positive count and no failure returns `""` (no bail); a count-only failure or a full-pass failure still bails; the bail path raises no `NameError` or `AttributeError`.
- `TypeError` is handled at the CLI entrypoint, the Step 2 dispatch boundary, and the Step 9a.1 `oos_filer` warn-and-continue wrapper.
- The retired `materialize-manifest-oos.sh`, its harness, and both `.md` docs are deleted and recorded in `python/migrated-scripts.tsv`; no tracked file references the retired basenames, and the orphaned `make test-materialize-manifest-oos` target is removed.
- `make lint-retired-scripts`, `make py-lint`, `make py-test`, and `make lint` pass.

diff_lines: 860

## Test plan
(no test plan section in plan-file)
