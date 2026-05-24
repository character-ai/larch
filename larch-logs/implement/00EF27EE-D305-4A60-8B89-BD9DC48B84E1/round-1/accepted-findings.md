### FINDING_1: Quoted-delimiter heredocs drop the rest of the fenced block without surfacing failure
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: In `parse-plan-commands.awk`, the double-quoted heredoc branch advances the physical-line index to EOF (or otherwise fast-forwards), so lines after the heredoc inside the same fenced block are not parsed or emitted. Tier 2 can report success while the plan still contains later commands (including bad ones); TSV can omit later invocations, giving a false sense of safety.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

---


### FINDING_10: Tier 3 dry-run inherits the full parent environment while logging stdout/stderr
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Tier 3 env invocation inherits the full parent environment while capturing stdout/stderr into validator logs; a registry-listed dry-run script could read inherited secrets and echo them into logs/failure blobs, widening exposure beyond composed-plan Tier-3-disable mitigations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Use env -i with an explicit minimal allowlist of variables required for dry-run.

---


### FINDING_11: Flag presence grep can treat `--$flag` as a regex pattern (metachar fragility)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `grep` uses the flag string as a regex pattern; unusual flag names with regex metacharacters can make the Tier-2 flag probe unreliable vs a deterministic rule.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Use grep -Fq or escape metacharacters for literal --flag matching.

---


### FINDING_12: `SECURITY.md` understates subprocess / environment trust boundaries for Tier 2 and Tier 3
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: The Tier 3 paragraph understates inherited-environment surface and does not adequately document Tier 2 probe/exec containment expectations, so operators may assume stricter isolation than bash provides.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Update SECURITY.md to document full inherited env unless env -i is adopted; document Tier 2 subprocess containment expectations.

---


### FINDING_13: Tier 2 flag validation can accept strict-prefix matches against help text (`--file` vs `--files`)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Flag checks match substrings against full help text, so a plan flag that is a strict prefix of a documented flag can be treated as valid, missing impossible commands.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

---


### FINDING_14: Command aggregation key collapses multiple physical lines that invoke the same script
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The aggregation key omits physical line index within a fence, so multiple lines in one ```bash block calling the same script can collapse into one merged argv for Tier 2/Tier 3; dry-run may not match the intended single plan line.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

---


### FINDING_15: Golden parser TSV fixtures conflict with normative `note` semantics for invocation rows
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Parser golden rows place `c0` in `note` for invocation rows while the normative schema calls for empty `note` on invocations, so downstream consumers/harnesses enforcing the written schema can reject real output until docs/code/fixtures align.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---


### FINDING_16: Tier 3 dry-run does not pin working directory to repo root
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Tier 3 dry-run does not pin process `cwd` to repo root despite plan-style expectations; repo-relative operands can validate differently from runtime shell behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---


### FINDING_17: Non-zero `--help` exit is treated as “no help,” potentially skipping flag validation
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Any non-zero `--help` exit is treated as no-help, which may omit allowance for conventional non-zero usage exits; scripts that exit non-zero while printing usage could silently skip flag validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---


### FINDING_18: `design-driver.md` resume narrative omits `VALIDATE_PLAN_COMMANDS` alongside `EMIT_PLAN`
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Resume documentation still singles out only `EMIT_PLAN` for no-sentinel resume quirks, which can mislead readers about resume behavior for `VALIDATE_PLAN_COMMANDS`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---


### FINDING_2: Sibling markdown contracts under-document supported shapes (including heredocs) versus plan-level expectations
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `parse-plan-commands.md` (and related sibling `.md` contracts) do not adequately document heredoc rules, awk split behavior, and the full normative schema/grammar/Tier rules promised by the plan. Operators cannot predict parser/validator behavior or rely on script-local docs as authoritative.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---


### FINDING_4: Tier 2 help probe mixes stdout and stderr for emptiness and flag grep vs stdout-only “no help” semantics
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `validate-plan-commands.sh` merges stdout+stderr for help detection and flag greps. Scripts that print usage only on stderr (or noisy stderr) can be misclassified as `help_ok`, skipping `SKIPPED_FLAG_CHECK` and/or validating flags against stderr noise, diverging from a stdout-only no-help rule and making behavior nondeterministic relative to documentation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Detect non-empty help from stdout only; document if stderr is intentionally included for grep

---


### FINDING_6: Tests never exercise Tier-3-off / composed inference for a real `composed-plan.md` basename
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `mktemp` templates yield `composed-plan.md.<suffix>`, but `validate-plan.sh` only treats the exact basename `composed-plan.md` as composed, so Tier-3 suppression for composed plans is not exercised in CI; registry-driven Tier 3 could run when the source should be composed-safe.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Use a directory + exact composed-plan.md basename (or assert source-kind in log)

---


### FINDING_7: Parse harness has too few golden fixtures relative to accepted grammar surface
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-parse-plan-commands.sh` relies on only a small set of golden fixtures; changes to continuation/env/quote/subshell/heredoc handling can regress without failing the harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

---


### FINDING_8: Validator harness does not cover many acceptance-listed branches and scenarios
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `test-validate-plan-commands.sh` stops short of several plan-listed cases (missing script, no-help skip, allow-listed flags, unsafe-token paths, Tier-3 dry-run failure, cwd pinning, composed vs plan Tier-3 behavior, injection-style probes, etc.), so regressions in critical branches can ship despite an acceptance bar.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---


### FINDING_9: Path `..` / non-canonical script paths break Tier-2 containment assumptions (parser + validator)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Tier-2 `is_repo_script` prefix matching can accept `..` segments and probe-help execution can resolve outside the intended repo script corpus; the parser can emit `script_path` without rejecting/stripping `..` after normalization, enabling prefix matches that traverse outside `REPO_ROOT` when executed or probed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Reject .. and non-canonical paths; realpath and require prefix under explicit allowed roots before any exec.
  - From cursor-specialist-security-output.txt: Emit parse_note or reject .. in script tokens before emitting invocation rows; pair with validator-side containment.

---


