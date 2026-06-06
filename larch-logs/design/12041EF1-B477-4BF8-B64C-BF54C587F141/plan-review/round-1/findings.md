### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/check-scope-reduction-marker.sh (planned); <TMPDIR>/plan.txt:43-50
- **Concern**: Planned stdin consolidation uses a Python heredoc as the same stream the detector then reads. Scenario: With `python3 - "${IN_PATH:--}" <<'PY'`, Python consumes stdin as the program text; when `sys.argv[1] == "-"`, `sys.stdin.read()` sees EOF instead of the caller's piped fixture, so stdin/file parity fails and callers using stdin miss scope-reduction markers
- **Proposed resolution**: Keep one detector body, but pass the Python source via `python3 -c '...' "${IN_PATH:--}"` or another mechanism that leaves the process stdin connected to the caller's input; keep the new parity test to pin this contract

### FINDING_2:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:43-44
- **Concern**: Proposed heredoc consolidation cannot preserve stdin data. Scenario: `python3 - ... <<'PY'` uses stdin for the Python program, so when the marker checker is invoked with piped input and `IN_PATH=-`, the Python body cannot also read the caller's original stdin; stdin mode will see EOF or wrong data
- **Proposed resolution**: Use `python3 -c` or another shape that leaves stdin available for data when the path argument is `-`, or keep separate minimal stdin/file wrappers while sharing the detector body through a real helper function/module

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/check-scope-reduction-marker.sh (plan.txt:43-44)
- **Concern**: Unified python3 - "${IN_PATH:--}" <<'PY' shape cannot read caller stdin in "-" mode. Scenario: Bash attaches the heredoc to fd 0, so when sys.argv[1] is "-" the Python body reads the script source (or EOF), not piped fixture bytes; file mode still works and the proposed stdin/file parity case will fail or give false negatives
- **Proposed resolution**: Keep one shared detector body but split invocation: file mode uses python3 - "$path" <<'PY', stdin mode uses python3 - <<'PY' with caller stdin unredirected, or duplicate fd 0 to another fd before the heredoc and read that fd in "-" mode

### FINDING_4:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/check-scope-reduction-marker.sh (plan.txt:43-44)
- **Concern**: Proposed Python invocation cannot read caller stdin. Scenario: The shape python3 - "${IN_PATH:--}" <<'PY' uses stdin for the Python program itself, so when sys.argv[1] == "-" the Python body sees EOF or the heredoc stream, not the piped marker fixture. Stdin-mode detection will report no marker while file mode works.
- **Proposed resolution**: Do not use fd 0 for both the script and data. Use python3 -c with the shared body, or preserve caller stdin on another fd before the heredoc and read that fd in "-" mode.

### FINDING_5:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/check-scope-reduction-marker.sh:19-24
- **Concern**: The proposed `python3 - "${IN_PATH:--}" <<'PY'` consolidation still consumes stdin for the Python program, so stdin mode cannot read the caller's piped finding text.. Scenario: `check-scope-reduction-marker.sh < fixture` sees EOF/empty input instead of the fixture, so the planned stdin/file parity test fails and stdin callers miss `[SCOPE-REDUCTION]` markers.
- **Proposed resolution**: Do not use a heredoc on stdin for the consolidated helper. Use `python3 -c '...' "${IN_PATH:--}"`, a temporary Python file, or preserve caller stdin on another fd and read that fd when argv is `-`.

### FINDING_6:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: security
- **Location**: skills/shared/scripts/render-assessor-prompt.sh:52-53
- **Concern**: The plan says SECURITY.md will require scope-anchor consumers, including the Step 3.6 assessor lane, to render literal-redacted escaped blocks with framing prose, but no plan step updates the assessor prompt renderer that currently cats FEATURE_FILE raw.. Scenario: A staged scope anchor containing delimiter-shaped text or instruction-like issue prose is still inlined raw into the assessor prompt, while the new SECURITY.md contract would claim the opposite.
- **Proposed resolution**: Add the minimal renderer/doc/test update for render-assessor-prompt.sh to wrap FEATURE_FILE with the same untrusted framing plus redact-and-escape block, and extend test-render-assessor-prompt.sh; or narrow the SECURITY.md wording so it does not claim escaped rendering for the assessor lane.

