## Decision 1: Fix location
- **Question**: Where should the pure-attestation fix live — inline Python validator, shell wrapper short-circuit, or both?
- **Resolution**: Inline Python validator (the `aggregate-validate.py` heredoc inside `skills/review/scripts/aggregate-findings.sh`). The shell wrapper's existing post-validate strip path already handles `MERGED_COUNT=0` cleanly via the `printf '\n' >"$merged_tmp"` fallback.
- **Source**: user

## Decision 2: Existing #2782 test expectation
- **Question**: What happens to the existing #2782 test that asserts `REASON=validation-exhausted` for `zero_findings_input_nonempty`?
- **Resolution**: Flip the assertion in place to expect `REASON=ok` and update the test comment/description to reference #2939's corrected semantics. Strengthen by also asserting `AGGREGATED=true`, `MERGED_COUNT=0`, and that the stripped findings file is empty/whitespace-only.
- **Source**: user

## Decision 3: Downstream consumer changes
- **Question**: Should `review-core.sh` / `review-and-fix` be modified in this PR for the new `REASON=ok` + `MERGED_COUNT=0` case?
- **Resolution**: Verify downstream paths first; include same-PR fixes only if a real consumer break is found. Otherwise verify-and-document.
- **Source**: user

## Decision 4: Preamble-finding rejection preserved
- **Question**: Does the existing `preamble_finding_substring` rejection (zero blocks + prose mentions of `FINDING_N`) still fire under the new behavior?
- **Resolution**: Yes. The preamble-signal branch in `aggregate-validate.py` runs **before** the attestation-only branch. Only outputs with the exact-line attestation, zero blocks, AND no preamble-finding signal AND no non-conforming heading markers should return 0.
- **Source**: codebase

## Decision 5: Contract surface
- **Question**: Does `skills/review/scripts/aggregate-findings.md` need a contract update?
- **Resolution**: Yes. The validator's behavior for attestation-only outputs is part of the public contract surface that callers depend on; `aggregate-findings.md` must document the corrected semantics.
- **Source**: codebase
