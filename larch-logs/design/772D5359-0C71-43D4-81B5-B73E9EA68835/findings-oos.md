### OOS_1: [SCOPE-REDUCTION] New `--report-framing` CLI flag duplicates work the tail wrapper could do by wrapping existing `emit-rejected` stdout
- **Description**: [SCOPE-REDUCTION] New `--report-framing` CLI flag duplicates work the tail wrapper could do by wrapping existing `emit-rejected` stdout. Scenario: Extra argparse surface and paired Python/shell heading strings to keep in sync; same operator outcome with fewer moving parts
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/plan_review.py:1216-1264,skills/design/scripts/design-step3b-tail.sh:107-114
- **Phase**: design



### OOS_2: Section relabel plus prompt hardening leaves #4884 concern-level overlap visible: rejected blocks whose Concern text still misstates the current plan remain in the operator list
- **Description**: Section relabel plus prompt hardening leaves #4884 concern-level overlap visible: rejected blocks whose Concern text still misstates the current plan remain in the operator list. Scenario: Real run #4773 class: five already-satisfied concerns still appear under softer framing; only the section title changes, not per-finding false claims
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/plan_review.py:1193-1213,python/rendering.py:1176-1198
- **Phase**: design



### OOS_3: [SCOPE-REDUCTION] No concern-level suppression for differently-worded re-raises
- **Description**: [SCOPE-REDUCTION] No concern-level suppression for differently-worded re-raises. Scenario: Issue #4884 also describes rejected findings whose concerns are already satisfied in `plan.txt` but whose dedup keys differ from accepted ledger entries; identity-key filtering cannot drop them. The plan deliberately chooses relabeling over semantic/plan-text matching. That is proportionate minimum-change hygiene, not a blocking gap for this umbrella.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: plan.txt:7-15
- **Phase**: design



