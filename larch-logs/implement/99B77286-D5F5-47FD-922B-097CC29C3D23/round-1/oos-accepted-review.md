### OOS_1: [OUT_OF_SCOPE] Drift docs still describe rc14/operator brake instead of rc0 advisory
- **Reviewer(s)**: codex-specialist-security-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-architecture-output.txt, dyn-code-quality-output.txt
- **Severity**: latent
- **Concern**: Runtime and consumer-facing docs still describe drift as an operator prompt, brake, Continue/Cancel path, or merged exit `14`, even though the implementation now treats drift as an `rc=0` logged advisory. Affected references include `skills/design/references/flags.md`, `skills/design/scripts/review-design-step3-loop.md`, `skills/design/references/approval-gates.md`, `skills/design/scripts/check-plan-size.md`, and `docs/configuration-and-permissions.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-security-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-architecture-output.txt, dyn-code-quality-output.txt: Address the concern above.


### OOS_2: [OUT_OF_SCOPE] Standalone Step 2b.5 drift path lacks durable warning audit
- **Reviewer(s)**: dyn-architecture-output.txt, dyn-code-quality-output.txt
- **Severity**: latent
- **Concern**: The retained standalone Step 2b.5 path records drift by touching `.completed/step-2b.5` but does not append an `execution-issues.md` warning, unlike the merged `design-postplan-emit.sh` path. Override/recovery callers can therefore hit `DRIFT_TRIGGER_FIRED=true` without the durable audit entry expected for sub-max growth.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-architecture-output.txt, dyn-code-quality-output.txt: Address the concern above.


### OOS_3: [OUT_OF_SCOPE] Drift advisory regression test misses breadcrumb and telemetry assertions
- **Reviewer(s)**: dyn-code-quality-output.txt
- **Severity**: nit
- **Concern**: `skills/design/scripts/test-design-postplan-emit.sh` verifies the rc0 drift-advisory path partially, but does not pin the operator-visible breadcrumb or `DRIFT_TRIGGER_FIRED=true` in `.design-postplan-emit-result.env`. A regression dropping either signal could still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-code-quality-output.txt: Address the concern above.


