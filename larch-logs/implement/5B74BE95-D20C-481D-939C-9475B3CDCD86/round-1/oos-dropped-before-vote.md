### OOS_1: [OUT_OF_SCOPE] SKILL.md summary omits REPO_ROOT binding
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: The Gate C summary in `SKILL.md` omits the `REPO_ROOT` binding now documented in `approval-gates.md`, so a skim of `SKILL.md` alone can miss the binding rule.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Update SKILL.md Gate C bullet to reference source-env.sh binding (optional polish)

### OOS_2: [OUT_OF_SCOPE] publish-time refresh still omits `--repo-root`
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-design-root
- **Severity**: latent
- **Concern**: Publish-time `write-design-env` refresh still runs without `--repo-root`, so it remains dependent on fallback precedence instead of an explicit propagated root.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address via shared writer fix; no publish call-site change required in this branch
  - From dyn-dyn-design-root: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] Step 2b drafting still lacks an explicit repo root
- **Reviewer(s)**: dyn-dyn-design-root
- **Severity**: latent
- **Concern**: The Step 2b drafting path still invokes `python/cli.py architectural-guidelines read` without an explicit `--repo-root` from `source-env.sh`, so drafting can still omit guidelines input when the cwd is the plugin checkout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-design-root: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] root resolution is inconsistent across the design lifecycle
- **Reviewer(s)**: dyn-dyn-design-root
- **Severity**: nit
- **Concern**: Final-summary / failure-report root resolution already prefers `CLAUDE_PROJECT_DIR`, then env `REPO_ROOT`, then `source-env.sh`, then `git rev-parse`, while Step 0 capture and `write-design-env` refresh use a different precedence chain, so root resolution is inconsistent across the lifecycle.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-design-root: Address the concern above.

