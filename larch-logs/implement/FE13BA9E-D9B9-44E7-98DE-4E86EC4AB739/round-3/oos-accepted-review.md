### OOS_3: [OUT_OF_SCOPE] Stale Gate C preview wrapper reference in configuration docs
- **Reviewer(s)**: cursor-specialist-testing, codex-generic
- **Severity**: nit
- **Concern**: `docs/configuration-and-permissions.md:336` still references the retired `design-step4b-preview.sh` Gate C preview fence while the active flow uses `skills/design/scripts/design-step3b-tail.sh`. Operators auditing Gate C flow may follow the wrong wrapper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Update docs to name design-step3b-tail.sh only.
  - From codex-generic: Update the stale reference to describe the merged Step 4 tail fence and `design-step3b-tail.sh`.


### OOS_4: [OUT_OF_SCOPE] dialectic-protocol.md Overview still documents removed Step 2a.5 flow
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-dialectic-lifecycle
- **Severity**: nit
- **Concern**: Overview prose in `skills/shared/dialectic-protocol.md` still describes the removed Step 2a.5 external debater waterfall and binding `dialectic-resolutions.md` output. Maintainers may implement against obsolete choreography even though the Gate C clarifier profile subsection was added.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Update Overview to Gate C clarifier profile.
  - From dyn-dyn-dialectic-lifecycle: Overview prose still describes the removed Step 2a.5 external debater waterfall and binding `dialectic-resolutions.md` output. That can mislead maintainers about the active Gate C clarifier path even though the clarifier profile subsection was added.


