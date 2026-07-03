### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/rendering/rendering.py:759-783; python/larch/review/findings_ledger.py:145-190
- **Concern**: Ledger payload accounting counts the whole raw ledger file instead of the rendered ledger section. Scenario: The plan says to add raw ledger-file bytes whenever a ledger section is present, but findings_ledger.prompt_section truncates ledgers to the most recent rows under 12000 bytes. On a large round-2 ledger, payload_bytes can exceed the bytes actually rendered, scaffold_bytes clamps to 0, and measure-panel-cost stops ranking the fixed reviewer/voter scaffold honestly.
- **Proposed resolution**: Compute ledger payload from the actual non-empty section string returned by _code_ledger_section or _plan_ledger_section after truncation, or from the included rows, not from the whole ledger file; pin with a greater-than-12000-byte ledger rendering case.

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/agents/agent_voters.py:220-306
- **Concern**: Code-review voter dispatch is absent from the plan. Scenario: /implement Step 5 and standalone /review voters render via `agent_voters._make_voter_prompt_file` and `code-voter-slots.ndjson`, not `plan_review_panel.py`; without the same `--payload-bytes-output` sidecar reads and per-tool `payload_files` manifest wiring, implement `slot_kind=voter` rows keep `payload_bytes=0` and acceptance ("every slot kind") fails for the 1.39M implement voter bytes cited in the issue
- **Proposed resolution**: Add `### UPDATED: python/larch/agents/agent_voters.py` (and `python/tests/agents/test_agent_voters.py`) mirroring the plan-review voter path: render with payload sidecar, build `payload_files` parallel to `prompt_files`, and pass selected counts through `build_panel_dispatch_env` / waterfall rows

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/coder_runner.py:356-365
- **Concern**: Implementer payload counts path-referenced findings despite the plan's own payload rule. Scenario: The Approach defines payload as inlined or intentionally attached content; `_compose_coder_prompt` only path-references `accepted-findings.scrubbed.md` via `Read {findings_file}`; counting that file's raw bytes can exceed `prompt_bytes`, force scaffold to clamp at zero, and erase implementer scaffold signal the issue needs for density ranking
- **Proposed resolution**: Set implementer `payload_bytes` to zero (or count only bytes actually written into `coder-prompt.md`), and drop the edge-case allowance for payload larger than prompt bytes on this path

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/rendering/rendering.py:1112-1148
- **Concern**: render voter payload helpers omit inlined calibration feedback. Scenario: When `--calibration-stats-file` is set (both `plan_review_panel.py` and `agent_voters.py` pass it per tool), `_voter_calibration_feedback_block` inlines per-run text into the voter prompt; omitting those bytes understates payload and overstates scaffold for voter rows whenever calibration feedback is enabled
- **Proposed resolution**: Extend voter payload accounting to add raw bytes from the non-empty calibration feedback block produced by `_voter_calibration_feedback_block`

### FINDING_5:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/rendering/rendering.py:759-768; python/larch/review/findings_ledger.py:147-170
- **Concern**: The plan counts raw ledger-file bytes, but the prompt renderer may include only a truncated ledger section. Scenario: When findings-ledger.tsv exceeds the prompt cap, prompt_section() renders only recent rows, but the proposed payload count uses the whole file; payload_bytes can exceed the rendered prompt and clamp scaffold_bytes to zero, hiding real scaffold in later-round specialist, voter, or plan-review rows
- **Proposed resolution**: Count the bytes of the actual ledger_section string inserted into the prompt, or expose the rendered ledger rows from findings_ledger and count only those bytes

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/agents/agent_voters.py:220-306
- **Concern**: Code-review voter dispatch is still missing from the plan. Scenario: The plan adds per-tool `payload_files` wiring for design voters in `plan_review_panel.py`, but `/implement` Step 5 and standalone `/review` voters are pre-rendered and dispatched only through `agent_voters.py` (`review_core_body.py` → `agent dispatch-voters`). That path still calls `render voter` without a payload sidecar, writes `code-voter-slots.ndjson` with only `prompt_files`, and builds `panel_env` without payload metadata, so `slot_kind=voter` rows will keep `payload_bytes=0` and scaffold will stay inflated for a major panel tier.
- **Proposed resolution**: Add `### UPDATED: python/larch/agents/agent_voters.py` mirroring the plan-review voter work: pass `--payload-bytes-output` from `_make_voter_prompt_file`, accumulate per-tool counts in `_build_voter_prompt_files`, emit a `payload_files` map in `_write_voter_waterfall_manifest`, and thread the selected tool's bytes through `build_panel_dispatch_env`. Add matching coverage in `python/tests/agents/test_agent_voters.py`.

### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/coder_runner.py:365-366
- **Concern**: The implementer payload rule contradicts the plan's own inlined-vs-path-referenced contract. Scenario: The plan's core rule counts only inlined or attached prompt content as `payload_bytes`, and the voter renderer explicitly excludes path-referenced ballots. `coder_runner._compose_coder_prompt()` only path-references findings via `Read {findings_file}`; it does not inline the scrubbed file. Recording scrubbed findings-file bytes as implementer payload would overstate payload, clamp scaffold to zero, and erase implementer scaffold signal.
- **Proposed resolution**: Set implementer `payload_bytes=0` (or pass explicit zero through `append_panel_prompt_size` / `build_panel_dispatch_env`). Drop the `coder_runner.py` bullet that counts scrubbed accepted-findings file bytes, and update `test_review_and_fix.py` to assert zero payload with non-zero scaffold for the path-referenced coder prompt.

### FINDING_9:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/findings_ledger.py:151-171; python/larch/rendering/rendering.py:759-774
- **Concern**: Ledger payload accounting targets the raw ledger file instead of the rendered ledger section. Scenario: When findings-ledger.tsv exceeds the prompt budget, prompt_section() inlines only truncated rows. Counting the whole raw file records bytes that never entered the prompt, can force scaffold_bytes to zero, and corrupts scaffold rankings for later rounds.
- **Proposed resolution**: Count the exact rendered ledger section bytes, or the exact truncated rows that prompt_section() emits, not the full ledger file size.

### FINDING_10:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/review_aggregate.py:320-380; python/larch/review/review_aggregate.py:861-877
- **Concern**: Aggregator payload accounting omits the generated reviewer-slot inventory. Scenario: The aggregator prompt adds a per-run Required reviewer slots section derived from source_text, but the plan only counts raw findings, scope anchor, and retry feedback. Aggregator rows will still classify this generated per-run content as scaffold.
- **Proposed resolution**: Include the variable inventory payload when computing aggregator payload_bytes, preferably by measuring the rendered per-run inventory fragment alongside source_text and retry feedback.

### FINDING_11:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/findings_ledger.py:146-164
- **Concern**: Ledger payload accounting should not count bytes that prompt_section truncates. Scenario: The plan says to add raw ledger-file bytes whenever a ledger section is emitted, but prompt_section caps the emitted ledger content; large ledgers would mark omitted rows as payload, make payload exceed the rendered prompt, and zero out scaffold ranking for later rounds
- **Proposed resolution**: Count the exact emitted ledger section bytes, or the kept ledger rows after truncation, and add a focused oversized-ledger rendering test
