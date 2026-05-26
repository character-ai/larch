### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:57-58; scripts/test-launch-claude-review.sh
- **Concern**: Dedup test targets claude argv, not launcher→subprocess forwarding. Scenario: launch-claude-review.sh invokes launch-claude-subprocess.sh by absolute path; subprocess embeds context into PROMPT_RENDERED and calls claude with only --model/--print on stdin, so grepping a stub claude "$@" log cannot observe --context-files dedup
- **Proposed resolution**: Count <context_file_N> markers in stub stdin (or add a test-only subprocess argv capture hook) and assert exactly one block when --diff-file and --context-files reference the same path


### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/launch-claude-review.sh:95-103
- **Concern**: Plan expects an outside-root explicit context file to be rejected, but the proposed reuse of append_context_file also adds that file's directory as --allow-root. Scenario: The new containment-propagation test will fail because launch-claude-subprocess.sh will see the explicit context directory in EXTRA_ROOTS and accept the file; the documented claim that subprocess containment remains authoritative is misleading for this launcher path
- **Proposed resolution**: Choose one contract: either explicit --context-files authorizes its parent directory and the outside-root rejection test/doc should be removed, or split helper behavior so explicit files are forwarded without auto-adding --allow-root when containment is meant to reject them


### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-claude-review.sh:30-48
- **Concern**: Proposed --context-files parser uses ${2:?--context-files requires a value} but the plan's test expects exit 2 for a trailing flag. Scenario: Bash exits with status 1 on that parameter-expansion error before the script can emit its normal validation exit; the planned missing-value test will fail even though stderr contains the message
- **Proposed resolution**: Add an explicit arity check for --context-files, for example [[ $# -ge 2 && "$2" != --* ]] || { larch_err "launch-claude-review.sh: --context-files requires a value"; exit 2; }, then append and shift


### FINDING_4:
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-claude-review.sh:112-118
- **Concern**: The proposed dedup test says to verify duplicate forwarding by wrapping the claude stub argv, but claude never receives --context-files. Scenario: launch-claude-review.sh invokes launch-claude-subprocess.sh by absolute path, and the subprocess consumes --context-files before calling claude --model ... --print, so $TMPROOT/claude-argv.log cannot prove the launcher forwarded one context file
- **Proposed resolution**: Validate dedup by making the claude stub inspect stdin and count rendered <context_file_...> sections, or add a deliberate test-only subprocess override/injection point and document it before using it in the harness


### FINDING_6:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:57-58
- **Concern**: Test case 6 expects subprocess outside-roots rejection for explicit --context-files. Scenario: Every path that passes strict=1 append_context_file also gets --allow-root for dirname(path); subprocess accepts via EXTRA_ROOTS so exit 0 and no outside-roots stderr
- **Proposed resolution**: Replace with a positive containment test (extra-root context succeeds through launch-claude-review) or drop case 6; negative outside-roots is already covered in test-launch-claude-subprocess.sh:69-80


### FINDING_7:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-claude-review.sh:29-43
- **Concern**: Proposed --context-files parser uses ${2:?...} but the planned missing-value test expects exit 2. Scenario: Trailing --context-files triggers Bash parameter-expansion failure with status 1 and shell-formatted stderr, so the launcher violates its validation-exit contract and the new test case fails
- **Proposed resolution**: Add explicit arity validation before reading $2, emit larch_err, and exit 2 for --context-files


### FINDING_8:
- **Reviewer(s)**: Codex-Edge, Codex-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/launch-claude-review.sh:95-108
- **Concern**: Proposed containment test conflicts with proposed allow-root plumbing. Scenario: The same helper used for explicit context files also appends the file directory as --allow-root, so the subprocess will accept the outside path instead of producing context file outside allowed roots
- **Proposed resolution**: Decide the contract: either explicit paths expand allow-roots and the test/docs should assert success, or explicit paths must not add --allow-root and the helper needs a parameter to enforce that


### FINDING_9:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-launch-claude-review.sh:12-16; scripts/launch-claude-subprocess.sh:147-165
- **Concern**: Dedup test cannot observe forwarded --context-files by capturing claude argv. Scenario: The subprocess invokes claude only as claude --model ... --print and injects context through stdin, so grepping claude argv for --context-files will always be wrong
- **Proposed resolution**: Capture the stub claude stdin and count context_file blocks or file content occurrences, or add a deliberate subprocess-argv test seam


### FINDING_11:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/launch-claude-review.sh:95-108; scripts/launch-claude-subprocess.sh:117-121
- **Concern**: Strict validation checks -f but not readability despite the unreadable error contract. Scenario: An explicit chmod 000 file passes launcher validation, then the subprocess can fail inside wc or cat under set -e with status 1 and a shell error instead of the planned exit 2
- **Proposed resolution**: Add -r checks in strict launcher validation and preferably in canonical_existing_file before wc/cat; add an unreadable explicit-context regression test


### FINDING_12:
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-launch-claude-review.sh:57-58
- **Concern**: Dedup test (5) proposes grepping stub claude argv for --context-files. Scenario: launch-claude-review.sh invokes launch-claude-subprocess.sh by absolute path; subprocess consumes --context-files and calls claude with only --model/--print on stdin, so claude-argv.log never contains --context-files and the test false-fails or is vacuous
- **Proposed resolution**: Count <context_file_ tags in captured claude stdin (extend stub to tee stdin to $TMPROOT/claude-stdin.log), or add LARCH_LAUNCH_CLAUDE_SUBPROCESS_OVERRIDE and a logging subprocess stub that records argv


### FINDING_13:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-claude-review.sh:30-48
- **Concern**: Planned ${2:?--context-files requires a value} does not satisfy the promised exit-2 missing-value contract. Scenario: Trailing --context-files exits from Bash parameter expansion with status 1 before larch_err/exit 2, while --context-files --timeout 5 treats --timeout as the path and reports a confusing later error
- **Proposed resolution**: Use explicit parser validation for this flag, e.g. check ${2+x}, non-empty, and possibly non-flag-like before appending, then larch_err and exit 2


### FINDING_14:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/launch-claude-review.sh:95-108
- **Concern**: Containment test contradicts the proposed allow-root propagation. Scenario: The plan says every accepted context file dir is appended to --allow-root, so an explicit context file outside PLUGIN_ROOT/SESSION_ROOT will be authorized and will not produce context file outside allowed roots
- **Proposed resolution**: Choose the actual security model: either do not auto-add --allow-root for strict=1 explicit files, or update the test/docs to state explicit operator paths are intentionally authorized outside the default roots


### FINDING_15:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/launch-claude-subprocess.sh:134-165
- **Concern**: Dedup test proposes observing --context-files via the claude stub argv, but those args never reach claude. Scenario: launch-claude-subprocess.sh consumes --context-files, renders context into a temp prompt, and invokes claude only as claude --model ... --print, so grep of claude argv cannot prove launcher dedup
- **Proposed resolution**: Have the stub claude persist stdin and assert one context_file block or one diff body occurrence, or add an explicit subprocess override hook in the implementation and test that hook


### FINDING_17:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-launch-claude-review.sh:58
- **Concern**: Containment test expects outside-roots failure for explicit --context-files. Scenario: append_context_file always adds --allow-root for each accepted context path's directory, so a valid explicit file under $TMPROOT is admitted when output also lives under $TMPROOT; case 6 will exit 0 instead of exit 2 with context file outside allowed roots
- **Proposed resolution**: Replace case 6 with a subprocess error the launcher cannot auto-allow (e.g. explicit symlink path → invalid context file, or >1 MB file → context file exceeds 1 MB) while still asserting stderr re-emission via lines 129-134


### FINDING_18:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/test-validate-plan-commands.sh:104-107
- **Concern**: Plan omits validate-plan-commands harness flip. Scenario: After usage() documents --context-files, help_documents_flag will pass and the launch-context-plan.md fixture will stop emitting DEFECT … flag=context-files; make lint / test-harnesses-12 fails on missing DEFECT line
- **Proposed resolution**: Update test-validate-plan-commands.sh and fixtures/validate-plan-commands/launch-context-plan.md to assert the flag is accepted (no unknown-flag DEFECT), or delete the regression case if no longer needed


### FINDING_21:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/test-validate-plan-commands.sh:104-107
- **Concern**: Plan omits an existing regression that currently requires scripts/launch-claude-review.sh --context-files to be reported as unknown. Scenario: After the launcher usage documents --context-files, make lint can fail because this harness still expects DEFECT script=scripts/launch-claude-review.sh kind=unknown-flag flag=context-files
- **Proposed resolution**: Update or remove the obsolete expectation and fixture so the validator asserts --context-files is now accepted


### FINDING_22:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-claude-review.sh:43-44
- **Concern**: Proposed parser arm uses ${2:?...} but the plan requires exit 2 for missing --context-files values. Scenario: Bash parameter-expansion errors exit 1 before larch_err handling, so the proposed missing-value test expecting rc=2 will fail; flag-like next tokens are also consumed as values
- **Proposed resolution**: Use explicit validation before appending, e.g. require $# >= 2, non-empty ${2:-}, and preferably ${2} != --*, then larch_err and exit 2 on failure


### FINDING_23:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/launch-claude-review.sh:95-103
- **Concern**: Strict explicit validation promises unreadable files hard-error with the fixed launcher message but only checks -f. Scenario: A present but unreadable file can pass launcher validation and then fail later inside the subprocess with a less predictable shell/wc/cat failure path
- **Proposed resolution**: Add -r to the strict=1 validation condition before forwarding the file; keep implicit silent-skip behavior scoped to existing callers


### FINDING_24:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-launch-claude-review.sh:57-58
- **Concern**: Case 6 cannot produce context file outside allowed roots. Scenario: `append_context_file()` always adds `--allow-root "$(dirname "$path")"` for every forwarded context file (plan UPDATED section; current scripts/launch-claude-review.sh:99-102). Explicit `--context-files` outside PLUGIN_ROOT/SESSION_ROOT therefore succeeds via widened roots, not exit 2. Additionally `$TMPROOT` is SESSION_ROOT when `--output "$TMPROOT/out.txt"` (scripts/launch-claude-subprocess.sh:94), so files under `$TMPROOT` are already in-bounds.
- **Proposed resolution**: Replace case 6 with a positive allow-root propagation test: context file under a separate mktemp dir, invoke with `--context-files`, assert exit 0. Optionally add a separate stderr-propagation case using an explicit symlink path expecting `invalid context file` (not outside-roots).


### FINDING_25:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-claude-review.sh:30-48
- **Concern**: Missing-value acceptance criterion cannot pass with the planned parser. Scenario: The plan requires trailing --context-files to exit 2, but ${2:?--context-files requires a value} aborts bash with status 1 before launcher validation can normalize the error
- **Proposed resolution**: Add an explicit parser guard for --context-files with [[ $# -ge 2 && "$2" != --* ]] or equivalent larch_err plus exit 2, and keep the missing-value test pinned to exit 2


### FINDING_26:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:57-59
- **Concern**: Security-relevant launcher read surface is not documented. Scenario: The plan exposes an operator-facing --context-files path on launch-claude-review.sh and auto-adds allow roots for those paths, but it modifies only the launcher contract doc and test; AGENTS.md requires SECURITY.md updates for security-relevant behavior changes
- **Proposed resolution**: Add a SECURITY.md update describing launch-claude-review.sh --context-files, strict missing/unreadable handling, dedup, allow-root widening, and subprocess-owned symlink/control-character/size/count validation


### FINDING_27:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-claude-review.sh:95-103
- **Concern**: Unreadable explicit context files are not actually validated. Scenario: The plan documents hard-error on missing/empty/unreadable operator-supplied paths, but the proposed strict check only tests -f and canonical dirname; unreadable regular files can proceed to launch-claude-subprocess.sh and fail later with a different status/message
- **Proposed resolution**: Add a -r check in strict mode, add an unreadable-file harness case where platform permissions permit it, and align the error assertion with the documented missing or unreadable message


### FINDING_28:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-claude-review.sh:95-118
- **Concern**: Containment propagation test conflicts with planned allow-root propagation. Scenario: Test case 6 expects an explicit context file outside PLUGIN_ROOT/SESSION_ROOT to be rejected by the subprocess, but the planned append_context_file path adds that file's directory to --allow-root for every forwarded context file, so the subprocess should accept it
- **Proposed resolution**: Decide the intended contract: either do not add --allow-root for explicit --context-files and keep the outside-root rejection test, or keep allow-root propagation and replace case 6 with a test that validates the propagated allow-root is what permits outside-session explicit context


### FINDING_29:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-launch-claude-review.sh:12-16
- **Concern**: Dedup test cannot observe the contract it claims to assert. Scenario: The plan proposes wrapping the claude stub and counting --context-files in its argv, but launch-claude-subprocess.sh consumes context files while building the rendered prompt and invokes claude only as claude --model ... --print
- **Proposed resolution**: Revise the test to observe the rendered prompt content count, introduce a deliberate launcher subprocess override hook and test that hook, or use a controlled subprocess fixture; do not rely on the final claude argv for --context-files forwarding


### FINDING_31:
- **Reviewer(s)**: Codex-dyn-test-observation-surface
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-claude-review.sh:30-48; <TMPDIR>/plan.txt:55
- **Concern**: Test case 3's asserted missing-value behavior does not match the proposed parser. Scenario: With --context-files --timeout 5, ${2:?...} accepts --timeout as the value and the parser later fails on unknown option 5, so stderr is not --context-files requires a value. With trailing --context-files, Bash's parameter expansion exits 1, not the asserted exit 2.
- **Proposed resolution**: Revise the implementation plan to add explicit validation for --context-files, e.g. reject when $# < 2 or $2 starts with -- via larch_err and exit 2, then test both trailing and flag-like missing-value forms against that observable behavior.


### FINDING_32:
- **Reviewer(s)**: Codex-dyn-test-observation-surface
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-claude-review.sh:112-118; scripts/launch-claude-subprocess.sh:134-165; <TMPDIR>/plan.txt:57
- **Concern**: Test case 5 observes dedup at the wrong boundary. Scenario: The plan's concrete fallback says to extend the claude stub and grep its $@ for --context-files, but launch-claude-subprocess.sh renders context into PROMPT_RENDERED and invokes claude only as claude --model "$MODEL" --print with the prompt on stdin, so $@ will always contain zero --context-files tokens regardless of dedup correctness. PATH also cannot replace launch-claude-subprocess.sh because launch-claude-review.sh calls it by absolute SCRIPT_DIR path.
- **Proposed resolution**: Revise the test to observe the earliest real boundary: either add/use an explicit subprocess-argv capture hook before launch-claude-subprocess.sh renders the prompt, or have the claude stub capture stdin and assert the rendered prompt contains exactly one context_file_N section for the duplicated path.


### FINDING_33:
- **Reviewer(s)**: Codex-dyn-test-observation-surface
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-claude-review.sh:95-103; scripts/launch-claude-subprocess.sh:102-119; <TMPDIR>/plan.txt:58
- **Concern**: Test case 6 expects a containment failure that the launcher is designed to avoid. Scenario: The plan says append_context_file adds each context file's directory to allow_root_args, matching the current launcher shape, and the subprocess accepts context under EXTRA_ROOTS. In the existing harness shape, output and prompt are also under TMPROOT, making TMPROOT the session root. Therefore an explicit context file passed through launch-claude-review.sh should not produce context file outside allowed roots.
- **Proposed resolution**: Remove this assertion from the launch-claude-review tests or move it to a direct launch-claude-subprocess.sh test without --allow-root. For launcher stderr propagation, use an observable rejection that survives allow-root propagation, such as symlink, oversize, or invalid context file.


### FINDING_36:
- **Reviewer(s)**: Cursor-dyn-sibling-doc-sync
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-launch-claude-review.md:5
- **Concern**: Plan updates scripts/test-launch-claude-review.sh with six new cases but does not list updating the harness sibling .md. Scenario: Covers line omits --context-files cases; violates .claude/rules/script-md-siblings.md same-PR edit-in-sync
- **Proposed resolution**: Add ### UPDATED: scripts/test-launch-claude-review.md; extend the Covers bullet for all six new scenarios


### FINDING_37:
- **Reviewer(s)**: Codex-dyn-sibling-doc-sync
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:49-60; scripts/test-launch-claude-review.md:5; .claude/rules/script-md-siblings.md:7-12
- **Concern**: Plan modifies scripts/test-launch-claude-review.sh but does not list the required sibling scripts/test-launch-claude-review.md update. Scenario: The sibling rule requires the .md to move with behavior changes, and line 5 is the current coverage set that will become stale when six new test cases are added
- **Proposed resolution**: Add UPDATED scripts/test-launch-claude-review.md to the plan and extend its line 5 coverage list for explicit --context-files reviewer/voter, missing value, missing path, dedup, and allow-root/validation propagation coverage


### FINDING_38:
- **Reviewer(s)**: Codex-dyn-sibling-doc-sync
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:23,58; scripts/launch-claude-review.sh:98-102; scripts/launch-claude-subprocess.sh:96-109
- **Concern**: The proposed containment test expects an explicit outside-root context file to fail, but the planned helper adds that file's directory to allow_root_args and the subprocess accepts files under --allow-root. Scenario: An implementation that follows the plan will make test case 6 fail; changing implementation to satisfy the test would regress the intended existing allow-root derivation pattern for context files
- **Proposed resolution**: Revise the test to assert explicit context files receive the same derived --allow-root forwarding as existing implicit context flags, and use a symlink or over-1MB file when testing subprocess validation propagation


### FINDING_39:
- **Reviewer(s)**: Codex-dyn-sibling-doc-sync
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:57; scripts/launch-claude-review.sh:112-118; scripts/launch-claude-subprocess.sh:157-165
- **Concern**: The dedup test plan says to capture --context-files by PATH-stubbing launch-claude-subprocess.sh or by inspecting the claude stub argv, but the launcher calls the subprocess by absolute path and the subprocess invokes claude only as --model ... --print. Scenario: The proposed assertion cannot observe forwarded context-file argv and will either fail with zero --context-files in the claude argv or provide no real dedup coverage
- **Proposed resolution**: Revise the test to have the claude stub capture stdin and count rendered context_file blocks or paths, or intentionally add and document a subprocess override hook before using one in the harness


