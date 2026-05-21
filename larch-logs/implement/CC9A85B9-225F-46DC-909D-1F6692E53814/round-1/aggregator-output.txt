Merging overlapping reviewer items into a single structured list. Out-of-scope items stay separate with `[OUT_OF_SCOPE]` preserved on the heading line.

```text
### FINDING_1: Unknown required-files TSV condition silently skipped in audit scan
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, dyn-shell-state-output.txt
- **Concern**: In `audit-scan-run.sh`, `_rf_condition_met` treats unknown `condition` tokens as non-met and the caller `continue`s, so the TSV row is never checked and `required-file-presence` can still pass. `verify-run-log-completeness.sh` treats unknown conditions as fatal. A typo or new condition token therefore fails verify/CI while the audit scan path can look healthy, hiding registry drift.
- **Suggested revision**: Align with the verifier: on unknown `condition`, emit a scan `error` NDJSON (or non-zero exit consistent with other registry-drift handling) instead of skipping the row.

### FINDING_2: Duplicated required-file condition, grep markers, and glob logic between audit scan and verifier
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-condition-sync-output.txt
- **Concern**: `audit-scan-run.sh` and `verify-run-log-completeness.sh` duplicate step/exception condition ladders, `grep -Fq` trigger strings, and glob handling (including mirrored test patterns). No shared fixture proves both surfaces agree on the same synthetic run dir; one-sided edits risk skew, false pass on one side and false fail on the other.
- **Suggested revision**: Factor shared condition + marker logic into one sourced include (or generator), optionally add a minimal golden run-dir test that both tools must satisfy for the same TSV rows.

### FINDING_3: Nested helpers in `scan_required_file_presence` hurt clarity and reuse
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Helpers nested inside `scan_required_file_presence` complicate refactors and increase subtle divergence risk from the verifier.
- **Suggested revision**: Move helpers to file scope or a shared include with a short cross-reference to the verifier.

### FINDING_4: SKILL.md scan results prose omits informational outcomes
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: The scan results table/template text implies only pass/fail, so operators may mis-label informational rows (e.g. cache-freshness) when writing reports.
- **Suggested revision**: Update prose to explicitly include informational and other non-binary scan outcomes.

### FINDING_5: `scans.tsv` pattern text implies fail semantics for version lag
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: The `pattern` column wording can lead downstream consumers of `scans.tsv` to infer the wrong severity after cache-freshness stopped being a hard `fail`.
- **Suggested revision**: Align pattern text with informational semantics or document that `pattern` is non-normative for severity.

### FINDING_6: Tests 52–53 duplicate aggregate-findings helpers instead of exercising production
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-condition-sync-output.txt
- **Concern**: Inline `committed_ref` / `failure_see_phrase` (or equivalent) logic in tests can drift from `aggregate-findings.sh`; production wording or basename rules can change while tests stay green.
- **Suggested revision**: Source a small shared include used by production, add a dry-run/CLI hook that prints resolved phrases, or add an integration test that runs `aggregate-findings.sh` and asserts emitted warning text.

### FINDING_7: Missing test for cache-freshness empty `larch_version` fail branch
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: No harness coverage for the empty/missing `larch_version` failure path despite plan contract; regressions could turn that into skip/pass without CI signal.
- **Suggested revision**: Add a fixture test with empty/missing `larch_version` asserting `fail` result and expected detail.

### FINDING_8: New verifier exn-agg and glob paths lack dedicated harness coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: New `exn-agg-*` and glob `MISSING` branches in `verify-run-log-completeness.sh` are not exercised by `test-verify-run-log-completeness.sh`, so logic bugs can ship on CI shard 7.
- **Suggested revision**: Add positive/negative fixtures for `exn-agg-validate-fail`, `exn-agg-dispatch-fail`, and glob `MISSING` paths.

### FINDING_9: Substring `grep` on `execution-issues.ndjson` risks false condition triggers
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: `grep -Fq` over the whole NDJSON file can match unrelated lines that quote markers like `DISPATCH_OK=false` or dispatch errors, forcing required aggregator stderr files and causing false failures in verify/audit required-file scans.
- **Suggested revision**: Parse structured fields with `jq`, tighten markers, or emit a dedicated unambiguous marker from the writer.

### FINDING_10: Unquoted glob expansion on TSV `relative_path` in audit required-file scan
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: The glob branch expands `rel_path` in a context where a malicious or mistaken TSV row could inject glob metacharacters or unintended word-splitting semantics when operators point `--required-files-tsv` at an untrusted file.
- **Suggested revision**: Use a quote-safe design: validate/allowlist glob grammar (e.g. `round-*/` only), or use `compgen -G` with a validated pattern after rejecting metacharacters outside the allowed set.

### FINDING_11: Informational cache-freshness may silence downstream alerts
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Plugin version lag is no longer a `fail` with low registry severity; consumers that only alert on `fail` or high severity may miss version lag across audited batches.
- **Suggested revision**: Document migration for consumers; optionally add an explicit boolean or severity field for legacy parsers that relied on `fail`.

### FINDING_12: `DISPATCH_OK` failure path omits `failure_see_phrase` in aggregate-findings
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Operators lack a stable round-relative “See …” pointer for the dispatch-failed variant, unlike the non-zero dispatch path.
- **Suggested revision**: Optionally append `failure_see_phrase` for symmetry with the other branch.

### FINDING_13: Test 52 omits explicit coverage for `aggregator-dispatch.stderr` basename
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Low-probability typo in the dispatch branch of the case may go untested.
- **Suggested revision**: Assert the phrase or basename for `aggregator-dispatch.stderr`, or loop allowed basenames.

### FINDING_14: Test 54 only asserts TMPDIR path redaction, not embedded stderr content
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: A regression could drop embedded stderr text while still redacting paths; the test would pass.
- **Suggested revision**: Assert an expected stderr substring remains present in the logged entry.

### FINDING_15: [OUT_OF_SCOPE] Verifier lacks absolute-path rejection for TSV rows vs audit-scan-run
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Pre-existing asymmetry; optional hardening in a follow-up.
- **Suggested revision**: None for this PR unless explicitly widening scope.

### FINDING_16: [OUT_OF_SCOPE] `load_required_files` synthetic harness omits step8/step9a1
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Pre-existing harness limitation for synthetic complete dirs.
- **Suggested revision**: Widen separately if desired.

### FINDING_17: [OUT_OF_SCOPE] Verifier uses same unquoted glob expansion style for manifest-fixed paths
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Risk mainly if `docs/run-logs-required-files.tsv` is maliciously or mistakenly edited; same class as audit glob hardening.
- **Suggested revision**: Apply shared validation/allowlist or treat as follow-up outside this change.

### FINDING_18: [OUT_OF_SCOPE] `sort -V` portability in `scan_cache_freshness`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Older BSD `sort` may mishandle `-V` or abort; pre-existing semver compare dependency.
- **Suggested revision**: Track separately from this diff.

### FINDING_19: [OUT_OF_SCOPE] Scout notes: `shopt nullglob` restored after loop including `break`
- **Reviewer(s)**: dyn-shell-state-output.txt
- **Concern**: Observation that `nullglob` is disabled after `done` even when the loop exits via `break` (not reported as a defect requiring change).
- **Suggested revision**: None unless product owners want explicit documentation.

### FINDING_20: [OUT_OF_SCOPE] Scout notes: `set -e` and `grep` in `|| continue` predicate context
- **Reviewer(s)**: dyn-shell-state-output.txt
- **Concern**: Observation that bash suppresses `-e` for failures in the RHS of `cmd1 || cmd2` when `cmd1` is a function—behavioral note, not a requested fix.
- **Suggested revision**: None unless tightening error propagation is desired.

### FINDING_21: [OUT_OF_SCOPE] Scout notes: nested functions and `_rf_mstat` / `_rf_mpr` initialization
- **Reviewer(s)**: dyn-shell-state-output.txt
- **Concern**: Observation that nested helpers are valid bash and `jq` failures are tolerated with empty strings consistent with step9a1 usage.
- **Suggested revision**: None.

### FINDING_22: [OUT_OF_SCOPE] Triplicated `exn-agg-*` heuristics across TSV and two scripts
- **Reviewer(s)**: dyn-shell-state-output.txt
- **Concern**: Operational drift risk from partial wording updates; framed as broader maintenance risk rather than a single new logic bug.
- **Suggested revision**: Address via consolidation finding (FINDING_2) in a future scoped change.

### FINDING_23: [OUT_OF_SCOPE] Committed `larch-logs/implement/...` tree in branch diff
- **Reviewer(s)**: dyn-shell-state-output.txt, dyn-condition-sync-output.txt
- **Concern**: Large partial run-log tree may be intentional for the implementing run but is orthogonal to functional script review unless explicitly part of the product change.
- **Suggested revision**: Confirm intent with authors; trim or relocate if accidental.

### FINDING_24: [OUT_OF_SCOPE] Tests 52–53 do not encode the `exn-agg` grep predicates
- **Reviewer(s)**: dyn-condition-sync-output.txt
- **Concern**: Clarifying observation: only audit and verify encode those substrings; tests cover the “See … committed run log” path only—no third independent implementation to compare for substring drift in the harness.
- **Suggested revision**: None by itself; overlaps motivation for FINDING_2 / FINDING_6 / FINDING_8 when in scope.
```
