### FINDING_1: MainAgent fallback references an untracked scope-anchor renderer
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-scope-anchor-output.txt, dyn-marker-lifecycle-output.txt, dyn-pr-lines-output.txt
- **Severity**: important
- **Concern**: `skills/design/SKILL.md` requires `skills/design/scripts/render-main-agent-scope-anchor.sh` for the degraded 0-judge MainAgent voting path, but reviewers report the script is untracked/not in `HEAD`. A clean checkout or shipped plugin can fail to render the scope anchor, so fallback voting loses the intended scope-reduction evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-scope-anchor-output.txt, dyn-marker-lifecycle-output.txt, dyn-pr-lines-output.txt: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] Unrelated PR line-count work is bundled with scope-anchor changes
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-scope-anchor-output.txt, dyn-marker-lifecycle-output.txt
- **Severity**: important
- **Concern**: The branch includes `compute-pr-line-counts.sh` / final-report line-count changes that reviewers consider unrelated or adjacent to the scope-anchor plan. This increases review and rollback risk, and adds independent CI/API failure surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-scope-anchor-output.txt, dyn-marker-lifecycle-output.txt: Address the concern above.

### FINDING_3: Duplicated inline Python and ballot-renumber logic can drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `plan-review-loop.sh` contains multiple inline Python blocks duplicating tagged/parity/renumber behavior, including identical ballot-renumber logic. Marker, dedup, aggregation, and ballot behavior can diverge if one copy is changed without the others.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Unused scope-reduction tally helper creates dead API surface
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `scripts/lib-vote-tally.sh` defines `is_scope_reduction_block`, but reviewers report it is not called by production tally paths. This leaves dead or misleading API surface around scope-reduction classification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] `is_scope_reduction_block` API implies inline markdown but expects a file path
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-pr-lines-output.txt, dyn-bash-runtime-output.txt
- **Severity**: important
- **Concern**: `is_scope_reduction_block` passes its argument to `check-scope-reduction-marker.sh --file`, so callers must provide a readable file path despite the parameter/API name implying an inline block. A future caller passing heredoc text could silently misclassify tagged findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-pr-lines-output.txt, dyn-bash-runtime-output.txt: Address the concern above.

### FINDING_6: `check-scope-reduction-marker.sh` duplicates stdin and file-mode Python
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-bash-runtime-output.txt
- **Severity**: nit
- **Concern**: The marker helper has separate duplicated Python blocks for stdin and `--file` modes. Future normalization changes could update only one path and make marker detection inconsistent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-bash-runtime-output.txt: Address the concern above.

### FINDING_7: MainAgent renderer duplicates redaction/escaping instead of sharing helper
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The new MainAgent scope-anchor renderer duplicates the redact-and-escape pipeline rather than reusing the shared untrusted-file rendering helper, risking inconsistent prompt escaping across reviewer/voter renderers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_8: No regression proves tagged scope-reduction findings can win normally
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The plan acceptance criterion that a `[SCOPE-REDUCTION]` finding can win under normal vote rules is not directly tested. Existing coverage reportedly checks neutral/unchanged-threshold cases but not a sufficient-YES accepted outcome.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_9: Dedup parity count guard treats legitimate tagged merges as marker loss
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-pr-lines-output.txt
- **Severity**: latent
- **Concern**: The post-dedup parity gate falls back when fewer tagged blocks remain after dedup. Legitimate merges of near-duplicate tagged findings can therefore restore pre-dedup findings, reintroducing duplicates and diluting voting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-pr-lines-output.txt: Address the concern above.

### FINDING_10: Missing dispatch-plan-voters scope-anchor forwarding tests
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Planned harness coverage does not assert `--scope-anchor-file` forwarding/omission for voter dispatch. Prompt wiring could regress without CI detecting it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_11: Missing collect-output-to-marker-detector regression
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Reviewers report no harness covers the live collect output shape where TSV `what:` content is folded into severity-prefixed `Concern` text and then passed to the canonical scope-reduction detector.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_12: Missing run-step3 feature binding and CR/LF handoff tests
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-scope-anchor-output.txt
- **Severity**: important
- **Concern**: Planned Step 3 regressions for `DESIGN_TMPDIR` vs stale `IMPLEMENT_TMPDIR` feature binding, scope-anchor env handoff, and CR/LF path handling are missing or incomplete. Stale sessions or unsafe path bytes could bind the wrong feature file without harness failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-scope-anchor-output.txt: Address the concern above.

