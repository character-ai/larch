## Plan

## Approach

Build a standalone coordinator on Piece 1’s assessment foundation while preserving its consumption, coverage-advance, materialization, and ship-outcome authorities.

1. Normalize and validate the requested kind set. Accept only `guidelines` and `invariants`, deduplicate repeated supported kinds, and process kinds in invariant-first order.
2. Resolve the repository and implement tmpdir from explicit CLI inputs or persisted run state. Do not derive the repository from ambient cwd.
3. Independently validate each requested kind’s recorded materialization envelope before any new work, but validate it against the identity it claims to cover rather than requiring it to equal the repository’s current `HEAD`:
   - Require regular, non-symlink metadata, frozen-diff, and knowledge-source files.
   - Validate `HEAD_SHA`, `BASE_REF`, frozen-diff fingerprint, and knowledge identities against the recorded covered snapshot and resolved covered commit/base.
   - Reject malformed or duplicate identity-bearing metadata fields, unresolved bases, out-of-root paths, and snapshot mismatches.
   - Permit the repository `HEAD` to have advanced after the recorded assessment materialization.
   - Copy only validated frozen diffs and normalized architectural knowledge into coordinator-owned evidence snapshots.
4. Determine whether each kind is already handled through Piece 1’s validators before deciding whether current-HEAD materialization or a new launch is needed:
   - Use `note_consumable(..., repo_root=..., base_ref=...)` for guidelines and `invariant_note_consumable(..., repo_root=..., base_ref=...)` for invariants.
   - Validate the corresponding existing schema-version-1 ship-outcome sidecar before accepting a consumable note as handled.
   - Preserve Piece 1’s coverage-advance behavior: when `HEAD` has moved, it compares the prior covered `HEAD` with the current `HEAD`, inspects only the incremental diff, and refreshes coverage without reauthoring when those paths are proven out of scope.
   - Do not reject a prior covered envelope merely because its `HEAD_SHA` differs from the current repository `HEAD`; let Piece 1 establish whether the incremental change remains out of scope.
   - Treat coordinator-owned unavailable receipts as handled only after validating their complete covered identity and required durable artifacts; do not invoke Claude again merely because an already-recorded unavailable result is re-entered for the same covered request.
5. For kinds that Piece 1 does not consume, determine whether the recorded covered materialization remains sufficient or must be refreshed for current work:
   - When `HEAD` still equals the validated covered `HEAD`, run the deterministic pre-filter against the validated frozen diff.
   - When `HEAD` has advanced, use Piece 1’s incremental coverage/materialization authority to inspect the diff from the covered `HEAD` to current `HEAD`; preserve the existing handled result when all incremental paths are proven out of scope.
   - If an incremental path intersects a kind’s scope, materialize a fresh current-HEAD envelope for only that unresolved kind before deterministic filtering or authoring.
   - Require a current-HEAD match only for a freshly materialized envelope used to launch Claude and immediately before persisting newly authored or deterministic results.
   - Reuse Piece 1’s conservative path classification so only proven out-of-scope changes skip authoring. Persist deterministic-clean notes and validated outcomes without launching Claude.
6. Build a dedicated, coordinator-owned evidence directory for each launch:
   - It contains only regular, non-symlink copies of the freshly validated current-HEAD frozen diff, per-kind knowledge snapshots, and the committed agent prompt.
   - It does not include session state, recovery files, prior results, logs, environment artifacts, or the rest of the implement tmpdir.
   - Keep the launcher-owned result file outside this readable directory.
7. Launch Claude once for the remaining kind set through an injectable launcher:
   - Use the committed agent prompt and pass only absolute evidence paths.
   - Grant read-only tools and plan-mode permissions, with the evidence directory as the sole added readable directory.
   - Capture stdout and stderr; the launcher, not Claude, atomically writes captured stdout into a prevalidated regular, non-symlink result file outside Claude’s readable grant.
   - Use a fixed timeout and never expose raw stdout or stderr as assessment prose.
