### FINDING_1: No-stall success path skips escalation-on-success reporting
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The escalation-on-success procedure is only reachable through `stall-recovery.md`, which is skipped when no stall tracking layer is active. A successful no-stall run with a non-empty escalation ledger can therefore finish without filing the required escalation issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a dedicated Step 18 escalation-on-success block in skills/implement/SKILL.md (between 18a skip and 18b) that always reads the ledger and runs investigation/file-or-print; keep stall-recovery.md terminal-only
  - From Cursor-Innovation: Add an explicit Step 18 sub-step before 18b (outside the STALL_TRACKING gate) with the full investigate-compose-file contract; keep stall-recovery.md success path only for post-recovery clears
  - From Cursor-Pragmatic: Add an explicit Step 18 branch (e.g. 18a.5) that runs before Step 18b when every stall layer is false: read the ledger, run root-cause investigation, compose escalation-success report, file or Tier-B print; reference it from stall-recovery.md and optionally a thin step-18 wrapper script
  - From Cursor-Requirements: Add an explicit no-stall Step 18 hook in skills/implement/SKILL.md (before 18b): read the canonical ledger, run investigation plus compose or file when non-empty, and skip when empty. Point the hook at the new stall-recovery.md procedure instead of the 18a-only gate.


### FINDING_2: Step 8+ CI-fix handoffs can edit before durable ledger recording
- **Reviewer(s)**: Codex-Arch, Codex-Requirements
- **Severity**: important
- **Concern**: Step 8+ autonomous main-agent CI-fix paths may defer or omit ledger recording before main-agent edits begin. A crash or later success can leave no durable escalation record.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Remove the Step 18 token-deferral alternative. Require python/ship.py or the Step 8 orchestrator branch to call record-escalation before the main-agent CI-fix procedure starts.
  - From Codex-Requirements: Add UPDATED skills/implement/references/ship-pr-exit-matrix.md with record-escalation before autonomous main-agent CI-fix edits and keep SKILL.md in sync


### FINDING_3: Lint-fix failed statuses lack ledger coverage
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: The plan excludes lint-fix-loop `failed` statuses from escalation ledger coverage, despite the scope requiring coverage for failed and main-agent-required lint-fix sites.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Record ledger events or ledger-ready tokens for failed and main-agent-required at the enumerated lint-fix sites. Keep no-ledger assertions only for applied no-changes and structural failures outside that surface.


### FINDING_4: Stall-recovery inline repair dispatches do not record escalations
- **Reviewer(s)**: Codex-Innovation, Codex-dyn-escalation-site-coverage
- **Severity**: important
- **Concern**: Step 18a recovery dispatch branches can perform inline main-agent repair for `step2-impl` or `step8-shippr` without first recording an escalation ledger event. A recovered run can clear the stall with an empty ledger.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Move the planned `record-escalation` calls into `stall-recovery.md` Step 5 dispatch branches before inline main-agent repair
  - From Codex-dyn-escalation-site-coverage: Add explicit record-escalation calls to stall-recovery.md dispatch branches before main Claude edits or reships for step2-impl and step8-shippr, and mirror those trigger/site tokens in the Tier B allowlist and tests.


### FINDING_5: Step 5 main-agent-vote-required handoff lacks ledger recording
- **Reviewer(s)**: Codex-Pragmatic, Cursor-dyn-escalation-site-coverage
- **Severity**: important
- **Concern**: The Step 5 review loop can emit `main-agent-vote-required`, then succeed after main-agent adjudication, but the planned ledger coverage does not record that handoff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Add record-escalation before the main-agent-vote-required branch body with stable site and trigger tokens, and cover the success-with-ledger path for that status.
  - From Cursor-dyn-escalation-site-coverage: Add `main-agent-vote-required` to the SKILL `record-escalation` list and instrument `review-implement-step5-loop.sh` (or `run-step5-review.sh` stdout parsing) before the MAV branch returns control to the orchestrator.


### FINDING_6: Step 5 lint-fix ledger sites use rejected helper tokens
- **Reviewer(s)**: Codex-Pragmatic, Codex-dyn-escalation-site-coverage
- **Severity**: important
- **Concern**: Planned Step 5 self-review and MAV lint ledger sites use `step5-self-review` and `step5-mav`, but `lint-fix-loop.sh` currently accepts only a narrower site set. Those paths can fail before emitting ledger-ready information.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Explicitly extend lint-fix-loop site validation, docs, and tests for step5-self-review and step5-mav, or keep --site step5 and pass separate ledger site and trigger tokens from the caller.
  - From Codex-dyn-escalation-site-coverage: Add step5-self-review and step5-mav to lint-fix-loop site validation, labels, docs, tests, and planned Tier B site allowlist, or change those SKILL call sites and ledger records to an accepted stable site token.


### FINDING_7: Tier B bounded root-cause can leak client data
- **Reviewer(s)**: Codex-Requirements, Cursor-dyn-tier-b-boundary-drift, Codex-dyn-tier-b-boundary-drift
- **Severity**: important
- **Concern**: The Tier B bounded root-cause contract does not sufficiently separate full evidence-citing Tier A findings from public bounded Tier B prose. Prompt-composed text can include client paths, branches, PR URLs, plan text, issue text, or log excerpts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add the instruction to the root-cause finding procedure and stall-recovery-report.md contract, and require bounded-root-cause-file to be produced under that constraint
  - From Cursor-dyn-tier-b-boundary-drift: Add a helper validation step for `--bounded-root-cause-file` before Tier B compose (deny `/`, `github.com`, PR URL shapes, lifecycle issue markers, and larch-log path patterns). Split Tier A `--root-cause-file` (full citations) from Tier B bounded prose. Document the instruction constraint in `stall-recovery-report.md` and extend sentinel tests beyond secrets.
  - From Codex-dyn-tier-b-boundary-drift: Split the contract: the full Tier A finding may cite paths and evidence content, but the Tier B bounded-root-cause file must use larch-internal tokens and artifact labels only, with no client paths, branch, PR URL, plan, issue, or log excerpts. Ensure Tier B rendering consumes only bounded-root-cause-file.


