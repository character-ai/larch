### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step-architectural-guidelines-materialize.sh:85-89
- **Concern**: Retired materialize wrapper/docs lack explicit delete steps unlike read.sh. Scenario: The plan deletes `step-architectural-guidelines-read.sh` and `step-architectural-guidelines-read.md` but leaves `### UPDATED:` entries for `step-architectural-guidelines-materialize.sh` and `.md` empty. An implementer can ship the prepare fold while the old materialize wrapper remains on disk and still listed in sibling-contract prose, breaking the stated retirement goal and leaving two Phase A materialization entrypoints.
- **Proposed resolution**: Mirror the read retirement bullets: delete `skills/implement/scripts/step-architectural-guidelines-materialize.sh` and `step-architectural-guidelines-materialize.md` with an explicit no-shim note.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/scripts/step-architectural-guidelines-prepare.md:71-72
- **Concern**: prepare.md overclaims write-staged and durable-pin ownership. Scenario: The planned sibling doc says Python owns staged assessment writes and durable pinning, but `prepare` only invalidates, reads guidelines, and materializes the diff. `write-staged-assessment` and `pin-note-from-staged` stay separate fences with prompt-side judgment between materialize and write-staged, which the issue scope requires. Misdocumented ownership can fold those steps into prepare or drop the write-staged fence.
- **Proposed resolution**: Limit prepare.md ownership to invalidation, parsing, path checks, and diff snapshot metadata emission. Point staged writes and durable pinning to `step-architectural-guidelines-write-staged.md` and `step-architectural-guidelines-pin-from-staged.md`.



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/architectural_guidelines.py:18-23
- **Concern**: [SCOPE-REDUCTION] prepare parses unused --output. Scenario: `prepare_main` is specified to parse `--output`, but the plan never wires it into the combined emit/write path (only `materialize-diff` documents that behavior). The /implement wrapper does not pass `--output`, so the new verb would advertise a dead flag and any direct caller relying on it would silently get no file.
- **Proposed resolution**: Drop `--output` from `prepare_main` unless the plan explicitly delegates to the same shared materialization helper path that honors `--output`; keep `--output` only on the retained `materialize-diff` verb.



### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/architectural_guidelines.py:18-35
- **Concern**: prepare_main parses `--output` but the plan never says to honor it.. Scenario: A caller can invoke the new `prepare` verb with `--output` and get a silent success with no file written, which breaks the command contract and leaves the combined verb incomplete.
- **Proposed resolution**: Either carry the existing materialize-diff file-write path into `prepare_main` or drop `--output` from the new verb, its wrapper, and its tests.



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:85-89
- **Concern**: Materialize wrapper retirement steps are blank while read retirement is explicit. Scenario: The plan tells implementers to delete `step-architectural-guidelines-read.sh` and `step-architectural-guidelines-read.md`, but the `### UPDATED:` sections for `step-architectural-guidelines-materialize.sh` and `.md` are empty. `residual-bash-paths.txt` removal alone is easy to miss; stale materialize wrappers can remain callable and defeat the one-fence fold.
- **Proposed resolution**: Mirror the read retirement bullets: delete `skills/implement/scripts/step-architectural-guidelines-materialize.sh` and `step-architectural-guidelines-materialize.md` with no shim, and list both paths wherever read deletions are enumerated.



### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/scripts/step-architectural-guidelines-prepare.md:72
- **Concern**: prepare.md overclaims write-staged and durable-pin ownership. Scenario: The NEW prepare sibling doc is told to state that Python owns staged assessment writes and durable pinning. `prepare_main` only invalidates, reads, and materializes; `write-staged-assessment` and `pin-note-from-staged` stay separate fences per the issue boundary. This repeats round-1 FINDING_3 and can cause an implementer to fold judgment steps into prepare.
- **Proposed resolution**: Limit prepare.md ownership to invalidation, guideline parsing, diff snapshot metadata, and stdout KVs. Point write-staged and pin-from-staged ownership at their existing wrappers and SKILL prose only.



### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:18-35
- **Concern**: prepare_main parses `--output` but never says to honor it. Scenario: Direct callers of the new `architectural-guidelines prepare` verb would accept `--output` and then silently skip writing the diff file, which makes that advertised write path dead and breaks parity with the existing `materialize-diff` contract.
- **Proposed resolution**: Explicitly write `diff_text` to `--output` the same way `materialize_diff_main` does, or remove `--output` from `prepare_main` if the new verb should not support it.



### FINDING_8:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/cli.py:567-679
- **Concern**: The plan adds `architectural-guidelines prepare` to the registry, but it never restores the existing `architectural-guidelines materialize-diff` entry in `_MACHINE_STDOUT_KEYS`.. Scenario: `python/test_design_cli_ports.py` still asserts that every `architectural-guidelines` verb is a machine-stdout surface, so the updated port-coverage test will fail on the preserved `materialize-diff` verb.
- **Proposed resolution**: Add `("architectural-guidelines", "materialize-diff")` to `_MACHINE_STDOUT_KEYS` in the same change, or explicitly drop that verb from the machine-stdout contract if it is no longer intended to be one.



