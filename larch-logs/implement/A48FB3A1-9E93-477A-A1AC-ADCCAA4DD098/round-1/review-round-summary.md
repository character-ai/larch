# Review Round 1

- Mode: `diff`
- 14 accepted, 3 rejected (2 exonerated)

## Accepted Findings

### FINDING_1: Redundant DISPATCH_OK/WARN prose in design skill
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Prose around `skills/design/SKILL.md` (lines cited ~592–594) repeats that `DISPATCH_OK` is parsed right after a loop that already documents parsing `DISPATCH_OK` and `WARN`. Skimmers may miss that `WARN` handling is the non-obvious half; merge the short paragraphs and keep `DISPATCH_OK=false` and `WARN` guidance once.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_10: Harness covers missing paths-file but not unreadable paths-file
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: In `scripts/test-collect-agent-results.sh` (~554–562), the scenario title implies missing or unreadable paths-file but only exercises missing file; plan acceptance (item 9) expects an unreadable existing paths-file to exit 1 with a “paths-file not readable” style diagnostic—a future regression in `-r` checks could ship untested. Add a `chmod a-r` subcase on a real temp file, assert exit 1 and stderr, restore permissions in cleanup (e.g. trap).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a chmod a-r (restore in trap) subcase asserting exit 1 and the unreadable stderr token.


### FINDING_11: No isolated CR fixture for manifest path newlines
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: In `scripts/test-dispatch-with-waterfall.sh` (~257–271), newline-only regression coverage for CR or LF in output paths lacks an isolated CR fixture; a partial regression that drops carriage-return handling while keeping newline rejection could pass CI. Add a `jq`-built manifest embedding only a literal CR and assert exit 2 with the newline or carriage return diagnostic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_12: Plan-voter tests under-assert `VOTER_PATHS_FILE` on retry and failed-voter paths
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: `scripts/test-dispatch-plan-voters.sh` scenarios (~157–171 and related retry / substantive-failure blocks per testing review; plan-fidelity cites ~167–171 for Plan item 13) do not adequately assert `VOTER_PATHS_FILE` path, line counts, contents, or omission of failed voter paths—e.g. when one voter is narrative-only and marked failed, CI may not pin one-line `plan-voter-paths.txt` for the surviving voter. Wrong or empty plan-voter paths-file under retry or substantive-failure wiring could pass undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Assert VOTER_PATHS_FILE path exists expected wc -l and that failed voter paths are omitted
  - From cursor-specialist-plan-fidelity-output.txt: Add assertions on VOTER_PATHS_FILE path, file non-empty, and exactly one line matching the surviving voter path


### FINDING_14: `mkdir -p` on `--paths-file` parent can materialize surprising directories
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: In `scripts/dispatch-with-waterfall.sh` (~351–353), `mkdir -p` on the dirname of caller `--paths-file` creates arbitrary intermediate directories when a caller or compromised wrapper passes a novel prefix—surprising side effect for a dispatcher flag. Require an existing parent dir or constrain paths-file location relative to slots/tmpdir before `mkdir -p`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_16: Empty `VOTER_PATHS_FILE` / zero-byte manifest semantics for downstream callers
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: In `dispatch-plan-voters.sh` (~235–247), `VOTER_PATHS_FILE` is always emitted even when no voter paths are written, so `plan-voter-paths.txt` can be zero bytes; a future caller feeding that file to `collect-agent-results --paths-file` gets “paths-file contains no entries” without surfacing that both voters failed. Document empty manifest behavior in `dispatch-plan-voters.md`, omit the KV when zero paths, or fail closed with a dedicated message.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_17: Paths-file gate: directory can pass `-r` then yield misleading “no entries”
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: In `collect-agent-results.sh` (~228–241), the paths-file gate uses `-r` only, so a directory can pass then fail as empty entries with misleading “paths-file contains no entries” when the argument is a directory rather than a flat file. Add a regular-file check or a distinct not-a-regular-file error before the read loop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_19: Multi-slot paths-file order/count not pinned in waterfall tests
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: In `scripts/test-dispatch-with-waterfall.sh` (~73–152), Plan item 11: existing two-slot dispatch tests do not assert `.output-files` line count/order or `ALL_OUTPUT_FILES_PATH`, so ordering bugs vs manifest slots could slip past CI. After multi-slot dispatches, assert default paths-file path, two lines in slot order matching known final outputs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---