### FINDING_8: Step 5 wrapper test coverage is omitted
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The plan changes `run-step5-review.sh` behavior but omits the targeted regression harness needed to verify stdout preservation, ledger creation, and ledger-write failure behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add UPDATED scripts/test-run-step5-review.sh and .md tests for coder-main-agent-required stdout preservation, ledger creation, and fail-open Tool Failures on ledger write failure


### FINDING_9: Matched classifier pattern has no emission contract
- **Reviewer(s)**: Cursor-dyn-tier-b-boundary-drift, Codex-dyn-tier-b-boundary-drift
- **Severity**: important
- **Concern**: Tier B requires a matched classifier pattern, but the current classifier emits only derived classification KVs. Without a stable emitted token, render code may omit the field, invent it, or leak raw evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-tier-b-boundary-drift: Extend `classify` (or a sibling KV) to emit a closed `MATCHED_CLASSIFIER_PATTERN` token; add `safe_matched_pattern_value` plus TSV `transform=enum` rows on every Tier B surface. Document the closed token set in `stall-recovery-report.md` Classifier Evidence.
  - From Codex-dyn-tier-b-boundary-drift: Add a stable CLASSIFIER_PATTERN token at the classifier decision point, emit it from classify, sanitize it through the Tier B enum, add TSV/code/doc parity rows, and test each classifier branch.


### FINDING_10: Tier B bail-token enum is underspecified
- **Reviewer(s)**: Cursor-dyn-tier-b-boundary-drift
- **Severity**: important
- **Concern**: The plan expands bail-token rendering only around classifier dispatch tokens, not the full set of renderable bail reasons. Real stall tokens may still render as `redacted`, or the allowlist may grow inconsistent phantom values.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-tier-b-boundary-drift: Define the Tier B bail enum as an explicit union: current `safe_bail_reason_value`, `classify_from_evidence` dispatch `case`, `codex-manifest-schema.md` §Bail-reason tokens, and orchestrator/bootstrap tokens from `implement-bootstrap.sh` / Step 12d. Keep non-union free-form tokens as `redacted`. Add a `lint` or harness check that union sets stay in sync.


### FINDING_11: Tier B allowlist surface mapping is incomplete
- **Reviewer(s)**: Cursor-dyn-tier-b-boundary-drift
- **Severity**: important
- **Concern**: New Tier B allowlist rows do not pin which output surfaces receive each field after `bug-comment` removal. Consumer chat-print can omit attempt history or operational fields while parity still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-tier-b-boundary-drift: Specify per-field surface mapping in the allowlist edit: mirror expanded rows on `chat-print` and Tier A `bug-body`; drop `bug-comment` rows; move attempt/ledger fields to the unified terminal body surface. Update `code_allowlist_lines()` and the doc table in the same change.


### FINDING_12: Dispatcher identity lacks a terminal-failure data path
- **Reviewer(s)**: Codex-dyn-tier-b-boundary-drift
- **Severity**: important
- **Concern**: Tier B requires dispatcher identity, but terminal-failure classification inputs may not persist a safe dispatcher token from Step 2 or Step 8+ handoffs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-tier-b-boundary-drift: Persist a safe dispatcher token from Step 2 and Step 8+ handoffs into classification/report inputs, or explicitly scope the dispatcher identity field to ledger rows if that is the intended contract.


### FINDING_13:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/lint-fix-loop.sh:517-576; skills/implement/SKILL.md:468,666
- **Concern**: [SCOPE-REDUCTION] Optional direct ledger writes in `lint-fix-loop.sh` create a second owner for the same handoff. Scenario: A Step 3 or Step 6 `main-agent-required` return can be recorded by both the helper and the prompt-side caller, producing duplicate ledger evidence for one escalation
- **Proposed resolution**: Make `lint-fix-loop.sh` emit ledger-ready tokens only; keep `record-escalation` at the call sites that hand control to the main agent


### FINDING_14:
- **Reviewer(s)**: Cursor-dyn-kv-stdout-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:148-156 and plan.txt:148-157 vs plan.txt:182-186
- **Concern**: [SCOPE-REDUCTION] Duplicate record-escalation ownership for Step 5 coder-main-agent-required. Scenario: Plan assigns ledger writes to run-step5-review.sh before return and also tells SKILL.md orchestrator to call record-escalation before main-agent repair for the same handoff; lint-fix-loop is similarly optional in-script while SKILL lists Step 3/5/6 orchestrator calls
- **Proposed resolution**: Pick one owner per surface: prefer script-side recording in run-step5-review.sh and lint-fix-loop.sh; remove duplicate SKILL.md record-escalation bullets for those script-owned paths or gate orchestrator calls on a ledger idempotency sentinel


### FINDING_15:
- **Reviewer(s)**: Codex-dyn-kv-stdout-contract
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:148-162,182-185; skills/implement/SKILL.md:591-605; scripts/run-step5-review.sh:237
- **Concern**: [SCOPE-REDUCTION] Same escalation can be recorded by both the wrapper or helper and the prompt-side caller. Scenario: `coder-main-agent-required` can be recorded in `run-step5-review.sh` before return and again in the Step 5 branch before main-agent edits; lint-fix `main-agent-required` has the same ambiguity between `lint-fix-loop.sh`, SKILL.md, and ship-pr callers. The ledger can duplicate one escalation and confuse the root-cause target.
- **Proposed resolution**: Pick one writer per surface. Prefer wrapper-owned Step 5 review recording and caller-owned lint-fix recording. Keep non-writers limited to existing stdout KVs used to derive site and trigger.




