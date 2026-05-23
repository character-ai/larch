## Plan

**Note**: This is the FINAL plan, post-Gate B revision incorporating all 29 accepted plan-review findings. The 10-reviewer panel (5 Cursor + 5 Codex archetypes) and 3-voter adjudication (Claude + Codex + Cursor) signed off on this revision. The implementor should execute this plan exactly.


## Architecture Diagram

```mermaid
graph TD
    classDef phase fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef waterfall fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef helper fill:#f3e5f5,stroke:#4a148c,stroke-width:1px
    classDef new fill:#c8e6c9,stroke:#1b5e20,stroke-width:2px
    classDef exit fill:#ffcdd2,stroke:#b71c1c,stroke-width:1px

    Start([entry]) --> Resume{RESUME_PHASE set?}
    Resume -->|yes| ResumeHandler[Legacy resume handler<br/>step8_apply_bump_same_version<br/>force-push-gate<br/>ship-pr-rrr-phase14<br/>NOT no-op — advances phase]:::new
    Resume -->|no| Loop
    ResumeHandler --> Loop

    Loop{PHASE} --> Checks
    Loop --> Bump
    Loop --> PrPrep
    Loop --> PrCreate
    Loop --> CiInitial
    Loop --> EvalFail
    Loop --> CiMerge
    Loop --> Postmerge

    Checks[run_checks_phase]:::phase --> ResolveLogA{resolve_checks_<br/>log_path?}
    ResolveLogA -->|fail| WfChecksA[run_recovery_waterfall<br/>phase=checks]:::waterfall
    ResolveLogA -->|ok| LintLoop[3× lint-fix-loop attempts]
    LintLoop -->|exhaust| WfChecksB[run_recovery_waterfall<br/>phase=checks]:::waterfall
    LintLoop -->|pass| BumpPhase[advance: bump]

    Bump[run_bump_phase]:::phase --> BumpGuard{bump-branch-guard}
    BumpGuard -->|fail| StallBumpGuard[exit_stall<br/>bump-branch-guard]:::exit
    BumpGuard -->|ok| ClassifyApply{classify+apply}
    ClassifyApply -->|version regression| Step8Mech[_run_step8_same_version<br/>_mechanically<br/>state counter persisted]:::new
    Step8Mech -->|attempt 1 fail<br/>or 2nd occurrence| StallBump[exit_stall 8]:::exit
    Step8Mech -->|recover| PostBump[postbump finalize]
    ClassifyApply -->|ok| PostBump
    PostBump -->|conflict<br/>force-push-gate| ForcePushMech[_run_force_push_gate<br/>_mechanically]:::new
    ForcePushMech -->|recover| PrPrepPhase[advance: pr-prep]
    ForcePushMech -->|fail| StallBumpB[exit_stall 8b]:::exit
    PostBump -->|ok| PrPrepPhase

    PrPrep[run_pr_prep_phase]:::phase --> OosGate{oos-disposition-<br/>gate}
    OosGate -->|fail| WfPrPrep[run_recovery_waterfall<br/>phase=pr-prep]:::waterfall
    OosGate -->|ok| PrCreatePhase[advance: pr-create]

    PrCreate[run_pr_create_phase]:::phase --> WriteFinalA[with_transient_retry<br/>write-final-report.sh]:::helper
    WriteFinalA -->|exhaust transient| ExitTransientA[exit_transient_net]:::exit
    WriteFinalA -->|fail non-transient| WfPrCreateA[run_recovery_waterfall<br/>phase=pr-create]:::waterfall
    WriteFinalA -->|ok| CreatePr[with_transient_retry<br/>create-pr.sh]:::helper
    CreatePr -->|exhaust transient| ExitTransientB[exit_transient_net]:::exit
    CreatePr -->|fail non-transient| WfPrCreateB[run_recovery_waterfall<br/>phase=pr-create]:::waterfall
    CreatePr -->|ok| CiInitialPhase[advance: ci-initial]

    CiInitial[run_ci_phase ci-initial]:::phase --> CiWait[with_transient_retry<br/>ci-wait.sh<br/>envelope-aware predicate]:::helper
    CiWait -->|merge| CiMergePhase[advance: ci-merge]
    CiWait -->|rebase| Rebase[run_rebase_rebump]
    CiWait -->|evaluate_failure| EvalFail
    CiWait -->|bail user-input| Exit3[exit 3 BAIL_NEEDS_USER_INPUT]:::exit
    CiWait -->|bail unknown| ExitStall10[exit_stall 10/12]:::exit

    Rebase[run_rebase_rebump]:::phase --> BumpConflict{bump-only<br/>conflict?}
    BumpConflict -->|yes| DetermPrePass[deterministic pre-pass<br/>auto-resolve-changelog<br/>--ours plugin.json etc]
    BumpConflict -->|no| WfRebase[run_recovery_waterfall<br/>phase=rebase-nonbump<br/>--role resolve-conflict<br/>verifier: rebase --continue<br/>+ plain-no-push]:::waterfall
    DetermPrePass --> RebumpPush
    WfRebase --> RebumpPush

    EvalFail[run_evaluate_failure]:::phase --> CiFixVendor[run_ci_fix_vendor<br/>3× cursor/codex<br/>UNCHANGED structure<br/>+ local-repro prompt]:::helper
    CiFixVendor -->|exhaust| ExitStallCi[exit_stall 10/12-max-retries]:::exit
    CiFixVendor -->|ok| CiMergePhase

    CiMerge[run_ci_phase ci-merge]:::phase --> MergePr[with_transient_retry<br/>merge-pr.sh<br/>envelope-aware predicate]:::helper
    MergePr -->|admin/policy fail| ExitStall12d[exit_stall 12d<br/>HARD BOUNDARY]:::exit
    MergePr -->|ok| Postmerge

    Postmerge[run_postmerge_phase]:::phase --> WriteFinalPM[with_transient_retry<br/>write-final-report.sh<br/>postmerge]:::helper
    WriteFinalPM --> Done([exit 0])

    WfChecksA --> WaterfallSubgraph
    WfChecksB --> WaterfallSubgraph
    WfPrPrep --> WaterfallSubgraph
    WfPrCreateA --> WaterfallSubgraph
    WfPrCreateB --> WaterfallSubgraph
    WfRebase --> WaterfallSubgraph

    subgraph WaterfallSubgraph[run_recovery_waterfall — 3 tiers, 1 attempt each]
        direction TB
        WfBaseline[Pre-tier baseline<br/>HEAD + tracked + untracked + staged]:::new
        WfBaseline --> WfCursor{Cursor tier<br/>launch-cursor-ci.sh<br/>--failure-log injected}
        WfCursor -->|verify ok| WfSuccess([tier success])
        WfCursor -->|verify fail<br/>or unavailable| WfRevert1[Rollback<br/>staged: git restore --staged<br/>then checkout + rm<br/>quoted -- pattern]:::new
        WfRevert1 --> WfCodex{Codex tier<br/>launch-codex-ci.sh<br/>--failure-log injected}
        WfCodex -->|verify ok| WfSuccess
        WfCodex -->|verify fail<br/>or unavailable| WfRevert2[Rollback]
        WfRevert2 --> WfClaude{Claude tier<br/>launch-claude-ci.sh<br/>NEW LAUNCHER}:::new
        WfClaude -->|verify ok| WfSuccess
        WfClaude -->|verify fail<br/>or unavailable| WfRevert3[Rollback]
        WfRevert3 --> WfExhaust[WATERFALL_EXHAUSTED=true<br/>caller exit_stalls]:::exit
    end

    WaterfallSubgraph -.->|tier success path| TierSuccess[stage + commit + push<br/>or skip for pr-prep/pr-create<br/>verify-as-rerun]
    TierSuccess -.-> ContinuePhase((continue phase))

    subgraph LaunchersSubgraph[CI launcher family — write-capable]
        LaunchCursorCi[launch-cursor-ci.sh<br/>+ --failure-log]:::helper
        LaunchCodexCi[launch-codex-ci.sh<br/>+ --failure-log]:::helper
        LaunchClaudeCi[launch-claude-ci.sh<br/>NEW<br/>writer persona<br/>--failure-log]:::new
        LaunchCSubproc[launch-claude-subprocess.sh<br/>UNCHANGED<br/>read-only reviewer]:::helper
    end

    LaunchersSubgraph -.->|consumer| Loop
```

