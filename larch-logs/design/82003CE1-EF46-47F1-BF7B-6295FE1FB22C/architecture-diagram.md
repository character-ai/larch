## Architecture Diagram

```mermaid
graph TD
    subgraph LIB["scripts/lib-net.sh (shared)"]
        ITNS[is_transient_net_signature]
        WTR[with_transient_retry<br/>3 attempts, 2s/4s sleep]
        TEN[transient_envelope_predicate_none]
    end

    subgraph SHIP["scripts/ship-pr.sh"]
        SPW[ship_pr_with_transient_retry<br/>re-runs predicate at exhaustion]
        ETN[exit_transient_net]
        TPM[transient_envelope_predicate_merge_pr]
        TPC[transient_envelope_predicate_ci_wait]
    end

    subgraph TIER1["Tier 1 — git push and gh pr verbs"]
        DLP[design-log-publish.sh<br/>push, pr create, pr merge]
        CPR[create-pr.sh]
        RPS[rebase-push.sh]
        MPR[merge-pr.sh]
        GBU[gh-pr-body-update.sh]
    end

    subgraph TIER2["Tier 2 — gh issue and gh api writes"]
        TRW[tracking-issue-write.sh]
        TRS[tracking-issue-summary.sh]
        CLAB[clarify-label.sh]
        CCP[clarify-comment-post.sh]
        NBW[named-block-write.sh]
        UDC[upsert-diagrams-comment.sh]
        DFI[decompose-file-issues.sh]
        CFI[cleanup-failed-issue.sh]
        CO[create-one.sh]
        AC[apply-combination.sh]
        ACP[audit-close-priors.sh]
    end

    subgraph TIER3["Tier 3 — git fetch, pull, ls-remote, submodule (hard-fail only)"]
        CRB[check-remote-branch.sh]
        PRF[preflight.sh]
        CBR[create-branch.sh]
        LCL[local-cleanup.sh]
        AUP[audit-preflight.sh]
        SFR[setup-forked-open-source-repo.sh]
    end

    subgraph TEST["scripts/test-lib-net.sh (new harness)"]
        TLN[stub commands and sleep<br/>asserts attempts and backoff]
    end

    WTR --> ITNS
    SPW --> WTR
    SPW --> ITNS
    SPW --> ETN
    SPW -.uses.-> TPM
    SPW -.uses.-> TPC

    SHIP -.7 callsites.-> SPW
    DLP -.per-call fail_files.-> WTR
    CPR --> WTR
    RPS --> WTR
    MPR --> WTR
    GBU --> WTR

    TIER2 --> WTR
    TIER3 --> WTR

    TLN -.stubs.-> WTR
    TLN -.stubs.-> ITNS
    TLN -.envelope-exhaust.-> SPW

    classDef new fill:#9f9,stroke:#363
    classDef carved fill:#fcc,stroke:#a33,stroke-dasharray:5
    classDef shared fill:#bdf,stroke:#369
    class WTR,TEN,SPW,TLN new
    class ITNS shared
```

Notes:
- Green: new code (lifted helper, lifted predicate, ship-pr thin wrapper, test harness).
- Blue: existing `is_transient_net_signature()` (byte-stable).
- Solid arrows: function calls. Dotted: usage relationships.
- `gh issue create` and `git clone` callsites are intentionally NOT wired to `with_transient_retry` (non-idempotent — Findings 4 and 6) and stay bare in their parent scripts.
