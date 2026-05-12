## Architecture Diagram


```mermaid
graph TD
    subgraph SharedPromptLayer["Shared Prompt Layer"]
        FP["skills/shared/focus-area-prompt.md\n(canonical compressed prose)"]
    end

    subgraph DesignSkill["skills/design/"]
        SKILL["SKILL.md Step 3\n(launch blocks → renderer calls)"]
        RENDERER["scripts/render-plan-review-prompt.sh\n(--archetype --vendor --plan-file)"]
        PLANREVIEW["references/plan-review.md\n(collection/voting procedure)"]
        TEST["scripts/test-plan-review-prompt.sh"]
    end

    subgraph ReviewLauncher["scripts/launch-review.sh"]
        CODEX_PRE["CODEX_REVIEW_HARDENING_PREAMBLE\n(3-line compact form)"]
        CURSOR_PRE["CURSOR_SANDBOX_ENFORCEMENT_LINE\n+ compact prohibition sentence"]
    end

    subgraph SkillMDs["Inline Prompt Blocks (CI-anchored)"]
        REVIEW_SKILL["skills/review/SKILL.md\n(compressed 40-word prose, enum inline)"]
        IMPL_SKILL["skills/implement/SKILL.md\n(compressed 40-word prose, NEVER-6 compliant)"]
    end

    subgraph CI["CI (ci.yaml focus-area enum check)"]
        BACKTICKED["BACKTICKED_FILES check"]
        UNQUOTED["UNQUOTED_FILES check"]
    end

    RENDERER -->|"renders archetype+vendor specific prompt"| SKILL
    SKILL -->|"--prompt-file via temp file"| ReviewLauncher
    FP -->|"human reference"| RENDERER
    FP -->|"added to BACKTICKED_FILES"| BACKTICKED
    REVIEW_SKILL -->|"enum inline"| UNQUOTED
    IMPL_SKILL -->|"enum inline"| UNQUOTED
    SKILL -->|"CI anchor comment"| UNQUOTED
    TEST -->|"asserts all 8 archetype×vendor combos"| RENDERER
    PLANREVIEW -->|"references renderer for external fallbacks"| RENDERER
```

## Code Flow Diagram


```mermaid
sequenceDiagram
    participant D as /design SKILL.md Step 3
    participant R as render-plan-review-prompt.sh
    participant LR as launch-review.sh
    participant EX as External Reviewer (Cursor/Codex)
    participant CI as .github/workflows/ci.yaml

    D->>R: --archetype arch --vendor cursor --plan-file plan.txt
    R-->>D: rendered prompt (stdout → temp file)
    D->>LR: --tool cursor --prompt-file _arch_prompt_file
    LR->>EX: launch with rendered prompt
    EX-->>LR: findings output
    LR-->>D: output file written

    Note over CI: Focus-area enum check
    CI->>D: grep SKILL.md for enum (anchor comment satisfies)
    CI->>LR: grep scripts for HARD CONSTRAINTS anchor
    CI->>LR: check compact preamble contains prohibition sentence
```