8. Parse exactly one JSON object from the launcher-owned result file. Require one result per launched kind, reject duplicates and omissions, and reject unknown fields, kinds, states, or architectural identifiers. Match each result to the freshly materialized pre-launch `HEAD`, base reference, diff fingerprint, and knowledge snapshot identities.
9. Persist successful results with Piece 1 compose writers so durable metadata preserves the validated `MATERIALIZE_ENV` identity:
   - Recheck the repository `HEAD` immediately before persistence.
   - If `HEAD` moved after launch, do not persist the stale authored result as current work; re-enter Piece 1 incremental coverage handling against the launch envelope.
   - Use `write_compose_assessment` for guideline results and `write_invariant_compose_assessment` for invariant results.
   - Write and validate the existing guideline or invariant schema-version-1 ship outcome.
   - Append only guideline deviations through `append_deviation_note`; invariant violations remain represented only by their invariant durable note and invariant ship outcome.
   - Establish handled state only after every required durable artifact is written and revalidated. For guideline deviations, verify the deduplicated deviation-log entry before accepting the note/outcome pair as handled.
10. Convert timeout, launcher, unreadable-result, stale-result, and schema failures into bounded, redacted unavailable results:
    - Persist an unavailable note and outcome using existing Piece 1 semantics without overwriting a valid invariant violation.
    - Write a coordinator-owned schema-version-1 unavailable receipt containing the covered `HEAD`, base reference, frozen-diff fingerprint and snapshot identity, knowledge identities, kind, and validated durable-artifact identities.
    - Validate that receipt on re-entry so an unavailable fallback is idempotent and does not cause repeated launches for the same covered request.
    - If required unavailable persistence cannot establish a valid durable postcondition, return internal failure rather than claiming handling.
11. Emit a stable machine-readable CLI summary. Return success when every requested kind reached authored, deterministic-clean, preserved-violation, or validated-unavailable state. Reserve usage failure for invalid arguments and internal failure for persistence that cannot establish a valid durable postcondition.

Keep the live Step 8 dispatch and prompt-side assessment route unchanged. Piece 3 will wrap this CLI in the bgjob start/wait contract, and Piece 4 will activate it.

## Files to modify/create

### NEW: python/larch/implement/architectural_assessment.py

Add the coordinator, typed immutable request and result records, and `main(argv) -> int`.

Include:

- Supported-kind normalization using `config.ASSESSMENT_KIND_GUIDELINES` and `config.ASSESSMENT_KIND_INVARIANTS`.
- Explicit repository and tmpdir resolution that is independent of cwd.
- Path validation that rejects symlinks, directories, devices, missing files, and paths outside their expected repository, implement-tmpdir, or coordinator-owned evidence roots.
- Strict materialization-envelope parsing with duplicate-key rejection for identity-bearing fields.
- Independent validation that each materialization envelope accurately describes its recorded covered `HEAD`, base reference, frozen diff, and knowledge sources without imposing a premature exact-current-`HEAD` requirement.
- Per-kind re-entry checks that delegate durable-note consumption and incremental coverage advancement to:
  - `architectural_guidelines.note_consumable` for guidelines; and
  - `architectural_guidelines.invariant_note_consumable` for invariants.
- Existing ship-outcome sidecar validation before a consumable note is treated as handled.
- Coordinator validation of unavailable receipts, including covered fingerprint, covered `HEAD`, base reference, frozen-diff snapshot identity, knowledge identities, kind, and durable-artifact identities.
- Incremental-diff/coverage-advance behavior delegated to Piece 1 consumption helpers. A post-assessment `HEAD` advance must not invalidate an otherwise valid covered envelope before Piece 1 can determine whether the incremental diff is out of scope.
- Fresh current-HEAD materialization only when a kind remains unresolved after consumption or an incremental diff introduces potentially relevant paths. Require the fresh envelope to match current `HEAD` before deterministic filtering, launching Claude, or persisting a new result.
- A deterministic diff-path parser that fails closed on malformed headers, unsafe paths, renames, binary ambiguity, absolute or traversal paths, undecodable paths, or any path not proven out of scope.
- Per-kind handling that permits one kind to be consumed, deterministic-clean, or unavailable while another still requires Claude.
- Coordinator-owned evidence-directory creation:
  - create a fresh private directory beneath the implement tmpdir;
  - copy only the validated fresh frozen diff, per-kind knowledge snapshots, and committed agent prompt;
  - verify every copied artifact before launch;
  - keep the launcher-owned result path outside the evidence directory and do not pass unrelated tmpdir paths to the prompt or launcher.
