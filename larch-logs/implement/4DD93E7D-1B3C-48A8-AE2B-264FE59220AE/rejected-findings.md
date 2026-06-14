### [rejected] FINDING_3

**Rejected subtype:** dismissed (0 YES)

### FINDING_3: Legacy `--mode single` continuation mislabeled as mid-loop resume fence in SKILL.md:682-688
- **Reviewer(s)**: dyn-prompt-contract-drift-output.txt
- **Severity**: important
- **Concern**: The legacy `--mode single` heuristic continuation path tells the orchestrator to "loop back through the launcher-only Step 3 resume fence," but it never shows a bash fence and does not distinguish that path from the mid-loop resume contract at lines 627-633. Legacy continuation after `design-step3-continuation-entry.sh` should launch a fresh review round via the no-flag wrapper call at line 591 (`design-step3-review.sh` without `--starting-round`), letting `run-step3-review.sh` advance `review-round-count.txt`. Reusing the mid-loop resume example (`--starting-round` plus `--phase awaiting-continuation`) would re-enter the prior round instead of starting the next one.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-contract-drift-output.txt: Replace "resume fence" wording with "first-entry Step 3 launch fence," cite the line 591 bash block explicitly, and state that legacy `--mode single` continuation must not pass `--starting-round` or any resume-state flag.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** dismissed (0 YES)

### FINDING_4: Step 3 resume fence section overgeneralizes continuation-only example in SKILL.md:627-633
- **Reviewer(s)**: dyn-prompt-contract-drift-output.txt
- **Severity**: important
- **Concern**: The section title is "Step 3 resume fence (all mid-loop returns)," but the only fenced example is the continuation form (`--phase awaiting-continuation`). Apply, post-apply, per-round findings, and postplan-operator resumes are described only in matrix prose above, with no parallel bash examples for `--phase awaiting-apply`, `--phase awaiting-post-apply`, `--findings-file`, or `--postplan-operator-continue`. That makes the continuation example look like the universal template and raises the odds of under-specified resumes on high-friction paths (MAV apply, Gate B per-round approval, postplan operator).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-contract-drift-output.txt: Either retitle the section to make the continuation fence an example only, or add minimal fenced variants for the other resume flags, matching `skills/design/scripts/review-design-step3-loop.md:35-39`.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

