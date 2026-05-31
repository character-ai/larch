### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:234-282
- **Concern**: Step 0b rewrite omits REPO resolve/pass-through to new drivers. Scenario: After fetch, `design-route.sh` may call `design-pause-load.sh` without `--repo`, and `design-init-runparams.sh` may rename via `tracking-issue-write.sh` without `--repo` — wrong default `gh` remote on fork/multi-remote clones (today's 2.5-bis/5.5 prose resolves REPO first)
- **Proposed resolution**: In sub-step 2 (after `issue-body.txt`), keep `resolve-repo.sh` / `gh repo view` fallback; pass `${REPO:+--repo "$REPO"}` on both driver invocations and on resume `write-design-current-env.sh`; pin in `test-design-structure.sh`