### FINDING_1: Canonical escalation ledger path is not pinned
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The design requires callers to pass an escalation ledger path, but does not pin one canonical tmpdir-relative path. Different call sites may write or read different files, so Step 18a.5 can miss recorded escalations and skip required escalation-on-success filing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Define one path (for example $IMPLEMENT_TMPDIR/stall-recovery-escalation-ledger.tsv), document it in stall-recovery-report.md, and require all record-escalation call sites to use it
  - From Cursor-Pragmatic: Call sites can write to different ledger files; Step 18a.5 reads one path and misses events recorded elsewhere, yielding false "success with no escalation" Pin default `$IMPLEMENT_TMPDIR/stall-recovery-escalation-ledger.tsv` in the contract, document init semantics, and require all owners to use that default unless explicitly overridden
  - From Cursor-Requirements: Call sites pass ad hoc --ledger-file values; Step 18a.5 may read an empty ledger while events were appended elsewhere, missing escalation-on-success filing Pin one default path (e.g. $IMPLEMENT_TMPDIR/escalation-ledger.tsv) in stall-recovery-report.md and reference it from every record-escalation and teardown reader


### FINDING_3: Tier B root-cause and title inputs can leak client data
- **Reviewer(s)**: Codex-Arch, Codex-Innovation
- **Severity**: important
- **Concern**: Tier B validation does not bind every published bounded prose and title input to the required client-data exclusions. Root-cause text or synthesized title text can include repo paths, branch names, repo names, PR URLs, plan text, issue content, or other client data and still appear in the consumer report.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: For Tier B, derive the title summary from the validated bounded root-cause artifact or run the same Tier B exclusion validator on title input before output. Fall back to an enum-only title on rejection.
  - From Codex-Innovation: Apply the Tier B bounded validator to both root-cause prose and title summary, and reject repo-relative path shapes plus known client repo, branch, PR, plan, and issue tokens available from state inputs


### FINDING_4: Python CI handoff recording has duplicate owners
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The Python ship-pr path appears to assign CI handoff recording to both `python/ship.py` and the SKILL.md orchestrator path. A single CI handoff can append duplicate ledger rows, which breaks the one-issue-per-run evidence model and can skew root-cause targeting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: A successful CI handoff can append two ledger rows for one event, breaking the one-issue-per-run evidence model and escalation-on-success root-cause targeting Pick one owner: prefer orchestrator-only (mirror bash: driver returns handoff, caller records once before edits) and drop ship.py recording; extend the existing no-duplicate rule to Python paths


### FINDING_5: Step 18a.5 can run after terminal recovery handling
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Step 18a.5 only skips on an empty ledger. If terminal stall handling has already composed a terminal report or written issue input, Step 18a.5 can still file an escalation-success issue, causing an extra issue for the same run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: After 18a terminal handling (`STALL_TRACKING` still true, terminal report composed, or `stall-recovery-issue-input.md` written), 18a.5 can still file an escalation-success issue in addition to the terminal report Add explicit 18a.5 skip predicates: all `STALL_TRACKING` layers false, no terminal report artifact from 18a, and run outcome succeeded; document in stall-recovery.md and SKILL.md


### FINDING_6: CI-fix exit matrix omits escalation recording before edits
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The ship-pr CI-fix exit matrix is a mandatory reference for CI handoff routing, but it is not updated to require `record-escalation` before main-agent CI-fix edits. Implementers following the matrix can miss required escalation ledger events.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Implementers following the matrix can run autonomous CI-fix edits (step 6) without ever recording the handoff, missing escalation-on-success filing on later green runs Add one matrix step before repo edits: orchestrator calls `record-escalation` with stable site/trigger tokens; list `skills/implement/references/ship-pr-exit-matrix.md` in Files to modify/create


### FINDING_7: Compound ci-local-unfixable tokens are absent from Tier B union
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Tier B requires full bail-token enum rendering, but bash can emit compound `ci-local-unfixable:<sanitized-list>` values while the proposed allowlist is exact-match only. Common local-unfixable handoffs can therefore render as `redacted`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Consumer Tier B bodies render `redacted` for common local-unfixable handoffs, defeating requirement 5 expanded operational fields Define union handling for `ci-local-unfixable` prefix (enum base + sanitized suffix transform) and align Python `needs_user_reason` tokens with bash; add harness rows for compound tokens


### FINDING_8: Issue title input is not constrained to one safe heading
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: Root-cause title text can contain newlines or markdown heading syntax. When written into the issue input file, `/larch:issue` batch parsing can treat injected headings as extra issue items.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Validate --title-file or equivalent title summary before issue-input-file output: reject newlines, control chars, and markdown heading starts; then compose exactly one ### heading


### FINDING_9: Success-with-ledger filing has duplicate call sites
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The plan can allow both Step 7 recovery handling and Step 18a.5 to file an escalation-success issue for the same ledger. A recovered stall run can therefore violate the one-issue-per-run requirement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: A stall run that recovers (step 7 clears STALL_TRACKING) and also reaches Step 18a.5 before 18b could file two escalation-success issues for the same ledger, breaking one-issue-per-run Add one owner: either only Step 18a.5 invokes success-with-ledger before 18b and step 7 defers, or add a durable filed sentinel / skip 18a.5 when step 7 already composed escalation-success


### FINDING_10: Root-cause artifact paths and verdict schema are unspecified
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The mandatory root-cause flow does not pin artifact paths or a verdict-file schema for root-cause, bounded root-cause, and title inputs. The helper composition path can fail closed or diverge between terminal and escalation reports.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Investigation can succeed in chat but helper composition fails closed or diverges across terminal vs escalation paths because --root-cause-file / --bounded-root-cause-file / --title-file inputs are unspecified Pin tmpdir artifact paths and verdict-file schema in stall-recovery.md and reference them from SKILL.md Step 18a/18a.5


### FINDING_11: SKILL.md Step 18a still points at first-detection filing
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The plan updates stall-recovery references, but SKILL.md Step 18a prose can still describe first-detection filing and bug-comment behavior. That can regress the design back to first-detection filing instead of terminal-only reporting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Implementers updating stall-recovery.md only may leave SKILL anti-halt bullets instructing first-detection filing, regressing terminal-only filing Extend the SKILL.md update to remove/replace first-detection and bug-comment references and point Step 18a/18a.5 at the new terminal-only and escalation-success procedures