- An injectable launcher protocol and production Claude launcher. Build exact read-only argv with the configured model and timeout. Use `Read` access only, plan permission mode, the repository as cwd, and the evidence directory as the sole added readable directory.
- Launcher result handling that captures Claude stdout and atomically writes it to a prevalidated regular, non-symlink result file. Claude must not receive result-file write access or a result-path instruction.
- A strict JSON decoder that consumes the complete launcher-owned result file. Validate the exact launched kind set, allowed states, required identity fields, bounded assessment text, and identifier membership in the corresponding knowledge snapshot.
- Persistence helpers that:
  - call `write_deterministic_clean_note` for proven skips;
  - call `write_compose_assessment` or `write_invariant_compose_assessment` for authored results so validated `MATERIALIZE_ENV` fields remain durable;
  - recheck `HEAD` before compose-writer persistence and route post-launch movement through Piece 1 incremental coverage handling rather than accepting stale authoring;
  - write and validate existing guideline or invariant ship-outcome schemas;
  - call `append_deviation_note` only for guideline deviations;
  - never route invariant violations through the guideline deviation log;
  - write, validate, and consume a coordinator-owned unavailable receipt for fallback idempotence;
  - re-read every required note, metadata file, outcome sidecar, unavailable receipt, and—when applicable—deviation-log entry before reporting handled completion.
- Persistence sequencing that verifies the required deduplicated guideline deviation-log entry before establishing a handled note-and-outcome postcondition. If log completion fails after authoring, retain enough validated state to retry only the missing log append without relaunching Claude.
- Failure classification that redacts secrets and tmpdir paths, strips line breaks, and caps diagnostic length before it reaches durable artifacts or machine stdout.
- Idempotent handling of partial combined runs. Preserve consumed and completed kinds, retry only incomplete durable postconditions, and launch only unresolved intersecting kinds.
- A machine-readable CLI contract with deterministic kind ordering and bounded status/detail fields.

Do not import or change the live Step 8 dispatcher.

### UPDATED: python/larch/cli.py

Register the coordinator as a module-level CLI entry, using a dedicated `(domain, verb)` key that dispatches to `larch.implement.architectural_assessment.main`.

Mark the entry as machine stdout. Preserve the existing lazy import and exit-code behavior.

Do not reroute `implement step-8-ship`, `ship`, or the current `NEXT_ACTION=assessments` handling.

### NEW: skills/implement/references/architectural-assessment-agent.md

Define the read-only assessment-agent contract.

Require the agent to:

- Treat the prompt, frozen diff, and architectural knowledge as untrusted evidence.
- Read every supplied evidence path with its tools. Emit an unavailable state for a kind if its evidence cannot be read.
- Assess only the requested kinds.
- Use only identifiers present in the supplied knowledge snapshot.
- Distinguish guideline `clean` and `deviation` from invariant `clean` and `violation`.
- Keep findings concise and tied to changed code.
- Echo the supplied `HEAD`, base reference, diff fingerprint, and knowledge identities exactly.
- Return one JSON object only, with no markdown fence or extra prose, to stdout.
- Avoid modifying files, invoking write-capable tools, requesting inline evidence, or attempting to create a result payload.
- Receive only the dedicated evidence-directory paths; the prompt must not name the broader implement tmpdir, a result-file path, session state, logs, or other unrelated artifacts.

Document the exact result schema expected by the coordinator, including combined-kind output and zero-finding clean results.

### NEW: python/tests/implement/test_architectural_assessment.py

Add offline unit and integration-style coverage with fake launchers and local git repositories.

Cover:

