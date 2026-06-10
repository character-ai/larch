### FINDING_1: Preserve accepted-only Vote tally filtering
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Codex-Requirements, Cursor-dyn-port-parity, Codex-dyn-port-parity, Codex-dyn-manifest-sweep
- **Severity**: important
- **Concern**: The plan narrows OOS serialization filtering to `Result=rejected`, but the current behavior serializes only blocks with no `Vote tally` `Result=` marker or with `Result=accepted`. Non-accepted results such as `neutral` could enter the accepted public OOS sink.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Port the awk gate exactly: reject only when a `Vote tally:` line has `Result=` and lacks `Result=accepted`; no tally line still accepts (prose `Result=rejected` unchanged)
  - From Codex-Arch: Port the existing predicate: when a Vote tally line has Result= present, emit only Result=accepted and exclude every other result. Add a neutral Result test.
  - From Codex-Innovation: Preserve the current predicate: when a Vote tally line contains Result=, serialize only Result=accepted and skip every other result; add a neutral parity case
  - From Cursor-Pragmatic: Mirror the awk rule: skip when a Vote tally line exists and Result is not accepted; keep the no-tally-line / prose Result= carve-out
  - From Codex-Pragmatic: Mirror the existing awk predicate: write only blocks with no Vote tally Result= marker or with Result=accepted, and add a neutral non-accepted parity case to python/test_oos.py
  - From Codex-Requirements: Specify the existing awk parity rule: if a Vote tally line has Result= and no Result=accepted token, skip the block. Add a pytest case for Result=neutral.
  - From Cursor-dyn-port-parity: Specify the awk parity rule: skip iff a ^Vote tally: line contains (^|[[:space:]])Result= and the line is not (^|[[:space:]])Result=accepted([[:space:]]|$); do not key only on the literal token Result=rejected
  - From Codex-dyn-port-parity: Specify the source accepted-whitelist logic: inspect only lines beginning Vote tally: that contain Result=; emit when no such line exists or when one has Result=accepted; otherwise skip
  - From Codex-dyn-manifest-sweep: Preserve the existing predicate in python/oos.py: parse Vote tally Result lines and write only absent Result or Result=accepted. Skip any present Result that is not accepted, and add a neutral case to python/test_oos.py.


### FINDING_2: Preserve `[OOS]` security header classification
- **Reviewer(s)**: Cursor-Arch, Codex-Innovation, Cursor-Pragmatic, Codex-Requirements, Codex-dyn-port-parity
- **Severity**: important
- **Concern**: The planned security header regex allows `[OUT_OF_SCOPE]` but omits the existing `[OOS]` prefix alternative. Header-tagged security blocks using `[OOS]` could be treated as non-security and published.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Copy the classifier regexes verbatim from the `oos-serialize.sh` heredoc (lines 52-71); do not implement from the abbreviated plan bullet
  - From Codex-Innovation: Keep the existing optional prefix as (OUT_OF_SCOPE|OOS) in the Python header regex
  - From Cursor-Pragmatic: Copy the heredoc regexes from skills/shared/scripts/oos-serialize.sh:53-61 (same as scripts/lib-vote-tally.sh:75-82) byte-for-byte into is_security_tagged
  - From Codex-Requirements: Change the planned explicit-header regex to allow (OUT_OF_SCOPE|OOS), and add a focused pytest case for [OOS] plus a header security tag.
  - From Codex-dyn-port-parity: Preserve the source staging and patterns: remove fenced blocks globally; use text_no_backtick only for focus-area\s*=\s*security; allow (OUT_OF_SCOPE|OOS) in the header tag regex; for field lines strip backticks and asterisks per line before matching the source focus-area field regex


### FINDING_3: Preserve field normalization for security focus-area matching
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Codex-dyn-port-parity
- **Severity**: important
- **Concern**: The plan omits the bash classifier’s per-line backtick and asterisk stripping before matching `focus-area` fields. Security-tagged fields such as inline-code or bold `security-hardening` can be missed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Match the heredoc loop: `normalized = line.replace("`", "").replace("*", "").strip()` before the field regex
  - From Cursor-Pragmatic: Document and implement the same per-line normalization loop as oos-serialize.sh:67-71
  - From Codex-dyn-port-parity: Preserve the source staging and patterns: remove fenced blocks globally; use text_no_backtick only for focus-area\s*=\s*security; allow (OUT_OF_SCOPE|OOS) in the header tag regex; for field lines strip backticks and asterisks per line before matching the source focus-area field regex


