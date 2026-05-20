# Review Round 1

- Mode: `diff`
- Accepted findings: 20
- Rejected findings: 4
- Exonerated findings: 2
- Neutral findings: 0

## Accepted Findings

### FINDING_1: **Important** `correctness` `docs/run-logs-required-files.tsv:11`  
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** `correctness` `docs/run-logs-required-files.tsv:11`      The new required-files manifest expects `run-statistics.json`, but the canonical batch table emits `run-statistics.md` (`scripts/larch-log-batches.sh:27`) and the docs list `run-statistics.md` (`docs/run-logs.md:27`). Any real run directory with the documented file will be reported as missing `run-statistics.json`, so the new verifier produces false negatives. Suggested fix: change the manifest and test harness expected file to `run-statistics.md` with extension `md`. Affected: `docs/run-logs-required-files.tsv:11`, `scripts/test-verify-run-log-completeness.sh:26-39`.
- **Suggested revision**: Address the concern above.


### FINDING_10: **[correctness]** [scripts/verify-run-log-completeness.md:27-28](scripts/verify-run-log-completeness.md) — Documents a CI workflow `.github/workflows/verify-run-logs.yml` that is not present under [.github/workflows/](.github/workflows/) (only `ci.yaml`, `release-tag.yaml`, and `requirements-lint.txt` exist). That misstates how completeness is enforced in CI. Suggested fix: add the workflow, wire it from `ci.yaml`, or remove/replace the bullet with the real enforcement path.
- **Reviewer**: dyn-lifecycle-ordering-output.txt
- **Concern**: - **[correctness]** [scripts/verify-run-log-completeness.md:27-28](scripts/verify-run-log-completeness.md) — Documents a CI workflow `.github/workflows/verify-run-logs.yml` that is not present under [.github/workflows/](.github/workflows/) (only `ci.yaml`, `release-tag.yaml`, and `requirements-lint.txt` exist). That misstates how completeness is enforced in CI. Suggested fix: add the workflow, wire it from `ci.yaml`, or remove/replace the bullet with the real enforcement path.
- **Suggested revision**: Address the concern above.


### FINDING_11: **[correctness]** [skills/implement/SKILL.md:1047-1066](skills/implement/SKILL.md) — `--design-only` explicitly skips Step 7a (including the pre-bump log flush at [skills/implement/SKILL.md:1631-1684](skills/implement/SKILL.md)), while Step 18’s `capture-session-transcript.sh` invocation was removed ([diff around former Step 18 block](skills/implement/SKILL.md)). Any design-only run (and similarly any bail-to–Step-18 path that never reaches Step 7a) therefore loses the last prompt-side opportunity that previously produced a committed `session-transcript.jsonl`. If those runs are still expected to carry a committed transcript, the lifecycle has a real gap; if not, [docs/run-logs.md](docs/run-logs.md) / [docs/run-logs-required-files.tsv](docs/run-logs-required-files.tsv) should spell out that exclusion so the “always” manifest does not contradict design-only behavior.
- **Reviewer**: dyn-lifecycle-ordering-output.txt
- **Concern**: - **[correctness]** [skills/implement/SKILL.md:1047-1066](skills/implement/SKILL.md) — `--design-only` explicitly skips Step 7a (including the pre-bump log flush at [skills/implement/SKILL.md:1631-1684](skills/implement/SKILL.md)), while Step 18’s `capture-session-transcript.sh` invocation was removed ([diff around former Step 18 block](skills/implement/SKILL.md)). Any design-only run (and similarly any bail-to–Step-18 path that never reaches Step 7a) therefore loses the last prompt-side opportunity that previously produced a committed `session-transcript.jsonl`. If those runs are still expected to carry a committed transcript, the lifecycle has a real gap; if not, [docs/run-logs.md](docs/run-logs.md) / [docs/run-logs-required-files.tsv](docs/run-logs-required-files.tsv) should spell out that exclusion so the “always” manifest does not contradict design-only behavior.
- **Suggested revision**: Address the concern above.


