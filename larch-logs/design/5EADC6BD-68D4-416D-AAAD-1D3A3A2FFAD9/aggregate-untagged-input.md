### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/engine.py:362-401
- **Concern**: Live symbol-metric projection lacks a fail-closed optional-field pairing rule (G-Py-4). Scenario: _validate_finding allows metric without qualified_symbol today; baseline-active comparison can mis-project that row as generic or proceed with an invalid symbol identity, hiding metric regressions or returning the wrong exit class
- **Proposed resolution**: Define and test live projection rules: generic only when both qualified_symbol and metric are absent; symbol-metric only when both are present; exit 2 when exactly one is set. Apply the pairing check only on baseline-active paths so scan-only behavior stays unchanged

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/engine.py
- **Concern**: Canonical baseline JSON bytes are required but not defined. Scenario: Post-write read-back demands exact byte equality yet the plan only says canonical order and trailing newline; implementers can pick different json.dumps settings and falsely return exit 2 or pass with non-interoperable baselines
- **Proposed resolution**: Pin serialization to sorted projected rows plus json.dumps(ordered, indent=2) + "\n", matching existing lint serialize_baseline helpers; test the exact bytes

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/engine.py
- **Concern**: Mixed-schema baseline arrays are not rejected. Scenario: Approach rejects mixed live projection shapes only; per-row exact-key validation still accepts one generic row and one symbol-metric row in the same baseline file, leaving compare/index behavior undefined
- **Proposed resolution**: Load-time homogeneity check after per-row validation: all rows must share one projection kind or return exit 2; add a mixed-array test case ### 1. [correctness] `python/larch/lint/engine.py` — Canonical baseline JSON bytes are required but not defined The plan requires post-publication read-back to match both parsed records and canonical bytes, but it never pins the serializer. Existing lint modules already use `json.dumps(ordered, indent=2) + "\n"` after sorting by identity key. Without that contract in the plan, write mode can spuriously fail read-back or emit baselines that later rule migrations cannot consume. **Suggested revision:** Specify sorted projected identity ordering and `json.dumps(ordered, indent=2) + "\n"` in the engine write path; pin the exact bytes in tests. ### 2. [correctness] `python/larch/lint/engine.py` — Mixed-schema baseline arrays are not rejected “Reject mixed row shapes” applies to live projection before dedupe, not to baseline load. A baseline file can contain one valid generic row and one valid symbol-metric row; each passes exact-key validation, but the engine has no single comparison model for check or write. **Suggested revision:** After per-row validation, require all baseline rows share one projection kind; exit `2` on mixed arrays; add an explicit mixed-array test. --- **Prior-round notes (no re-raise):** Filtered stale scoping, symbol identity before dedupe, generic line validation, scan-only duplicate policy, CAS/rollback narrowing, and strict-stale precedence appear addressed in the revised plan. FINDING_2 (live projection classification) remains thin in approach text but is covered enough by planned invalid-symbol/metric tests; not re-raised as a duplicate OOS item.

### FINDING_4:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/engine.py
- **Concern**: Live Finding projection shape rules are still not pinned beyond "coherent qualified_symbol and metric use". Scenario: Baseline-active mode must reject mixed projected shapes and compare against a homogeneous baseline file, but the plan never states when a live Finding maps to generic vs symbol-metric (e.g., both optional fields absent vs both present vs only one present). Two implementers can classify the same detector output differently, breaking match/stale/write symmetry and the mixed-shape guard.
- **Proposed resolution**: Spell out the positive mapping in Approach/engine bullets: generic projection only when both qualified_symbol and metric are absent; symbol-metric only when both are present; any partial presence is exit 2 before comparison. Require the same homogeneous shape for every live row and every baseline row in a run.

### FINDING_5:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/engine.py
- **Concern**: Read-back validation requires exact canonical bytes but serialization is unspecified. Scenario: Approach items 5 and 7 and the engine write bullet require post-write read-back of both parsed records and canonical bytes, yet the plan only says "canonical order" and "trailing newline." Existing lint baselines use json.dumps(..., indent=2) + "\n" with identity-sorted rows; without pinning that contract, read-back can flap on whitespace or key order and falsely return exit 2 or accept non-canonical output.
- **Proposed resolution**: Add one serialization contract: sort rows by the projected identity tuple, emit json.dumps(rows, indent=2) + "\n" with fixed per-schema field order, and compare read-back text byte-for-byte to that serializer output.

### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/lint/engine.py
- **Concern**: Combined strict-stale and new-findings exit precedence is referenced but not defined. Scenario: Tests require "new findings plus stale rows obey the documented error precedence," but Approach and Failure modes only list exit 1 and exit 2 separately. Legacy unreachable-branch check returns exit 2 whenever any stale row exists, even if new findings also exist; absent an explicit rule, strict_stale runs may disagree with tests and with later rule migrations.
- **Proposed resolution**: Document one precedence rule in Approach item 4 and Failure modes: when strict_stale is active and any in-scope stale row exists, return exit 2 even if new or regressed findings also exist; otherwise stale warnings alone keep exit 1 when findings are present.

### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/larch/lint/engine.py
- **Concern**: Trusted baseline I/O failures are not fully absorbed into the ScanError exit-2 path. Scenario: run_rule only catches ScanError today (engine.py:507-509). trusted_atomic_write and read_trusted_text raise OSError/ValueError (io.py:129-257), and the plan's conversion list omits those operational failures even though Failure modes promise exit 2 for publication/read-back errors. An unwrapped OSError can escape as an unhandled exception instead of exit 2.
- **Proposed resolution**: Wrap baseline read, write, and read-back calls in a narrow converter to ScanError (or a single outer except) so every trusted I/O failure surfaces on stderr and returns EXIT_ERROR without bypassing the buffered-output contract. ### 1. [correctness] `python/larch/lint/engine.py` — Live projection classification The plan adds baseline-active mixed-shape rejection and tests for invalid symbol/metric pairs, but it never defines the positive mapping from a `Finding` to generic vs symbol-metric projection. Piece 1 already allows independent optional fields (`engine.py:47-55`, `354-400`), and scan-only dedupe ignores `qualified_symbol` (`404-414`). Without an explicit rule, baseline comparison can classify the same detector output inconsistently. **Suggested revision:** Add normative bullets: generic only when both optional fields are absent; symbol-metric only when both are present; partial presence is exit 2; all live rows and the baseline file must share one shape per run. ### 2. [correctness] `python/larch/lint/engine.py` — Canonical JSON bytes for read-back Read-back validation is a core acceptance requirement, but the plan does not pin the on-disk JSON format. Repo baselines already use `json.dumps(ordered, indent=2) + "\n"` (for example `lint_unreachable_branch.py:680-683`). Byte comparison without that contract is not implementable deterministically. **Suggested revision:** Document the exact serializer (sort key, `indent=2`, trailing newline, fixed field order per schema) and require read-back to match those bytes. ### 3. [correctness] `python/larch/lint/engine.py` — `strict_stale` vs new-findings precedence The test plan references "documented error precedence," but the plan body never defines combined behavior. Existing lint check modes treat stale rows as hard failures (`lint_unreachable_branch.py:775-776`), which differs from warn-only stale in this plan. **Suggested revision:** State explicitly that in-scope stale rows under `strict_stale` force exit 2 even when exit-1 findings also exist. ### 4. [risk-integration] `python/larch/lint/engine.py` — Trusted I/O error wrapping Exit code `2` is only reliable if trusted read/write failures are converted before `run_rule` returns. The plan lists several ScanError sources but not `OSError`/`ValueError` from `larch.io` helpers. **Suggested revision:** Convert trusted I/O failures to `ScanError` at the baseline boundary so buffering and exit codes stay coherent. --- **Prior ledger notes:** Accepted items on filtered stale scoping, symbol-aware projection before dedupe, generic line validation, scan-only duplicate policy, and no-rollback read-back failure look addressed. I did not re-raise rejected/OOS items (CAS, JSON duplicate keys, directory TOCTOU, docstring, legacy stale exit-2 parity) unless noted above.
