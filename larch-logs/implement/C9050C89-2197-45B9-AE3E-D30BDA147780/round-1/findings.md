### FINDING_1: code-quality: scripts/test-tracking-issue-read-sentinel.sh:179-209
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] ADOPTED negative cases use assert_equal_stdout while ISSUE_NUMBER/RUN_ID cases (p)-(w) still use assert_contains-only envelopes A future emit_kv regression that appends an extra KV line on ISSUE_NUMBER/RUN_ID failure would not fail (p)-(w) but would fail (e)-(h), leaving inconsistent regression depth across the three redacted fields Optionally promote (p)-(w) to assert_equal_stdout plus assert_not_contains, or add a shared helper for fixed-token two-line failure envelopes
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: scripts/test-tracking-issue-read-sentinel.sh:179-209
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Four identical expected stdout printf strings for invalid ADOPTED Changing the fixed-token message requires four synchronized edits; one miss leaves contradictory assertions Define one ADOPTED_INVALID_ENVELOPE variable before case (e) and reuse in (e)-(h)
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/test-tracking-issue-read-sentinel.md:32-35
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Case table rows (e)-(h) duplicate the same long expected-result prose Doc drift if the envelope string changes and only some rows are updated Reference invariant #6 in the table; keep per-case detail limited to input variants and negative needles
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] code-quality: scripts/tracking-issue-read.sh:287-296
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Mixed validation styles (case vs if) for sentinel fields Pre-existing inconsistency; not introduced by this branch Unify in a dedicated hardening issue if desired
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] code-quality: scripts/tracking-issue-read.sh:231-234
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Sentinel argv ISSUE_NUMBER still accepts 0 Issue 0 can pass sentinel/argv validation while get-issue-context rejects it Intentionally deferred; tighten lax peers in a follow-up per get-issue-context comment
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] code-quality: CHANGELOG.md:5374
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Stale historical ADOPTED error text with '<val>' Grep-based audits may think the verbatim echo contract is still current Optional changelog annotation in a docs-only follow-up; not required for runtime correctness
- **Suggested revision**: Address the concern above.

### FINDING_7: `78ec03c4` — Harden ADOPTED sentinel error redaction (feature)
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - `78ec03c4` — Harden ADOPTED sentinel error redaction (feature)
- **Suggested revision**: Address the concern above.

### FINDING_8: `8d7b7647` — chore(larch-logs) implement run flush
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - `8d7b7647` — chore(larch-logs) implement run flush
- **Suggested revision**: Address the concern above.

