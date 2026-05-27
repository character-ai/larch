## Architecture Diagram

```mermaid
graph TD
    subgraph callers["Current callers (unchanged in this partition)"]
        review_core["review-core.sh<br/>(--findings-file under REVIEW_TMPDIR)"]
        plan_review["plan-review-loop.sh<br/>(--findings-file under DESIGN_TMPDIR)"]
    end

    subgraph future["Future caller (separate partition)"]
        multi_round["multi-round plan-review loop<br/>(--findings-file at round-N/<br/>findings-in-scope.md)"]
    end

    subgraph script["aggregate-findings.sh"]
        argv["argv parse +<br/>boolean validation<br/>(new: --allow-findings-outside-tmpdir<br/>validated early)"]
        symlink["symlink rejection<br/>(unconditional)"]
        canon["canonicalize<br/>--findings-file path"]
        containment["containment case<br/>(rejection branch flag-gated)"]
        dispatch["dispatch +<br/>merge pipeline"]
        output["post-dispatch output<br/>containment check<br/>(strict; not flag-gated)"]
        mv["mv -f merged-tmp<br/>FINDINGS-FILE<br/>(guarded under flag=true)"]
    end

    subgraph docs["Docs + tests"]
        agg_md["aggregate-findings.md<br/>(CLI row + Escape hatch +<br/>asymmetric note +<br/>disabled-mode note)"]
        security_md["SECURITY.md<br/>(trust-model paragraph<br/>for new opt-in)"]
        harness["test-aggregate-findings.sh<br/>(3 new cases:<br/>reject, allow, output-strict)"]
    end

    review_core -- calls --> argv
    plan_review -- calls --> argv
    multi_round -. opts in to flag .-> argv

    argv --> symlink
    symlink --> canon
    canon --> containment
    containment --> dispatch
    dispatch --> output
    output --> mv

    agg_md -. documents .- script
    security_md -. records trust boundary .- containment
    harness -. exercises .- script
```

The diagram shows the asymmetric trust boundary inside `aggregate-findings.sh`: the **containment case** rejection branch is now flag-gated, but **symlink rejection** stays unconditional and the **post-dispatch output containment check** stays strict. Existing callers (`review-core.sh`, `plan-review-loop.sh`) are byte-equivalent because the flag defaults to `false`; only the future multi-round plan-review loop (out of scope here) will opt in. Docs and the regression harness sit adjacent to the script, documenting the new opt-in and locking the relaxation contract.
