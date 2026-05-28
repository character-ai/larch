### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-lint-readability-preamble.sh:72-74; plan.txt:83-87
- **Concern**: A4 sketch grep changes but compliant fixture still uses backtick external_style_line. Scenario: After sketch variant switches to grep -Fc 'Style requirements: <READABILITY_STYLE>.' the compliant fixture sketch-prompts.md rows use Style requirements: `<READABILITY_STYLE>`. — count 0 vs expected 4 and five legacy cases fail on TSV refactor
- **Proposed resolution**: When updating populate_fixture for TSV sourcing also write sketch rows with the no-backtick line shape (or four real sketch-prompts.md excerpt lines); call this out under test-lint-readability-preamble.sh in the plan

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/relevant-checks.sh:62-64; plan.txt:36-37; scripts/test-design-structure.sh:6-14
- **Concern**: Broadening test-design-structure routing to skills/*/ has no new pin coverage. Scenario: test-design-structure.sh only greps skills/design/* variables; edits to skills/implement/SKILL.md or other skills still run the full harness with zero new assertions
- **Proposed resolution**: Keep test-design-structure on skills/design/SKILL.md|skills/design/references/*.md; if cross-skill pin drift is a goal route test-check-contains-pins only or extend the harness later

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:29-34; scripts/relevant-checks.sh:61-65
- **Concern**: test-parse-codex-usage.sh bundled into pin-verifier direct-target case. Scenario: Changing the Codex usage parser harness runs test-design-structure and test-check-contains-pins despite unrelated contains grammar (stderr label checks only)
- **Proposed resolution**: Drop scripts/test-parse-codex-usage.sh from that case; keep scripts/check-contains-pins* scripts/test-check-contains-pins* scripts/test-design-structure.sh only

### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: latent
- **Focus area**: correctness
- **Location**: plan.txt:127-129; plan.txt:17-24
- **Concern**: Failure mode #3 escape-with-bare-dollar guard not in A1 deliverables or Section 5. Scenario: Failure modes require post-unescape re-scan for $[A-Za-z_{] and a mixed-literal fixture but Section 5 lists only bare-dollar-still-skipped; implementer may ship unescape without the mixed-literal guard
- **Proposed resolution**: Either add escape-with-bare-dollar to Section 5 and A1 or delete that mitigation from Failure modes

### FINDING_5:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: plan.txt:36-37; scripts/relevant-checks.md:7
- **Concern**: A2 cites check-contains-pins --changed-files scoping for test-design-structure expansion. Scenario: test-design-structure is a direct Make target with no --changed-files; the rationale misstates why broadening any-skill paths helps pin drift
- **Proposed resolution**: Revise Approach A2 to say test-design-structure always re-checks design pins or narrow the routing pattern

### FINDING_6:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/check-contains-pins.sh:280-292
- **Concern**: The plan only replaces the dollar-skip branch, but the parser still finds the closing double quote with index(rest, quote), so escaped quotes end the literal before unescape runs.. Scenario: Planned fixtures like escape-dollar and escape-quotes-only remain SKIPPED_NON_CANONICAL or parse as the wrong payload, so acceptance for escaped double-quoted literals is not met.
- **Proposed resolution**: Within parse_contains, scan double-quoted literals character by character to find the first unescaped closing quote, then apply the narrow unescape pass to the captured literal.

### FINDING_7:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/check-contains-pins.sh:292-296
- **Concern**: The plan's mitigation says to rescan the unescaped literal for dollar expansion, which conflicts with checking escaped dollar literals after they become ${...}.. Scenario: Following that instruction makes escape-dollar and escape-defect skip instead of checking the intended literal, so the main A1 behavior regresses.
- **Proposed resolution**: Track whether the original double-quoted source contained an unescaped dollar before unescaping; skip only in that case, and allow dollars that came from escaped \$.

### FINDING_8:
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/relevant-checks.sh:61-64
- **Concern**: The plan broadens test-design-structure routing to all skills, but that harness is design-specific and the existing pin verifier already checks changed pin targets through --changed-files.. Scenario: Non-design skill edits run an unrelated design harness that cannot prove their pins and may fail for unrelated design drift, adding scope without matching coverage.
- **Proposed resolution**: Keep the design-structure arm scoped to skills/design, and route only test-check-contains-pins for verifier or actual canonical pin-harness changes.

### FINDING_9:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/check-contains-pins.sh:281-295
- **Concern**: A1 only unescapes after naive index(rest, quote) boundary. Scenario: Double-quoted literals with \" (Section 5 escape-quotes-only, escape-dollar, test-design-structure.sh:44) truncate at the first embedded quote; unescape never runs on the full literal → false DEFECT or wrong CHECK payload
- **Proposed resolution**: Add escape-aware closing-quote scan in parse_contains (treat \" as non-terminating) before the unescape pass; keep post-unescape bare-$ SKIP

### FINDING_10:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/check-contains-pins.sh:280-288
- **Concern**: Plan unescapes after the existing delimiter scan, but that scan treats escaped double quotes as closing quotes. Scenario: The planned escape-quotes-only fixture with "say \"hi\"" still parses only up to the escaped quote, then emits SKIPPED_NON_CANONICAL instead of CHECK
- **Proposed resolution**: Make the double-quoted literal end scan escape-aware before the unescape pass; keep single-quoted parsing unchanged

### FINDING_11:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-relevant-checks.sh:338-339
- **Concern**: Plan changes relevant-checks direct target output but omits the harness that pins that output. Scenario: test-relevant-checks still expects only test-lint-foreground-markers test-design-structure, so adding test-check-contains-pins to the design-reference route will fail the harness
- **Proposed resolution**: Update scripts/test-relevant-checks.sh and its sibling .md for the new target list/order; add only the minimum assertion needed for the broadened skills/* route

### FINDING_12:
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/check-contains-pins.sh:280-287
- **Concern**: Escaped double quotes are still parsed as terminators before the proposed unescape pass. Scenario: The planned escape-quotes-only fixture using "say \"hi\"" is SKIPped because index(rest, quote) stops at the escaped quote before unescaping can run
- **Proposed resolution**: Replace literal_end=index(rest, quote) for double-quoted literals with a char scanner that treats only unescaped " as the closing delimiter, then unescape the captured body

### FINDING_13:
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/check-contains-pins.sh:292-296
- **Concern**: The plan loses escape-state when checking for bare dollars after unescaping. Scenario: If implementation follows the failure-mode mitigation and rescans the unescaped payload, "\${MISSING}" becomes ${MISSING} and is misclassified as interpolated instead of checkable
- **Proposed resolution**: Detect unescaped $ while scanning the original double-quoted source, before rewriting \$ to $, or carry an escaped flag through the unescape loop

### FINDING_14:
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-readability-preamble.sh:64-67
- **Concern**: Plain Bash read with IFS=$'\t' does not preserve empty TSV fields. Scenario: The SKILL.md row needs an empty prompt_kind before step_markers, but Bash collapses adjacent tab delimiters so 2b,3b,4,5 shifts into prompt_kind and step placement never runs
- **Proposed resolution**: Parse the TSV with awk -F '\t' or another field-preserving parser, and have the malformed/empty-field tests cover the SKILL.md row shape

### FINDING_15:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-lint-readability-preamble.sh:58-94; plan.txt:80-87
- **Concern**: Existing harness fixtures lack step markers and per-step directive placement. Scenario: B5 adds a placement check for SKILL.md (`step_markers=2b,3b,4,5`). `populate_fixture` still writes four stacked directives with no `<!-- step:…>` markers. The plan requires the five legacy cases to keep passing but only adds new placement fixtures; `compliant` and `orchestrator-partial` will fail (missing-marker and/or placement errors) after B5 lands
- **Proposed resolution**: Update `populate_fixture` (and any fixture-specific writers) so SKILL.md fixtures include the step markers and at least one orchestrator directive inside each listed step; adjust `orchestrator-partial` expectations if stderr order changes

### FINDING_16:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-readability-preamble.sh:55-59; scripts/test-lint-readability-preamble.sh:96-103; plan.txt:52-59
- **Concern**: Manifest path is tied to `--root` but the plan omits per-fixture TSV staging. Scenario: The proposed reader uses `manifest_tsv="$ROOT/scripts/lint-readability-preamble.tsv"`. Harness runs use `--root` on temp dirs that today have no `scripts/lint-readability-preamble.tsv`, so lint exits 2 or reads the wrong manifest unless every case copies/symlinks the TSV first
- **Proposed resolution**: Spell out that each fixture root must ship `scripts/lint-readability-preamble.tsv` (copy repo TSV, then mutate for B6), or split paths: canonical manifest beside the lint script, `--root` only for target files

### FINDING_17:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/check-contains-pins.sh:292-295; plan.txt:7-24; plan.txt:129
- **Concern**: Mixed escaped+bare `$` guard is specified in Failure modes but not in the A1 edit or Section 5. Scenario: Failure modes require a post-unescape re-scan and fixture `escape-with-bare-dollar`; the UPDATED awk section and Section 5 only cover full SKIP (`"$VAR"`) and pure escapes. A literal like `"ok \${A} bad $B"` could CHECK and false-DEFECT
- **Proposed resolution**: Add the re-scan rule to the `check-contains-pins.sh` bullet and a Section 5 fixture (or drop the Failure modes mitigation if truly out of scope)

### FINDING_18:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-lint-readability-preamble.sh:72-73; plan.txt:83-84
- **Concern**: A4 sketch fix breaks the compliant sketch fixture. Scenario: The sketch variant switches to line-anchored `Style requirements: <READABILITY_STYLE>.` (no backticks). `populate_fixture` still writes four `external_style_line` rows (backticked). The compliant run will report count 0/4 unless that branch is updated
- **Proposed resolution**: Change the sketch branch in `populate_fixture` to emit the real sketch line shape; keep `sketch-bare-token-rejected` as the negative case

### FINDING_19:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/relevant-checks.sh:61-64; scripts/test-design-structure.sh:1-14; plan.txt:36-37; plan.txt:99
- **Concern**: Broadening `test-design-structure` to `skills/*` is mis-justified and expands unrelated CI. Scenario: `test-design-structure.sh` is design-only (hardcoded design paths) and does not call `check-contains-pins.sh`. Editing `skills/implement/SKILL.md` would still run the full design structural harness without validating that skill. The plan’s “invokes check-contains-pins repo-wide” rationale is false
- **Proposed resolution**: Keep the case pattern on `skills/design/SKILL.md|skills/design/references/*.md` (minimum change). Rely on the new pin-script case block for verifier/harness edits; only broaden skill routing if acceptance explicitly requires it

### FINDING_20:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/relevant-checks.sh:29-34; plan.txt:30
- **Concern**: `test-parse-codex-usage.sh` in the pin-routing case is unrelated scope. Scenario: Changes to the Codex usage parser harness would also run `test-check-contains-pins` and `test-design-structure`, adding cost and noise with no pin contract link
- **Proposed resolution**: Remove `scripts/test-parse-codex-usage.sh` from that case pattern; keep only `check-contains-pins*`, `test-check-contains-pins*`, and optionally `test-design-structure.sh` if pin lines there must re-verify

### FINDING_21:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-readability-preamble.sh:41-53
- **Concern**: Proposed TSV reader loses empty middle fields. Scenario: Rows like skills/design/SKILL.md<TAB>orchestrator-inline<TAB>4<TAB><TAB>2b,3b,4,5 are parsed by Bash read with tab as IFS whitespace, so 2b,3b,4,5 shifts into prompt_kind and step_markers is empty; the new B5 placement check is silently disabled
- **Proposed resolution**: Parse TSV with awk FS="\t" or translate tabs to a non-whitespace delimiter before read so empty fields are preserved in both lint and test consumers

### FINDING_22:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/check-contains-pins.sh:281-296
- **Concern**: Plan only replaces the dollar skip branch but leaves quote parsing and dollar detection incompatible with escaped double-quote literals. Scenario: The current literal_end=index(rest, quote) stops at escaped quotes, so fixtures like say \"hi\" and the real --round-num \"\${STEP3_REVIEW_ROUND_NUM...}\" pin still SKIP; additionally rescanning the unescaped payload for $ would reject intended escaped-dollar literals
- **Proposed resolution**: Replace closing-quote detection with an escape-aware scan for double-quoted literals, and detect bare unescaped dollars on the original literal before converting \$ to $

### FINDING_23:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-lint-readability-preamble.sh:58-147
- **Concern**: Offline harness never seeds `scripts/lint-readability-preamble.tsv` under `--root` fixtures. Scenario: After the lint reads `$ROOT/scripts/lint-readability-preamble.tsv`, the five existing cases (`compliant`, `external-bad`, etc.) call `lint-readability-preamble.sh --root "$fixture"` with no manifest in the fixture tree; runs fail before A4/B5/B6 assertions execute
- **Proposed resolution**: Add a shared setup step (e.g. in `populate_fixture` or a helper) that copies or writes the repo manifest into `$root/scripts/lint-readability-preamble.tsv` for every fixture root before lint invocation

### FINDING_24:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/check-contains-pins.sh:280-287
- **Concern**: Plan supports escaped double quotes in double-quoted contains literals but does not update quote-boundary parsing. Scenario: `contains "$TARGET" "say \"hi\""` will terminate at the escaped quote before the planned unescape pass, causing SKIP instead of CHECK and leaving the double-quoted static literal requirement incomplete
- **Proposed resolution**: Replace `literal_end = index(rest, quote)` with a double-quote-aware scanner that ignores escaped `"`, `\`, and `$` while keeping single-quoted parsing unchanged

### FINDING_25:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/check-contains-pins.sh:292-296
- **Concern**: Plan conflicts on escaped dollar handling: it expects `\$` to become a checkable literal but later says to rescan the unescaped literal for `$` and SKIP. Scenario: An escaped-dollar fixture such as `"\${FOO}"` would normalize to `${FOO}` and then be skipped by the mitigation, contradicting the acceptance case that it should verify the literal
- **Proposed resolution**: Track bare versus escaped `$` during the source scan before normalization; only SKIP when the original double-quoted literal contains an unescaped dollar, and add a mixed escaped-plus-bare-dollar fixture to lock that contract

### FINDING_26:
- **Reviewer(s)**: Cursor-dyn-portability-audit, Codex-dyn-portability-audit
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/check-contains-pins.sh:280-292
- **Concern**: Escaped double quotes are parsed as the closing quote before the planned unescape branch can run. Scenario: The planned escape-quotes-only fixture contains say \"hi\", but literal_end=index(rest, quote) stops at the escaped quote, leaves non-whitespace rest, and emits SKIP instead of CHECK
- **Proposed resolution**: Replace the double-quoted literal_end lookup with a POSIX awk character scan that skips backslash-escaped quotes before running the unescape pass

### FINDING_27:
- **Reviewer(s)**: Cursor-dyn-portability-audit, Codex-dyn-portability-audit
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-readability-preamble.sh:41-67; scripts/test-lint-readability-preamble.sh:17-31
- **Concern**: IFS tab read collapses the empty prompt_kind field before non-empty step_markers. Scenario: Bash treats tab as IFS whitespace, so the SKILL.md TSV row with empty prompt_kind and step_markers=2b,3b,4,5 assigns prompt_kind=2b,3b,4,5 and step_markers empty; the B5 placement check is silently skipped
- **Proposed resolution**: Do not split TSV rows with IFS=$'\t' read into fields; read the whole line and split with POSIX awk -F '\t' or another parser that preserves empty middle fields

### FINDING_28:
- **Reviewer(s)**: Cursor-dyn-portability-audit, Codex-dyn-portability-audit
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/lint-readability-preamble.sh:64-67
- **Concern**: The planned expected_count case pattern accepts an empty count. Scenario: case "$expected_count" in (*[!0-9]*) rejects non-digits but lets an empty expected_count through, which can fall back to the existing default-count behavior instead of failing malformed TSV rows
- **Proposed resolution**: Validate empty explicitly with ''|*[!0-9]* before using expected_count

### FINDING_29:
- **Reviewer(s)**: Cursor-dyn-portability-audit, Codex-dyn-portability-audit
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/test-check-contains-pins.sh:286-305; scripts/lint-bash32.sh:86-98
- **Concern**: BASH_COMPAT=3.2 is not a substitute for the Bash 3.2 static portability gate. Scenario: On a Bash 4.3+ host, BASH_COMPAT changes compatibility behavior but does not make Bash 4-only syntax unavailable, so a smoke run can pass while constructs banned by lint-bash32 remain in the script
- **Proposed resolution**: Keep the BASH_COMPAT smoke if required, but make lint-bash32 or the existing forbidden-token assertions the stated portability gate for this harness

### FINDING_30:
- **Reviewer(s)**: Cursor-dyn-consumer-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:52-59,plan.txt:85-86
- **Concern**: B6 only asserts lint iterates a synthetic TSV row; test harness parser coverage is unspecified. Scenario: After refactor the test can still build fixtures from a stale hardcoded subset while lint reads the full manifest; acceptance item 6 (mechanical sync) passes B6 but missing TSV rows never get fixture files and CI can false-pass
- **Proposed resolution**: Extend B6 to assert the harness enumeration matches lint row count (or that populate_fixture writes every parsed path); add an assertion that a deliberately omitted parser row leaves a manifest-only path without a fixture and fails

### FINDING_31:
- **Reviewer(s)**: Cursor-dyn-consumer-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:55-59,scripts/test-lint-readability-preamble.sh:96-103
- **Concern**: Lint reads manifest at $ROOT/scripts/lint-readability-preamble.tsv but the plan never installs that file into offline --root fixture trees. Scenario: All five existing harness cases call bash lint-readability-preamble.sh --root "$TMPROOT/..."; with an inline manifest removed, each fixture root lacks scripts/lint-readability-preamble.tsv and lint exits 2 before exercising assertions
- **Proposed resolution**: In UPDATED test-lint-readability-preamble.sh add a helper that copies or writes the manifest into $root/scripts/ for every fixture (B6 uses a variant copy with the extra row)

### FINDING_32:
- **Reviewer(s)**: Cursor-dyn-consumer-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:52-59,plan.txt:78-79,plan.txt:111-118
- **Concern**: Duplicated TSV readers are specified but not contract-aligned; test section has no parse pseudocode. Scenario: Implementers can diverge on comment/blank skipping, empty expected_count (${expected_count:-1} vs raw empty), and step_markers handling so populate_fixture repeat counts disagree with lint comparisons while both read the same TSV
- **Proposed resolution**: Paste the same read loop contract into both UPDATED subsections (or scripts/lint-readability-preamble.tsv.md): five tab fields, identical skip rule, identical ${expected_count:-1} for file-level checks, step_markers ignored by the harness except for B5 fixtures

### FINDING_33:
- **Reviewer(s)**: Cursor-dyn-consumer-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:125,plan.txt:52-59
- **Concern**: Failure modes require non-negative integer validation and a malformed-row harness case; UPDATED lint/test sections omit both. Scenario: Malformed expected_count (empty, whitespace, text) silently becomes 1 via ${expected_count:-1} in lint while the test may derive a different fixture count; consumers accept/reject different rows without exiting 2
- **Proposed resolution**: Add the case ... (*[!0-9]*) exit 2 block to lint-readability-preamble.sh UPDATED and add a malformed-tsv-row case to test-lint-readability-preamble.sh UPDATED (as already promised in Failure modes)

### FINDING_34:
- **Reviewer(s)**: Codex-dyn-consumer-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:78-87; scripts/test-lint-readability-preamble.sh:58-93
- **Concern**: The plan adds lint-side step_markers placement checks but the test-script update only says to derive paths and expected_count, not to parse step_markers or generate marker-bounded fixture bodies.. Scenario: The existing compliant fixture shape writes repeated directive lines without <!-- step:... --> anchors. After the proposed lint change, that fixture fails with missing step-marker errors, or the harness may special-case fixtures and drift from lint parsing.
- **Proposed resolution**: Specify that test-lint-readability-preamble.sh reads the same five TSV fields with the same skip/default/validation rules, and for non-empty step_markers creates fixture bodies with those step anchors and directives inside each named step body. Empty step_markers should keep using expected_count for existing fixture assertions.

### FINDING_35:
- **Reviewer(s)**: Codex-dyn-consumer-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:85-86; <TMPDIR>/plan.txt:138; scripts/test-lint-readability-preamble.sh:17-31
- **Concern**: The B6 tsv-is-source-of-truth case is specified as proving the lint script iterates the synthetic TSV row, not that the test script parser reads every TSV row.. Scenario: An implementation could leave the test harness path lists effectively hardcoded, add a synthetic TSV row, and assert lint stderr names that row. B6 would pass while the test parser still ignores new TSV rows for fixture generation and expected_count derivation.
- **Proposed resolution**: Revise B6 so the extra TSV row must be consumed by the test harness parser itself, for example by requiring the manifest-derived fixture writer to create the extra file and asserting the compliant synthetic fixture passes only because that parsed row was handled.
