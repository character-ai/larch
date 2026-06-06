## Decision 1: Behavioral idempotency change (Part A #2) in scope
- **Question**: Include the runtime change aligning record-implement-review-round-timing.sh's idempotency pre-check to full-tuple fingerprinting, or defer it and ship only the test/attribution plumbing?
- **Resolution**: Include it (full issue scope). The implement helper's round-only short-circuit becomes full-tuple (round+start+end) like the design-helper variant, so a stale/partial row is overwritten instead of silently reused.
- **Source**: user

## Decision 2: Cross-skill symmetry (design side)
- **Question**: Also close an analogous A1-scanner gap for the design helper record-plan-review-round-timing.sh?
- **Resolution**: No — implement-only. test-design-structure.sh has no analogous "15-file A1 scanner" to extend (it only contains-checks the SKILL.md invocation), so mirroring would be net-new infrastructure beyond this OOS issue.
- **Source**: codebase

## Decision 3: Preserve strict same-line enforcement for existing emitters (hard constraint)
- **Question**: When teaching the A1 scanner the export-or-same-line rule, must the strict same-line pin requirement for the existing implement timing emitters be preserved?
- **Resolution**: Yes. The export-or-same-line relaxation must be scoped so it does not weaken misattribution detection for the existing emitters. The scanner must still fail on a genuinely unpinned timing call.
- **Source**: codebase

## Decision 4: Backward compatibility (hard constraint)
- **Question**: What existing behavior must not break?
- **Resolution**: The timing-ledger.tsv row schema and timing-ledger.sh record-round/record-vendor-task contracts must be preserved. The lint-fix guard must only pin LARCH_TIMING_SKILL at the implement dispatch site (lint-fix-loop.sh) — NOT a blanket pin on the generic launch-codex-exec.sh, which also serves design/review/research.
- **Source**: codebase