**Merge notes (for voters, not separate findings):**  
- Input **FINDING_11** and **FINDING_12** merged into **FINDING_10** (same file, slot, and behavioral gap: unreadable paths-file untested).  
- Input **FINDING_14** and **FINDING_22** merged into **FINDING_12** (same test surface and risk: `VOTER_PATHS_FILE` / degraded panel regressions); distinct verbatim bullets preserved.  
- Input **FINDING_7**, **FINDING_10**, and **FINDING_21** merged into **FINDING_7** with **`[OUT_OF_SCOPE]`** retained on the heading; identical generic “Address…” bullets from structure and edge-cases combined per your literal-identical rule.  
- **FINDING_6** (collector CR/LF) vs **FINDING_11** (dispatch test CR fixture): different code paths and fixes—kept separate.  
- **FINDING_8** (KV emission vs I/O ordering) vs **FINDING_14** (`mkdir -p` side effect): same script region but different failure modes and fixes—kept separate.

There are one or more `### FINDING_N:` blocks above, so **`LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` must not appear** in this output.

### FINDING_2: `$_manifest.output-files` referenced before assignment in plan-review doc
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: In `skills/design/references/plan-review.md` (~75–79), prose references `$_manifest.output-files` before the fenced block assigns `_manifest`, so top-down readers see an undefined shell variable. Use a concrete path in prose or explicitly forward-reference the assignment in the fence below.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_3: `usage()` omits `--paths-file` and default manifest path
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: In `scripts/dispatch-with-waterfall.sh` (~11–13), `usage()` omits the new `--paths-file` flag and default paths-file location while argparse implements them; `--help` users only learn from source or sibling docs. Extend `usage()` to mention `--paths-file`, the default `SLOTS_FILE.output-files` path, and `ALL_OUTPUT_FILES_PATH` emission.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_4: Callers doc omits `--paths-file` handoff for plan-review
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: In `scripts/collect-agent-results.md` (~31–41), the wired bullet for `plan-review.md` does not mention the new `--paths-file` cross-subshell handoff; readers may think plan-review still relies only on positional path lists. Add a clause tying plan-review Step 3 to `--paths-file` and the line-oriented manifest.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_6: Paths-file ingestion does not reject embedded CR/LF (collector vs dispatcher)
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: In `scripts/collect-agent-results.sh` (~223–236), paths-file ingestion does not reject CR/LF inside lines unlike dispatcher-side validation; malicious or hand-edited lines can diverge from dispatcher guarantees. Add optional CR/LF rejection per line or tighten the documented trust boundary with a fail-closed guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_8: Paths-file I/O before `emit_kv` can drop stdout contract on failure
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: In `scripts/dispatch-with-waterfall.sh` (~351–377), paths-file materialization runs before `emit_kv` under `set -e`; I/O failure (e.g. disk quota / `ENOSPC` on `mkdir`/`mktemp`/`mv` after reviewers finish) can exit before emitting stdout KVs, so the orchestrator loses `DISPATCH_OK` / `WARN` / `ALL_OUTPUT_FILES_PATH` despite existing outputs. Emit KVs before the paths-file write, or contain paths-file I/O in a failure-tolerant branch that still emits contract lines; document partial-failure semantics for `ALL_OUTPUT_FILES_PATH`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_9: NEVER #4 “Why” underspecifies `--paths-file` exit reasons
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: In `skills/design/SKILL.md` (cited ~7107), NEVER #4 “Why” text underspecifies `collect-agent-results` exit reasons for `--paths-file`, so orchestrators misread which guardrail fired when comparing stderr vs skill prose. Expand “Why” to cover unreadable paths-file vs empty entries vs missing positionals.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


