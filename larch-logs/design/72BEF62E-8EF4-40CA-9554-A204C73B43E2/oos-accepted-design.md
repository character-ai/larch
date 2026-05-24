### OOS_1: `ACTION=FINALIZE` still requires a non-empty `voting-tally.md`; any tally abort that skips
- **Reviewer(s)**: Cursor-dyn-kv-contract
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/finalize-plan.sh:59-64
- **Description**: `ACTION=FINALIZE` still requires a non-empty `voting-tally.md`; any tally abort that skips writing a populated tally file breaks Step 4 unchanged by this KV refactor. Scenario: Step 4 `FINALIZE` hard-fails when `voting-tally.md` is missing or zero bytes even if earlier steps already logged a tally failure
- **Suggested fix**: Track as follow-up: relax finalize rules or guarantee `tally-plan-review.sh` always materializes `voting-tally.md` before non-zero exit
- **Phase**: design
- **Filed URL**: https://github.com/character-ai/larch/issues/2720
### OOS_3: New Claude voter subprocess surface
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: security
- **Location**: SECURITY.md:1-200
- **Description**: New Claude voter subprocess surface. Scenario: launch-claude-review.sh on plan ballots changes trust and logging boundaries vs in-process Agent voter
- **Suggested fix**: Note subprocess data paths and any secret-handling expectations in SECURITY.md when implementation lands
- **Phase**: design
- **Filed URL**: https://github.com/character-ai/larch/issues/2721