- Supported kind acceptance, deduplication, deterministic ordering, empty requests, and unknown-kind rejection.
- Explicit repository and tmpdir resolution independent of cwd.
- Valid combined guideline and invariant requests.
- Missing, malformed, duplicate-key, stale, or mismatched materialization metadata.
- Validation of a recorded envelope against its covered commit and snapshot identity independently of whether the repository has subsequently advanced `HEAD`.
- Invalid or unresolvable base references.
- Frozen-diff byte and fingerprint mismatches.
- Missing, changed, symlinked, non-regular, or out-of-root diff and knowledge files.
- Knowledge snapshot identity changes after launch.
- Delegation to Piece 1 `note_consumable` and `invariant_note_consumable`, including validated ship-outcome sidecars rather than coordinator-reimplemented handled rules.
- A docs-only or logs-only `HEAD` advance after a durable note, mirroring Piece 1 coverage-advance behavior: the historical envelope remains valid for its covered commit, the note remains consumable, and the launcher is not called.
- An incremental `HEAD` advance that intersects guideline or invariant scope: the previously covered note is not blindly accepted, only the affected kind is refreshed and launched, and the fresh launch envelope matches the current `HEAD`.
- Deterministic-clean skips for every proven-safe path class, including combined requests, with an assertion that the launcher was not called.
- Conservative pre-filter behavior for code, mixed, renamed, malformed, binary, absolute, traversal, and undecodable paths.
- Evidence-directory isolation: Claude receives only copied diff, knowledge, and prompt artifacts; the broader implement tmpdir, existing result files, session state, logs, and unavailable receipts are absent from the read grant and prompt.
- Exact read-only launcher argv, timeout, cwd, evidence-directory grant, prompt source, and path-based evidence references.
- Launcher-owned atomic stdout-to-result-file persistence, including rejection of symlinked, missing, or non-regular result payload paths. Assert that the agent contract does not require Claude to write a result file.
- Full-output JSON parsing. Reject leading or trailing prose, fences, multiple objects, malformed JSON, missing or duplicate kinds, unknown fields, unknown identifiers, invalid states, oversized text, and stale identities.
- Successful clean, guideline deviation, invariant violation, and combined results.
- Compose-writer persistence retaining validated `MATERIALIZE_ENV` identity fields, including `HEAD_SHA`, `BASE_REF`, diff fingerprint, and snapshot identity required by Piece 1 consumption.
- Durable note metadata and schema-version-1 outcome persistence.
- Guideline deviation logging, deduplication, redaction, and required-log validation before handled completion.
- An invariant violation assertion that `append_deviation_note` is never called.
- A deviation-log failure after an authored guideline result: re-entry retries the missing append without relaunching Claude and does not claim fully handled state before the log is validated.
- Timeout, non-zero exit, signal, missing executable, unreadable output, and schema-failure unavailable fallbacks.
- Unavailable receipts with complete durable identity, re-entry for the same covered request without a second launch, and rejection of malformed, stale, mismatched, symlinked, or incomplete receipts.
- Preservation of an existing valid invariant violation when a later attempt becomes unavailable.
- Partial combined failures, ensuring one kind’s failure does not erase another kind’s valid result.
- Re-entry for the same fingerprint and kind set without a second launch.
- Re-entry with one handled kind, which launches only the pending kind.
- Rejection of stale durable notes or outcome sidecars rather than treating them as handled.
- `HEAD` drift before launch and between launch and persistence, including preservation of a prior covered envelope through Piece 1 incremental out-of-scope coverage advancement and rejection of a freshly launched stale result when the incremental change is relevant.
- Post-write verification failures returning a non-success exit.
- Stable machine-readable stdout and exit codes.
- No network access and no real Claude invocation.

### UPDATED: python/tests/design/test_design_cli_ports.py

Add the architectural assessment registry entry and assert that it points to `larch.implement.architectural_assessment.main`.

Assert that the entry is included in `_MACHINE_STDOUT_KEYS`. Leave all existing design and Step 8 registry expectations unchanged.

## Edge cases