## Acceptance


1. `scripts/launch-claude-ci.sh` exists with argv mirroring cursor/codex CI launchers (including `--failure-log`), writer-persona prompt (no read-only preamble), local-reproduction invariant text, and ONLY `fix` / `resolve-conflict` roles. Sibling `.md` + harness exist and pass.

2. `run_recovery_waterfall` wired at 5 sites in `scripts/ship-pr.sh`: `run_checks_phase` at BOTH `exit_stall 6` sites (the earlier `resolve_checks_log_path` failure path AND the after-lint-loop path), `run_pr_prep_phase` exit_stall 9a1, `run_pr_create_phase` BOTH exit_stall 9b sites, `run_rebase_rebump` non-bump conflict block. Each site falls through to existing `exit_stall` on waterfall exhaustion. Verifier per phase: `run-relevant-checks-captured.sh` for checks/pr-prep; re-run failing helper for pr-create; `git rebase --continue` + `_run_rebase_rebump_verify_plain_no_push` for rebase-nonbump.

3. `with_transient_retry` is **envelope-aware**: takes a predicate parameter and retries on rc=0 transient envelopes for `merge-pr.sh` (`MERGE_RESULT=error|admin_failed`) and `ci-wait.sh` (`ACTION=bail BAIL_REASON=...`). Classification uses combined stderr+stdout (the `fail_file` contents).

