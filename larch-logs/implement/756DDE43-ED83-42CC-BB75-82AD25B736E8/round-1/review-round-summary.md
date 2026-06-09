# Review Round 1

- Mode: `diff`
- 17 accepted, 4 rejected (2 neutral)

## Accepted Findings

### FINDING_1: CI failed-log collection and failure-log artifacts expose unredacted secrets
- **Reviewer(s)**: cursor-specialist-security-output.txt, codex-specialist-security-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `collect_failed_logs` and `_write_failure_log` no longer guarantee redacted, private failure-log output before logs are written to `.redacted.log` files or passed to downstream agents. This can leak tokens from failed CI output into artifacts, prompts, or vendor logs; the misleading `.redacted.log` suffix and missing `0o600` permissions compound the risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From codex-specialist-security-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_10: `push checkpoint-probe` omits `REBASE_OUTCOME`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-contract-parity-output.txt
- **Severity**: important
- **Concern**: The checkpoint probe wrapper does not emit the legacy `REBASE_OUTCOME=ok|skipped|conflict|failed` envelope on all paths. `/implement` rebase macros branch on that KV and can miss conflict/stall handling after cutover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.
  - From dyn-contract-parity-output.txt: Address the concern above.


### FINDING_11: `ci wait` wrapper contract diverges from `ci-wait.sh`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The Python wait wrapper misses legacy fields/order, `.done` sentinel semantics, stale-output cleanup/trap behavior, and exit-0 handling for valid `ACTION=bail` decisions. File-mode consumers may hang or treat normal bail decisions as hard failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_12: `create_pr_parity` diverges on clean-tree, push, existing-PR, and title behavior
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-contract-parity-output.txt
- **Severity**: important
- **Concern**: The Python PR creation path can skip the clean-worktree guard, skip pushing local commits for existing PRs, use the caller-provided title instead of the GitHub PR title, and map push failures differently from the shell helper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-contract-parity-output.txt: Address the concern above.


### FINDING_16: `ci status` fallback parsing loses shell parity
- **Reviewer(s)**: codex-specialist-correctness-output.txt, dyn-contract-parity-output.txt
- **Severity**: important
- **Concern**: Text fallback behavior differs from `ci-status.sh`: failed text checks may not populate `FAILED_RUN_ID`, empty/non-array JSON can skip the text parser, and empty-check grace can report `NO_CHECKS` despite usable text output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From dyn-contract-parity-output.txt: Address the concern above.


### FINDING_17: `ci behind-count` emits a bare integer instead of `BEHIND_COUNT=`
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Existing parsers expect `BEHIND_COUNT=<N>`, but the Python CLI prints only the integer, causing cut-over callers to parse an empty count.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_18: `git phantom-probe` CLI shape drops legacy `--step` contract
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The Python phantom-probe CLI expects positional arguments instead of the shell helper’s `--step <token>` shape, so mechanical call-site cutover can fail before reaching the phantom warning logic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_19: `ci decide` does not accept legacy flag names
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The Python `ci decide` CLI renamed `--status`/`--behind` to different flags. Mechanical bash-to-Python cutovers using the old argv will usage-exit or make the wrong decision.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_2: Failed-job output lacks legacy sanitization
- **Reviewer(s)**: cursor-specialist-security-output.txt, codex-specialist-security-output.txt
- **Severity**: important
- **Concern**: The Python `ci failed-jobs` path emits job names and diagnostics without the retired shell sanitizers, so control bytes, newlines, or `KEY=value`-like text can corrupt structured KV/JSON/stderr output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From codex-specialist-security-output.txt: Address the concern above.


### FINDING_22: Plan-required CLI contract tests are absent for high-risk wire formats
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Required tests for `ci wait` and checkpoint-probe `REBASE_OUTCOME` behavior are missing, leaving the highest-risk cutover contracts without automated regression coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_25: `ci status` usage errors return non-zero instead of shell-style error KV block
- **Reviewer(s)**: dyn-contract-parity-output.txt
- **Severity**: important
- **Concern**: The Python `ci status` path returns exit 1 on argv/parse errors, while the shell helper exits 0 and communicates the failure through a full `CI_STATUS=error` KV block.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-contract-parity-output.txt: Address the concern above.


### FINDING_28: Migration lint treats ship-pr diagnostic labels as live script invocations
- **Reviewer(s)**: dyn-migration-gate-output.txt
- **Severity**: important
- **Concern**: `_ship_pr_live_ref` matches bare `basename.sh` tokens in `scripts/ship-pr.sh`, so diagnostic prose such as `record_failure` labels can be flagged as retained live callers after actual `$SCRIPT_DIR/...` invocations are removed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-migration-gate-output.txt: Address the concern above.


### FINDING_3: Phantom probe calls retained scripts with incompatible contracts
- **Reviewer(s)**: cursor-specialist-security-output.txt, codex-specialist-security-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `python/phantom.py` bypasses or mis-invokes the retained phantom helpers, including unsupported `check-mid-run-dirty-tree.sh` arguments and invalid `append-execution-issue.sh` flags. Dirty-tree probes can report `unknown`/zero phantom counts and never append phantom warnings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From codex-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_4: CI-fix exhaustion detail embeds raw failed-log text
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `_fix_exhausted_detail` composes issue/chat detail from `logs.text` without redacting it, despite comments implying upstream redaction. A failed-run tail containing secrets can be posted directly to tracking surfaces.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_7: `git.add` omits `--` for a single path
- **Reviewer(s)**: codex-specialist-security-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: For exactly one supplied path, `git.add` builds a command without the `--` separator. Dash-prefixed filenames can be interpreted as git options, potentially staging the wrong files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-security-output.txt: Address the concern above.
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_8: `pr create-branch` does not preserve shell contract
- **Reviewer(s)**: codex-specialist-security-output.txt, cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, dyn-contract-parity-output.txt
- **Severity**: important
- **Concern**: The Python create-branch path diverges from `create-branch.sh`: check mode requires the wrong inputs and emits different KVs, the user prefix is hard-coded instead of derived, existing branches can be reset via `checkout -B`, and exit codes differ.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-contract-parity-output.txt: Address the concern above.


### FINDING_9: `git commit --only` is emitted as `--only ""`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt, dyn-contract-parity-output.txt
- **Severity**: important
- **Concern**: The Python commit wrapper models `--only` as an option with an empty operand instead of a bare flag, which can fail or change commit scope compared with the shell helper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.
  - From dyn-contract-parity-output.txt: Address the concern above.


