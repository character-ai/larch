### [Plan Review] FINDING_11

### FINDING_11: render-cost-line.sh and render-run-summary.sh duplicate fmt_usd / cost display
- **Concern**: New helper duplicates `fmt_usd` and cost-formatting logic from `render-run-summary.sh:127-136`. Drift risk over time.
- **Reviewers**: Cursor-Arch, Codex-Arch (latent)
- **Proposed resolution**: Two options: (a) share a sourced fragment `scripts/lib-cost-fmt.sh` consumed by both helpers; (b) have `render-cost-line.sh` consume only `token-cost.sh` `KEY=value` lines with a single in-house formatter (since token-cost.sh already does the math). Option (b) is simpler and matches the plan's existing "centralize in token-cost.sh" decision.


