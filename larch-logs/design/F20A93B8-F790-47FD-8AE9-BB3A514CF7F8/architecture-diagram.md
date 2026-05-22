## Architecture Diagram

```mermaid
flowchart TD
    user[User]
    design[/design Skill]
    implement[/implement Skill]
    issue[GitHub Issue + larch:plan]

    subgraph session [/design Session Setup]
        setup[session-setup.sh]
        writer[write-design-current-env.sh NEW]
        envfile[SESSION_TMPDIR/source-env.sh]
        symlink["~/.cache/larch/sessions/current-design-env.sh<br/>stable symlink"]
    end

    subgraph design_steps [/design Steps]
        step0[Step 0 setup<br/>no Step 1 branch step]
        step1c[Step 1c questions]
        step1d[Step 1d Round 1]
        gateA[Step 1e Gate A<br/>2-opt first-time<br/>3-opt re-entry includes Show-plan]
        plan[Step 2b plan.txt]
        review[Step 3 plan review]
        gateB[Step 3.5 Gate B]
        gateC[Step 4b Gate C]
        publish[Step 5 plan-block-write + log publish]
    end

    subgraph implement_branch [/implement Branch Lifecycle UNCHANGED]
        ibranch[Step 0 + Step 2<br/>create feature branch]
        iimpl[implementation]
        iship[ship-pr]
        iclean[finalize-state.sh + teardown<br/>cleanup branch post-merge]
    end

    user --> design
    user --> implement

    design --> setup
    setup -- writes --> writer
    writer -- writes --> envfile
    writer -- updates --> symlink
    envfile -- sourced by --> design_steps
    symlink -. points to .-> envfile

    step0 --> step1c --> step1d --> gateA
    gateA -- first-time Ready --> plan
    gateA -- re-entry Show-plan --> gateA
    gateA -- re-entry Ready --> review
    plan --> review --> gateB
    gateB -- Apply / Iterate --> gateC
    gateB -- Discuss --> gateA
    gateC -- Discuss --> gateA
    gateC -- Re-run --> review
    gateC -- Approve --> publish
    publish --> issue

    issue -- read by --> implement
    implement --> ibranch --> iimpl --> iship --> iclean
```