### FINDING_12:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/scripts/stall-recovery-report-allowlists.tsv:1-30; skills/implement/scripts/stall-recovery-report.md:103-134
- **Concern**: [SCOPE-REDUCTION] Tier A remains mirrored into allowlist rows despite Tier A requiring secrets-only filtering. Scenario: Tier A report composition can stay bound to TSV parity and enum fields, so dev-clone terminal reports omit validated logs, branches, PR URLs, and full evidence that the feature explicitly requires. It also keeps Tier A in Tier B lint machinery.
- **Proposed resolution**: Remove Tier A bug-body from the allowlist/parity plan. Keep TSV/code/doc allowlists only for Tier B chat-print/consumer body. Render Tier A from the composed body passed only through redact secrets.


### FINDING_13:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/stall-recovery.md:21-24
- **Concern**: [SCOPE-REDUCTION] Planned Step 18a step8-shippr recording covers ordinary reships, not only script-to-main-agent escalations. Scenario: A transient-infra or normal retry re-enters ship-pr and succeeds. The ledger is non-empty solely because of the retry, so Step 18a.5 files an escalation-success issue even though no escalation event occurred.
- **Proposed resolution**: Record Step 18a ledger entries only on branches that hand work to Main Claude for inline repair. Do not record plain step8-shippr retry/reship dispatches.


### FINDING_14:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-fix-loop.sh:41-44
- **Concern**: [SCOPE-REDUCTION] Plan emits ledger-ready tokens for lint-fix `failed` but issue scope covers only script-to-main-agent handoffs. Scenario: At Step 3 `LINT_FIX_STATUS=failed` sets `STALL_TRACKING=true` and skips to Step 18 without main-agent repair (`skills/implement/SKILL.md`); recording `failed` as escalation mislabels terminal stalls as expensive handoffs and can pollute escalation-success or terminal ledger narratives
- **Proposed resolution**: Limit ledger token emission and any `record-escalation` call sites to `main-agent-required` paths that actually route to orchestrator main-agent repair; drop `failed` from the lint-fix escalation contract and tests unless a caller explicitly hands off to the main agent


### FINDING_15:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/scripts/stall-recovery-report-allowlists.tsv:1-29
- **Concern**: [SCOPE-REDUCTION] Tier A bug-body is still planned as an allowlist surface. Scenario: Tier A is required to drop the field allowlist and use secret redaction only, but mirroring Tier A bug-body rows into the TSV preserves the old public-surface model and can either omit required dev-clone evidence or make SECURITY.md inaccurate
- **Proposed resolution**: Keep TSV, code, and doc allowlist parity scoped to Tier B chat-print only; make Tier A body composition bypass field allowlists and run only the secret redactor


### FINDING_16:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/stall-recovery-report-allowlists.tsv:1-31
- **Concern**: [SCOPE-REDUCTION] Plan keeps unified Tier A bug-body in the TSV allowlist despite Tier A being redactor-only. Scenario: If implementers mirror allowlist rows onto Tier A bug-body, the dev-clone report can omit required Tier A content such as run linkage, branch, PR URL, validated logs, and run-log pointer
- **Proposed resolution**: Scope TSV and lint parity to Tier B surfaces only; keep Tier A body composition outside field allowlists with python/cli.py redact secrets as the final filter


### FINDING_17:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: security
- **Location**: skills/implement/scripts/stall-recovery-report-allowlists.tsv (plan.txt:50,94)
- **Concern**: [SCOPE-REDUCTION] The plan keeps a Tier A bug-body allowlist surface even though Tier A must drop the field allowlist and use only secret redaction. Scenario: Tier A reports may still be constrained by TSV/code/doc parity, so required dev-clone content such as branch, PR URL, validated log content, and full evidence citations can be omitted or treated as drift
- **Proposed resolution**: Remove Tier A bug-body rows from the allowlist plan. Scope TSV/code/doc parity to Tier B chat-print or consumer report fields only, and render Tier A outside the allowlist with redact-secrets as the sole filter




### FINDING_2: Step 18a.5 skip sentinels are not pinned
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: Step 18a.5 references terminal-report and escalation-success skip predicates without authoritative tmpdir artifact names. Implementers may choose incompatible sentinels, causing duplicate filing or skipped required reports.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin exact paths in stall-recovery-report.sh and stall-recovery.md (for example stall-recovery-terminal-report.env and stall-recovery-escalation-success.env) and add matching harness assertions


### FINDING_3: Step 18a.5 run-success predicate is undefined
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Step 18a.5 depends on “run succeeded” but does not define the mechanical predicate. Orchestrators may file escalation-success reports for stalled or partial recovery runs, or skip common successful no-merge outcomes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Specify one authoritative source (for example finalize-state.sh MERGE_RESULT when --merge else absence of STALL_TRACKING plus Step 17 completion) and document it in stall-recovery.md and SKILL.md Step 18a.5
  - From Cursor-Pragmatic: Pin succeeded to an explicit allowlist (for example STALL_TRACKING false on all four layers plus OUTCOME in {merged, pr-created, pr-created-draft, forked-dry-run}) and reference the same state files Step 17/18b already read.


### FINDING_4: Terminal report API migration leaves ambiguous subcommands and titles
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: The plan removes `bug-comment` and adds report composition concepts without naming one public replacement surface. Existing `issue-input-file` title synthesis may also conflict with the new `--title-file` and root-caused title grammar.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Rename or extend a single documented subcommand (for example compose-report replacing bug-body) and update the usage line classify init-attempts record-escalation compose-report issue-input-file lint
  - From Cursor-Innovation: Replace synthesized-heading with `--title-file` on `issue-input-file` or add a single `compose-report` subcommand that emits body plus heading for both `terminal-failure` and `escalation-success`


### FINDING_6: Python ship-pr ledger tokens can break the single-JSON stdout contract
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic
- **Severity**: important
- **Concern**: The Python ship-pr ledger-token plan may emit extra stdout lines, but Step 8 expects exactly one JSON object. Extra KV output can break routing before record-before-edit handling runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add ledger fields to the existing JSON envelope, or another already-documented durable side channel, and update SKILL.md plus tests to assert stdout remains exactly one JSON line
  - From Codex-Pragmatic: Keep stdout as one JSON object; carry ledger site trigger dispatcher and exit code inside that JSON payload or a tmpdir sidecar, then update Step 8 to record from that channel before edits


