# Review Round 4

- Mode: `diff`
- Accepted findings: 8
- Rejected findings: 1
- Exonerated findings: 7
- Neutral findings: 0

## Accepted Findings

### FINDING_1: Stale public `--panel` docs for `review-and-fix`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Concern**: Orchestrator-facing markdown still documents a public `--panel simple|hard` argv surface after the shell entrypoint stopped parsing/forwarding `--panel`, so readers, grepped “contracts,” and operators can follow docs into `unknown option` / wrong automation assumptions.
- **Suggested revision**: Remove `--panel` from the `review-and-fix.sh` orchestrator flag table; document the internal `review-core.sh --panel hard` chain only; keep “Edit-In-Sync” prose aligned with the actual `review-and-fix.sh` argv.


### FINDING_2: Step 5 harness markdown contract drift (`test-run-step5-review`)
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: `scripts/test-run-step5-review.md` still claims `run-step5-review` derives/forwards `--panel hard` while the harness/launcher no longer passes `--panel`, risking stale assertions and future CI/doc-sync confusion.
- **Suggested revision**: Update the harness markdown “coverage” lines to match real argv (e.g., round-cap, dynamic-archetypes, session paths) and explicitly state `--panel` is not forwarded.


### FINDING_20: `PLAN_FILE` miss can fall back to local `design-export/plan.txt` in Step 1 / Step 5 runners
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: On `PLAN_FILE` absence, scripts may consume a stale local export instead of the GitHub-validated `larch:plan` materialization expected after Preflight, masking session-env writer bugs/partial writes.
- **Suggested revision**: Remove or strictly gate the `design-export` fallback on issue-anchored runs; fail closed with an error pointing maintainers at `persist-post-plan-keys.sh` (or equivalent writer contract).


### FINDING_22: `/fix-issue` discovery text omits plan-mandated flags (`--merge` / `--no-dedup`)
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: YAML `argument-hint` / description surfaces omit flags that the plan and forwarding paths expect, causing operators to miss supported argv.
- **Suggested revision**: Update `skills/fix-issue/SKILL.md` argument-hint (and related description line if needed) to match plan C.1 and actual forwards.


### FINDING_23: Topology authority still uses “hard and simple panels” phrasing (`topology.tsv`)
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Projection row description preserves SIMPLE/HARD split language despite a unified internal panel story, undermining the “single internal panel + `POST_PLAN_WORKFLOW_PATH` semantics” messaging sweep.
- **Suggested revision**: Reword the row to unified hard panel semantics (and post-plan workflow depth), keeping `topology.tsv` consistent with counted projection authority.
```

### FINDING_4: Unknown-flag exit code inconsistency (`clarify-label.sh`)
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Unknown-option path exits `1` after usage, unlike peer scripts that commonly exit `2`, which can mis-route thin automation that maps exit `2` to “bad argv.”
- **Suggested revision**: Align unknown-option exit code with the repo’s dominant convention (and any harness expectations), or document the intentional divergence.


### FINDING_8: `agnix-fix` SKILL missing normative `/implement` exit-code routing (esp. `3`, incl. ambiguous caveat)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: `.claude/skills/agnix-fix/SKILL.md` lacks an explicit outcomes/exit-code subsection mirroring `skills/implement/SKILL.md` (`0` vs `2` vs `3`), increasing risk that wrappers treat non-zero exits generically, retry incorrectly, or fail to route operators back to `/design` after preflight refuse / ambiguous clarify-related failures.
- **Suggested revision**: Add an exit/outcomes subsection: document `3` as a terminal branch for that attempt until upstream `/design` resolves clarify/plan issues; include the `2` vs `3` split and the ambiguous-state caveat as applicable.


### FINDING_9: Stale header comment referencing removed `/implement --issue` (`find-lock-issue.sh`)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Maintainer-facing header still points at a removed `--issue` flag shape, encouraging rediscovery/reintroduction of obsolete argv.
- **Suggested revision**: Reword to the supported positional `/implement <issue-N>` contract (and any related lock-script notes).