### FINDING_12: **[correctness]** [skills/implement/SKILL.md:1687-1687](skills/implement/SKILL.md) — The Step 7a prose requires logging `capture-session-transcript.sh` failures via `pre-bump-log-flush-<tool>.log` + `append-tool-failure.sh` and forbids a bare `|| true`, but the exemplar block still ends the capture invocation with `|| true` ([skills/implement/SKILL.md:1675-1681](skills/implement/SKILL.md)) and does not show any capture/append pattern. Separately, the same sentence conditions on “non-zero `capture-session-transcript.sh`”, yet the wrapper’s terminal paths use `emit_status` and `exit 0` ([scripts/capture-session-transcript.sh:71-77](scripts/capture-session-transcript.sh), [scripts/capture-session-transcript.sh:165-173](scripts/capture-session-transcript.sh)), so exit-code–based orchestration cannot satisfy that contract anyway. Suggested fix: align prose with actual behavior (status line / Warnings appended inside the script, exit 0) and either update the exemplar to match the real logging contract or drop the over-strong “non-zero” wording.
- **Reviewer**: dyn-lifecycle-ordering-output.txt
- **Concern**: - **[correctness]** [skills/implement/SKILL.md:1687-1687](skills/implement/SKILL.md) — The Step 7a prose requires logging `capture-session-transcript.sh` failures via `pre-bump-log-flush-<tool>.log` + `append-tool-failure.sh` and forbids a bare `|| true`, but the exemplar block still ends the capture invocation with `|| true` ([skills/implement/SKILL.md:1675-1681](skills/implement/SKILL.md)) and does not show any capture/append pattern. Separately, the same sentence conditions on “non-zero `capture-session-transcript.sh`”, yet the wrapper’s terminal paths use `emit_status` and `exit 0` ([scripts/capture-session-transcript.sh:71-77](scripts/capture-session-transcript.sh), [scripts/capture-session-transcript.sh:165-173](scripts/capture-session-transcript.sh)), so exit-code–based orchestration cannot satisfy that contract anyway. Suggested fix: align prose with actual behavior (status line / Warnings appended inside the script, exit 0) and either update the exemplar to match the real logging contract or drop the over-strong “non-zero” wording.
- **Suggested revision**: Address the concern above.


### FINDING_18: architecture: skills/implement/SKILL.md:1675-1687 vs scripts/capture-session-transcript.sh:71-174
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] SKILL implies exit-code-driven append-tool-failure for capture; script always exits 0 Tool Failures path never triggers on transcript status via $? Update prose or exit-code contract
- **Suggested revision**: Address the concern above.


### FINDING_19: code-quality: scripts/test-verify-run-log-completeness.sh:94-107
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Hardcoded required file list duplicates `docs/run-logs-required-files.tsv`. Manifest and harness drift independently; tests can pass while manifest semantics rot. Parse TSV in the harness or assert list parity with manifest.
- **Suggested revision**: Address the concern above.


