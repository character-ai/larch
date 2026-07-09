### FINDING_1: Pin the full session-key and cwd fallback chain
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-Hook Toctou Security
- **Severity**: major
- **Concern**: The Python helper must preserve the existing session-key ladder and empty-cwd default so no-session reads keep the same counter partitioning as the Bash hook; otherwise unrelated invocations can collapse into one bucket or split incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin the chain in the NEW module spec: session_id, else conversation_id, else nosession-${HOOK_ANTI_READ_POLL_DISCRIMINATOR} when set, else nosession; hash that key for the filename component
  - From Codex-Arch: Keep the existing chain: default empty `cwd` to `/`, prefer `session_id`, then `conversation_id`, then `nosession-${HOOK_ANTI_READ_POLL_DISCRIMINATOR}`, then `nosession`; add a unit test for the no-session path
  - From Cursor-Innovation: Add explicit preserve bullets and unit tests for the full chain and cwd default before hashlib filename components.
  - From Codex-Innovation: Keep the existing fallback chain and `cwd:-/` default in the helper. Only fail open for malformed JSON or unsafe paths, not for absent session metadata.
  - From Cursor-Pragmatic: Document and implement the exact chain session_id then conversation_id then nosession-${HOOK_ANTI_READ_POLL_DISCRIMINATOR} then nosession; add unit tests for conversation_id-only payloads and discriminator-split nosession keys
  - From Cursor-Pragmatic: Specify cwd default ${cwd:-/} and the same session-key inputs in the filename helper; add one unit test for empty cwd
  - From Cursor-Requirements: Add an explicit session_key helper contract in hook_anti_read_poll.py and unit tests for conversation_id and HOOK_ANTI_READ_POLL_DISCRIMINATOR fallbacks
  - From Codex-Requirements: Carry the existing fallback chain into the new helper and cover it in the shell and unit tests.
  - From Cursor-dyn-Hook Toctou Security: Spell out the exact session_key chain in the plan and tests: session_id, else conversation_id, else nosession-${HOOK_ANTI_READ_POLL_DISCRIMINATOR}, else nosession; hash that key with cwd_hash for the state filename.


### FINDING_2: Preserve the hashed state-row contract
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: major
- **Concern**: The on-disk state contract must keep the hashed basename and a tab-separated hashed-path row; otherwise the helper can leak raw file paths or drift from the shipped state layout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Keep filenames read-${cwd_hash}-${session_hash}.state; persist tab-separated path_hash offset count epoch where path_hash is a digest of file_path, never the raw path
  - From Cursor-Requirements: Writing raw paths into state files breaks the SECURITY.md posture that read metadata is untrusted local state Pin row format as path_hash, offset, count, epoch with path_hash derived from tool_input.file_path; fail open on empty file_path


### FINDING_4: Preserve the wrapper ingress contract
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: major
- **Concern**: The wrapper must forward hook JSON unchanged and short-circuit non-Read invocations before any filesystem or hashing work; otherwise Bash calls can consume stdin, do unnecessary state work, or silently disable reminders.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Specify that the wrapper forwards the hook JSON to Python unchanged (inherit stdin or explicit pipe) and must not consume stdin before the cli.py invocation
  - From Cursor-Innovation: A mandate parse tool_name first; on non-Read return exit 0 before any filesystem or hashing work; add a unit test that Bash stdin performs zero state_dir opens.


### FINDING_5: Lock down the PostToolUse reminder envelope and keep its context path-free
- **Reviewer(s)**: Codex-Arch, Cursor-Requirements
- **Severity**: major
- **Concern**: The reminder output must be exact: emit only the PostToolUse JSON envelope at the third read, and keep `additionalContext` fixed so it never echoes a requested path or basename.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add one unit test that parses the emitted JSON and asserts the reminder text is fixed and does not contain the requested path or basename
  - From Cursor-Requirements: Wrong JSON shape is ignored or treated as hook failure even though the helper exits 0 Document and test stdout as exactly {"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"<fixed reminder text>"}} only when count equals 3; otherwise print nothing


### FINDING_1:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/core/hook_anti_read_poll.py:77
- **Concern**: Prior fallback fix is incomplete: discriminator must be non-empty, not merely set. Scenario: Current Bash uses `${HOOK_ANTI_READ_POLL_DISCRIMINATOR:-}` with `-n`; an exported empty discriminator still falls back to `nosession`. The plan says "is set", which can change that bucket to `nosession-` and regress shipped partitioning.
- **Proposed resolution**: Pin `session_key` to use `HOOK_ANTI_READ_POLL_DISCRIMINATOR` only when its value is non-empty, and cover the empty-string env case where the ladder is tested.


