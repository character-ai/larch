## Architecture Diagram

```mermaid
flowchart TB
  classDef new fill:#d4edda,stroke:#155724
  classDef updated fill:#fff3cd,stroke:#856404
  classDef existing fill:#e9ecef,stroke:#495057

  subgraph implement[/implement orchestrator]
    direction TB
    stall_bail[Existing bail paths<br/>STALL_TRACKING=true]:::existing
    step17[Step 17 final report]:::existing
    step18a[Step 18a recovery gate<br/>NEW entry-guard]:::new
    step18b[Step 18b teardown<br/>existing body]:::existing
    rename_done[Rename to DONE]:::existing
    rename_stalled[Rename to STALLED]:::existing
  end

  subgraph helper[stall-recovery-report sh helper]
    direction TB
    classify[classify subcommand]:::new
    init_attempts[init-attempts]:::new
    record_attempt[record-attempt]:::new
    bug_body[bug-body]:::new
    bug_comment[bug-comment]:::new
    issue_input[issue-input-file]:::new
    dev_clone[is-larch-dev-clone]:::new
  end

  subgraph contracts[Helper contracts and allowlists]
    direction TB
    helper_md[stall-recovery-report md<br/>caps and allowlist doc]:::new
    allowlist_tsv[allowlists tsv<br/>machine-readable]:::new
    ref_md[references/stall-recovery md<br/>dispatch and retry loop]:::new
  end

  subgraph wrappers[Existing wrapper scripts]
    direction TB
    run_step5[run-step5-review sh]:::existing
    ship_pr[ship-pr sh]:::existing
    lint_fix[lint-fix-loop sh]:::existing
  end

  subgraph io[State and outputs]
    direction TB
    ship_state[ship-pr-state sh]:::existing
    session_env[session-env sh]:::existing
    exec_issues[execution-issues md]:::existing
    attempts_env[stall-recovery-attempts env]:::new
    issue_env[stall-recovery-issue env]:::new
    larch_issue[/larch:issue Skill]:::existing
    gh_comment[gh issue comment]:::existing
    chat_print[chat print consumer repo]:::new
  end

  subgraph shared[Shared infra]
    direction TB
    lib_clone[lib-larch-dev-clone sh]:::new
    stale_plugin[check-stale-plugin sh]:::updated
    redact[redact-secrets sh]:::existing
    security_md[SECURITY md]:::updated
    makefile[Makefile shard]:::updated
  end

  stall_bail -->|skip to Step 18| step17 --> step18a
  step18a -->|STALL_TRACKING true| classify
  step18a -->|STALL_TRACKING false| step18b
  classify --> init_attempts --> record_attempt
  classify -->|inputs| ship_state
  classify -->|inputs| session_env
  classify -->|inputs| exec_issues
  classify -->|signature dedup| attempts_env
  classify --> bug_body
  bug_body -->|allowlist| allowlist_tsv
  bug_body -->|backstop| redact
  bug_body --> issue_input
  issue_input -->|larch clone| larch_issue --> issue_env
  bug_body -->|consumer repo| chat_print
  dev_clone -->|true or false| ref_md
  dev_clone -->|sources| lib_clone
  stale_plugin -->|sources| lib_clone
  ref_md -->|step5-review| run_step5
  ref_md -->|step8-shippr| ship_pr
  ref_md -->|step2-impl| lint_fix
  ref_md -->|caps lookup| helper_md
  ref_md -->|retry record| record_attempt
  ref_md -->|terminal| bug_comment
  bug_comment -->|larch clone| gh_comment
  bug_comment -->|consumer repo| chat_print
  ref_md -->|success atomic| ship_state
  step18a -->|recovery success| step18b --> rename_done
  step18a -->|recovery exhausted| step18b --> rename_stalled
  helper_md -->|allowlist source| allowlist_tsv
  security_md -.documents.-> allowlist_tsv
  makefile -.test shard.-> helper
```
