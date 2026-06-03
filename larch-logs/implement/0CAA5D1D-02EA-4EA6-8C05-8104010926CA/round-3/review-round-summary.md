# Review Round 3

- Mode: `diff`
- 9 accepted, 2 rejected (2 exonerated)

## Accepted Findings

### FINDING_1: SECURITY.md documents removed post-bump PostToolUse hook
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: SECURITY.md still describes a Plugin-shipped PostToolUse Skill hook running `hook-post-bump-version.sh`, but Phase 5 removed the hook registration and deleted the script. Operators/auditors may believe bump-resume hygiene is hook-enforced when shipped `hooks.json` no longer does that.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_11: linting docs assign test-classify-bump to wrong harness shard
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `docs/linting.md` says `test-classify-bump` belongs to `test-harnesses-10`, but the Makefile assigns it to `test-harnesses-20`, so shard debugging/rebalancing follows stale documentation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_13: classify-bump uses predictable TMPDIR fallback reasoning filename
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: When `IMPLEMENT_TMPDIR` is not writable, `classify-bump.sh` falls back to a fixed `bump-version-reasoning.md` path under `TMPDIR`, creating a possible symlink race on multi-user systems.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_16: Alias skill still says /implement includes version bump
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `skills/alias/SKILL.md` still lists version bump as part of the `/implement` pipeline, implying alias-driven implement runs still bump per PR despite the Phase 1/5 contract moving versioning to `/release`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: SECURITY.md postbump trust-boundary docs still mention removed changelog inputs
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: SECURITY.md still documents `--changelog-bullets-file` and changelog fail-closed postbump behavior that was removed from `implement-finalize.sh`. Readers may implement, audit, or call a non-existent postbump input surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_3: Research eval set still asks about deleted rebase-rebump procedure
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `skills/research/references/eval-set.md` eval-7/eval-15 still reference the removed rebase-rebump sub-procedure, so eval scoring can reward answers grounded in deleted behavior instead of CI-fix rebase/conflict-resolution docs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_4: git-sync-local-main contract still frames caller as classify-bump re-bump
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/git-sync-local-main.md` still describes classify-bump/re-bump usage, which can confuse maintainers about why the helper runs during ship-pr CI-fix rebase.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_5: git-force-push contract still references re-bump sub-procedure
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/git-force-push.md` still documents Re-bump Sub-procedure and rebase+re-bump call sites, creating stale maintainer guidance for CI-fix force-push behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_6: Postbump state contract retains unused or ghost bump keys
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Postbump state still requires or emits bump-era keys such as `BUMP_REASONING_FILE`, `MANIFEST_PATH`, `TOOL_LABEL`, and `HAS_BUMP` even though current postbump logic no longer reads/validates them. Future edits and debugging may treat these as meaningful contract fields.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