### FINDING_9: `91ff1f2a` — chore(larch-logs) design run flush
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - `91ff1f2a` — chore(larch-logs) design run flush The feature commit (`78ec03c4`, 6 files, +32/−16) matches the implementation plan. Runtime behavior is a string-only change on the existing ADOPTED guard; validation order, exit codes, and strict `true`/`false`/empty semantics are unchanged. ### Plan verification (correctness lens) | Requirement | Status | |-------------|--------| | ADOPTED `emit_kv ERROR` uses fixed token (parity with ISSUE_NUMBER/RUN_ID at 288–291) | Done at `tracking-issue-read.sh:293-296` | | Header + inline `--sentinel` contract comments updated | Done; `'<v>'` removed | | Harness cases (e)–(h): `assert_equal_stdout` + quoted/raw `assert_not_contains` | Done; needles avoid bare `yes`/`1` per plan | | `.md` siblings + `SECURITY.md` | Done | | `get-issue-context.sh` comment only; regex unchanged | Done; peer citations verified | **Logic check:** The guard `[[ -n "$ADOPTED_VAL" && "$ADOPTED_VAL" != "true" && "$ADOPTED_VAL" != "false" ]]` still runs only for non-empty values after `\r` strip; empty/absent ADOPTED remains valid (cases c/d). Failures still emit exactly `FAILED=true` + one `ERROR=` line before `exit 1`, with no success keys — same as ISSUE_NUMBER/RUN_ID failures. **Caller impact:** `implement-bootstrap.sh` reads `FAILED`, `ISSUE_NUMBER`, `RUN_ID`, and `ADOPTED` via `kv_value_from_block`; it does not parse `ERROR=` text. No production regression from the message shape change. **Comment accuracy:** `get-issue-context.sh:32-37` correctly names lax peers (`tracking-issue-read.sh` argv ~231 and sentinel ~287; `get-issue-state.sh` ~53) and disambiguates clarify scripts’ two-stage `>=1` guard.
- **Suggested revision**: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 1. **correctness** `scripts/tracking-issue-read.sh:287-288` — Sentinel `ISSUE_NUMBER` still accepts `0` via `case *[!0-9]*` (also argv `--issue` at 232–234 and `implement-bootstrap.sh:125-129`). This is pre-existing lax behavior, now documented in `get-issue-context.sh`; not introduced by this branch. **Suggested fix:** Future hardening pass per the new comment (tighten peers, not loosen `get-issue-context.sh`).
- **Suggested revision**: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] code-quality
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 2. **code-quality** `CHANGELOG.md:5374` — Historical changelog entry still documents the old verbatim-echo ADOPTED error form. Not in the plan’s touch list and not runtime-affecting. **Suggested fix:** Optional follow-up changelog correction if maintainers want doc parity.
- **Suggested revision**: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 1. **risk-integration** `scripts/test-tracking-issue-read-sentinel.sh:284-354` — Invariant #8 documents an exact two-line failure envelope for all invalid sentinel paths, but **(p)–(w)** still use `assert_contains` only (no `assert_equal_stdout`), while **(e)–(h)** were upgraded in this PR. A future KV-injection regression on `ISSUE_NUMBER`/`RUN_ID` failure paths could add a third stdout line without failing **(p)–(w)**. **Suggested fix:** In a follow-up, reshape **(p)–(w)** like **(e)–(h)** (exact envelope + raw-token negatives).
- **Suggested revision**: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 2. **risk-integration** `scripts/test-get-issue-context.sh` — The harness exercises happy path, gh failure, bad repo, and missing `jq`, but not `--issue 0` / leading-zero rejection. The new comment in `get-issue-context.sh` documents intentional `>=1` semantics; behavior is unchanged and untested here (plan scope was comment-only). **Suggested fix:** Add negative cases for `0` and `01` when tightening validation parity.
- **Suggested revision**: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] code-quality
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 3. **code-quality** `CHANGELOG.md:5374` — Historical entry still describes the pre-redaction ADOPTED `ERROR=` format (`'<val>' (expected 'true' or 'false' or absent)`). **Suggested fix:** Update that bullet on the next user-visible release note pass (not required for this narrow hardening PR). ### Summary | Area | Assessment | |------|------------| | Plan test obligations | Met — **(e)–(h)** reshaped; harness + `.md` siblings + `SECURITY.md` updated | | Regression risk | Low — contract change is error-string only; harness pins new envelope | | CI | Covered via existing `test-harnesses-18` shard | | Breaking consumers | None identified in-repo for `ERROR=` text parsing | | `get-issue-context.sh` | Comment-only; peer citations verified accurate | Commits on branch: `78ec03c4` (hardening), `8d7b7647` / `91ff1f2a` (larch-logs).
- **Suggested revision**: Address the concern above.

### FINDING_15: `78ec03c4` — Harden ADOPTED sentinel error redaction (feature)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `78ec03c4` — Harden ADOPTED sentinel error redaction (feature)
- **Suggested revision**: Address the concern above.