### FINDING_4: Create output parent directories before serialization
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: The plan omits the bash helper’s `mkdir -p` behavior for the serializer output parent directory. Rebuild paths can fail before writing when the target directory does not exist.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `output_file.parent.mkdir(parents=True, exist_ok=True)` (or equivalent) before truncate/write, matching `oos-serialize.sh:23`
  - From Cursor-Innovation: Preserve mkdir -p (or Path.parent.mkdir(parents=True, exist_ok=True)) before truncating/writing the output file


### FINDING_5: Define fail-closed classifier error semantics
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The plan does not preserve the serializer’s fail-closed behavior when security classification fails. A Python exception or non-boolean classifier failure could exit incorrectly, write partial output, or leak security-tagged content.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Specify is_security_tagged failure semantics (exit 2), abort-before-next-write, truncate/leave output empty on any mid-run failure, and add pytest covering classifier failure with no partial sink
  - From Cursor-Pragmatic: Define tri-state security classification (held / not-held / error); on error exit 2 from oos serialize without writing the current block; add pytest mirroring test-oos-serialize.sh:60-78
  - From Cursor-Requirements: Add Failure modes / oos_serialize spec: classifier failures exit 2; output_file is truncated only at entry and must stay empty on any mid-run failure; no partial accepted blocks


### FINDING_8: Port full oos-serialize harness parity into pytest
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The planned pytest coverage is thinner than the bash `test-oos-serialize.sh` harness. Missing fixture counts, body-heading non-security behavior, and classifier-failure parity weaken the pre-delete gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add explicit tests for stdin mode, `--seq`/missing-file exit 2, and one integration case reproducing the harness fixture and exact count assertions
  - From Cursor-Innovation: Port the harness fixture verbatim (including the broken-python3/classifier-failure case adapted to pure-Python failure injection) before deleting skills/shared/scripts/test-oos-serialize.sh
  - From Cursor-Pragmatic: Port the harness findings.md fixture and count/header assertions into test_oos_serialize_accepted_and_held (or equivalent) before harness deletion
  - From Cursor-Requirements: Add test_oos_serialize_classifier_failure_no_partial_sink mirroring the PATH-broken-python3 harness (or inject an equivalent failure) asserting exit 2 and zero-length output
  - From Codex-Requirements: Add a case asserting a body-cited security heading is serialized while header-tagged security blocks stay held


### FINDING_9: Port normalize-header stdin and argv validation parity
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: The planned normalize-header tests omit stdin mode and CLI validation failures covered by the bash harness. Bad arguments could regress to tracebacks, exit 0, or wrong exit codes after harness deletion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add explicit tests for stdin mode, `--seq`/missing-file exit 2, and one integration case reproducing the harness fixture and exact count assertions
  - From Cursor-Innovation: Add explicit pytest cases for stdin mode and the three validation failures, not only happy-path header rewrites
  - From Cursor-Requirements: Add pytest cases for the three validation branches (or one parametrized test) matching the harness exit-2 expectations


### FINDING_10: Sweep retired helper references from caller docs and comments
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Codex-Innovation, Codex-Requirements, Codex-dyn-port-parity, Codex-dyn-manifest-sweep
- **Severity**: important
- **Concern**: The plan retires OOS bash helper paths but omits tracked docs and comments that still reference them. After manifest rows land, `lint-retired-scripts` can fail, and shipped docs may point operators to deleted files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add these docs to the plan and replace the retired helper path references with the new python3 python/cli.py oos normalize-header invocation.
  - From Cursor-Innovation: Add UPDATED rows for those .md files (and any other tracked full-path mentions) replacing the bash path with python3 "${PLUGIN_ROOT}/python/cli.py" oos normalize-header / oos serialize
  - From Codex-Innovation: Update these docs in the same PR to name the new python/cli.py oos normalize-header path or describe the behavior without retired script paths
  - From Codex-Requirements: Add explicit plan sections to update the three caller contract docs and OOS-specific scripts/relevant-checks.sh routing, with a matching test-relevant-checks assertion if routing changes. Keep agent-lint.toml limited to existing OOS rows, or state no change is needed after grep.
  - From Codex-dyn-port-parity: Add updates for the caller docs to replace the retired helper path references with the new python3 python/cli.py oos serialize or oos normalize-header surfaces, or with path-free CLI wording where exact commands are unnecessary
  - From Codex-dyn-manifest-sweep: Add these doc/comment updates to the file list and Approach. Replace old helper references with the new python3 python/cli.py oos serialize or oos normalize-header wording, then run git grep plus make lint-retired-scripts.




