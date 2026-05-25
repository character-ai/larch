## Architecture Diagram

```mermaid
flowchart TD
    A[ship-pr.sh: run_evaluate_failure] -->|gh_logs_rc=0| B[gh-run-logs.sh]
    A -->|gh_logs_rc=0| C[ci-failed-jobs.sh NEW]
    C -->|FD-3: FAILED_JOBS_COUNT, FAILED_JOBS_FIXABLE, FAILED_JOBS_UNFIXABLE| A
    C -->|TSV: JOB_NAME, SHARD, CLASS| D[run_per_job_local_fix_loop NEW]
    A -->|fixable_count gt 0| D
    D --> E[_per_job_argv NEW: case dispatcher]
    E -->|argv array, no eval| F[run_captured_cmd_then_fix_loop NEW]
    F -->|capture log, redact| G[lint-fix-loop.sh]
    G -->|--site ship-pr-ci-per-job<br/>--target-cmd-args-file| H[launch-cursor-ci.sh<br/>launch-codex-ci.sh<br/>launch-claude-ci.sh]
    H -->|FIXED or UNFIXABLE| F
    F -->|rerun mapped cmd via callback| E
    F -->|status: ok| D
    F -->|status: exhausted| I[unfixable_set]
    D -->|Phase B: verification sweep| E
    D -->|no-local-equivalent rows| I
    I -->|non-empty| J[BAIL: exit 3<br/>BAIL_REASON=ci-local-unfixable]
    D -->|all jobs ok, sweep clean| K[_stage_and_push_ci_fixes NEW]
    K --> L[append-token-record.sh]
    K --> M[refresh-run-logs.sh]
    K --> N[git-commit then git-push]
    A -->|ci-failed-jobs rc=1 or 3, graceful degrade| O[run_ci_fix_vendor existing]
    O -->|3-tier waterfall| H
    O -->|on success| K
    P[run_checks_with_lint_fix_loop refactored] -->|reuses| F
    Q[test-ci-failed-jobs.sh NEW] -.->|drift pin on jobs block of ci.yaml| C
    Q -.->|argv allowlist coverage| E
    R[ci.yaml: lint, lint-mermaid, shellcheck,<br/>test-harnesses N, agent-lint, agnix,<br/>smoke-dialectic, agent-sync,<br/>gitleaks, trufflehog] -.->|parsed by gh --json jobs| C
    S[Makefile: lint-only, lint-mermaid,<br/>agent-sync, test-harnesses-N] -.->|invoked by argv array| E
    style C fill:#cfe
    style D fill:#cfe
    style E fill:#cfe
    style F fill:#cfe
    style K fill:#cfe
    style Q fill:#cfe
    style I fill:#fcc
    style J fill:#fcc
    style P fill:#fed
```

**Legend**: green = new components introduced by this plan; pink = bail / unfixable-set sink; orange = refactored existing component; solid arrows = control flow; dashed arrows = data references / drift pins / config inputs.
