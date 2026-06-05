## Decision 1: Timeout-hardening scope
- **Question**: compute-pr-line-counts.sh has no explicit timeout on the gh api --paginate call and no repo-wide gh-timeout convention exists. Add timeout-hardening code, or document the as-built behavior only?
- **Resolution**: Document only. The plan records the as-built error handling (gh failure → LINES_STATUS=unavailable → N/A render) and notes the no-explicit-timeout limitation in acceptance criteria. No new timeout code.
- **Source**: user

## Decision 2: Fallback-test target file
- **Question**: The issue names scripts/test-render-run-summary.sh, but compose_self_fallback / LINES_DATA_OK live in skills/implement/scripts/write-final-report.sh, tested by skills/implement/scripts/test-write-final-report.sh. Where does the new test go?
- **Resolution**: skills/implement/scripts/test-write-final-report.sh — add a LINES_DATA_OK=true stage2-fallback case there. The renderer's own harness already covers both bullet shapes (test-render-run-summary.sh:76,231,254,279); no renderer-harness change.
- **Source**: user

## Decision 3: Pagination edge-case coverage
- **Question**: Does item 1's "covering gh api --paginate pagination edge cases" require new pagination tests?
- **Resolution**: No new pagination test. test-compute-pr-line-counts.sh already pins the --paginate flag (line 94) and bucketing math; the plan documents the GitHub pulls/files 3000-file API cap and existing coverage as acceptance evidence. Issue item 2 names exactly one test gap — the fallback branch.
- **Source**: codebase

## Decision 4: Security-validation posture
- **Question**: Does "security validation of REPO/PR_NUMBER inputs" require new validation code?
- **Resolution**: No. Shipped code already rejects non-numeric PR_NUMBER (case guard, compute-pr-line-counts.sh:33-38) and malformed REPO (single-slash owner/name check, lines 40-47); values pass as argv to gh — no eval/interpolation surface. Both paths are test-pinned (test-compute-pr-line-counts.sh:101-109). Plan documents this as acceptance criteria.
- **Source**: codebase
