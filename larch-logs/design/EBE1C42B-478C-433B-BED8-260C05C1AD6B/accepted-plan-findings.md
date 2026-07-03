### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_core.py:169-177
- **Concern**: Plan mandates CLONE_PATH on every marker writer but does not pin how writers obtain that value. Scenario: Shell writers use ad hoc printf redirects and Python writers use separate helpers. If one stamps pwd from a non-repo cwd while .larch-keepalive holds the bootstrap clone root, marker_foreign_clone prefers the embedded value, can classify the session's own live marker as foreign, drop it from live_dirs_file, and fail to deny Monitor/TaskOutput/progress Bash during an active wait.
- **Proposed resolution**: Pin one stamp contract in the plan: copy CLONE_PATH from the sibling tmpdir .larch-keepalive at write time (Python: reuse existing keepalive readers such as _read_keepalive_clone_path). Document that rule in hook docs and marker writer sibling .md files.




