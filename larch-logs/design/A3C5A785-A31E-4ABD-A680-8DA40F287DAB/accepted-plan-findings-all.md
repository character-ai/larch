### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-plan-adequacy-audit.sh:38-45
- **Concern**: Plan removes Preflight item 3 emergency prose from SKILL.md but the harness still greps for those exact refusal/fallback strings in skills/implement/SKILL.md. Scenario: Implementation follows the plan, then bash scripts/test-plan-adequacy-audit.sh fails even though the plan lists that harness in Testing strategy
- **Proposed resolution**: Add ### UPDATED: scripts/test-plan-adequacy-audit.sh: retarget greps to implement-preflight.sh and/or keep canonical operator strings in SKILL emergency summary only where the harness still expects them


### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:181-188
- **Concern**: Proposed helper invocation passes --emergency when emergency_requested is set to false. Scenario: All boolean flags default to false, so ${emergency_requested:+--emergency} would enable emergency mode on ordinary /implement runs and bypass missing-plan or missing-designed-prefix gates
- **Proposed resolution**: Build argv explicitly and append --emergency only when emergency_requested=true


### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/preflight-plan-audit.md:5-38
- **Concern**: Plan changes audit.txt to refuse-only but leaves the mandatory audit reference requiring audit.txt on pass. Scenario: Preflight item 4 must read this reference, so the proposed SKILL edit can still cause agents to write audit.txt on the pass path, failing the accepted pass-path contract
- **Proposed resolution**: Update the reference contract and envelope section so AUDIT=pass is chat-only and audit.txt is written only for AUDIT=refuse


### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-plan-adequacy-audit.sh:38-45
- **Concern**: Existing harness pins the emergency fallback prose that the plan removes from SKILL.md. Scenario: The required test command will fail after a correct centralization into implement-preflight.sh because the old SKILL.md literals are intentionally gone
- **Proposed resolution**: Update these assertions to pin the new helper-owned contract or move equivalent checks into scripts/test-implement-preflight.sh


### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: .claude/rules/script-md-siblings.md:7-12; scripts/implement-preflight.sh:new; scripts/test-implement-preflight.sh:new
- **Concern**: New scripts are planned without required sibling .md contracts. Scenario: The repo rule requires every scripts/*.sh file to have a neighboring .md contract or stub, so the new helper and harness would violate the script documentation invariant
- **Proposed resolution**: Add scripts/implement-preflight.md and scripts/test-implement-preflight.md with the primary contract and harness stub respectively


### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-plan-adequacy-audit.sh:38-59
- **Concern**: Plan removes Preflight emergency prose from skills/implement/SKILL.md but testing still runs this harness unchanged. Scenario: The harness greps SKILL.md for missing-plan/malformed-plan/empty-title emergency contracts; implementation will fail scripts/relevant-checks.sh / make test-harnesses-5
- **Proposed resolution**: Add scripts/test-plan-adequacy-audit.sh (and its .md contract if present) to plan surfaces; retarget checks to implement-preflight.sh and/or retain minimal SKILL pointers the harness still needs


### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/preflight-plan-audit.md:5-7; skills/implement/references/preflight-plan-audit.md:38-55
- **Concern**: Audit reference still requires writing audit.txt on pass. Scenario: The proposed SKILL change says pass no longer writes $PREFLIGHT_TMPDIR/audit.txt, but item 4 must read this reference and the reference still tells the agent to write AUDIT=pass to that file; the post-PR prompt remains contradictory and can keep producing the pass-path audit file the issue asked to suppress.
- **Proposed resolution**: Add this reference to the UPDATED set and change its contract/envelope text so AUDIT=pass is returned in chat only while audit.txt is written only for AUDIT=refuse, preserving item 5's audit-questions read on refuse.


### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-fence-shape.sh:63-95; scripts/test-implement-fence-shape.sh:162-163; scripts/test-plan-adequacy-audit.sh:38-45
- **Concern**: Existing harness pins conflict with proposed preflight collapse. Scenario: The plan removes the two plan-block read fences and long emergency fallback prose, but these harnesses still require those fences and grep for the removed prose; make test-implement-fence-shape and make test-plan-adequacy-audit fail after the proposed SKILL edit, so the feature cannot pass the repo harness suite.
- **Proposed resolution**: Include these existing harnesses in the plan: recognize the single implement-preflight.sh pre-bootstrap call and adjusted fence counts, and replace removed emergency-prose pins with minimal pins for the helper call, issue.json/plan paths, and canonical bypass tokens.


### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/implement-preflight.sh:79-90
- **Concern**: Emergency missing-plan path treats any non-empty body as plan text instead of whitespace-only as empty. Scenario: Body with only spaces/newlines is written to plan-from-issue.txt; title fallback and empty-title abort never run
- **Proposed resolution**: Mirror current SKILL semantics: treat whitespace-only body like empty; title-strip only after that check


### FINDING_10:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/preflight-plan-audit.md:5-8,38-42
- **Concern**: Audit reference still requires audit.txt on pass. Scenario: The plan changes SKILL.md so audit.txt is written only on AUDIT=refuse, but item 4 still mandates reading this reference, whose contract says to write audit.txt for both AUDIT=pass and AUDIT=refuse. The proposed pass path can keep writing the supposedly removed pass audit file or leave conflicting prompt instructions.
- **Proposed resolution**: Add this reference to the plan and update its contract so AUDIT=pass is returned in chat only, while audit.txt is written only for AUDIT=refuse.


### FINDING_11:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:179-219
- **Concern**: Proposed preflight call can pass --emergency when the flag is false. Scenario: If the final SKILL edit uses the shown ${emergency_requested:+--emergency} shape while emergency_requested=false is set, normal /implement runs execute the emergency bypass path. Missing or malformed plans and missing [DESIGNED] admission can be bypassed unintentionally.
- **Proposed resolution**: Build argv with an explicit true check, for example append --emergency only when [ "${emergency_requested:-false}" = true ], and use the same explicit construction for --repo.


### FINDING_12:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:183,200-201
- **Concern**: Helper-owned missing or malformed emergency fallback omits loud warning preservation. Scenario: The plan removes the long prompt-side missing and malformed fallback paragraphs, but the helper flow only writes the fallback plan and bypass log. A --emergency run can proceed from raw body or title fallback without the existing operator-visible warning about untrusted issue content.
- **Proposed resolution**: Require implement-preflight.sh to print the existing bold warnings for missing-plan and malformed-plan body or title fallbacks before appending the bypass log.


### FINDING_13:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-fence-shape.sh:63-74
- **Concern**: Plan collapses Preflight items 1-3 into one `implement-preflight.sh` fence but does not update the fence-shape harness that pins two guard-only `plan-block read` old-shape anchors and `EXPECTED_OLD=5`.. Scenario: After SKILL.md drops the forked/default plan-block fences, `make test-implement-fence-shape` fails (`expected old=5 new=32`) and blocks merge even when the helper is correct.
- **Proposed resolution**: Add `scripts/test-implement-fence-shape.sh` (and `scripts/test-implement-structure.md` launcher invariants) to plan surfaces: register `implement-preflight.sh` as the single Preflight old-shape anchor and adjust `EXPECTED_OLD` / `old_target_kind` accordingly.


### FINDING_14:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/preflight-plan-audit.md:5-38
- **Concern**: Plan changes item 4 to avoid writing audit.txt on pass but omits the mandatory audit reference. Scenario: Preflight item 4 still requires reading the entire reference, and that reference still tells the agent to write $PREFLIGHT_TMPDIR/audit.txt for AUDIT=pass, violating the acceptance requirement to write the audit envelope file only on refuse
- **Proposed resolution**: Include skills/implement/references/preflight-plan-audit.md in the plan and update its contract/envelope section so pass returns the AUDIT=pass envelope without writing audit.txt, while refuse still writes audit.txt for item 5


### FINDING_15:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-fence-shape.sh:36-69,162-163; scripts/test-plan-adequacy-audit.sh:38-45
- **Concern**: Plan removes the old Preflight fences and emergency prose but omits existing harness updates that pin those old surfaces. Scenario: The proposed SKILL.md edit makes make test-implement-fence-shape expect the wrong old/new fence counts and makes bash scripts/test-plan-adequacy-audit.sh fail on removed missing/malformed fallback prose, so the stated validation path cannot pass
- **Proposed resolution**: Update the existing harnesses to recognize the single implement-preflight.sh pre-bootstrap call and to assert the moved emergency fallback contracts on the helper or its new harness instead of the removed SKILL.md paragraphs


### FINDING_16:
- **Reviewer(s)**: Cursor-dyn-kv-envelope-binding
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:185-202
- **Concern**: The plan replaces Preflight items 1-3 with one `implement-preflight.sh` call but does not add an orchestrator contract to capture stdout, parse the KV envelope (`ADMISSION_RESULT`, `RESUME`, `TITLE`, `BLOCK_PRESENT`, `PLAN_PATH`, `ISSUE_JSON_PATH`, `BYPASS_COUNT`), require all keys on exit 0, and abort before item 4 on non-zero exit.. Scenario: Failure modes mention required keys (plan.txt:229-230) only in the script section; the mandated SKILL.md update bullets (plan.txt:190-206) omit parse/bind prose. The orchestrator can reach item 4 without validating `ISSUE_JSON_PATH` or binding `PLAN_TMP` from `PLAN_PATH`, breaking the chain from collapsed items 1-3 to item 4's issue title/body and plan reads.
- **Proposed resolution**: Add explicit SKILL.md prose after the single fence: capture helper stdout; on exit 0 parse and require all envelope keys; set `PLAN_TMP` from `PLAN_PATH` (or assert it equals `$PREFLIGHT_TMPDIR/plan-from-issue.txt`); verify `ISSUE_JSON_PATH` is readable before item 4; on exit 2/3 abort without item 4.


### FINDING_17:
- **Reviewer(s)**: Codex-dyn-kv-envelope-binding
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-implement-fence-shape.sh:33-38,63-69,162-163; <TMPDIR>/plan.txt:176-204
- **Concern**: The plan replaces the two preflight plan-block fences but does not update the structural harness that still recognizes only those fences and expects old=5. Scenario: After SKILL.md uses one scripts/implement-preflight.sh pre-bootstrap fence, make test-implement-fence-shape fails because the helper fence is treated as new-shape and the old/new counts no longer match
- **Proposed resolution**: Add scripts/test-implement-fence-shape.sh to the plan; recognize scripts/implement-preflight.sh as the single preflight old-shape call and update expected counts


### FINDING_18:
- **Reviewer(s)**: Codex-dyn-kv-envelope-binding
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-plan-adequacy-audit.sh:38-45; <TMPDIR>/plan.txt:203-222
- **Concern**: The plan removes long emergency fallback prose from SKILL.md but leaves the targeted audit harness that greps for those exact paragraphs out of modified files. Scenario: After implementation, bash scripts/test-plan-adequacy-audit.sh in the plan's own testing strategy fails even if the helper owns fallback correctly
- **Proposed resolution**: Update the harness to assert the new helper ownership and retained bypass grammar instead of the removed body/title fallback paragraphs


### FINDING_19:
- **Reviewer(s)**: Codex-dyn-kv-envelope-binding
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/preflight-plan-audit.md:5-7,38-55; <TMPDIR>/plan.txt:197-199
- **Concern**: The plan only changes SKILL.md to avoid audit.txt on pass, but the mandatory item-4 reference still instructs writing audit.txt for both pass and refuse. Scenario: When item 4 reads the reference, the pass path can still write $PREFLIGHT_TMPDIR/audit.txt, violating the requested pass-path contract
- **Proposed resolution**: Update preflight-plan-audit.md so AUDIT=pass is returned in chat only and $PREFLIGHT_TMPDIR/audit.txt is written only for AUDIT=refuse; adjust related tests


### FINDING_20:
- **Reviewer(s)**: Cursor-dyn-bypass-token-compat
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:81-90
- **Concern**: [SCOPE-REDUCTION] Emergency body fallback uses "nonblank"/"blank" instead of whitespace-trimmed empty. Scenario: Whitespace-only issue bodies are treated as plan text instead of triggering title fallback, diverging from skills/implement/SKILL.md:200-201 and producing wrong plan-from-issue.txt under --emergency
- **Proposed resolution**: Match current contract: treat body as empty when trim is empty; use title fallback and missing-plan bypass only after trim fails


### FINDING_21:
- **Reviewer(s)**: Cursor-dyn-strip-prefix-fidelity
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:81-83
- **Concern**: Body fallback uses nonblank instead of empty/whitespace-only. Scenario: Preflight SKILL today treats a whitespace-only issue body as empty and falls through to title strip; the plan writes any nonblank body verbatim, so body " " becomes the emergency plan and title strip never runs
- **Proposed resolution**: Match skills/implement/SKILL.md:200: use the same empty/whitespace-only test for body before choosing title fallback in steps 6 and 7




### FINDING_1: Old-shape fence validation rejects the new preflight helper fence
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The planned multi-line preflight fence can fail the existing single-logical-command shape test even though it still invokes the helper once.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In test-implement-fence-shape.sh, exempt preflight-helper from the one-logical-command check while still requiring exactly one scripts/implement-preflight.sh invocation


### FINDING_2: TITLE envelope contract is incomplete on success and for titles with equals signs
- **Reviewer(s)**: Cursor-Arch, Cursor-dyn-kv-envelope-contract, Codex-dyn-kv-envelope-contract
- **Severity**: important
- **Concern**: The helper can omit `TITLE` on successful admission, and the parser contract does not require first-`=` splitting or compatible single-line normalization. Valid GitHub titles can be missing, truncated, or rejected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: After writing issue.json, always set envelope TITLE from the fetched title (empty only if truly absent)
  - From Cursor-dyn-kv-envelope-contract: A prompt-side parser that splits on every `=`, or a Bash helper that does not normalize newlines/whitespace in TITLE, can truncate TITLE or fail envelope validation on otherwise-valid issues. Document in `scripts/implement-preflight.md` and SKILL envelope-parse prose: split each line on the first `=` only; normalize TITLE with the same single-line rules as `_single_line`; source TITLE from `issue.json` on success (admission often omits TITLE on `ADMISSION_RESULT=pass`, `python/admission.py:214-215`).
  - From Codex-dyn-kv-envelope-contract: Update the SKILL.md preflight parser contract and helper contract to say parse exact allowed keys by prefix, split at the first "=", and preserve the remaining value verbatim as a single line. Add one targeted harness case with a title containing spaces and "=".


### FINDING_3: Preflight audit reference still names stale inputs and audit.txt behavior
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: important
- **Concern**: The audit reference still points item 4 at live `gh issue view` and plan-block reads, and still implies unconditional `audit.txt` writes, conflicting with the helper-owned issue JSON and refuse-only audit file design.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Update preflight-plan-audit.md When-to-load to issue.json plus plan-from-issue.txt, and make the Contract header refuse-only for audit.txt
  - From Cursor-Requirements: Add When-to-load/input steps: after implement-preflight.sh exit 0, read title/body from $PREFLIGHT_TMPDIR/issue.json and plan from $PREFLIGHT_TMPDIR/plan-from-issue.txt; remove plan-block read and gh issue view prerequisites


### FINDING_5: Protocol directive still describes three mechanical preflight calls
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The top-level implement protocol can still instruct the orchestrator to run admission, issue fetch, and plan-block read separately, conflicting with the one-helper design.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Rewrite the Protocol Directive and Preflight intro to name scripts/implement-preflight.sh as the sole mechanical items 1-3 surface


### FINDING_6: Harness misses emergency admission carve-out and --repo forwarding
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: The proposed tests can pass even if `--emergency` still blocks `missing-designed-prefix`, or if the helper fails to forward `--repo` to admission.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add one offline case where admission gate exits 5 with ADMISSION_RESULT=missing-designed-prefix, run helper with --emergency --repo owner/repo, assert it continues, appends BYPASS kind=missing-designed-prefix issue=<N>, and forwards --repo owner/repo to admission gate


### FINDING_7: Direct helper invocation may fail without executable mode
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: The SKILL fence runs the new helper directly, but planned checks only require the file to exist. A non-executable helper can pass checks and fail at runtime.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Use bash "${CLAUDE_PLUGIN_ROOT}/scripts/implement-preflight.sh" in the fence, or explicitly require chmod 755 and add an executable assertion for scripts/implement-preflight.sh


### FINDING_9: Plan-block read capture may miss quiet-mode key output
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The helper may parse stdout from `plan-block read`, but quiet mode can route required `BLOCK_PRESENT` or `MALFORMED` keys away from stdout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Wrap plan-block read with LARCH_QUIET_DISABLE=1 (match admission gate) before parsing stdout KVs


### FINDING_10: Malformed emergency fallback may omit a valid BLOCK_PRESENT envelope value
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: A malformed plan can emit `MALFORMED` without `BLOCK_PRESENT`; even if emergency fallback recovers, the required envelope can still fail validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Define the synthesized malformed-path envelope explicitly. For example, emit BLOCK_PRESENT=true when MALFORMED is set, and add the malformed emergency harness assertion for that envelope value.


### FINDING_12: Missing-plan emergency branch can skip or overwrite BYPASS handling
- **Reviewer(s)**: Cursor-dyn-bypass-log-compat
- **Severity**: important
- **Concern**: The non-empty body fallback can skip the `missing-plan` BYPASS append, and ambiguous indentation can allow title fallback to run afterward and overwrite the synthesized plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-bypass-log-compat: Rewrite step 6 as explicit if/else: (a) non-empty body writes plan-from-issue.txt prints raw-body warning appends BYPASS kind=missing-plan issue=N to $PREFLIGHT_TMPDIR/emergency-bypass.log; (b) whitespace-empty body runs title strip abort-on-empty write title warning append same BYPASS line; do not fall through between branches


### FINDING_13: BYPASS append destination is not explicit in the algorithm
- **Reviewer(s)**: Cursor-dyn-bypass-log-compat
- **Severity**: important
- **Concern**: The plan names BYPASS payloads but not the log file target in key algorithm steps, so implementers can append to stdout or the wrong file and break bootstrap compatibility.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-bypass-log-compat: In steps 3 6 and 7 specify append target explicitly: printf '%s\n' "BYPASS kind=<token> issue=<N>" >> "$PREFLIGHT_TMPDIR/emergency-bypass.log" (exit 2 on failure per edge case line 143); keep BYPASS_COUNT equal to the number of lines appended


### FINDING_14:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-fence-shape.sh:85-101
- **Concern**: [SCOPE-REDUCTION] Preflight helper fence needs explicit validator carve-outs not fully specified. Scenario: The planned SKILL fence uses `preflight_args=(...)`, `if [ -n "${UPSTREAM_REPO:-}" ]`, and `if [ "${emergency_requested:-false}" = true ]` before one `implement-preflight.sh` call. Current `validate_old` requires exactly one logical command and rejects any `if` in the joined command string; only bumping `EXPECTED_OLD` to 4 will fail CI even when the helper call is correct.
- **Proposed resolution**: Extend `test-implement-fence-shape.sh` for `preflight-helper`: skip the single-command and inline-control bans; assert exactly one `scripts/implement-preflight.sh` invocation and the guard/`--repo`/`--emergency` branches described in the plan.




### FINDING_1: Emergency admission bypass can fail before parsing stdout
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The preflight helper must parse `ADMISSION_RESULT` before acting on the admission gate exit code. Otherwise allowed emergency bypasses for `missing-designed-prefix` may exit as failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In step 3, parse stdout first; continue on `ADMISSION_RESULT=missing-designed-prefix` with `--emergency` regardless of rc; reserve rc-based exit **2** for all other blocked results


### FINDING_2: Stdout envelope contract conflicts with line-based KV parsing
- **Reviewer(s)**: Cursor-Innovation, Cursor-dyn-envelope-consistency
- **Severity**: important
- **Concern**: The plan describes the stdout envelope as a single-line contract while the parser and examples expect one `KEY=value` record per line. This can mis-bind or drop fields, especially when values contain spaces or `=`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Pin implement-preflight.md: emit one KV line per allowed key; values must be single-line; orchestrator scans stdout for the allowed key set only
  - From Cursor-dyn-envelope-consistency: Replace "single-line envelope" with "one `KEY=value` record per line; values single-line; embedded `=` allowed in values" and align the example comment with the contract doc.


### FINDING_3: Emergency fallback JSON extraction is underspecified
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The emergency fallback depends on issue title and body extraction, but the plan does not define a safe JSON parsing mechanism. Fragile shell parsing can corrupt escaped newlines, quotes, or abort behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Specify one approach in the helper contract, e.g. python3 -c/json module for .body and .title with whitespace-only empty checks; exit 2 on parse failure without printing body


### FINDING_5: Admission refusal templates are not pinned
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: Moving admission handling into the helper without exact refusal templates can change operator-visible behavior. Generic errors may drop required `ADMISSION_RESULT`, `ADMISSION_ERROR`, `BLOCKERS`, or `TITLE` context.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Copy the exact refusal templates from skills/implement/SKILL.md item 1 into implement-preflight.md, keyed by ADMISSION_RESULT and exit code
  - From Cursor-Requirements: Pin the exact admission refusal templates in `scripts/implement-preflight.sh` / `scripts/implement-preflight.md` (mirror current SKILL item 1 branches), and extend `scripts/test-implement-preflight.sh` case 1 to assert the managed-prefix refusal includes the `preflight: admission blocked` prefix plus `ADMISSION_RESULT=`.


### FINDING_6: Warning regression harness may lose exact trust-boundary text
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Replacing exact grep pins with vague placeholders can let the harness pass while dropping the current emergency and untrusted-data operator warnings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Keep the current exact -Fq strings (or move them verbatim into implement-preflight.md) and grep the script for those literals, not descriptive placeholders




### FINDING_1: Malformed-plan refusal is not byte-pinned
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Non-emergency malformed-plan refusal can lose the parsed `MALFORMED=` reason while still passing the proposed harness, because the plan only requires a distinct refusal and a vague substring grep.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin one exact non-emergency malformed refusal template in `scripts/implement-preflight.sh` and `scripts/implement-preflight.md` (include the `MALFORMED=` token) and assert that literal in `scripts/test-implement-preflight.sh` case 4


### FINDING_2: Fork-env-first ordering is not pinned
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The Protocol Directive rewrite does not explicitly preserve the required fork-env-first sequence before `implement-preflight.sh` and Step 0 bootstrap, which can drop `--repo "$UPSTREAM_REPO"` on forked runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In the Protocol Directive rewrite, pin the three-step sequence explicitly: (1) `admission fork-env` when `forked_target=true`; (2) one `implement-preflight.sh` call; (3) Step 0 bootstrap unchanged.


### FINDING_4: Plan-adequacy audit retarget leaves stale SKILL greps
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The proposed `test-plan-adequacy-audit.sh` retarget only removes two long SKILL paragraph checks, leaving other greps for refusal and emergency fallback prose that moves into `scripts/implement-preflight.sh`; this can block CI after the SKILL prose is removed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: In `### UPDATED: scripts/test-plan-adequacy-audit.sh`, explicitly remove or replace every SKILL grep for relocated strings (38-45), including the malformed empty-body cross-reference at line 43 that has no helper literal. Retarget pins to `scripts/implement-preflight.sh` exact refusal/warning strings from plan steps 8-9.


### FINDING_5:
- **Reviewer(s)**: Cursor-dyn-envelope-alignment
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:256-257 vs plan.txt:525-542
- **Concern**: [SCOPE-REDUCTION] Exit-2 partial envelope clause conflicts with parser contract. Scenario: Emitter step 10 says to emit the seven-key envelope on handled exit 2 when values are known, but the SKILL.md update aborts on any non-zero helper exit and only parses the full key set on exit 0. No branch matrix lists which keys are known for admission refusal, gh failure, missing-plan exit 2, empty-title abort, or malformed refusal. Implementers may emit inconsistent partial KVs, omit the envelope entirely, or add harness expectations with no parser consumer.
- **Proposed resolution**: Remove the exit-2 envelope sentence from implement-preflight.sh step 10 and implement-preflight.md, or add an explicit per-branch table (branch, exit code, which of the seven keys are emitted). Prefer removal for SIMPLE: parser never consumes exit-2 stdout.




### FINDING_2: Admission refusal templates drop parsed-field echoes
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Refusal templates pin only generic first lines and omit parsed-field echo lines for `has-blockers` and some title-based branches. This can drop blocker or title context that current runs expose for operators and debugging.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Pin branch bodies in implement-preflight.sh and implement-preflight.md: has-blockers must print `BLOCKERS=<value>`; managed-prefix, report-title, and non-emergency missing-designed-prefix must print `TITLE=<value>` when parsed; add harness case stubbing `ADMISSION_RESULT=has-blockers` with `BLOCKERS=1,2`


### FINDING_3: RESUME envelope default is ambiguous on normal pass
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-dyn-kv-envelope-alignment
- **Severity**: important
- **Concern**: The success envelope requires `RESUME`, but admission omits `RESUME=` on the normal non-resume pass path. Without a pinned default, implementations may omit the key or choose incompatible sentinel values, causing prompt-side preflight validation or resume semantics to fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Pin one rule in implement-preflight.sh and implement-preflight.md: copy RESUME only when admission stdout contains RESUME=true; otherwise emit RESUME= with a zero-length value (physical line RESUME=). Forbid the literal token empty. Add a harness case on the normal pass path.
  - From Cursor-dyn-kv-envelope-alignment: In implement-preflight.sh step 10 and implement-preflight.md, pin: when admission stdout lacks RESUME=, emit RESUME=false; when RESUME=true (resume sentinel path, admission.py:188-189), forward RESUME=true. Drop the ambiguous empty token from the RESUME=<true|false|empty> template
  - From Cursor-dyn-kv-envelope-alignment: In `implement-preflight.sh` step 10 and `implement-preflight.md`, pin: when admission stdout lacks `RESUME=`, emit `RESUME=false`; when `RESUME=true` is present (resume sentinel path at ```188:189:python/admission.py```), forward it. Replace the ambiguous `RESUME=<true|false|empty>` template with `RESUME=false|true`


### FINDING_6: Source grep pins confuse markdown placeholders with executable output
- **Reviewer(s)**: Cursor-dyn-harness-pin-coherence
- **Severity**: important
- **Concern**: Harness pins check executable source for exact user-visible strings containing documentation placeholders like `<N>`, while the script is expected to emit runtime-interpolated values. This can false-fail correct implementations or force placeholder literals into source.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-harness-pin-coherence: Split pins: keep stable technical tokens (`BYPASS kind=`, `LARCH_QUIET_DISABLE=1`, `$PREFLIGHT_TMPDIR/emergency-bypass.log`) on `implement-preflight.sh`; pin full warning/refusal templates in `implement-preflight.md` (already specified there) or use substring pins without `<N>`; reserve byte-exact stdout checks to `scripts/test-implement-preflight.sh`.
  - From Cursor-dyn-harness-pin-coherence: Align `test-implement-preflight.sh` with stdout assertions (already used for malformed refusal) or grep stable substrings/`implement-preflight.md` contract literals; drop "script contains exact … with `<N>`" requirements for executable source.