### FINDING_7:
- **Reviewer(s)**: Cursor-dyn-dependency-chain
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:5
- **Concern**: Hard-dependency prose says items 1, 2, 4, and 6 edit files that exist only on branch sergey-zhupanov/implementing-design-review-anchor-scout-3511. Scenario: git cat-file shows assess-plan-round.sh, tally-plan-review.sh, and SECURITY.md on both main and origin/sergey-zhupanov/implementing-design-review-anchor-scout-3511; only scripts/check-scope-reduction-marker.sh is branch-only
- **Proposed resolution**: Rephrase dependency: files 1/2/6 exist on main; gate on branch-only symbols (plan-review-scope-anchor.txt, SCOPE_ANCHOR_FILE handoff, marker helper) not file presence

### FINDING_8:
- **Reviewer(s)**: Cursor-dyn-dependency-chain
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:8-9,34-35
- **Concern**: Item 3 marked partially done on main; only residual framing prose needed. Scenario: On main skills/design/scripts/revise-plan-with-waterfall.sh:143-149 still emit raw plan/findings/feature tags via sed; emit_untrusted_file_block exists only on the branch (#3548) at revise-plan-with-waterfall.sh:39-48
- **Proposed resolution**: Reclassify item 3 as branch-dependent; state framing prose applies only after #3548 lands (or list porting emit_untrusted_file_block as prerequisite)

### FINDING_9:
- **Reviewer(s)**: Cursor-dyn-dependency-chain
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:9,52-53
- **Concern**: Item 5 marked fully done in code; plan adds tests only. Scenario: On main scripts/launch-claude-subprocess.sh:180-181 cat context files without redact-secrets.sh or HTML escaping; branch adds redact+sed at lines 181-184
- **Proposed resolution**: Reclassify item 5 as branch-dependent test coverage; note main would need the #3548 redact/escape pipeline before tests can pass

### FINDING_10:
- **Reviewer(s)**: Cursor-dyn-dependency-chain
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:31-32,13-14
- **Concern**: Item 2 SKILL.md re-tally edit assumes SCOPE_ANCHOR_FILE MainAgent choreography. Scenario: main skills/design/SKILL.md:1128 has no SCOPE_ANCHOR_FILE or render-main-agent-scope-anchor.sh; branch adds that block at SKILL.md:1133 plus render-main-agent-scope-anchor.sh (missing on main)
- **Proposed resolution**: Applying item 2 to main would add orphaned scope-anchor KV/re-tally prose with no materialization or renderer; keep hard gate on #3548 merge before item 2

### FINDING_11:
- **Reviewer(s)**: Cursor-dyn-dependency-chain
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:13-14,55-56
- **Concern**: Item 1 anchor preference assumes plan-review-scope-anchor.txt is staged. Scenario: Neither main nor branch assess-plan-round.sh references plan-review-scope-anchor.txt today (resolve_feature_file at assess-plan-round.sh:83-94); staging exists only on branch plan-review-loop.sh:133-172
- **Proposed resolution**: Dependency claim is correct for symbols but under-specified: item 1 is a no-op until loop materializes the anchor; call out symbol dependency explicitly in the hard-dependency block

### FINDING_12:
- **Reviewer(s)**: Codex-dyn-dependency-chain
- **Severity**: important
- **Focus area**: security
- **Location**: skills/shared/scripts/render-assessor-prompt.sh:52-53; skills/design/scripts/assess-plan-round.sh:193-199
- **Concern**: Step 3.6 assessor scope anchor would still render as raw prompt text. Scenario: Item 1 makes assess-plan-round prefer the staged issue-scope anchor, then passes it as --feature-file, but render-assessor-prompt.sh cats FEATURE_FILE directly under Refined problem statement. Tag-like or instruction-like issue text can steer the assessor despite item 6's claimed literal-redacted escaped-block contract.
- **Proposed resolution**: Update render-assessor-prompt.sh to render FEATURE_FILE with the same untrusted framing, redact-secrets, HTML escaping, and encoding="literal-redacted" block used by the other scope-anchor consumers; add a small harness assertion for the assessor prompt.

### FINDING_13:
- **Reviewer(s)**: Cursor-dyn-kv-propagation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/approval-gates.md:95
- **Concern**: Parallel MainAgent re-tally contract omits SCOPE_ANCHOR_FILE mechanical passthrough. Scenario: Plan item 2 only updates skills/design/SKILL.md MainAgent re-tally prose (~4 lines) but approval-gates.md line 95 duplicates the same re-tally refresh contract and is CI-pinned (scripts/test-design-structure.sh:1905). Gate B normative text can drift from SKILL.md on --scope-anchor-file and parsing SCOPE_ANCHOR_FILE from re-tally stdout
- **Proposed resolution**: Add matching --scope-anchor-file and parse/persist SCOPE_ANCHOR_FILE language to approval-gates.md line 95 (or cite SKILL as sole authority and trim duplicate re-tally flags there)

### FINDING_14:
- **Reviewer(s)**: Cursor-dyn-kv-propagation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1128
- **Concern**: Re-tally env refresh prose names only status fields not SCOPE_ANCHOR_FILE. Scenario: Existing pin (scripts/test-design-structure.sh:1912) requires setting TALLY_PLAN_REVIEW_STATUS and LOOP_STATUS then persisting both result env files from re-tally. Plan replaces preserve-SCOPE_ANCHOR_FILE prose with parse-from-re-tally but does not require writing SCOPE_ANCHOR_FILE= into .step3-plan-review-result.env and .step3-review-result.env on refresh. Orchestrator may parse the KV then drop it when rewriting env files
- **Proposed resolution**: In the SKILL.md MainAgent re-tally edit explicitly require parsing SCOPE_ANCHOR_FILE from re-tally stdout and including it in both refreshed result env writes (same keys as other durable Step 3 KVs)

### FINDING_15:
- **Reviewer(s)**: Cursor-dyn-kv-propagation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/plan-review-loop.sh:1405-1413
- **Concern**: plan-review-loop.sh tally KV parser not accounted for in plan consumer inventory. Scenario: plan-review-loop.sh is the only production caller of tally-plan-review.sh and parses stdout (TALLY_PLAN_REVIEW_STATUS VOTING_TALLY_FILE WARN only). Plan adds --scope-anchor-file emission on ok and main-agent-vote-required but does not pass the flag on initial tally (lines 1389-1402) and does not forward SCOPE_ANCHOR_FILE. Initial main-agent-vote-required tally therefore never emits the new KV in the live loop path; only orchestrator-direct re-tally does
- **Proposed resolution**: Add one plan sentence: loop intentionally omits --scope-anchor-file on initial tally; SCOPE_ANCHOR_FILE durable handoff remains #3548 loop materialization; tally KV emission serves re-tally mechanical passthrough only

### FINDING_16:
- **Reviewer(s)**: Cursor-dyn-kv-propagation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/scripts/tally-plan-review.sh:88-90
- **Concern**: --help exit path omitted from SCOPE_ANCHOR_FILE emission matrix. Scenario: Plan edge cases document ok and main-agent-vote-required emitters and tally-error intentional omission. tally-plan-review.md:35 already exempts --help from TALLY_PLAN_REVIEW_STATUS; --help emits no KVs at all (third terminal class)
- **Proposed resolution**: When updating tally-plan-review.md note SCOPE_ANCHOR_FILE is absent on --help and all tally-error paths including EXIT trap pre-success failures

### FINDING_17:
- **Reviewer(s)**: Codex-dyn-kv-propagation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/plan-review-loop.sh:1389-1412; skills/design/scripts/plan-review-loop.sh:136-176; skills/design/scripts/run-step3-review.sh:293-318; skills/design/scripts/run-step3-review.sh:341-366; skills/design/SKILL.md:1079-1096
- **Concern**: The plan adds tally SCOPE_ANCHOR_FILE output but does not update the downstream KV chain that must read and forward it. Scenario: Normal Step 3 captures tally output inside plan-review-loop, which currently parses only TALLY_PLAN_REVIEW_STATUS and VOTING_TALLY_FILE; run-step3-review and the SKILL Step 3 handoff also allowlist fixed key sets. The MainAgent re-tally prose can reference SCOPE_ANCHOR_FILE, but the variable may never reach that orchestrator state.
- **Proposed resolution**: Add the minimum passthrough: have plan-review-loop pass the flag to tally when set, parse SCOPE_ANCHOR_FILE, include it in emit_loop_kvs and write_step3_result_env, then add it to run-step3-review parse/emit/result-env allowlists and the SKILL Step 3 handoff allowlist.