### FINDING_7: Tier B bounded-root-cause writing lacks the larch-internal-only instruction
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: Tier B root-cause prose may pass path and URL validation while still narrating client repo facts because the plan omits the required larch-internal-terms-only write instruction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add the explicit larch-internal-only instruction to the Main Claude artifact-writing step before validation and keep the helper validator as a backstop


### FINDING_8: Ledger write failures can hide required escalation reporting
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: `record-escalation` failure is fail-open without a durable fallback. A script-to-main-agent handoff can occur, the run can succeed, and Step 18a.5 can see an empty ledger and file nothing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Preserve a durable fallback escalation marker or make Step 18a.5 treat record-escalation Tool Failures as escalation evidence; do not let this path look like success with an empty ledger


### FINDING_10: Tier B bail-token union misses bash ship-pr and ci-decide emitters
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: The Tier B bail-token enum omits bash ship-pr `needs_user_bail_reason` and ci-decide emitters. Bash opt-in terminal reports can still redact valid bail reasons.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Extend the Tier B union and parity tests to include scripts/ship-pr.sh needs_user_bail_reason plus scripts/ci-decide.sh emitters, and keep those aligned with python/config.py.


### FINDING_11: Title fallback can violate root-caused title requirements
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: If a Tier B title summary is rejected, the planned enum-only fallback can produce a class/step heading that is no longer titled from the root-cause finding.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Fail closed and require a safe bounded title rewrite, or synthesize only from a validated larch-internal root-cause summary


### FINDING_12: Operator-action success-with-ledger records can be lost after post-merge cleanup
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: A merged successful run with an escalation ledger and `operator-action` verdict may skip filing, skip run-log commit due to the post-merge sentinel, and then lose the tmpdir record during cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Add a durable non-filing path for this post-merge skip case before cleanup, or preserve the tmpdir when the run-log cannot be committed; cover the post-merge sentinel path in tests


### FINDING_13: Terminal and escalation-success paths omit dev-clone versus consumer orchestration
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The plan rewrites report composition but does not restate the required `is-larch-dev-clone` routing, `/larch:issue --input-file` filing path, env normalization, and Tier B chat-print path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Restore explicit terminal and Step 18a.5 procedures: Tier A dev clone runs investigation, writes root-cause artifacts, composes report, builds `issue-input-file` from `stall-recovery-title.txt`, files via `/larch:issue`, normalizes env; Tier B/forked prints via `chat-print` only


### FINDING_14: Escalation-success reports may lack initialized attempt history
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: A run can succeed after script-to-main-agent escalation without entering the stall-recovery path that creates `stall-recovery-attempts.env`. Step 18a.5 may then fail closed or omit the required attempt table.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Have Step 18a.5 initialize/read $IMPLEMENT_TMPDIR/stall-recovery-attempts.env as a zero-attempt file before root-cause investigation and report composition, or make escalation-success composition treat a missing attempts file as an empty history. Add the planned success-with-ledger test with no preexisting attempts file.


### FINDING_15: Root-caused issue titles are not explicitly secret-redacted
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The plan applies secret redaction as a body backstop, but the new public issue heading is synthesized from the root-cause finding. Secrets in summaries or titles can bypass body-only redaction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Redact the full issue input after composing the ### heading and body, or run the same secrets redactor over the title before writing it. Document this as applying to public headings as well as bodies, and add a title-secret regression test.


### FINDING_17: Bash ship-pr internal lint-fix handoff can start recovery before prompt-side recording
- **Reviewer(s)**: Codex-dyn-ownership-trace
- **Severity**: important
- **Concern**: Bash ship-pr can capture lint-fix output and enter `run_recovery_waterfall`, including CI repair, before Step 8+ can record the escalation. The ship-pr-internal lint-fix handoff can be missing or recorded too late.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-ownership-trace: Specify that ship-pr exits or returns a Step 8+ handoff with ledger-ready tokens on lint-fix main-agent-required before run_recovery_waterfall or other CI-fix edits. Then SKILL.md and ship-pr-exit-matrix record once before Main Claude edits.


### FINDING_18: ci-local-unfixable suffix grammar is not pinned for Tier B rendering
- **Reviewer(s)**: Cursor-dyn-tier-b-leakage-gaps, Codex-dyn-tier-b-leakage-gaps
- **Severity**: important
- **Concern**: The plan names `ci-local-unfixable:<sanitized-list>` but does not pin the report-side suffix grammar. A prefix-only or overly broad implementation can render unsafe or unsanitized suffix bytes in consumer reports.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-tier-b-leakage-gaps: Pin the suffix charset to the existing _sanitize_bail_list algorithm (or extract one shared helper), require safe_bail_reason_value to accept ci-local-unfixable only when the suffix matches that charset (else redacted), document the transform in the TSV row, and add a harness case for unsanitized compound input at compose time
  - From Codex-dyn-tier-b-leakage-gaps: Specify one report-side grammar, for example `^ci-local-unfixable:[A-Za-z0-9_,-]+$`; render non-matches as `redacted`; name that transform in TSV/code/docs; add tests for slash, dot, colon, equals, and empty suffix


### FINDING_19: Tier B validation omits real plan and issue-text artifact sources
- **Reviewer(s)**: Codex-dyn-tier-b-leakage-gaps
- **Severity**: important
- **Concern**: Tier B validation names excluded plan and issue text tokens but does not identify the actual artifact sources, such as `$IMPLEMENT_TMPDIR/plan.txt` and `$IMPLEMENT_TMPDIR/feature-description.txt`. Bounded prose can leak those strings while still passing validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-tier-b-leakage-gaps: Add explicit Tier B sensitive-token sources for `$IMPLEMENT_TMPDIR/plan.txt` and `$IMPLEMENT_TMPDIR/feature-description.txt`, plus state keys for repo, branch, and PR URL; add tests that leak strings from those real files into bounded root-cause and title inputs




