### FINDING_1: Python heredoc consolidation breaks stdin mode
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Cursor-Innovation, Codex-Innovation, Codex-Pragmatic
- **Severity**: important
- **Concern**: The planned `python3 - "${IN_PATH:--}" <<'PY'` shape uses stdin for the Python program itself, so `IN_PATH=-` cannot also read the caller’s piped fixture; stdin callers would miss scope-reduction markers while file mode works.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Keep one detector body, but pass the Python source via `python3 -c '...' "${IN_PATH:--}"` or another mechanism that leaves the process stdin connected to the caller's input; keep the new parity test to pin this contract
  - From Codex-Edge: Use `python3 -c` or another shape that leaves stdin available for data when the path argument is `-`, or keep separate minimal stdin/file wrappers while sharing the detector body through a real helper function/module
  - From Cursor-Innovation: Keep one shared detector body but split invocation: file mode uses python3 - "$path" <<'PY', stdin mode uses python3 - <<'PY' with caller stdin unredirected, or duplicate fd 0 to another fd before the heredoc and read that fd in "-" mode
  - From Codex-Innovation: Do not use fd 0 for both the script and data. Use python3 -c with the shared body, or preserve caller stdin on another fd before the heredoc and read that fd in "-" mode.
  - From Codex-Pragmatic: Do not use a heredoc on stdin for the consolidated helper. Use `python3 -c '...' "${IN_PATH:--}"`, a temporary Python file, or preserve caller stdin on another fd and read that fd when argv is `-`.


### FINDING_2: Assessor prompt still renders scope anchors as raw prompt text
- **Reviewer(s)**: Codex-Requirements, Codex-dyn-dependency-chain
- **Severity**: important
- **Concern**: The plan claims scope-anchor consumers render literal-redacted escaped blocks, but the Step 3.6 assessor prompt renderer still cats `FEATURE_FILE` raw, allowing delimiter-like or instruction-like issue text to steer the assessor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add the minimal renderer/doc/test update for render-assessor-prompt.sh to wrap FEATURE_FILE with the same untrusted framing plus redact-and-escape block, and extend test-render-assessor-prompt.sh; or narrow the SECURITY.md wording so it does not claim escaped rendering for the assessor lane.
  - From Codex-dyn-dependency-chain: Update render-assessor-prompt.sh to render FEATURE_FILE with the same untrusted framing, redact-secrets, HTML escaping, and encoding="literal-redacted" block used by the other scope-anchor consumers; add a small harness assertion for the assessor prompt.


### FINDING_3: Hard-dependency prose overstates branch-only file presence
- **Reviewer(s)**: Cursor-dyn-dependency-chain
- **Severity**: important
- **Concern**: The hard-dependency block says several items edit files that exist only on the dependent branch, but most named files already exist on main; the real dependency is on branch-only symbols and handoffs, not file presence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-dependency-chain: Rephrase dependency: files 1/2/6 exist on main; gate on branch-only symbols (plan-review-scope-anchor.txt, SCOPE_ANCHOR_FILE handoff, marker helper) not file presence


### FINDING_7: Item 1 anchor preference is under-specified without loop materialization
- **Reviewer(s)**: Cursor-dyn-dependency-chain
- **Severity**: important
- **Concern**: The anchor preference change is a no-op unless the review loop has already staged `plan-review-scope-anchor.txt`; the dependency is on branch-only materialization symbols, not just the assessor script.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-dependency-chain: Dependency claim is correct for symbols but under-specified: item 1 is a no-op until loop materializes the anchor; call out symbol dependency explicitly in the hard-dependency block


### FINDING_8: Approval-gates duplicate re-tally contract omits SCOPE_ANCHOR_FILE
- **Reviewer(s)**: Cursor-dyn-kv-propagation
- **Severity**: important
- **Concern**: The plan updates SKILL.md re-tally prose but not the duplicated, CI-pinned Gate B contract in approval-gates.md, allowing normative text to drift on `--scope-anchor-file` and `SCOPE_ANCHOR_FILE` parsing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-kv-propagation: Add matching --scope-anchor-file and parse/persist SCOPE_ANCHOR_FILE language to approval-gates.md line 95 (or cite SKILL as sole authority and trim duplicate re-tally flags there)


### FINDING_9: Re-tally env refresh may parse but drop SCOPE_ANCHOR_FILE
- **Reviewer(s)**: Cursor-dyn-kv-propagation
- **Severity**: important
- **Concern**: The SKILL.md re-tally refresh prose does not require writing `SCOPE_ANCHOR_FILE` into the refreshed Step 3 result env files, so the orchestrator may parse the KV and then lose it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-kv-propagation: In the SKILL.md MainAgent re-tally edit explicitly require parsing SCOPE_ANCHOR_FILE from re-tally stdout and including it in both refreshed result env writes (same keys as other durable Step 3 KVs)


### FINDING_10: Downstream Step 3 KV chain does not propagate SCOPE_ANCHOR_FILE
- **Reviewer(s)**: Cursor-dyn-kv-propagation, Codex-dyn-kv-propagation
- **Severity**: important
- **Concern**: Adding `SCOPE_ANCHOR_FILE` output to tally is insufficient unless the live Step 3 callers pass, parse, emit, and persist that key; otherwise the MainAgent re-tally prose may reference a variable that never reaches orchestrator state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-kv-propagation: Add one plan sentence: loop intentionally omits --scope-anchor-file on initial tally; SCOPE_ANCHOR_FILE durable handoff remains #3548 loop materialization; tally KV emission serves re-tally mechanical passthrough only
  - From Codex-dyn-kv-propagation: Add the minimum passthrough: have plan-review-loop pass the flag to tally when set, parse SCOPE_ANCHOR_FILE, include it in emit_loop_kvs and write_step3_result_env, then add it to run-step3-review parse/emit/result-env allowlists and the SKILL Step 3 handoff allowlist.


