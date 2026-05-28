### FINDING_1: Sketch fixture still emits backticked style lines
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The planned sketch grep expects `Style requirements: <READABILITY_STYLE>.` without backticks, but the compliant sketch fixture still emits the legacy backticked `external_style_line`, so existing compliant cases will count 0 matches and fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: When updating populate_fixture for TSV sourcing also write sketch rows with the no-backtick line shape (or four real sketch-prompts.md excerpt lines); call this out under test-lint-readability-preamble.sh in the plan
  - From Cursor-Pragmatic: Change the sketch branch in `populate_fixture` to emit the real sketch line shape; keep `sketch-bare-token-rejected` as the negative case


### FINDING_2: Design-structure routing is broadened without matching coverage
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan broadens `test-design-structure` routing to `skills/*`, but that harness is design-specific and does not validate arbitrary skill pin drift; non-design skill edits would run unrelated design checks without new assertions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Keep test-design-structure on skills/design/SKILL.md|skills/design/references/*.md; if cross-skill pin drift is a goal route test-check-contains-pins only or extend the harness later
  - From Cursor-Arch: Revise Approach A2 to say test-design-structure always re-checks design pins or narrow the routing pattern
  - From Codex-Arch: Keep the design-structure arm scoped to skills/design, and route only test-check-contains-pins for verifier or actual canonical pin-harness changes.
  - From Cursor-Pragmatic: Keep the case pattern on `skills/design/SKILL.md|skills/design/references/*.md` (minimum change). Rely on the new pin-script case block for verifier/harness edits; only broaden skill routing if acceptance explicitly requires it


### FINDING_3: Codex usage parser harness is included in unrelated pin routing
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The relevant-checks pin-verifier direct-target case includes `scripts/test-parse-codex-usage.sh`, causing Codex usage parser changes to run pin and design-structure harnesses with no pin-contract relationship.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Drop scripts/test-parse-codex-usage.sh from that case; keep scripts/check-contains-pins* scripts/test-check-contains-pins* scripts/test-design-structure.sh only
  - From Cursor-Pragmatic: Remove `scripts/test-parse-codex-usage.sh` from that case pattern; keep only `check-contains-pins*`, `test-check-contains-pins*`, and optionally `test-design-structure.sh` if pin lines there must re-verify


### FINDING_4: Escaped-quote literals still terminate at the escaped quote
- **Reviewer(s)**: Codex-Arch, Cursor-Edge, Codex-Edge, Cursor-Innovation, Codex-Innovation, Codex-Pragmatic, Codex-Requirements, Cursor-dyn-portability-audit, Codex-dyn-portability-audit
- **Severity**: important
- **Concern**: The plan unescapes double-quoted literals only after using the existing `index(rest, quote)` delimiter lookup, so literals containing escaped double quotes are truncated before unescape runs and remain skipped or misparsed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Within parse_contains, scan double-quoted literals character by character to find the first unescaped closing quote, then apply the narrow unescape pass to the captured literal.
  - From Cursor-Edge: Add escape-aware closing-quote scan in parse_contains (treat \" as non-terminating) before the unescape pass; keep post-unescape bare-$ SKIP
  - From Codex-Edge: Make the double-quoted literal end scan escape-aware before the unescape pass; keep single-quoted parsing unchanged
  - From Cursor-Innovation: Replace literal_end=index(rest, quote) for double-quoted literals with a char scanner that treats only unescaped " as the closing delimiter, then unescape the captured body
  - From Codex-Innovation: Replace literal_end=index(rest, quote) for double-quoted literals with a char scanner that treats only unescaped " as the closing delimiter, then unescape the captured body
  - From Codex-Pragmatic: Replace closing-quote detection with an escape-aware scan for double-quoted literals, and detect bare unescaped dollars on the original literal before converting \$ to $
  - From Codex-Requirements: Replace `literal_end = index(rest, quote)` with a double-quote-aware scanner that ignores escaped `"`, `\`, and `$` while keeping single-quoted parsing unchanged
  - From Cursor-dyn-portability-audit: Replace the double-quoted literal_end lookup with a POSIX awk character scan that skips backslash-escaped quotes before running the unescape pass
  - From Codex-dyn-portability-audit: Replace the double-quoted literal_end lookup with a POSIX awk character scan that skips backslash-escaped quotes before running the unescape pass


### FINDING_5: Escaped dollar handling conflicts with bare-dollar skip logic
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Pragmatic, Cursor-Innovation, Codex-Innovation, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The plan expects escaped dollars to become checkable literals, but also describes rescanning after unescape for bare dollars; that would misclassify escaped-dollar literals, while the mixed escaped-plus-bare-dollar case is not clearly covered in A1 or Section 5.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Either add escape-with-bare-dollar to Section 5 and A1 or delete that mitigation from Failure modes
  - From Codex-Arch: Track whether the original double-quoted source contained an unescaped dollar before unescaping; skip only in that case, and allow dollars that came from escaped \$.
  - From Cursor-Pragmatic: Add the re-scan rule to the `check-contains-pins.sh` bullet and a Section 5 fixture (or drop the Failure modes mitigation if truly out of scope)
  - From Cursor-Innovation: Detect unescaped $ while scanning the original double-quoted source, before rewriting \$ to $, or carry an escaped flag through the unescape loop
  - From Codex-Innovation: Detect unescaped $ while scanning the original double-quoted source, before rewriting \$ to $, or carry an escaped flag through the unescape loop
  - From Codex-Pragmatic: Replace closing-quote detection with an escape-aware scan for double-quoted literals, and detect bare unescaped dollars on the original literal before converting \$ to $
  - From Codex-Requirements: Track bare versus escaped `$` during the source scan before normalization; only SKIP when the original double-quoted literal contains an unescaped dollar, and add a mixed escaped-plus-bare-dollar fixture to lock that contract


### FINDING_6: Relevant-checks output harness is not updated for new target list
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Concern**: The plan changes relevant-checks direct target output, but omits the harness expectations that pin that output, so `test-relevant-checks.sh` will still expect the old target list.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Update scripts/test-relevant-checks.sh and its sibling .md for the new target list/order; add only the minimum assertion needed for the broadened skills/* route


### FINDING_7: Bash TSV parsing collapses empty middle fields
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation, Codex-Pragmatic, Cursor-dyn-portability-audit, Codex-dyn-portability-audit
- **Severity**: important
- **Concern**: Using Bash `IFS=$'\t' read` for TSV rows loses empty middle fields, so rows with an empty `prompt_kind` and non-empty `step_markers` shift fields and disable the planned placement checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Parse the TSV with awk -F '\t' or another field-preserving parser, and have the malformed/empty-field tests cover the SKILL.md row shape
  - From Codex-Innovation: Parse the TSV with awk -F '\t' or another field-preserving parser, and have the malformed/empty-field tests cover the SKILL.md row shape
  - From Codex-Pragmatic: Parse TSV with awk FS="\t" or translate tabs to a non-whitespace delimiter before read so empty fields are preserved in both lint and test consumers
  - From Cursor-dyn-portability-audit: Do not split TSV rows with IFS=$'\t' read into fields; read the whole line and split with POSIX awk -F '\t' or another parser that preserves empty middle fields
  - From Codex-dyn-portability-audit: Do not split TSV rows with IFS=$'\t' read into fields; read the whole line and split with POSIX awk -F '\t' or another parser that preserves empty middle fields


### FINDING_8: SKILL.md fixtures lack step markers required by placement checks
- **Reviewer(s)**: Cursor-Pragmatic, Codex-dyn-consumer-contract
- **Severity**: important
- **Concern**: The lint plan adds `step_markers` placement checks for SKILL.md rows, but existing test fixtures still write repeated directives without marker-bounded step bodies, so compliant fixtures will fail or the harness may drift from lint behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Update `populate_fixture` (and any fixture-specific writers) so SKILL.md fixtures include the step markers and at least one orchestrator directive inside each listed step; adjust `orchestrator-partial` expectations if stderr order changes
  - From Codex-dyn-consumer-contract: Specify that test-lint-readability-preamble.sh reads the same five TSV fields with the same skip/default/validation rules, and for non-empty step_markers creates fixture bodies with those step anchors and directives inside each named step body. Empty step_markers should keep using expected_count for existing fixture assertions.


### FINDING_9: Offline fixture roots do not receive the TSV manifest
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-consumer-contract
- **Severity**: important
- **Concern**: The lint script is planned to read `$ROOT/scripts/lint-readability-preamble.tsv`, but offline `--root` test fixtures do not stage that manifest, so existing harness cases will exit before exercising the intended assertions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Spell out that each fixture root must ship `scripts/lint-readability-preamble.tsv` (copy repo TSV, then mutate for B6), or split paths: canonical manifest beside the lint script, `--root` only for target files
  - From Cursor-Requirements: Add a shared setup step (e.g. in `populate_fixture` or a helper) that copies or writes the repo manifest into `$root/scripts/lint-readability-preamble.tsv` for every fixture root before lint invocation
  - From Cursor-dyn-consumer-contract: In UPDATED test-lint-readability-preamble.sh add a helper that copies or writes the manifest into $root/scripts/ for every fixture (B6 uses a variant copy with the extra row)


### FINDING_10: Empty expected_count is not rejected as malformed
- **Reviewer(s)**: Cursor-dyn-portability-audit, Codex-dyn-portability-audit, Cursor-dyn-consumer-contract
- **Severity**: important
- **Concern**: The planned expected-count validation rejects non-digits but may allow empty values to fall through to default behavior, despite failure-mode requirements for malformed-row validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-portability-audit: Validate empty explicitly with ''|*[!0-9]* before using expected_count
  - From Codex-dyn-portability-audit: Validate empty explicitly with ''|*[!0-9]* before using expected_count
  - From Cursor-dyn-consumer-contract: Add the case ... (*[!0-9]*) exit 2 block to lint-readability-preamble.sh UPDATED and add a malformed-tsv-row case to test-lint-readability-preamble.sh UPDATED (as already promised in Failure modes)


### FINDING_13: Lint and test TSV reader contracts are under-specified
- **Reviewer(s)**: Cursor-dyn-consumer-contract
- **Severity**: important
- **Concern**: The plan specifies duplicated TSV readers without a shared contract for comment skipping, blank rows, defaults, validation, and `step_markers`, so lint and test behavior can diverge while both nominally read the same TSV.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-consumer-contract: Paste the same read loop contract into both UPDATED subsections (or scripts/lint-readability-preamble.tsv.md): five tab fields, identical skip rule, identical ${expected_count:-1} for file-level checks, step_markers ignored by the harness except for B5 fixtures

