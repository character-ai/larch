## Decision 1: In-scope item set
- **Question**: Issue #4757 bundles 14 independent cleanup items. How much should this single design plan cover?
- **Resolution**: All 14 items in one comprehensive plan. Investigate the audit items during design; fix what is real, record explicit no-defect closures for the rest.
- **Source**: user

## Decision 2: Audit-item handling (Items 8, 10-14)
- **Question**: Items that say "re-review and pin a concrete defect or close as no-defect" — resolve during design, or defer to /implement?
- **Resolution**: Resolve during design. Investigate now so the plan carries concrete changes or explicit no-defect closure notes per item. /implement should be mechanical.
- **Source**: user

## Decision 3: No-defect closure policy
- **Question**: For audit items that resolve to "no defect found", add a regression test to pin behavior, or just document closure?
- **Resolution**: Pin only where risk is real. Add a regression test when the audit reveals a genuine correctness risk worth locking down (e.g. byte-escape round-trip, pylint bootstrap); otherwise document closure with rationale. Balances coverage against churn.
- **Source**: user

## Decision 4: Do not re-split this issue
- **Question**: Should the 14-item catch-all be routed to the decomposition panel?
- **Resolution**: No. #4757 was deliberately produced by `/combine-issues --oos` (combining #4744 + #4751). Re-splitting would undo that combination. Items are independent and may be implemented piecemeal within one plan.
- **Source**: codebase / issue provenance