### FINDING_2: **Important** `correctness` `skills/implement/SKILL.md:1650`  
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` `skills/implement/SKILL.md:1650`      `execution-issues.md` is flushed before `capture-session-transcript.sh` runs, but the capture status warning is appended later by `scripts/capture-session-transcript.sh:71-77`. In a no-retry run where transcript capture fails, the merged run log can miss both `session-transcript.jsonl` and the `SESSION_TRANSCRIPT_STATUS=...` warning explaining why; `scripts/refresh-run-logs.sh:89-94` also suppresses stdout and omits `--execution-issues-log`, so retry captures are invisible too. Suggested fix: make transcript capture write its status before the pre-bump `execution-issues` flush, or run a second `flush-execution-issues.sh` before the final pre-bump commit; also pass `--execution-issues-log "$issue_log"` from `refresh-run-logs.sh`. Affected: `skills/implement/SKILL.md:1650-1683`, `scripts/capture-session-transcript.sh:71-77`, `scripts/refresh-run-logs.sh:89-94`.
- **Suggested revision**: Address the concern above.


### FINDING_20: code-quality: scripts/verify-run-log-completeness.md:27-28
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Contract lists non-existent CI workflow `.github/workflows/verify-run-logs.yml`. Operators or contributors believe PRs are gated by a verify-run-logs workflow; no such workflow exists in `.github/workflows`. Add the workflow, or edit Callers to name the real CI job/file.
- **Suggested revision**: Address the concern above.


### FINDING_21: code-quality: skills/implement/SKILL.md:1675-1688
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Prose requires `append-tool-failure` capture for non-zero `capture-session-transcript.sh`; fenced Step 7a block still uses bare `|| true` for that call. Orchestrator following prose vs snippet gets conflicting instructions; strengthened sentence is false for the shown bash. Align snippet with prose or narrow prose to match actual orchestration.
- **Suggested revision**: Address the concern above.


### FINDING_22: correctness: docs/run-logs-required-files.tsv:9-12
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Manifest requires run-statistics.json; canonical batch is .md Verify script false MISSING on every real run dir with run-statistics.md Use run-statistics.md and align harness + extension column
- **Suggested revision**: Address the concern above.


### FINDING_25: correctness: skills/implement/SKILL.md:1650-1681
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] `flush-execution-issues.sh` runs before transcript capture; capture appends to `execution-issues.md` with no second flush before `larch-log.sh commit`. Pre-bump commit's `execution-issues.ndjson` can omit transcript-status warnings that exist only in `.md` until a later flush. Re-flush after capture before commit, or document NDJSON lag.
- **Suggested revision**: Address the concern above.


### FINDING_26: correctness: skills/implement/SKILL.md:1687
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Step 7a prose requires append-tool-failure on non-zero capture-session-transcript.sh but that script always exits 0 via emit_status Orchestrator using $? after capture never sees failure even for SESSION_TRANSCRIPT_STATUS=commit-failed Document status-on-stdout contract or adopt non-zero exits for failure statuses
- **Suggested revision**: Address the concern above.


### FINDING_27: risk-integration: scripts/refresh-run-logs.sh:84-94
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Transcript re-capture discards all output and omits --execution-issues-log; warnings are not written to execution-issues.md. On CI retry, capture failures are silent in the audit trail and may leave a stale session-transcript.jsonl without a Warnings row. Pass --execution-issues-log "$issue_log" and preserve or log diagnostics instead of redirecting all stderr to /dev/null.
- **Suggested revision**: Address the concern above.


### FINDING_28: risk-integration: scripts/refresh-run-logs.sh:84-94
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] `capture-session-transcript.sh` called without `--execution-issues-log` despite `issue_log` in scope; diverges from implementation plan. On CI retry refresh, transcript status warnings are not appended to `execution-issues.md` because `EXECUTION_ISSUES_LOG` is unset. Pass `--execution-issues-log "$issue_log"` (match Step 7a / plan).
- **Suggested revision**: Address the concern above.


### FINDING_30: risk-integration: scripts/verify-run-log-completeness.md:27-28
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Documents CI workflow verify-run-log-completeness.yml that is not present in the repo. Reviewers assume PR CI enforces run-log completeness; missing files could merge without automated detection. Remove the CI bullet or add the referenced workflow.
- **Suggested revision**: Address the concern above.


### FINDING_4: **[architecture]** [`docs/run-logs-required-files.tsv`](docs/run-logs-required-files.tsv) and [`scripts/verify-run-log-completeness.md:31-35`](scripts/verify-run-log-completeness.md): **Edit-in-sync** names `docs/run-logs.md` and the TSV but not [`scripts/larch-log-batches.sh`](scripts/larch-log-batches.sh), which is the actual slug/extension SSOT; combined with the wrong `run-statistics` path, the TSV is not a reliable single source of truth. Suggested fix: state explicitly that new or renamed batches must match `larch-log-batches.sh` (and optionally add a small guard or doc cross-link); keep the TSV’s `batch_slug` / `extension` columns consistent with that file.
- **Reviewer**: dyn-manifest-completeness-output.txt
- **Concern**: - **[architecture]** [`docs/run-logs-required-files.tsv`](docs/run-logs-required-files.tsv) and [`scripts/verify-run-log-completeness.md:31-35`](scripts/verify-run-log-completeness.md): **Edit-in-sync** names `docs/run-logs.md` and the TSV but not [`scripts/larch-log-batches.sh`](scripts/larch-log-batches.sh), which is the actual slug/extension SSOT; combined with the wrong `run-statistics` path, the TSV is not a reliable single source of truth. Suggested fix: state explicitly that new or renamed batches must match `larch-log-batches.sh` (and optionally add a small guard or doc cross-link); keep the TSV’s `batch_slug` / `extension` columns consistent with that file.
- **Suggested revision**: Address the concern above.


### FINDING_5: **[architecture]** [`scripts/test-verify-run-log-completeness.sh:34-47`](scripts/test-verify-run-log-completeness.sh): The harness hardcodes `REQUIRED_FILES` in parallel to the TSV instead of deriving expectations from [`docs/run-logs-required-files.tsv`](docs/run-logs-required-files.tsv), so the test can stay green while the manifest drifts from repo reality (as with `run-statistics`). Suggested fix: generate the list from the same manifest the verifier reads, or assert TSV rows match `larch-log-batches.sh` in a dedicated test.
- **Reviewer**: dyn-manifest-completeness-output.txt
- **Concern**: - **[architecture]** [`scripts/test-verify-run-log-completeness.sh:34-47`](scripts/test-verify-run-log-completeness.sh): The harness hardcodes `REQUIRED_FILES` in parallel to the TSV instead of deriving expectations from [`docs/run-logs-required-files.tsv`](docs/run-logs-required-files.tsv), so the test can stay green while the manifest drifts from repo reality (as with `run-statistics`). Suggested fix: generate the list from the same manifest the verifier reads, or assert TSV rows match `larch-log-batches.sh` in a dedicated test.
- **Suggested revision**: Address the concern above.


### FINDING_7: **[architecture]** [`scripts/verify-run-log-completeness.md:27-29`](scripts/verify-run-log-completeness.md): The **Callers** section lists `.github/workflows/verify-run-logs.yml`, but that workflow is **not** added in this branch and does not exist under [`.github/workflows/`](.github/workflows/) (only `ci.yaml`, `release-tag.yaml`, etc.). The manifest checker is therefore documented as CI-enforced when it is only wired via [`Makefile`](Makefile) (`test-verify-run-log-completeness` in `test-harnesses-7`). Suggested fix: either add the workflow and hook it from `ci.yaml`/a new file, or remove/reword the Callers bullet so docs match enforcement.
- **Reviewer**: dyn-manifest-completeness-output.txt
- **Concern**: - **[architecture]** [`scripts/verify-run-log-completeness.md:27-29`](scripts/verify-run-log-completeness.md): The **Callers** section lists `.github/workflows/verify-run-logs.yml`, but that workflow is **not** added in this branch and does not exist under [`.github/workflows/`](.github/workflows/) (only `ci.yaml`, `release-tag.yaml`, etc.). The manifest checker is therefore documented as CI-enforced when it is only wired via [`Makefile`](Makefile) (`test-verify-run-log-completeness` in `test-harnesses-7`). Suggested fix: either add the workflow and hook it from `ci.yaml`/a new file, or remove/reword the Callers bullet so docs match enforcement.
- **Suggested revision**: Address the concern above.


### FINDING_8: **[correctness]** [`docs/run-logs-required-files.tsv:11`](docs/run-logs-required-files.tsv): The manifest requires `run-statistics.json` with `extension=json`, but the canonical batch table defines `run-statistics` as `.md` ([`scripts/larch-log-batches.sh:27`](scripts/larch-log-batches.sh)), [`docs/run-logs.md`](docs/run-logs.md) documents `run-statistics.md`, and committed runs use `run-statistics.md` only. [`scripts/verify-run-log-completeness.sh`](scripts/verify-run-log-completeness.sh) tests `-f` for that path, so any real `larch-logs/implement/<RUN_ID>/` tree will be reported **MISSING=run-statistics.json** even when the run log is complete. Suggested fix: change the manifest row (and the `extension` column) to `run-statistics.md` / `md`, aligned with `larch-log-batches.sh` and `run-logs.md`.
- **Reviewer**: dyn-manifest-completeness-output.txt
- **Concern**: - **[correctness]** [`docs/run-logs-required-files.tsv:11`](docs/run-logs-required-files.tsv): The manifest requires `run-statistics.json` with `extension=json`, but the canonical batch table defines `run-statistics` as `.md` ([`scripts/larch-log-batches.sh:27`](scripts/larch-log-batches.sh)), [`docs/run-logs.md`](docs/run-logs.md) documents `run-statistics.md`, and committed runs use `run-statistics.md` only. [`scripts/verify-run-log-completeness.sh`](scripts/verify-run-log-completeness.sh) tests `-f` for that path, so any real `larch-logs/implement/<RUN_ID>/` tree will be reported **MISSING=run-statistics.json** even when the run log is complete. Suggested fix: change the manifest row (and the `extension` column) to `run-statistics.md` / `md`, aligned with `larch-log-batches.sh` and `run-logs.md`.
- **Suggested revision**: Address the concern above.


### FINDING_9: **[correctness]** [scripts/capture-session-transcript.sh:165-170](scripts/capture-session-transcript.sh) — `larch-log.sh commit` stderr is redirected to `/dev/null`, so a `commit-failed` status conflates policy refusals (default branch, post-merge sentinel — see [scripts/larch-log.sh:442-449](scripts/larch-log.sh)) with a genuine `git commit` failure; the emitted message always says “git commit failed”. Suggested fix: preserve or map `larch-log.sh`’s stderr into the warning text, or branch on known refusal strings before collapsing to `commit-failed`.
- **Reviewer**: dyn-lifecycle-ordering-output.txt
- **Concern**: - **[correctness]** [scripts/capture-session-transcript.sh:165-170](scripts/capture-session-transcript.sh) — `larch-log.sh commit` stderr is redirected to `/dev/null`, so a `commit-failed` status conflates policy refusals (default branch, post-merge sentinel — see [scripts/larch-log.sh:442-449](scripts/larch-log.sh)) with a genuine `git commit` failure; the emitted message always says “git commit failed”. Suggested fix: preserve or map `larch-log.sh`’s stderr into the warning text, or branch on known refusal strings before collapsing to `commit-failed`.
- **Suggested revision**: Address the concern above.


