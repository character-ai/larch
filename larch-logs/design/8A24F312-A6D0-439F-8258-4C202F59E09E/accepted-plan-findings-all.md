### FINDING_2: Voter payload metadata needs per-tool manifest wiring
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements, Cursor-dyn-Telemetry Contract
- **Severity**: important
- **Concern**: A single slot-level `payload_bytes` cannot represent `prompt_files` voter rows that choose different prompt bodies per tool, and the hand-built plan-review voter manifest also appends raw JSON with only `prompt_files`; fallback launches can therefore record the wrong payload or zero payload for the tool that actually ran.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an optional `payload_files` map (parallel to `prompt_files`), parse it in `_parse_slot_row`, and in `_launch_slot` select the active tool's payload the same way `_prompt_file_for_tool` selects the prompt file; thread that value into `build_panel_dispatch_env` / `LARCH_PANEL_PAYLOAD_BYTES`.
  - From Cursor-Innovation: Add a per-tool map (e.g. `payload_files` parallel to `prompt_files`) parsed in `_parse_slot_row`, and in `_launch_slot` set `LARCH_PANEL_PAYLOAD_BYTES` from the selected tool’s entry after `_prompt_file_for_tool()`. Update hand-built voter manifest writes in `plan_review_panel.py` and `agent_voters.py`, not only `_slot_row()`.
  - From Cursor-Innovation: When building `manifest_lines`, include the per-tool payload map alongside `prompt_maps_by_slot`, and add tests in `test_plan_review_panel.py` that assert manifest + TSV values for waterfall voter launches.
  - From Cursor-Requirements: Extend the manifest and Slot parsing with an optional `payload_files` map keyed like `prompt_files` (or equivalent per-tool lookup); in _launch_slot set `LARCH_PANEL_PAYLOAD_BYTES` from the prompt file chosen for the active tool, and have plan_review_panel/agent_voters populate that map when writing voter NDJSON.
  - From Cursor-dyn-Telemetry Contract: Extend Slot/manifest with an optional `prompt_files_payload` map parallel to `prompt_files`; select payload in _launch_slot by active tool; update plan_review_panel.py:1027-1039 and agent_voters.py manifest writers accordingly


### FINDING_4: Payload sidecar reads can reuse stale data after a failed write
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: A best-effort sidecar write failure can leave a previous file at the same path, so a later render that fails to rewrite the sidecar can be measured with stale payload bytes from an earlier render.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Before each render, unlink or use a unique fresh sidecar path. Read payload bytes only from the sidecar written by the current successful render; otherwise pass 0.


### FINDING_5: Retry aggregation needs fresh payload env per attempt
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The retry loop builds `panel_env` once and reuses it across attempts even after the prompt body changes, so later retries can inherit stale payload bytes and under-report payload while over-reporting scaffold.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Inside the retry loop, after composing `prompt_file` text, recompute payload bytes, rewrite `aggregator-slots.ndjson`, and rebuild `panel_env` with `payload_bytes=` before each dispatch.


### FINDING_6: Generated per-run prompt content is still being counted as scaffold
- **Reviewer(s)**: Codex-Innovation, Cursor-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: Ledger sections and dynamic scout bodies are generated per run, but the current payload accounting misses those bytes, so later rounds and dynamic slots overstate scaffold bytes and understate payload bytes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add minimal payload accounting for the ledger rows actually emitted by _code_ledger_section and _plan_ledger_section, and for dynamic scout rationale/prompt_body when _synthesize_dynamic_slots() pre-renders dynamic specialist prompt files.
  - From Cursor-Pragmatic: Extend the rendering payload accounting helpers to add raw ledger file bytes when the rendered prompt includes a non-empty ledger section; cover round-2 specialist and voter cases in python/tests/rendering/test_rendering.py.
  - From Codex-Requirements: Count the dynamic scout rationale and prompt_body bytes in _synthesize_dynamic_slots or pass them through an explicit renderer payload input, then include that value in each dynamic manifest row's payload_bytes.


### FINDING_7: build_panel_dispatch_env should clear inherited payload state
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: Starting from `os.environ` without clearing `LARCH_PANEL_PAYLOAD_BYTES` can leak a previous slot's payload into later fallback or failure paths, so an unknown-payload render can be recorded as if it inherited the prior slot's bytes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Revise the plan to clear LARCH_PANEL_PAYLOAD_BYTES in build_panel_dispatch_env before optionally setting it, and pass explicit 0 for known fallback paths.


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