### FINDING_13: Missing plan-review-loop regressions for materialization, dedup, parity, renumber, and aggregation fallback
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-scope-anchor-output.txt, dyn-marker-lifecycle-output.txt
- **Severity**: important
- **Concern**: The plan listed loop-level regressions for malformed `larch:plan`, outline append, marker preservation through dedup, parity fallback, ballot renumbering, aggregation fallback, and inline emitter behavior. Reviewers report the committed loop/scope-anchor harnesses are much thinner and do not exercise these paths end-to-end.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-scope-anchor-output.txt, dyn-marker-lifecycle-output.txt: Address the concern above.

### FINDING_14: Missing aggregate-findings plan-mode fallback and code-mode negative tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-mode aggregation tests reportedly lack marker-loss fallback, code-mode negative, and inline-emitter cases. Partial marker loss or code-mode leakage could regress without failing the existing happy-path test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_15: Missing panel prompt assertions for scope-anchor content
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The panel dispatch harness forwards `--feature-file`, but does not assert that rendered reviewer prompts contain the binding scope anchor and untrusted-evidence framing. Prompt injection or omission could regress while argv tests pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_16: Residual prompt-injection risk from expanded untrusted issue text is undocumented
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Even with delimiter escaping and untrusted-evidence framing, expanded issue text sent to external LLMs can contain instruction-like content. Reviewers ask to document the residual risk and consider stronger separation if models prove instruction-sensitive.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_17: Scope-anchor outbound scrubbing omits broader PII/internal-detail redaction
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Scope-anchor redaction relies on `redact-secrets.sh`, which may not remove internal URLs, account IDs, or operational details from issue bodies before forwarding them to external voters/reviewers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_18: Parity gate conflates marker-helper infrastructure failures with genuine parity loss
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The post-dedup parity path reportedly handles helper exit `2` the same as marker parity failure, producing parity warnings and pre-dedup fallback instead of surfacing a broken canonical detector/tool failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_19: Brainstorm feature-context artifact preserves embedded stale `larch:plan`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-scope-anchor-output.txt
- **Severity**: latent
- **Concern**: `plan-review-feature-context.txt` is built from the original feature file without stripping embedded `larch:plan` blocks, unlike the binding scope anchor. Although non-binding today, a future reader could reintroduce stale plan text as scope evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-scope-anchor-output.txt: Address the concern above.

### FINDING_20: Voter dispatch hard-fails on unreadable scope-anchor file unlike reviewer paths
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `dispatch-plan-voters.sh` exits when `--scope-anchor-file` is unreadable, while some reviewer prompt paths degrade by omitting missing feature files. This asymmetry can abort a whole review round for transient tmpdir issues unless explicitly intended.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_21: Scout uses escaped scope-anchor bytes while reviewers use raw bytes escaped at render time
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-scope-anchor-output.txt
- **Severity**: latent
- **Concern**: Scout receives an HTML-escaped scope-anchor file, while reviewers/panel prompts receive raw scope-anchor bytes that are escaped at prompt render time. Issue text containing markup-sensitive characters can cause scout archetype selection to diverge from the effective reviewer/voter scope string.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt, dyn-scope-anchor-output.txt: Address the concern above.

### FINDING_22: Voter prompt no-flag regression compares output to itself
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The no-flag byte-identical regression in `scripts/test-render-voter-prompt.sh` reportedly uses self-comparison rather than a main/golden baseline, so unrelated default prompt changes may not fail CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_23: Tagged+tagged dedup can keep the weaker first body and drop later scope-cut text
- **Reviewer(s)**: dyn-marker-lifecycle-output.txt
- **Severity**: latent
- **Concern**: When two tagged blocks merge, the Jaccard deduper keeps the first body and merges reviewer attribution. If the later tagged block has the stronger scope-cut text, that content can be dropped before parity checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-marker-lifecycle-output.txt: Address the concern above.

### FINDING_24: Parity matching uses Concern-only tokens while marker detection also accepts heading/what
- **Reviewer(s)**: dyn-marker-lifecycle-output.txt
- **Severity**: latent
- **Concern**: Scope-reduction marker detection considers heading, `Concern`, and `what:`, but post-dedup parity compares only Concern-like text. Findings tagged only in the heading or `what:` can trigger broad fallback and duplicate ballot headings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-marker-lifecycle-output.txt: Address the concern above.

### FINDING_25: Raw Claude context-file attachment bypasses scope-anchor escaping
- **Reviewer(s)**: dyn-prompt-boundary-output.txt
- **Severity**: important
- **Concern**: The generic Claude plan-review fallback both inlines an escaped scope anchor and forwards the same raw file through `--feature-file` into `launch-claude-subprocess.sh`, where it is appended inside XML-like tags without the same redaction/escaping. Delimiter-breakout issue text can reach the model through the raw attachment channel.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-boundary-output.txt: Address the concern above.