### FINDING_1: Step 18a.5 success allowlist diverges from canonical outcomes
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: Step 18a.5 uses a success predicate that does not match the canonical `/implement` final-report outcome enum. It includes non-emitted outcomes such as `local-dry-run` and `no-merge-success`, and omits `force-merged-externally`. A successful run with escalation ledger entries that normalizes to `force-merged-externally` can skip the required escalation-on-success report.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Reuse write-final-report.sh outcome computation (or extract a shared helper) and treat merged, force-merged-externally, pr-created, pr-created-draft, and forked-dry-run as success; drop invented tokens; add harness parity with test-write-final-report.sh.
  - From Codex-Arch: Add force-merged-externally to the Step 18a.5 success allowlist, or normalize MERGE_RESULT=already_merged to a succeeded state before the allowlist check
  - From Cursor-Innovation: Reuse the write-final-report.sh outcome enum verbatim: drop `local-dry-run` and `no-merge-success`; add `force-merged-externally`; gate 18a.5 on that shared outcome set
  - From Codex-Innovation: Align the Step 18a.5 success predicate with write-final-report outcomes: include force-merged-externally, remove or explicitly define any new outcome labels, and prefer deriving the predicate from the same normalized outcome source used by write-final-report.
  - From Cursor-Pragmatic: Align the allowlist with `write-final-report.sh` outcomes: include `force-merged-externally`, `pr-created`, and `pr-created-draft`; drop or map invented tokens; add harness cases for each success outcome
  - From Codex-Pragmatic: Align Step 18a.5 with the existing /implement outcome enum. Include force-merged-externally or derive from write-final-report logic, and drop no-merge-success/local-dry-run unless the plan also defines real source states and tests for them
  - From Cursor-Requirements: Normalize Step 18a.5 against the nine implement outcomes in `write-final-report.md` (at minimum include `force-merged-externally`); drop or define fictional tokens; document mapping from finalize/ship-pr state to that enum
  - From Codex-Requirements: Align the Step 18a.5 success predicate with the canonical write-final-report success outcomes. Include force-merged-externally and add a regression test for success-with-ledger on that outcome.


### FINDING_2: Reuse design still hard-pins stall-recovery artifact paths
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The proposed helper claims reusable structure, but its artifacts remain hard-pinned to `$IMPLEMENT_TMPDIR/stall-recovery-*` except for a test-only ledger override. `/design` reuse may require forking or duplicating strings because compose/report inputs, sentinels, and root-cause files are not generally parameterized.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add a documented artifact-prefix or basename table (env/flags on `record-escalation` and `compose-report`) so `/design` can supply `DESIGN_TMPDIR` and distinct basenames without copying the script


### FINDING_4: Lint-fix ledger stdout contract lacks stable field names
- **Reviewer(s)**: Codex-dyn-stdout-channel-audit
- **Severity**: important
- **Concern**: The plan describes ledger-ready stdout fields for lint-fix handoffs but does not name exact keys. Prompt-side recorders in Step 3, Step 5, and Step 6 cannot parse a stable KV contract if dispatcher and exit-code fields remain implicit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-stdout-channel-audit: Pin exact namespaced KV names in the plan docs and tests, emitted only on main-agent-required paths and ignored by existing consumers


### FINDING_5: Ship-pr exit matrix still forbids edits for the new Step 6 handoff path
- **Reviewer(s)**: Cursor-dyn-escalation-ownership-gaps
- **Severity**: important
- **Concern**: The ship-pr exit matrix still says orchestrator main-agent edits are forbidden when `STALL_STEP=6`, but the plan adds a ship-pr lint-fix main-agent-required handoff that expects Step 8+ recording and Main Claude repair. The handoff can be recorded while repair is blocked or ownership becomes ambiguous.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-escalation-ownership-gaps: Revise ship-pr-exit-matrix.md: carve out a lint-fix-main-agent-required / ship-pr-internal handoff branch (record-escalation, then Step-3-style main-agent repair, then re-invoke Step 8+); keep the STALL_STEP=6 no-edit rule only for exhausted/non-handoff stalls


### FINDING_8: Tier B sensitive-token validation omits required evidence sources
- **Reviewer(s)**: Cursor-dyn-tier-b-leakage-surface, Codex-dyn-tier-b-leakage-surface
- **Severity**: important
- **Concern**: The Tier B validator source list does not cover all raw evidence that Main Claude must read for root-cause investigation. Evidence such as `execution-issues.md`, failure-detail logs, state files, attempts values, and run-log pointers can contain client-specific terms that may be copied into bounded prose without matching the planned path, URL, PR, or log-tail checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-tier-b-leakage-surface: Add `$IMPLEMENT_TMPDIR/execution-issues.md` to the sensitive-token source list (and matching tests/docs); reject bounded prose/title substrings sourced from that file the same way as plan/feature-description
  - From Codex-dyn-tier-b-leakage-surface: Expand the Tier B sensitive-token source list and tests to cover every root-cause evidence source, including full client-bearing keys from ship-pr-state.sh/finalize-state.sh/session-env.sh, validated failure-detail log text, raw attempts values if read, execution-issues.md, run-log pointer, and any ledger/fallback evidence pointer; or constrain Tier B bounded prose to a helper-generated allowlisted projection before validation.




### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/write-final-report.sh:184-207
- **Concern**: Step 18a.5 outcome parity names write-final-report.sh as canonical but the plan never updates that script or adds a shared outcome API. Scenario: The if/elif OUTCOME chain stays only in write-final-report.sh while Step 18a.5 reimplements or forks it; parity tests can pass on fixtures while production paths diverge on admin_merged, bailed-needs-user-input ordering, or future outcome edits
- **Proposed resolution**: Add a shared normalize-implement-outcome helper (e.g. stall-recovery-report.sh subcommand with stdout KV contract), list skills/implement/scripts/write-final-report.sh under ### UPDATED:, and call the helper from both write-final-report.sh and Step 18a.5


### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/ship.py:612-625
- **Concern**: Lint-fix ledger KVs are fully pinned (LINT_FIX_LEDGER_*), but Python ship.py ledger-ready data has no pinned JSON field names or sidecar path. Scenario: Step 8 orchestrator parsing drifts across python/ship.py edits; record-escalation is skipped or uses wrong site/trigger on the default driver
- **Proposed resolution**: Pin exact JSON keys (or one documented sidecar filename and KV grammar) in python/ship.py, python/ship.md, skills/implement/SKILL.md, and python/test_ship.py, mirroring the lint-fix contract


