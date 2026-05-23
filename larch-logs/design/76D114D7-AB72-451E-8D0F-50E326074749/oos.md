### OOS_1: Triple external dispatch increases prompt exposure surface
- **Description**: When the outer waterfall stacks with dispatch-with-waterfall.sh's internal Claude fallback, an adversarial vendor output could trigger up to 3-6 model invocations for a single aggregator slot, expanding token cost and untrusted-input handling surface. Optional follow-up: env var to suppress inner fallback when outer loop owns tool rotation.
- **Reviewer**: Cursor-Arch (out_of_scope, latent, security)
- **focus-area = code-quality**


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### OOS_2: Archived `/implement` prompt logs enumerate STALL_REASON values without aggregator-validation-exhausted
- **Description**: `larch-logs/implement/06D2F52E-5E2D-4FDD-894D-CAD7B67AB5E5/round-1/dyn-mav-resume-cap-semantics-prompt.md:132-136` (and similar archived prompt templates) list panel-failed and other STALL_REASON tokens without aggregator-validation-exhausted. If these archived prompts are still authoritative for training, they're stale.
- **Reviewer**: Cursor-Arch (out_of_scope, nit, risk-integration)
- **focus-area = code-quality**

## Voting

For each finding above, vote YES (accept and revise the plan), NO (reject), or EXONERATE (legitimate concern but not worth changing the plan for). Use proportionality — if a finding's concern is real but the proposed change is heavier than the issue warrants, vote EXONERATE.

Write your votes as:
```
FINDING_1: YES
FINDING_2: YES
...
OOS_1: NO
OOS_2: EXONERATE
```

Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

