## Architecture Diagram

```mermaid
flowchart TD
    subgraph implement-bootstrap.sh
        main["main case plan / coder / all"]
        phase_tracking["phase_tracking"]
        early_return["RESUME_PLAN_TAIL early return lines 540-582"]
        phase_plan["phase_plan_materialize"]
        resume_skip["resume-skip block lines 703-749"]
        dirty_check["run_dirty_tree_checkpoint line 750"]
        post_check["post-checkpoint helpers lines 754-911"]
    end

    subgraph documentation
        bootstrap_md["scripts/implement-bootstrap.md Resume-tail idempotency section new"]
    end

    subgraph structural_pins
        struct_test["scripts/test-implement-structure.sh dirty-tree pins lines 419-450"]
        new_pins["new pins resume-tail prose plus 4 ib expansion tokens"]
    end

    main --> phase_tracking
    main --> phase_plan
    phase_tracking --> early_return
    phase_plan --> resume_skip
    phase_plan --> dirty_check
    dirty_check -->|first pass bail| post_check
    dirty_check -->|resume clean| post_check
    post_check -.documents.-> bootstrap_md
    struct_test --> new_pins
    new_pins -.pins.-> bootstrap_md
    new_pins -.pins SKILL.md.-> main
```