### FINDING_6:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:201-203
- **Concern**: Tier A report contents omit the required verbatim bail reason. Scenario: The feature requires Tier A to publish the verbatim bail reason after secret redaction, but the proposed Tier A field list does not include it
- **Proposed resolution**: Add raw BAIL_REASON or equivalent verbatim bail-reason evidence to the Tier A body and Tier A tests before redaction


### FINDING_7:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:19-23,120-132,736-739
- **Concern**: [SCOPE-REDUCTION] Public generic artifact profile over-expands this SIMPLE change. Scenario: The /implement feature can ship with pinned artifacts plus reusable internals; adding public --profile generic path, vocabulary, and evidence override surfaces creates extra CLI and path-validation scope before the /design port uses it
- **Proposed resolution**: Keep internal constants or helper functions for later reuse, document the intended /design parameters, and defer public generic-profile flags and generic-profile tests to #3992


### FINDING_10:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/write-final-report.sh:184-207
- **Concern**: Plan leaves outcome normalization as reuse-or-extract without one callable. Scenario: Step 18a.5 and write-final-report can drift on precedence (STALL_TRACKING before MERGE_RESULT, bailed-needs-user-input)
- **Proposed resolution**: Add one exported helper (e.g. write-final-report.sh --emit-outcome-only or stall-recovery-report.sh normalize-outcome) and require both Step 18a.5 and parity tests to call it


### FINDING_11:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/stall-recovery.md:21-26
- **Concern**: Step 18a step2-impl escalation recording is bullet-only, not in numbered dispatch. Scenario: Requirement 2 names step2-impl as a covered handoff; bullets under the update section never reach procedure step 5
- **Proposed resolution**: In step 5, before step2-impl (and inline step8-shippr repair) edits, require record-escalation with stable site/trigger tokens and add harness coverage


### FINDING_14:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/stall-recovery-report.sh:19-19
- **Concern**: Public subcommand list drops normalize-issue-env without a replacement contract. Scenario: Tier A terminal and escalation-success paths still need post-/larch:issue ISSUE_NUMBER/ISSUE_URL capture for sentinels and dry-run
- **Proposed resolution**: Keep normalize-issue-env (or fold equivalent into compose-report) and document terminal plus 18a.5 filing sequences in stall-recovery-report.md


### FINDING_15:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/scripts/stall-recovery-report.sh (plan.txt:120-132,289-292,736-739)
- **Concern**: [SCOPE-REDUCTION] Public generic artifact profiles and test-only overrides over-serve the SIMPLE lane. Scenario: The issue requires /implement reporting plus reuse seams for future /design adoption, not a new public profile API with generic swapping tests in this PR
- **Proposed resolution**: Keep the canonical /implement CLI and add only the named reuse seams needed by this change. Defer public generic profile flags, artifact-prefix swapping, and test-only override machinery to #3992 unless a current /implement caller needs them


### FINDING_16:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: security
- **Concern**: skills/implement/scripts/stall-recovery-report.sh (plan.txt:56-73,158-164,182-186,309-315). Scenario: Tier B substring rejection conflicts with required larch-internal root-cause prose
- **Proposed resolution**: The sensitive corpus includes attempts and ledger text, but Tier B prose is allowed to mention larch operational tokens such as main-agent-required, ci-fix-exhausted, step names, site tokens, and trigger tokens. A blanket substring reject can fail valid Tier B reports or force non-actionable prose Build the Tier B sensitive corpus from excluded client-bearing values and raw evidence text only, with explicit exemptions for allowlisted larch operational enums that Tier B may publish. Add one test that prose can cite an allowed ledger token while still rejecting a client branch, path, PR URL, or plan phrase


### FINDING_17:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:439-465
- **Concern**: Step 18a recovery `step2-impl` is not in the prompt-side `record-escalation` inventory. Scenario: `stall-recovery.md` requires recording before inline `step2-impl`, but the planned `implement/SKILL.md` list covers Steps 3/5/6/8+ only. Recovered runs can finish without ledger rows, so requirement 2 (escalation-on-success filing) is missed
- **Proposed resolution**: Add Step 18a recovery dispatches (`step2-impl`, and any inline repair not covered by child-script recording) to the SKILL `record-escalation` call sites with stable site/trigger tokens before Main Claude edits


### FINDING_18:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/references/ship-pr-exit-matrix.md:28
- **Concern**: Plan adds a Step 6 lint-fix handoff but does not pin stall-state on that return. Scenario: Current bash checks path falls through to `exit_stall 6` (`scripts/ship-pr.sh:849-862`). If handoff returns with `STALL_TRACKING=true` / `STALL_STEP=6`, Step 18a.5 skips (stall layers active) and escalation-success issues are silently dropped after a successful repair
- **Proposed resolution**: Require handoff return to leave all `STALL_TRACKING` layers false (or clear them before re-invoking Step 8+). Document this in `ship-pr-exit-matrix.md`, `ship-pr.md`, and tests alongside the no-edit carve-out


### FINDING_19:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/write-final-report.sh:184-207
- **Concern**: Step 18a.5 success predicate says reuse or extract outcome logic but does not mandate one shared helper. Scenario: `write-final-report.sh` maps both `merged` and `admin_merged` to outcome `merged`. A duplicated if/elif in `stall-recovery-report.sh` can drift (e.g. miss `admin_merged`), misclassifying success and skipping or misfiling escalation reports
- **Proposed resolution**: Extract a single `normalize-implement-outcome` function or shell helper used by both `write-final-report.sh` and Step 18a.5; parity tests should call that helper, not reimplement the chain


### FINDING_21:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:703-706
- **Concern**: Generic Tool Failure evidence can trigger escalation-success reporting. Scenario: A successful run has no escalation ledger but contains an unrelated Tool Failures entry; Step 18a.5 may treat that entry as escalation evidence and file or print an escalation report, violating the no-escalation success criterion
- **Proposed resolution**: Count only the canonical ledger, fallback ledger, record-failure marker, or a uniquely tagged record-escalation Tool Failure entry; ignore generic execution-issues Tool Failures


