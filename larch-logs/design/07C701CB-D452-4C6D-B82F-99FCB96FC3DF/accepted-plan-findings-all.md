### FINDING_1: Parent-ascent lint misses later path operands
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: The parent-ascent grep lint only checks the first detected path operand, so commands with a safe first path and a later `../` path can still evade detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Refactor the argv walk to collect all path operands (reuse the existing option/pattern/-- terminator rules) and run the `(^|/)\.\.(/|$)` segment test on each before any `< /dev/null` short-circuit
  - From Cursor-Innovation: Add an ascent helper that iterates all post-pattern path operands (same option/pattern/`--` rules as today) and flags any operand matching `(^|/)\\.\\.(/|$)`. Add a harness violation for a second path operand with `../`, and keep single-path cases from the plan.
  - From Cursor-Requirements: Require the awk helper to iterate all path operands after the pattern and flag any token matching (^|/)\.\.(/|$); add a harness violation such as rg -n PATTERN python/ ../python


### FINDING_3: Add regression coverage for a second `../` path operand
- **Reviewer(s)**: Cursor-Arch
- **Severity**: latent
- **Concern**: The regression harness does not cover a command with multiple path operands and a later `../` ascent, so a first-path-only implementation could still pass tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a violation fixture such as `rg -n PATTERN "$CLAUDE_PLUGIN_ROOT/python" ../python` and assert the new stderr text


### FINDING_5: Step 18a stall-recovery guidance is too narrow
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The new stall-recovery bounded-probe guidance is limited to sub-step 5 retry dispatch, but the reported runaway grep happened during sub-step 6 token discovery, leaving that failure mode unaddressed in the docs operators read for Step 18a.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Broaden the new text to all Step 18a prompt-side investigation probes (sub-steps 5-8). At sub-step 6 add: prefer python/cli.py stall-recovery validate-token --token-kind trigger --value CANDIDATE or the listed owner tokens step2-impl and step8-shippr; never grep via ../ ascents from $IMPLEMENT_TMPDIR


### FINDING_2: Preserve tier-1a size budget for the BASH_AUTHORING.md expansion
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The proposed BASH_AUTHORING.md addition risks pushing the file over its tier-1a line cap unless the plan explicitly budgets for the growth or validates the cap update.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add a firm plan step to keep the BASH_AUTHORING.md edit line-neutral, or update TIER1A_LINE_CAPS with the intentional growth and include tier1a-size validation in the focused checks

