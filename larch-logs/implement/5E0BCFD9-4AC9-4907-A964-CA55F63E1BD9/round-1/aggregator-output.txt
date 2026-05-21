Here is the normalized structured finding list (merged where the behavioral risk and fix direction align; `[OUT_OF_SCOPE]` items kept separate with the tag preserved on the heading).

```text
### FINDING_1: Stale `--output` left after `MALFORMED` exit in `plan-block-read`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: On malformed plan-block exits, the script can leave a prior successful extraction in `--output`, so automation that treats fresh stderr/exit as authoritative may still read stale inner markdown from disk.
- **Suggested revision**: On every malformed path (and/or in shared malformed exit), truncate or remove `OUT_PATH` before `exit 1`; document the contract in the helper doc (e.g. `plan-block-read.md`).

### FINDING_2: Plan/issue acceptance and PR narrative understate real touch surface
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-gh-stub-fidelity-output.txt, dyn-awk-state-machine-output.txt
- **Concern**: Stated scope (“Makefile-only”, “new files only”, narrow wiring) does not match edits to `agent-lint.toml`, `docs/issue-anchored-plan.md`, and (per several reviewers) a committed `larch-logs/implement/...` tree—widening review, CI, lint expectations, and merge/backport risk.
- **Suggested revision**: Reconcile acceptance text, implementation plan, and PR description with the full file list (or revert/split changes); drop committed implement run artifacts unless policy explicitly requires them (`docs/run-logs.md` / team convention).

### FINDING_3: Duplicated `gh` repo resolve / stderr redact / failure-emit helpers across scripts
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Near-identical helper blocks in five scripts invite behavioral drift if only one copy is fixed or hardened.
- **Suggested revision**: Extract one sourced shared helper and have all call sites import it.

### FINDING_4: `test-clarify-state` assertions are too loose for stable regression signal
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Concern**: Cases match `STATE=` as a substring of full stdout (fragile if harness output grows) and do not assert expected `LAST_REQUEST_ID` / `LAST_RESPONSE_ID`, so ID regressions can slip while `STATE` strings still match.
- **Suggested revision**: Assert specific KV lines (or structured slices), including `LAST_REQUEST_ID` and `LAST_RESPONSE_ID` for key scenarios.

### FINDING_5: `test-clarify-comment` omits invalid `--id` shapes beyond `0`
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Harness does not cover negative or non-numeric `--id`; non-digit rejection could regress with CI still green.
- **Suggested revision**: Add cases (e.g. `--id -1`, `--id abc`) expecting exit `1` and `ERROR=invalid-id`.

### FINDING_6: `test-plan-block` does not cover `MALFORMED=multiple-end`
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Production returns that token but no fixture asserts it; regressions in `end_count>1` handling could ship unnoticed.
- **Suggested revision**: Add read (and optionally write-refusal) tests mirroring existing `multiple-start` coverage.

### FINDING_7: Unused `expect_kv` helper in `test-clarify-state`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Dead helper adds misleading maintenance surface.
- **Suggested revision**: Use it for KV assertions or remove it.

### FINDING_8: `redact_gh_error` may emit partially raw, token-bearing `gh`/`jq` stderr on redactor failure
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: When redaction is missing or fails, `ERROR=` may still include up to ~500 chars of sensitive stderr instead of failing closed with a generic error.
- **Suggested revision**: On redactor missing/failure, emit a generic `ERROR` only; never `printf` raw stderr into `ERROR` after a failed redaction attempt.

### FINDING_9: Broad `agent-lint` excludes for new plan/clarify scripts and harnesses
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Static security/style checks no longer apply to the new `gh`-facing shell surface.
- **Suggested revision**: Remove or shrink excludes after scripts conform to lint rules.

### FINDING_10: Unvalidated `--repo` interpolated into `gh api` paths (`clarify-state`)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Malformed `owner/repo` increases unpredictability before `gh` errors.
- **Suggested revision**: Validate `owner/repo` format up front and fail with a stable, non-leaky error.

### FINDING_11: `eval`-based argv scan in `test-clarify-comment` `gh` stub
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Low direct risk in tests but a hazardous pattern if copied into production-like tooling.
- **Suggested revision**: Replace `eval` with safe positional/`case` parsing.

### FINDING_12: `clarify-state` can emit `response-pending` when lower clarification IDs are not satisfied (wire-format gap)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-awk-state-machine-output.txt
- **Concern**: State machine can treat the last request as answered while an earlier request id never received a response but a higher id already has a response—conflicting with `docs/issue-anchored-plan.md` gap/ordering rules (should be `ambiguous` or refuse progress).
- **Suggested revision**: Extend `END`-state logic (and harness) so `response-pending` requires all lower ids satisfied per the doc, else emit `STATE=ambiguous` (with a dedicated fixture such as request `1`, request `2`, response `2` only).

### FINDING_13: `clarify-state` only scans the first line of each comment for markers
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Markers on later lines are ignored, so `STATE=clean` can hide visible clarify markers in the body.
- **Suggested revision**: Scan full comment bodies for marker regex, or fail closed if markers appear outside line 1; document the rule.

### FINDING_14: `LAST_RESPONSE_ID` semantics vs “open” last request
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: `LAST_RESPONSE_ID` can reflect an earlier round while the latest state is `awaiting-response` for a newer request, inviting mis-parsing downstream.
- **Suggested revision**: Tighten the contract in docs and/or only emit `LAST_RESPONSE_ID` when it pairs to `LAST_REQUEST_ID` under the documented rules.

### FINDING_15: `STATE` values table in `docs/issue-anchored-plan.md` omits `ambiguous`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-gh-stub-fidelity-output.txt
- **Concern**: Helpers emit `STATE=ambiguous` but the summary table does not, creating a normative gap for operators even when prose discusses ambiguity elsewhere.
- **Suggested revision**: Add an `ambiguous` row (or explicit non-exhaustive disclaimer + pointer to `clarify-state.md` / marker rules).

### FINDING_16: `clarify-comment-post` docs/plan promise `POSTED=false` that success-path stdout may not emit
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Contract text mentions `POSTED=true|false` while shipped behavior may only print `POSTED=true` on success; benign skips may omit `POSTED=false`.
- **Suggested revision**: Align documentation/plan wording with actual stdout, or implement `POSTED=false` where intentionally required.

### FINDING_17: `test-clarify-state` `gh api` stub never exercises multi-page `jq -s 'add // []'` merge behavior
- **Reviewer(s)**: dyn-gh-stub-fidelity-output.txt
- **Concern**: Stub always emits a single JSON array, so pagination/slurp aggregation paths are untested.
- **Suggested revision**: Add a fixture where the stub prints two paginated JSON roots and assert merged timeline matches single-array expectations.

### FINDING_18: `eval`-based `--body-file` discovery in `gh` stubs (`test-plan-block`, `test-clarify-comment`)
- **Reviewer(s)**: dyn-gh-stub-fidelity-output.txt
- **Concern**: Paths with spaces or metacharacters could break; real `gh` accepts arbitrary paths.
- **Suggested revision**: Replace index `eval` walks with a Bash-3.2-safe `while`/`case` parser in each stub.

### FINDING_19: `gh issue view --json body --jq -r '(.body // "")'` passes two tokens to `--jq` (live CLI incompatibility)
- **Reviewer(s)**: dyn-awk-state-machine-output.txt
- **Concern**: Reported against live `gh`: `accepts 1 arg(s), received 2`, so issue body may not load in real runs; pattern duplicated across read/write scripts.
- **Suggested revision**: Pass a single `--jq` expression and/or pipe JSON through `jq -r` (or use supported `gh` formatting) so the decoded issue body reaches marker logic.

### FINDING_20: [OUT_OF_SCOPE] Pre-existing `redact_gh_error` fallback in `tracking-issue-write.sh`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Same class of redaction fallback as flagged elsewhere, but not introduced by this branch.
- **Suggested revision**: Track central hardening separately from this PR.

### FINDING_21: [OUT_OF_SCOPE] Run log artifact readability (`plan-goals-test.md` duplicated headings)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Flushed implement log noise only; not part of helper runtime correctness.
- **Suggested revision**: No change required for helper correctness.

### FINDING_22: [OUT_OF_SCOPE] `gh issue view` stub stdout shape vs `--json/--jq` for covered fixtures
- **Reviewer(s)**: dyn-gh-stub-fidelity-output.txt
- **Concern**: For behaviors the harness asserts, stub output shape matches the decoded-body stdout contract.
- **Suggested revision**: None for the asserted coverage; optional hardening only if new assertions need richer fidelity.

### FINDING_23: [OUT_OF_SCOPE] Prose already discusses ambiguous threads; gap is the summary table vs helper stdout
- **Reviewer(s)**: dyn-gh-stub-fidelity-output.txt
- **Concern**: Clarifies that the doc issue is table alignment, not absence of ambiguity discussion in prose.
- **Suggested revision**: Treat as nuance when executing FINDING_15; no separate code change beyond table/contract alignment.

### FINDING_24: [OUT_OF_SCOPE] Multi-round ordered completion path behaves as intended in harness
- **Reviewer(s)**: dyn-awk-state-machine-output.txt
- **Concern**: Ordered `request`/`response` pairs match `response-pending` expectations for that scenario.
- **Suggested revision**: None; keep coverage when changing state machine for FINDING_12.

### FINDING_25: [OUT_OF_SCOPE] `last_req` tracks last request marker in timeline order (not max id)
- **Reviewer(s)**: dyn-awk-state-machine-output.txt
- **Concern**: Explains why monotonic ids align with “latest round” but do not subsume stronger gap constraints (FINDING_12 locus).
- **Suggested revision**: None standalone; informs FINDING_12 design/tests.
```