### FINDING_3: Emit-tally cutover leaves SHARED_DIR unused and can fail shellcheck
- **Reviewer(s)**: Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: Replacing the only `SHARED_DIR` consumer in `emit-tally.sh` leaves the assignment unused. Shellcheck can report SC2034 and fail lint validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Remove the SHARED_DIR assignment as part of the emit-tally.sh cutover, or keep the variable only if another planned use remains
  - From Cursor-Requirements: Add an explicit emit-tally.sh step to delete the `SHARED_DIR=...` line when switching to `python3 "${PLUGIN_ROOT}/python/cli.py" oos serialize` (mirror the tally plan item that removes `NORMALIZE_OOS_HELPER`).
  - From Codex-Requirements: Remove the SHARED_DIR assignment as part of the emit-tally.sh cutover


### FINDING_4: Security-held OOS counting order can change rejected security block handling
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: The serializer plan filters Vote tally results before applying the security hold. A rejected security-tagged OOS block is currently counted as held before accepted-whitelist serialization, but the proposed order can skip it and undercount `OOS_HELD_SECURITY`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Classify each OOS block first; increment held_security for security blocks; run the accepted-whitelist serialization only for non-security blocks


### FINDING_5: Validation plan omits required make lint
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The testing strategy does not include `make lint`, although the definition of done requires it. The listed validation can pass while shellcheck or agent-lint failures remain.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add make lint to the validation set alongside py-lint and py-test


### FINDING_9:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:182-207
- **Concern**: [SCOPE-REDUCTION] Retired-helper relevant-checks routing can conflict with the retired-script manifest lint. Scenario: The plan appends the OOS helper paths to python/migrated-scripts.tsv and also tells scripts/relevant-checks.sh and scripts/test-relevant-checks.sh to route those retired helper paths. If the implementation follows existing relevant-checks style and stores full literals such as skills/shared/scripts/oos-serialize.sh, make lint-retired-scripts will flag those tracked references and the required validation cannot pass.
- **Proposed resolution**: Omit deleted-helper path routing if manifest plus python/oos.py coverage already triggers the needed checks, or require basename-only/glob matching that does not store the retired repo-relative paths in tracked files.



### FINDING_1: Preserve retired vote tally Result token boundaries
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic, Cursor-dyn-migration-parity, Codex-dyn-migration-parity
- **Severity**: important
- **Concern**: The planned Python OOS serializer widens retired vote tally detection by treating any `Result=` substring on a `Vote tally:` line as a present result. That can skip blocks that remain eligible today, such as lines containing `NotResult=rejected` or `NoResult=rejected`, and can mishandle accepted-result boundaries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Use the retired predicate for found tally lines: line starts Vote tally: and matches (^|[ \t])Result=; keep the existing Result=accepted([ \t]|$) accepted check.
  - From Codex-Pragmatic: Use the retired found regex equivalent, (^|\s)Result=, and keep the accepted regex equivalent, (^|\s)Result=accepted(\s|$).
  - From Cursor-dyn-migration-parity: On a line matching `^Vote tally: ` with a `Result=` token, bash only accepts when `$0 ~ /(^|[[:space:]])Result=accepted([[:space:]]|$)/`; any other present tally line makes `found=1` and skips unless accepted. A hand-rolled Python check can mis-handle `Result=accepted-extra`, missing whitespace boundaries, or lines that mention `Result=` outside the tally prefix. Copy the awk conditions verbatim into the plan (or oos.py module docstring): tally lines must match `^Vote tally: ` and `/(^|[[:space:]])Result=/`; acceptance requires `/(^|[[:space:]])Result=accepted([[:space:]]|$)/` on that same line; `END { exit (found && !accepted) ? 1 : 0 }`.
  - From Codex-dyn-migration-parity: Port the found check exactly: line starts with Vote tally: and re.search(r"(^|[ \t])Result=", line), with the accepted check using the same retired Result=accepted whitespace/end boundary. Add a parity case.


### FINDING_2: Keep normalize-header payload on stdout
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The normalize-header CLI contract is not pinned to stdout. Existing callers capture helper output with shell redirection, so routing normalized block text through the quiet FD-3 contract could produce empty captured files and silently drop accepted OOS markdown.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: State explicitly that normalized block text prints to stdout (stderr for validation errors only); do not route payload through `quiet_init` / `contract_stream`. Add a subprocess test that asserts captured stdout is non-empty for a fixture block



