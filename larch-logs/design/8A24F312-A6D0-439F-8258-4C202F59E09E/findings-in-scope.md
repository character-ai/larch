### FINDING_1: Ledger payload accounting uses raw file size instead of rendered section
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: Ledger payload accounting counts the full raw ledger file even when the prompt renderer truncates the emitted ledger section. On oversized ledgers, payload bytes can exceed what was actually rendered, pushing scaffold bytes to zero and distorting scaffold-based ranking.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Compute ledger payload from the actual non-empty section string returned by _code_ledger_section or _plan_ledger_section after truncation, or from the included rows, not from the whole ledger file; pin with a greater-than-12000-byte ledger rendering case.
  - From Codex-Innovation: Count the bytes of the actual ledger_section string inserted into the prompt, or expose the rendered ledger rows from findings_ledger and count only those bytes
  - From Codex-Pragmatic: Count the exact rendered ledger section bytes, or the exact truncated rows that prompt_section() emits, not the full ledger file size.
  - From Codex-Requirements: Count the exact emitted ledger section bytes, or the kept ledger rows after truncation, and add a focused oversized-ledger rendering test

### FINDING_2: Code-review voter dispatch still lacks payload sidecar wiring
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The code-review voter path still does not record payload bytes the same way as the plan-review voter path. As a result, voter rows dispatched through `agent_voters.py` can remain at `payload_bytes=0`, which inflates scaffold accounting for a major panel tier.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add `### UPDATED: python/larch/agents/agent_voters.py` (and `python/tests/agents/test_agent_voters.py`) mirroring the plan-review voter path: render with payload sidecar, build `payload_files` parallel to `prompt_files`, and pass selected counts through `build_panel_dispatch_env` / waterfall rows
  - From Cursor-Pragmatic: Add `### UPDATED: python/larch/agents/agent_voters.py` mirroring the plan-review voter work: pass `--payload-bytes-output` from `_make_voter_prompt_file`, accumulate per-tool counts in `_build_voter_prompt_files`, emit a `payload_files` map in `_write_voter_waterfall_manifest`, and thread the selected tool's bytes through `build_panel_dispatch_env`. Add matching coverage in `python/tests/agents/test_agent_voters.py`.

### FINDING_3: Implementer payload counting overstates path-referenced findings content
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The implementer prompt counts scrubbed findings-file bytes even though the prompt only path-references that file rather than inlining it. That can overstate payload, drive scaffold to zero, and erase the implementer scaffold signal needed for ranking.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Set implementer `payload_bytes` to zero (or count only bytes actually written into `coder-prompt.md`), and drop the edge-case allowance for payload larger than prompt bytes on this path
  - From Cursor-Pragmatic: Set implementer `payload_bytes=0` (or pass explicit zero through `append_panel_prompt_size` / `build_panel_dispatch_env`). Drop the `coder_runner.py` bullet that counts scrubbed accepted-findings file bytes, and update `test_review_and_fix.py` to assert zero payload with non-zero scaffold for the path-referenced coder prompt.

### FINDING_4: Voter payload helpers omit calibration feedback bytes
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: When calibration stats are enabled, the voter prompt includes inline calibration feedback text, but the payload accounting does not include those bytes. That understates payload and overstates scaffold for voter rows whenever calibration feedback is present.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Extend voter payload accounting to add raw bytes from the non-empty calibration feedback block produced by _voter_calibration_feedback_block

### FINDING_5: Aggregator payload accounting ignores generated reviewer-slot inventory
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: The aggregator prompt includes a generated per-run reviewer-slot inventory section, but the proposed accounting does not include that variable fragment. As a result, aggregator rows can misclassify that content as scaffold.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Include the variable inventory payload when computing aggregator payload_bytes, preferably by measuring the rendered per-run inventory fragment alongside source_text and retry feedback.

### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/report/tokens.py:52-85
- **Concern**: [SCOPE-REDUCTION] The plan adds scaffold_tokens and payload_tokens beyond the byte split the issue requires. Scenario: The committed TSV and measure-panel-cost schemas grow extra derived columns even though acceptance only needs scaffold and payload byte columns plus scaffold-byte ranking
- **Proposed resolution**: Limit panel-prompt-sizes.tsv additions to scaffold_bytes and payload_bytes; keep existing prompt and agent token columns unchanged and omit per-section token columns unless a separate requirement needs them