### FINDING_23:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:19-23,120-132,736-739
- **Concern**: [SCOPE-REDUCTION] Public generic artifact profile flags overexpose future /design reuse. Scenario: /implement can ship with canonical paths and internal reusable helpers; public generic flags add path and vocabulary override surface, containment checks, and tests for a non-goal /design caller
- **Proposed resolution**: Keep an internal profile table or factorization only; expose the /implement CLI now and defer public generic flags to #3992 when /design wires in


### FINDING_24:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: security
- **Location**: plan.txt:59-73,161-186,656-660
- **Concern**: Tier B substring validation does not separate client data from safe larch terms. Scenario: Evidence commonly contains safe terms like lint-fix-loop, ship-pr, and main-agent-required; rejecting substrings from every evidence input can make valid Tier B root-cause prose fail closed, so consumer terminal reports are not printed
- **Proposed resolution**: Build the rejection corpus from explicit client-bearing values plus path, URL, branch, PR, plan, issue, and log-tail patterns; exempt allowlisted larch operational tokens and machine fields with tests for safe terms that also appear in evidence


### FINDING_26:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:165-174
- **Concern**: compose-report has no classification input. Scenario: The terminal report composer has no stated source for FAILURE_CLASS, STALL_STEP, PHASE, BAIL_REASON, EXIT_CODE, FAILURE_SIGNATURE, or MATCHED_CLASSIFIER_PATTERN, so cap-0 terminal failures with no attempts can lose required class/step/bail fields and cannot render the required title suffix or Tier B operational fields deterministically.
- **Proposed resolution**: Add a required --classification-file input or documented canonical classification state read to compose-report; update Step 18a terminal calls, docs, and tests to pass/read $IMPLEMENT_TMPDIR/stall-recovery-classification.env.


### FINDING_27:
- **Reviewer(s)**: Cursor-dyn-escalation-ownership
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:439-445 vs skills/implement/references/stall-recovery.md:366-368
- **Concern**: Issue-scoped Step 18a step2-impl handoff has no named record-escalation owner in the SKILL.md record-site list. Scenario: stall-recovery.md only says to add record calls for step2-impl; SKILL.md lists Step 3/5/6/8+ sites but omits Step 18a step2-impl and step8-shippr inline repair, so implementers can skip recording or record in the wrong layer during stall recovery
- **Proposed resolution**: Add prompt-side Step 18a ownership in SKILL.md (record-escalation before inline edits on step2-impl and conditional step8-shippr repair) and mirror the same owner tokens in stall-recovery.md dispatch step 5


### FINDING_28:
- **Reviewer(s)**: Codex-dyn-escalation-ownership
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/run-step5-review.sh:237; skills/implement/SKILL.md:587-605; <TMPDIR>/plan.txt:439-445,517-525
- **Concern**: Step 5 MAV handoff lacks an exact ledger-ready KV schema. Scenario: The plan says SKILL.md records Step 5 main-agent-vote-required and run-step5-review.sh emits stable KV tokens, but it never names the tokens or pins site/trigger/step/phase fields. The prompt-side owner cannot implement or test a single record contract as precisely as lint-fix does.
- **Proposed resolution**: Define exact Step 5 ledger-ready KV names for main-agent-vote-required, parse those names in SKILL.md, and make the run-step5-review test assert those names plus one prompt-side record.


### FINDING_29:
- **Reviewer(s)**: Codex-dyn-escalation-ownership
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/references/stall-recovery.md:21-26; <TMPDIR>/plan.txt:366-370,770-777
- **Concern**: Step 18a step2-impl escalation is not testable as a single-owner record path. Scenario: The plan says Step 18a step2-impl inline repair records an escalation, but the Step 18a.5 tests cover reporting ownership after success, not the inline dispatch record before Main Claude edits. A dispatcher failure recovered by inline implementation could ship without a ledger row, or gain a duplicate row later, without a named regression test catching it.
- **Proposed resolution**: Add a targeted Step 18a fixture for RESUME_HINT=step2-impl that asserts one record-escalation call before inline repair and no second record during Step 18a.5 success reporting.


### FINDING_30:
- **Reviewer(s)**: Cursor-dyn-tier-data-containment
- **Severity**: important
- **Focus area**: security
- **Location**: plan.txt:165-174
- **Concern**: The compose-report argv surface omits any way to supply runtime prompt-state tokens that the plan lists in the Tier B sensitive-token corpus (plan.txt:73) but that are not guaranteed to exist on disk when validation runs.. Scenario: Main Claude can read in-memory IMPLEMENT_BAIL_REASON/FINAL_BAIL_REASON, gh-fetched issue text, or a PR URL before ship-pr-state is seeded; compose-report only accepts root-cause/title/ledger files, so the substring validator may never load those tokens and Tier B bounded prose can echo client data that never appeared in scanned files.
- **Proposed resolution**: Add a pinned pre-compose step and compose-report flag (for example --sensitive-corpus-file or --prompt-state-env) that the orchestrator writes from every non-file evidence source it read; document it in stall-recovery-report.md and stall-recovery.md; require tests that fail when bounded prose contains a token present only in the supplement file.


### FINDING_31:
- **Reviewer(s)**: Codex-dyn-tier-data-containment
- **Severity**: important
- **Focus area**: security
- **Location**: <TMPDIR>/plan.txt:60-73,161-186,643-661
- **Concern**: Tier B names prompt-state values as sensitive, but the plan does not wire them into validation at compose time. Scenario: The proposed compose-report inputs include root-cause, bounded-root-cause, title, and output files, but no required prompt-state or sensitive-token input. A Tier B bounded root-cause can mention an in-memory branch, repo, PR URL, issue text, plan text, or client path that is not present in static evidence files, pass validation, and violate the excluded-client-data contract.
- **Proposed resolution**: Add one required Tier B validator input, such as --prompt-state-sensitive-file or repeated --sensitive-token label=value, populated by SKILL.md immediately before compose-report. Include those dynamic tokens in tests and in the SECURITY.md residual-risk wording.



