# Review Round 1

- Mode: `diff`
- Accepted findings: 12
- Rejected findings: 0
- Exonerated findings: 6
- Neutral findings: 1

## Accepted Findings

### FINDING_1: Stale `--output` left after `MALFORMED` exit in `plan-block-read`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: On malformed plan-block exits, the script can leave a prior successful extraction in `--output`, so automation that treats fresh stderr/exit as authoritative may still read stale inner markdown from disk.
- **Suggested revision**: On every malformed path (and/or in shared malformed exit), truncate or remove `OUT_PATH` before `exit 1`; document the contract in the helper doc (e.g. `plan-block-read.md`).


### FINDING_12: `clarify-state` can emit `response-pending` when lower clarification IDs are not satisfied (wire-format gap)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-awk-state-machine-output.txt
- **Concern**: State machine can treat the last request as answered while an earlier request id never received a response but a higher id already has a response—conflicting with `docs/issue-anchored-plan.md` gap/ordering rules (should be `ambiguous` or refuse progress).
- **Suggested revision**: Extend `END`-state logic (and harness) so `response-pending` requires all lower ids satisfied per the doc, else emit `STATE=ambiguous` (with a dedicated fixture such as request `1`, request `2`, response `2` only).


### FINDING_15: `STATE` values table in `docs/issue-anchored-plan.md` omits `ambiguous`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-gh-stub-fidelity-output.txt
- **Concern**: Helpers emit `STATE=ambiguous` but the summary table does not, creating a normative gap for operators even when prose discusses ambiguity elsewhere.
- **Suggested revision**: Add an `ambiguous` row (or explicit non-exhaustive disclaimer + pointer to `clarify-state.md` / marker rules).


### FINDING_17: `test-clarify-state` `gh api` stub never exercises multi-page `jq -s 'add // []'` merge behavior
- **Reviewer(s)**: dyn-gh-stub-fidelity-output.txt
- **Concern**: Stub always emits a single JSON array, so pagination/slurp aggregation paths are untested.
- **Suggested revision**: Add a fixture where the stub prints two paginated JSON roots and assert merged timeline matches single-array expectations.


### FINDING_19: `gh issue view --json body --jq -r '(.body // "")'` passes two tokens to `--jq` (live CLI incompatibility)
- **Reviewer(s)**: dyn-awk-state-machine-output.txt
- **Concern**: Reported against live `gh`: `accepts 1 arg(s), received 2`, so issue body may not load in real runs; pattern duplicated across read/write scripts.
- **Suggested revision**: Pass a single `--jq` expression and/or pipe JSON through `jq -r` (or use supported `gh` formatting) so the decoded issue body reaches marker logic.


### FINDING_2: Plan/issue acceptance and PR narrative understate real touch surface
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-gh-stub-fidelity-output.txt, dyn-awk-state-machine-output.txt
- **Concern**: Stated scope (“Makefile-only”, “new files only”, narrow wiring) does not match edits to `agent-lint.toml`, `docs/issue-anchored-plan.md`, and (per several reviewers) a committed `larch-logs/implement/...` tree—widening review, CI, lint expectations, and merge/backport risk.
- **Suggested revision**: Reconcile acceptance text, implementation plan, and PR description with the full file list (or revert/split changes); drop committed implement run artifacts unless policy explicitly requires them (`docs/run-logs.md` / team convention).


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


