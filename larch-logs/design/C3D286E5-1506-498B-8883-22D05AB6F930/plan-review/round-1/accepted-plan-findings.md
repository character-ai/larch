### FINDING_2: primary stderr-sink test cannot prove run-external-agent received the flag
- **Reviewer(s)**: Cursor-Edge, Codex-Edge, Cursor-Innovation, Cursor-Pragmatic, Codex-dyn-harness-realism, Cursor-dyn-doc-sync
- **Severity**: important
- **Concern**: The proposed primary-path runtime checks target leaf Codex/Cursor argv logs or outer `.meta` records, but `--stderr-sink` is consumed at the `run-external-agent.sh` boundary. Those checks can either fail despite correct forwarding or pass from launcher metadata without proving `_RUN_EXTERNAL_SINK_ARGS` reached the wrapper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Keep run-external-agent real; assert STDERR_SINK= appears before OUTER_LAUNCHER= in the primary .meta (run-external writes base meta before append_outer_meta) or add a test-only run-external-agent wrapper on PATH that logs argv
  - From Codex-Edge: Keep real launcher/helper paths and assert observable artifacts instead: for launch-review count exact STDERR_SINK records in OUTPUT.meta; for collector CMD_JSON assert retry-output.meta contains STDERR_SINK; for outer retry use canonical scripts/launch-review.sh with existing CLI stubs and assert the retry meta shows both wrapper and outer records
  - From Cursor-Innovation: Assert STDERR_SINK= appears before the first OUTER_LAUNCHER= line in ${OUTPUT}.meta (run-external block precedes append_outer_meta); mirror for cursor lane without adding a cursor argv logger unless needed
  - From Cursor-Pragmatic: Record argv at the `run-external-agent.sh` boundary (minimal `$STUB_BIN/run-external-agent.sh` wrapper that logs `"$@"` then `exec`s the real script) and assert `--stderr-sink` plus the sink path appear before `--`; keep the existing outer `.meta` assertion as a second check
  - From Codex-dyn-harness-realism: Assert an artifact only run-external-agent.sh can write, such as STDERR_SINK appearing in the pre-CMD_JSON metadata block for the same run, while keeping the outer metadata check separate.
  - From Cursor-dyn-doc-sync: Prefer asserting the sink file receives wrapper stderr after `--stderr-sink`, or add a dedicated `run-external-agent` argv log stub; for cursor, follow case AK1 `CURSOR_STUB_ARGV_LOG` only if testing leaf argv—otherwise mirror the sink-file or wrapper-stub approach (`scripts/test-run-external-agent.sh` ~465-497)


### FINDING_3: collector outer-retry test uses an OUTER_LAUNCHER stub that validation rejects
- **Reviewer(s)**: Codex-Edge, Codex-Innovation, Codex-Pragmatic, Codex-Requirements, Codex-dyn-meta-contract, Cursor-dyn-meta-contract, Codex-dyn-harness-realism
- **Severity**: important
- **Concern**: The proposed collector outer-retry runtime test points `OUTER_LAUNCHER` at an argv-recording stub, but collector validation only accepts the canonical real `scripts/launch-review.sh`, so the test fails before exercising stderr-sink forwarding or creates pressure to weaken launcher hardening.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Keep real launcher/helper paths and assert observable artifacts instead: for launch-review count exact STDERR_SINK records in OUTPUT.meta; for collector CMD_JSON assert retry-output.meta contains STDERR_SINK; for outer retry use canonical scripts/launch-review.sh with existing CLI stubs and assert the retry meta shows both wrapper and outer records
  - From Codex-Innovation: Keep OUTER_LAUNCHER as the canonical scripts/launch-review.sh path and assert forwarding through downstream artifacts such as the retry .meta STDERR_SINK line or an inner argv/sink observable produced by the real launcher
  - From Codex-Pragmatic: Keep OUTER_LAUNCHER as the real canonical scripts/launch-review.sh and keep real scripts/run-external-agent.sh. Use existing cursor/codex leaf stubs, then assert the retry .meta carries STDERR_SINK=<sink> or inspect leaf argv. Do not loosen collector validation.
  - From Codex-Requirements: Keep OUTER_LAUNCHER pointed at scripts/launch-review.sh, stub only the leaf CLI via PATH, and assert forwarding by inspecting the retry output meta for STDERR_SINK=$sink or another real run-external-agent artifact. For CMD_JSON, keep the real scripts/run-external-agent.sh path and assert its retry .meta records STDERR_SINK.
  - From Codex-dyn-meta-contract: Keep OUTER_LAUNCHER pointed at scripts/launch-review.sh, stub only the leaf CLI via PATH, and assert forwarding by inspecting the retry output meta for STDERR_SINK=$sink or another real run-external-agent artifact. For CMD_JSON, keep the real scripts/run-external-agent.sh path and assert its retry .meta records STDERR_SINK.
  - From Cursor-dyn-meta-contract: Keep OUTER_LAUNCHER=$REPO_ROOT/scripts/launch-review.sh (mirror case Q). Assert forwarding via retry artifact: STDERR_SINK= on ${retry_output}.meta and/or --stderr-sink on run-external-agent (extend HELPER logging only for CMD_JSON path).
  - From Codex-dyn-harness-realism: Keep OUTER_LAUNCHER as the real canonical launch-review.sh, stub only the leaf CLI through PATH, then assert the retry .meta shows run-external-owned STDERR_SINK before CMD_JSON.


### FINDING_4: CMD_JSON retry test uses an invalid run-external-agent command shape
- **Reviewer(s)**: Codex-Pragmatic, Codex-Requirements, Codex-dyn-meta-contract, Codex-dyn-harness-realism
- **Severity**: important
- **Concern**: The proposed CMD_JSON retry test treats CMD_JSON as a way to invoke a `run-external-agent.sh` stub, but CMD_JSON is validated as the inner vendor command and must match the allowed Codex/Cursor argv shape. A run-external-agent CMD_JSON is rejected or tests the wrong path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Keep OUTER_LAUNCHER as the real canonical scripts/launch-review.sh and keep real scripts/run-external-agent.sh. Use existing cursor/codex leaf stubs, then assert the retry .meta carries STDERR_SINK=<sink> or inspect leaf argv. Do not loosen collector validation.
  - From Codex-Requirements: Keep OUTER_LAUNCHER pointed at scripts/launch-review.sh, stub only the leaf CLI via PATH, and assert forwarding by inspecting the retry output meta for STDERR_SINK=$sink or another real run-external-agent artifact. For CMD_JSON, keep the real scripts/run-external-agent.sh path and assert its retry .meta records STDERR_SINK.
  - From Codex-dyn-meta-contract: Keep OUTER_LAUNCHER pointed at scripts/launch-review.sh, stub only the leaf CLI via PATH, and assert forwarding by inspecting the retry output meta for STDERR_SINK=$sink or another real run-external-agent artifact. For CMD_JSON, keep the real scripts/run-external-agent.sh path and assert its retry .meta records STDERR_SINK.
  - From Codex-dyn-harness-realism: Use a valid cursor or codex CMD_JSON fixture and assert the generated retry .meta contains the wrapper-owned STDERR_SINK entry.


