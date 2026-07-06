## Decision 1: Application-fidelity audit scope
- **Question**: The fidelity audit relies on per-round before/after snapshots, but `plan-pre-apply-round-N.txt` is deleted mid-loop, so per-round diffs are not durably available at Gate C. How should we scope the fidelity check?
- **Resolution**: End-state diff audit. Preserve ONE durable pre-review plan snapshot. At Gate C the main agent diffs it against the final `plan.txt`: confirm every change traces to an accepted finding, and no unrelated section was damaged. Covers acceptance and fidelity intent with a minimal, low-risk loop touch (one preserved file). Do NOT add per-round durable diff emission to the background Step 3 loop.
- **Source**: user

## Decision 2: Digest / persistence Python surface
- **Question**: Point 6 says "Consider a `plan-review preview --variant accepted-audit` helper." How much Python should the audit add?
- **Resolution**: Mirror the architectural-guidelines assessment. Compose the audit digest prompt-side. Add ONE persist helper (like `persist-design-assessment`) that writes the assessment into the design log. Do NOT add a dedicated `plan-review preview --variant accepted-audit` renderer.
- **Source**: user

## Decision 3: Out of scope (from proposal)
- **Question**: What must this feature NOT touch?
- **Resolution**: Do not raise the reviser tier in `plan revise-waterfall` (explicit OOS). Do not add per-round main-agent participation (rejected in the proposal's Cost section: it would force loop bail-outs and reopen the background Step 3 loop). The audit runs once, at Gate C Presentation, end-of-run only.
- **Source**: codebase / proposal

## Decision 4: Voting-contract hard constraint (from proposal)
- **Question**: How does the audit act on disagreement?
- **Resolution**: Escalate, never silently revert. Strong disagreement surfaces as dissent in the Gate C `AskUserQuestion`; reversal flows through the existing Discuss-further -> Gate A path. Under `--skip-approve`, strong disagreement overrides auto-approve and forces the Gate C prompt (the unattended-run tripwire). Agree and mild-disagree keep auto-approve. Escalation bar: concrete breakage, or contradiction of an explicit Round-1 refusal or approved-outline non-goal. Everything else is a printed note, not an escalation.
- **Source**: codebase / proposal
