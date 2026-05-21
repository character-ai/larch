Here is the normalized finding list (merged by behavioral risk; IDs follow first appearance when scanning the supplied input in order).

```text
### FINDING_1: Test 49 duplicates production jstr
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-jq-output-slice-output.txt
- **Concern**: Test 49 uses an inlined `jstr_test49` (or equivalent copy) instead of exercising `jstr()` from `audit-scan-run.sh`, so the suite can stay green while shipped scan NDJSON regresses if only the script changes. The duplicated helper can also diverge from the real `jq` primary path vs `sed` fallback. One source additionally notes the current identity-style cases may miss edge inputs (empty string, embedded quotes/backslashes, control characters) where the two implementation paths differ.
- **Suggested revision**: Share one implementation with the scan script (e.g. small sourced helper, narrow wrapper that loads the production function, or assertions driven through a code path that calls production `jstr()`), and broaden the assertion vector to cover those edge cases so regressions surface on the path the script actually uses.

### FINDING_2: Test 44b duplicates git/gh stub harness from Test 44
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Test 44b repeats large `git`/`gh` stub heredocs already defined in Test 44, overlapping coverage (one slot notes only a narrow slice like `[44b0]` is uniquely additive) and increasing maintenance cost: stub contract changes require parallel edits and risk skew between tests.
- **Suggested revision**: Fold uniquely additive coverage into Test 44 or extract shared stub construction (single helper or reused heredoc pair) and keep only 44b-specific assertions separate.

### FINDING_3: gh stub `-R` / `--repo` detection is pattern-based on flattened argv
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Stub behavior keys off flattened argv pattern matching; unusual argv shapes might not match even if they are valid for `gh`, though the fixed scripts under test may never emit them.
- **Suggested revision**: Treat as a known regression-guard limitation unless stricter matching is required; if so, parse argv tokens explicitly instead of broad substring rules.

### FINDING_4: [OUT_OF_SCOPE] Implement run logs / branch packaging
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-jq-output-slice-output.txt
- **Concern**: The branch includes committed implement run artifacts under `larch-logs/implement/178CDA25-E5C7-4C89-A000-33BF291DB5D4/` (possibly as a separate chore-style commit). One line of review frames this as intentional per `docs/run-logs.md` and not a trust-boundary/security regression; another frames it as orthogonal to audit-runs behavior and potentially worth splitting from the functional change per repo policy.
- **Suggested revision**: No security action required for trust boundaries if intentional per run-log policy; optionally split or document packaging if the project prefers functional fixes isolated from log flushes.

### FINDING_5: Strict gh stub may reject future valid global `-R` argv shapes
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: If `audit-preflight.sh` (or related tooling) ever adopts `gh`-supported global `-R` placement before the `repo view` subcommand, the current strict stub rules might fail tests for valid CLI usage unless stubs are updated; broad `-R` substring checks may be too coarse compared to asserting the exact emitted command line.
- **Suggested revision**: If global `-R` is adopted, align stub checks with the precise emitted argv rather than brittle broad rules; otherwise document as a known coupling to current invocation shape.

### FINDING_6: [OUT_OF_SCOPE] Pre-existing jstr sed fallback / macOS behavior and `@json` trimming
- **Reviewer(s)**: dyn-jq-output-slice-output.txt
- **Concern**: The `sed` fallback path and macOS `sed`/`tr` behavior around control characters pre-existed; the `@json` change aligns the primary path with `jq` encoding, and stripping quotes via `${_j:1:${#_j}-2}` is described as appropriate for standard `jq -nj` `@json` output on non-defective builds—i.e., not a new defect introduced by the reviewed change set.
- **Suggested revision**: None required from this review thread beyond awareness; any hardening belongs to explicit scope for the helper, not implied by this delta.
```
