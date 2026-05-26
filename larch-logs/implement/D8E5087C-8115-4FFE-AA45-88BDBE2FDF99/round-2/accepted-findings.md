### FINDING_16: risk-integration: scripts/test-design-log-publish.md:9-14
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Coverage paragraph omits the render-cache regular-file rejection test added in round 1. Contributors reading the contract doc may believe non-directory roots are untested. Mention render-cache non-directory root rejection alongside the symlink bullet list.
- **Suggested revision**: Address the concern above.


### FINDING_2: code-quality: scripts/design-log-publish.md:95-115
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] New render-cache section documents per-file -L recheck and parent-dir race limits; plan-review section omits both despite identical code at design-log-publish.sh:340-344. Operators reading only the plan-review section may assume render-cache has stricter TOCTOU coverage than plan-review. Add matching per-file recheck and parent-directory race bullets under ## plan-review allowlist.
- **Suggested revision**: Address the concern above.


### FINDING_23: correctness: SECURITY.md:141-142
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] SECURITY.md states plan-review requires a real directory root but the script only enters the block when [[ -e plan-review ]] A dangling plan-review symlink is skipped as missing optional content while SECURITY.md implies stricter subtree rules comparable to render-cache Qualify plan-review in SECURITY.md or add [[ -e ... || -L ... ]] to the plan-review outer guard for parity with render-cache
- **Suggested revision**: Address the concern above.


