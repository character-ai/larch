# Review Round 1

- Mode: `diff`
- 6 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Missing Makefile targets for new cross-repo harnesses
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: New resolver and cross-repo filing harnesses are not wired into Makefile targets, harness shards, or relevant-checks mapping, so CI and local lint can pass without running the new safety tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_11: Dedup-comment success can emit a blank URL
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-risk-integration-output.txt
- **Severity**: important
- **Concern**: The helper emits dedup-comment success even when GitHub comment JSON lacks a usable `html_url`, leaving downstream notices with an empty report URL.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-risk-integration-output.txt: Address the concern above.


### FINDING_13: Tier B compose-report integration paths are under-tested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Tier B compose-report tests cover create-only behavior but omit resolver failure and dedup-match paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_3: Missing Tier A dedup entrypoint coverage
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-architecture-output.txt
- **Severity**: important
- **Concern**: `dedup-tier-a-report` has no harness coverage for no-match, lookup-failed-open, dedup-comment, dry-run, repo binding, or normalized stdout behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-architecture-output.txt: Address the concern above.


### FINDING_4: Stale Tier B policy says chat-only
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-architecture-output.txt
- **Severity**: important
- **Concern**: `stall-recovery.md` still says Tier B prints through chat only, contradicting the new filing flow that files upstream on success and prints only on fallback or dry-run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-architecture-output.txt: Address the concern above.


### FINDING_9: Resolver accepts newline-bearing metadata
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `resolve-upstream-larch-repo.sh` trims repository metadata before checking it, so raw metadata with a trailing newline can be accepted despite the plan requiring rejection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