### FINDING_16: `8d7b7647` / `91ff1f2a` — `chore(larch-logs)` flushes (out of review scope per instructions)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `8d7b7647` / `91ff1f2a` — `chore(larch-logs)` flushes (out of review scope per instructions) The security-relevant work is entirely in `78ec03c4`: it closes the last sentinel validation gap where invalid `ADOPTED` values were echoed verbatim into the `KEY=VALUE` stdout stream that downstream callers parse. ### What was reviewed | Area | Assessment | |------|------------| | **KV injection via `ERROR=`** | **Fixed.** Invalid `ADOPTED` now uses the same fixed-token pattern as `ISSUE_NUMBER` / `RUN_ID` at `scripts/tracking-issue-read.sh:293-296`. | | **Contract propagation** | Header comment, inline contract, `.md` siblings, `SECURITY.md`, and harness cases (e)–(h) are aligned. | | **`get-issue-context.sh` comment** | Documentation-only; peer citations verified (`get-issue-state.sh:52-54`, `tracking-issue-read.sh:231-234`, clarify scripts with explicit `0` rejection). | | **Test regression depth** | `assert_equal_stdout` (exact two-line envelope) plus quoted/raw `assert_not_contains` needles correctly guard against re-introducing verbatim echo. | `emit_kv` still uses `printf '%s=%s\n'` without sanitizing embedded newlines; that is a long-standing property of the helper. For this sentinel path, invalid `ADOPTED` no longer reaches `ERROR=` with attacker-controlled bytes, and successful emissions are constrained to `true` / `false` / empty after validation.
- **Suggested revision**: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **security** `scripts/tracking-issue-read.sh:287-288` — Sentinel `ISSUE_NUMBER` still accepts `0` via the all-digit `case` guard (same for `--issue` at `231-234`). GitHub has no issue #0; a lax sentinel could propagate `ISSUE_NUMBER=0` on the success path. This PR documents the intentional stricter regex in `get-issue-context.sh` but does not tighten the lax peers. **Suggested fix:** Future hardening: reject `0` and leading-zero forms in `tracking-issue-read.sh` sentinel/argv validation to match `get-issue-context.sh`.
- **Suggested revision**: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **security** `scripts/tracking-issue-read.sh:277-282` — Line-oriented `extract_sentinel_key` means embedded newlines in a value split across physical lines and may bypass post-extraction validators (documented in `scripts/test-tracking-issue-read-sentinel.md` item 9). Not introduced or worsened by this diff. **Suggested fix:** Reject values containing `\n` before emission, or validate the full sentinel with a stricter parser.
- **Suggested revision**: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 3. **security** `scripts/lib-quiet.sh:123-129` — `emit_kv` does not strip or reject embedded newlines in arbitrary `ERROR` values (e.g. `gh` failures, `$SENTINEL` path errors at `262-267`). Pre-existing across the script family. **Suggested fix:** Centralize single-line enforcement in `emit_kv` for contract streams. --- **Verdict:** Approve from a security/trust-boundary perspective. The branch closes a real KV-injection vector on invalid `ADOPTED`, matches the established redaction contract, and strengthens regression tests without introducing new unsafe behavior.
- **Suggested revision**: Address the concern above.

### FINDING_20: architecture: scripts/test-tracking-issue-read-sentinel.sh:179-211 vs 287-353
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] ADOPTED invalid cases use byte-exact stdout assertions while ISSUE_NUMBER/RUN_ID invalid cases still use contains-only checks Extra KV lines on ISSUE_NUMBER/RUN_ID failure paths could regress without failing (p)-(w) even though (e)-(h) would catch the same class of bug for ADOPTED Reshape cases (p)-(w) to assert_equal_stdout plus assert_not_contains on quoted and raw malformed tokens
- **Suggested revision**: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] security: scripts/tracking-issue-read.sh:260-267
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Sentinel missing/unreadable errors still echo full $SENTINEL path in ERROR= Attacker-influenced --sentinel path could inject newline or KEY= tokens into KV-parsed stdout Redact or basename-only sentinel paths in ERROR messages in a follow-up hardening pass
- **Suggested revision**: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] architecture: scripts/test-tracking-issue-read-sentinel.md:22
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Embedded-newline rejection for sentinel values is explicitly unpinned Line-oriented grep/sed can miss same-line injection behaviors not covered by post-extraction validators Add harness cases when parser hardening expands beyond line-oriented extraction
- **Suggested revision**: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] correctness: scripts/tracking-issue-read.sh:231-234
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Sentinel and argv ISSUE_NUMBER validation accepts 0 Downstream consumers may treat ISSUE_NUMBER=0 as valid digits and proceed incorrectly Tighten lax peers in a future hardening pass per get-issue-context.sh comment
- **Suggested revision**: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] code-quality: CHANGELOG.md:5374
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Changelog still documents old ADOPTED error envelope with quoted val Operators reading CHANGELOG see stale contract text Update changelog entry when doing doc hygiene
- **Suggested revision**: Address the concern above.