- Both kinds may share one frozen diff but use separate knowledge snapshots and durable artifacts.
- One kind may be already consumable through Piece 1 while the other requires deterministic or authored assessment.
- One kind may be deterministic-clean while the other requires Claude.
- A previous invariant violation may remain valid while guideline work is pending or unavailable.
- A docs-only or logs-only `HEAD` advance must first validate the historical envelope against its covered commit, then use Piece 1 incremental coverage advancement to preserve the existing note without a second authoring launch.
- A newly relevant incremental path after `HEAD` movement must invalidate consumption only for the affected kind, require a fresh current-HEAD envelope for that kind, and permit one new authoring launch.
- A fake or real launcher may return success without a regular result payload.
- The repository `HEAD` may change at any point. Historical envelopes remain valid only for their recorded covered commit; require current-HEAD identity for fresh launch evidence and recheck immediately before authored persistence.
- A valid JSON object may still describe a different request or stale evidence.
- Repeated kinds must not create duplicate result requirements or duplicate deviation-log entries.
- Empty architectural knowledge must not be treated as an authored model result. Follow existing Piece 1 clean or absent semantics.
- A failed combined launch must create per-kind unavailable artifacts only for unresolved kinds.
- Unavailable re-entry must validate the receipt identity and durable artifacts rather than repeatedly launching for the same covered request.
- The assessment agent must never receive access to the whole implement tmpdir or a writable result destination.

## Failure modes

- Invalid CLI arguments return usage failure without writing artifacts.
- Untrusted or stale evidence fails closed before launch.
- A historical envelope whose recorded commit, base, frozen diff, or knowledge identity cannot be verified fails closed; a valid historical envelope is not rejected solely because current `HEAD` advanced.
- Ambiguous pre-filter input requires authored assessment rather than a deterministic skip.
- Launcher, timeout, and parse failures persist redacted unavailable results with validated durable identity.
- An unavailable fallback does not suppress or overwrite an existing invariant violation.
- A persistence failure is not reported as handled. Re-read and validate every durable postcondition.
- A guideline deviation-log failure is surfaced in the machine result, prevents full handled completion, and is retryable without reauthoring when the note and result remain valid.
- Invariant violations do not use guideline deviation logging.
- Result text, stderr, exceptions, and paths are redacted and bounded before persistence or stdout.
- Any evidence-directory escape, non-regular artifact, symlink, or result-path mismatch fails closed.

## Testing strategy

Run only the changed-file checks:

- `python3 -m pytest python/tests/implement/test_architectural_assessment.py`
- `python3 -m pytest python/tests/design/test_design_cli_ports.py`
- Ruff, pylint, and pyright through the repository’s changed-file Python lint commands for:
  - `python/larch/implement/architectural_assessment.py`
  - `python/larch/cli.py`
  - `python/tests/implement/test_architectural_assessment.py`
  - `python/tests/design/test_design_cli_ports.py`
- The relevant Markdown lint for `skills/implement/references/architectural-assessment-agent.md`.
- `python3 python/cli.py lint agent-tool-contract` to verify the prompt’s read-tool contract if the lint covers reference agents.

Use fake launcher call capture to prove exact read-only argv, evidence-directory isolation, and launcher-owned result-file creation. Use local temporary git repositories for materialization identity, historical-envelope validation after `HEAD` movement, incremental coverage advancement, stale-result, unavailable-reentry, and persistence-order tests. Do not require credentials, network access, or an installed Claude executable.

## Acceptance

Run only the changed-file checks:

- `python3 -m pytest python/tests/implement/test_architectural_assessment.py`
- `python3 -m pytest python/tests/design/test_design_cli_ports.py`
- Ruff, pylint, and pyright through the repository’s changed-file Python lint commands for:
  - `python/larch/implement/architectural_assessment.py`
  - `python/larch/cli.py`
  - `python/tests/implement/test_architectural_assessment.py`
  - `python/tests/design/test_design_cli_ports.py`
- The relevant Markdown lint for `skills/implement/references/architectural-assessment-agent.md`.
- `python3 python/cli.py lint agent-tool-contract` to verify the prompt’s read-tool contract if the lint covers reference agents.

Use fake launcher call capture to prove exact read-only argv, evidence-directory isolation, and launcher-owned result-file creation. Use local temporary git repositories for materialization identity, historical-envelope validation after `HEAD` movement, incremental coverage advancement, stale-result, unavailable-reentry, and persistence-order tests. Do not require credentials, network access, or an installed Claude executable.

review_status: complete
rounds_completed: 2
difficulty: HARD
mechanical_churn: false
oversize_override: operator
diff_lines: 1704