4. Three `exit 5` paths absorbed in-script. The legacy `RESUME_PHASE` handler retains its existing semantics (advance phase + dispatch the per-token path), now backed by in-script mechanical recovery instead of prompt-side work. State-key documentation accurately describes the legacy mapping (`RESUME_PHASE=bump CALLER_KIND=step8_apply_bump_same_version`, NOT `RESUME_PHASE=step8_apply_bump_same_version`).

5. CI-fix local-reproduction invariant prompt text in `scripts/launch-cursor-ci.sh`, `scripts/launch-codex-ci.sh`, `scripts/launch-claude-ci.sh` for `--role fix`. `--failure-log` argv added to all three launchers (validated as absolute path under `$IMPLEMENT_TMPDIR`, content piped through `redact-secrets.sh` and capped at 4KB before injection into prompt). Argv shapes of cursor/codex launchers are extended (new optional flag), existing harness coverage adapted for the new flag.

6. 26 new `scripts/test-ship-pr.sh` cases pass. Existing cases continue to pass with stub updates as needed (relaxed acceptance wording per FINDING_12).

7. 14 new `scripts/test-launch-claude-ci.sh` cases pass. `scripts/test-launch-cursor-ci.sh` and `scripts/test-launch-codex-ci.sh` each gain 3 new cases for the `--failure-log` argv and local-reproduction invariant.

8. Bash 3.2: `make lint-bash32` passes. Per-tier rollback uses `--` sentinel + quoted-`while read` loop (no unquoted `$delta` expansion). No `local -n`, no `mapfile`, no `&>>`, no `declare -A`.

9. Source-safe testing: `scripts/ship-pr.sh` can be `source`d without ANY side effects. ALL top-level executable logic (argv parsing, validation, state init, RESUME_PHASE handler, main loop) is wrapped in a `main()` function gated by `if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then main "$@"; fi`.

10. `scripts/ship-pr.md`, `scripts/launch-cursor-ci.md`, `scripts/launch-codex-ci.md`, new `scripts/launch-claude-ci.md` reflect runtime changes accurately (especially the legacy RESUME_PHASE handler semantics — `ship-pr-rrr-phase14` is NOT a no-op, it advances the phase and runs `run_rebase_rebump`). `scripts/lib-timing-kinds.sh` includes `claude-ci-fix`. `Makefile` registers `scripts/test-launch-claude-ci.sh` in the appropriate shard.

11. No new emitters of `exit 5` in `scripts/ship-pr.sh` (CI structure assertion). No new emitters of `exit_transient_net` outside the `with_transient_retry` fall-through path.

12. The unquoted-path rollback security risk (FINDING_14/F23) is structurally prevented by the `--` sentinel + quoted-argument `while read` pattern; tests `recovery_waterfall_rollback_handles_paths_with_spaces_and_globs` and `recovery_waterfall_rollback_restores_staged_changes_via_git_restore_staged` pin the safe behavior.

13. `make lint` and `bash scripts/relevant-checks.sh` pass cleanly. No regression in existing harness coverage.

diff_lines: 1480
