### OOS_1: [OUT_OF_SCOPE] README feature matrix still describes --oos as actuality-only
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-oos-prompt-contract
- **Severity**: nit
- **Concern**: The README feature matrix still describes `--oos` as actuality-only behavior and omits the merit-gate / approval-staging wording, so operators who stop there get stale guidance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: README feature matrix omits merit-gate wording for --oos Operators reading README see actuality-only description; plan scoped sync to docs/skills.md only Update README --oos row when doing a broader catalog sync
  - From cursor-specialist-testing: README --oos blurb still actuality-only Operators using the feature matrix miss merit staging until they open docs/skills.md or the dev skill Update README combine-issues row when doing a broader docs sync (out of this PR scope)
  - From dyn-dyn-oos-prompt-contract: Sync the README table row with the updated docs/skills.md `--oos` wording in a follow-up docs pass.

### OOS_2: [OUT_OF_SCOPE] No automated harness for the rescue-matching prompt contract
- **Reviewer(s)**: dyn-dyn-oos-prompt-contract
- **Severity**: nit
- **Concern**: Prompt regressions in oos-4 will not be caught by CI until a manual skill run unless a structural harness is added for the prompt contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-oos-prompt-contract: Add a structural harness only if prompt contracts become machine-checkable; plan excluded test changes

