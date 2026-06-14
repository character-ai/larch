### OOS_1: [OUT_OF_SCOPE] REPORT_GATE_SIDECARS sidecar emit sites lack delivery-channel rules
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `REPORT_GATE_SIDECARS` sidecar emit sites in `skills/design/SKILL.md:864,868` lack explicit delivery-channel rules. Sidecar content emitted via tool stdout instead of orchestrator text could be collapsed/hidden.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add delivery-channel prohibition at sidecar emit sites in a follow-up.