### FINDING_26: PR line-count cache can combine current PR number with stale counts
- **Reviewer(s)**: dyn-pr-lines-output.txt
- **Severity**: latent
- **Concern**: `write-final-report.sh` appends `LINES_*` rows to state and reads the last PR number but the first matching count rows. Reused or appended session state can show line counts from an earlier PR under the current PR number.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pr-lines-output.txt: Address the concern above.

### FINDING_27: Scope-anchor materialization cleanup trap may not run on internal `exit`
- **Reviewer(s)**: dyn-bash-runtime-output.txt
- **Severity**: nit
- **Concern**: `_materialize_scope_anchor` installs a `RETURN` trap for temp files but calls `exit 2` on failure paths. Exiting inside the function bypasses the `RETURN` cleanup and can leave temp files in `$DESIGN_TMPDIR` until session cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-runtime-output.txt: Address the concern above.

### FINDING_28: Scope-anchor materialization discards strip-helper stderr
- **Reviewer(s)**: dyn-bash-runtime-output.txt
- **Severity**: nit
- **Concern**: `_materialize_scope_anchor` redirects `plan-block-strip-body.sh` stderr to `/dev/null` and only parses stdout. Malformed-marker or infrastructure diagnostics can be hidden, making failures harder to debug.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-runtime-output.txt: Address the concern above.

### FINDING_29: PR line-count cache treats transient unavailable status as authoritative
- **Reviewer(s)**: dyn-bash-runtime-output.txt
- **Severity**: latent
- **Concern**: `write-final-report.sh` reuses any cached non-empty `LINES_STATUS`, including `unavailable` from transient `gh api` failure. Later final-report runs may never retry and can permanently show `Lines (PR diff): N/A`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-runtime-output.txt: Address the concern above.

### OOS_1: CR/LF sanitation checks path string rather than file contents
- **Reviewer(s)**: dyn-scope-anchor-output.txt
- **Severity**: nit
- **Concern**: The reviewer notes that content-based CR/LF checks would be defense-in-depth only because tmpdir paths make path-string injection unlikely.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scope-anchor-output.txt: Address the concern above.

### OOS_2: Raw Claude context-file append path also predates non-plan review launches
- **Reviewer(s)**: dyn-prompt-boundary-output.txt
- **Severity**: latent
- **Concern**: The raw `<context_file_N>` append path predates this branch and also affects other Claude review launches using `--plan-file` / `--feature-file`; the in-scope concern is the new/amplified plan-review scope-anchor wiring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-boundary-output.txt: Address the concern above.

### OOS_3: Renderer-side prompt defenses look sound on covered paths
- **Reviewer(s)**: dyn-prompt-boundary-output.txt
- **Severity**: nit
- **Concern**: The reviewer reports that renderer-side defenses using redaction, escaping, untrusted framing, and delimiter-breakout tests look sound for the paths they cover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-boundary-output.txt: Address the concern above.

### OOS_4: Dynamic archetype validation added wrapper-tag rejection
- **Reviewer(s)**: dyn-prompt-boundary-output.txt
- **Severity**: nit
- **Concern**: The reviewer identifies the dynamic-archetype wrapper-tag rejection as a positive defense-in-depth addition.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-boundary-output.txt: Address the concern above.

### OOS_5: Scout escaped-anchor split is described as reasonable by one reviewer
- **Reviewer(s)**: dyn-prompt-boundary-output.txt
- **Severity**: nit
- **Concern**: One reviewer treats the scout escaped-copy split as reasonable, while noting that the Claude context-file path lacks the same treatment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-boundary-output.txt: Address the concern above.

### OOS_6: `compute-pr-line-counts.sh` / `plan-block-strip-body.sh` otherwise follow conventions
- **Reviewer(s)**: dyn-bash-runtime-output.txt
- **Severity**: nit
- **Concern**: The reviewer notes these helpers otherwise follow existing shell conventions such as `set -euo pipefail`, temp-file cleanup, quiet KV output, and non-fatal `gh` failure reporting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-runtime-output.txt: Address the concern above.

### OOS_7: Dispatch voter prompt path correctly gates and preserves default output
- **Reviewer(s)**: dyn-bash-runtime-output.txt
- **Severity**: nit
- **Concern**: The reviewer reports that `dispatch-plan-voters.sh` / `render-voter-prompt.sh` correctly gate `--scope-anchor-file`, inline redacted anchor content, and preserve default output when the flag is omitted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-runtime-output.txt: Address the concern above.

### OOS_8: Dedup/parity/renumber paths degrade safely according to one reviewer
- **Reviewer(s)**: dyn-bash-runtime-output.txt
- **Severity**: nit
- **Concern**: One reviewer reports that `plan-review-loop.sh` dedup/parity/ballot-renumber paths degrade safely via pre-dedup or aggregation fallback rather than silently dropping tags.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-runtime-output.txt: Address the concern above.
