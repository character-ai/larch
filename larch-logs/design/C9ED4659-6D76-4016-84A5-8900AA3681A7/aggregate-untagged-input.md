### FINDING_1:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:17-22
- **Concern**: Checks Failure Entry stub still narrows routing to "pinned site split" while Approach assigns sections 1-5 to the reference. Scenario: The proposed stub tells implementers to "Follow the reference's pinned site split for the call site." In checks-repair-loop.md, "site split" names only the section 4 `NEXT_ACTION=continue` branch. Sections 1 (structural `FAILURE_REASON` gate), 4 (`main-agent-edit` re-entry loop), and 4 (`NEXT_ACTION=stall` default vs Step 5 MAV/coder deferral) sit outside that term. An implementer can write a 3-line stub that omits delegating to those branches; folded-site repair may skip structural fail-closed routing, skip composite re-capture after `continue`, or seed durable bail at the blockquote layer on MAV/coder terminal stalls.
- **Proposed resolution**: Round-1 FINDING_2 stayed neutral; the current plan still encodes the narrow wording. Replace the stub bullet with: after mandatory load of checks-repair-loop.md, follow sections 1-5 for the call site's blockquote-pinned `--site` / `--checks-site` pair (not "site split" alone). Keep the in-step-not-halt line.
